"""Capture the current extended .pkt without modifying topology/configuration.

Keeps v2 and previous extension evidence immutable. 52 endpoint sources each
exercise 62 destination IPs: 3,224 actual CLI ping commands.
"""
import argparse
import hashlib
import ipaddress
import json
import re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

from project_api import js, BASE
import scale50 as campus
import n4_runner as lab
import extend_ospf_pat as extension
from build_snapshot import raw_inventory

RUN_ID='WEBSITE-V3-20261102'
RUN=BASE/'evidence'/RUN_ID
RUN.mkdir(exist_ok=True)
FILE=BASE/'Secure_Campus_Network_Submission.pkt'
IOS=campus.IOS+['R2-EXTERNAL']
HOSTS=campus.HOSTS+['SRV-EXTERNAL']
STAMP=lambda:datetime.now(timezone(timedelta(hours=5,minutes=30))).isoformat(timespec='seconds')
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def ident(name):
    return {'R1-CAMPUS':'r1','R2-EXTERNAL':'r2','SRV-CAMPUS':'server0','SRV-EXTERNAL':'server1','SW1-CORE':'sw1','SW2-ACCESS':'sw2','SW3-FACULTY':'sw3','SW4-STUDENTS':'sw4','PC8-MGMT':'pc8','PC9-ADMIN':'pc9'}.get(name,name.lower())


def write(name,value):
    extension.RUN=RUN
    extension.write(name,value)


def setup():
    lab.RUN=RUN;lab.RUN_ID=RUN_ID;lab.ALL_HOSTS=HOSTS;lab.CLIENTS=campus.HOSTS[:-1]
    campus.RUN=RUN
    lab.initialize()


def hosts():
    lease=campus.leases()
    result=[dict(name=n,id=ident(n),ip=lease[n]['ip'],vlan=v) for v,names in campus.GROUPS.items() for n in names]
    result += [dict(name='SRV-CAMPUS',id='server0',ip=campus.SERVER,vlan=40),dict(name='SRV-EXTERNAL',id='server1',ip='203.0.113.10',vlan=None)]
    return result,lease


def targets_extra():
    return [dict(name=n,id=ident(n),ip=f'192.168.10.{99+i}',vlan=10) for i,n in enumerate(campus.IOS[1:])]+[dict(name='R1-CAMPUS',id='r1',ip=campus.NETS[v][3],vlan=v) for v in (10,20,30,40)]+[dict(name='R1-CAMPUS',id='r1',ip='198.51.100.1',vlan=None),dict(name='R2-EXTERNAL',id='r2',ip='198.51.100.2',vlan=None),dict(name='R2-EXTERNAL',id='r2',ip='203.0.113.1',vlan=None)]


def decision(src,dst):
    if src['id']=='server1':
        if dst['id']=='r2':return True,None,None,'Direct external delivery or routing to R2 local interface'
        if dst['ip']=='198.51.100.1':return False,'r1','WAN-IN','WAN-IN denies unsolicited ICMP Echo to the PAT outside address'
        return False,'r2',None,'R2 has no route to the private campus destination; this is a routing failure, not an ACL match'
    vlan=src['vlan']
    if vlan==dst['vlan'] or (vlan==10 and dst['vlan'] in (20,30)) or (vlan in (10,20,30) and dst['id']=='server0'):
        return True,None,None,'Local switching, campus service access, or Administration diagnostic permission'
    if dst['id']=='server1' and vlan in (10,20,30):
        return True,None,None,'Client ACL permits external Echo; OSPF supplies the route and PAT enables return traffic'
    return False,'r1',campus.ACLS[vlan],'Source VLAN ingress ACL denies this newly initiated request'


def preflight():
    setup()
    assert Path(campus.inventory()['file']).resolve()==FILE.resolve()
    inventory=raw_inventory();assert len(inventory['nodes'])==58 and len(inventory['links'])==57
    hs,lease=hosts();assert len({h['ip'] for h in hs})==52
    assert 'FULL' in lab.show('R1-CAMPUS','show ip ospf neighbor')
    write('inventory.json',inventory);write('leases.json',lease)
    configs={n:lab.show(n,'show running-config') for n in IOS}
    write('ios-configs.json',configs)
    write('routing.json',{n:{cmd:lab.show(n,cmd) for cmd in ['show ip route','show ip ospf neighbor','show ip protocols']} for n in ['R1-CAMPUS','R2-EXTERNAL']})
    write('run.json',dict(runId=RUN_ID,startedAt=STAMP(),submissionFile=FILE.name,submissionSha256=digest(FILE),method='Actual Packet Tracer command prompts, read-only configuration capture, built-in realtime fast-forward',counterScope='capture-batch'))
    print('Preflight: current saved file, 58 devices, 57 links, 52 unique endpoint addresses and FULL OSPF verified',flush=True)


def matrix():
    setup()
    meta=json.loads((RUN/'run.json').read_text());sha=meta['submissionSha256'];assert digest(FILE)==sha
    hs,lease=hosts()
    assert lease==json.loads((RUN/'leases.json').read_text())
    before_configs={n:lab.show(n,'show running-config') for n in IOS}
    records=[]
    jobs_all=[[(src,hs[(i+offset)%len(hs)]) for i,src in enumerate(hs)] for offset in range(1,len(hs))]
    jobs_all += [[(src,dst) for src in hs] for dst in targets_extra()]
    assert len(jobs_all)==62
    for bi,jobs in enumerate(jobs_all,1):
        before=lab.counters();pending=list(jobs);outputs={};attempts={}
        for attempt in range(3):
            js('for(var j of '+json.dumps([(s['name'],d['ip']) for s,d in pending])+'){n4Collectors[j[0]].text="";ipc.network().getDevice(j[0]).getCommandPrompt().enterCommand("ping "+j[1]);}return true;')
            for _ in range(12):
                js('ipc.appWindow().getRealtimeToolbar().fastForwardTime();return true;');time.sleep(.08)
                data=js('var out={};for(var n of '+json.dumps([s['name'] for s,d in pending])+')out[n]=n4Collectors[n].text;return out;')
                if all('Sent = 4' in text for text in data.values()):break
            retry=[]
            for src,dst in pending:
                text=data[src['name']];key=src['id']+':'+dst['ip'];attempts.setdefault(key,[]).append(text)
                m=re.search(r'Sent = (\d+), Received = (\d+)',text)
                allowed,*_=decision(src,dst)
                good=bool(m and int(m[1])==4 and int(m[2])==(4 if allowed else 0))
                outputs[key]=dict(output=text,sent=int(m[1]) if m else 0,received=int(m[2]) if m else 0,passed=good)
                if not good:retry.append((src,dst))
            pending=retry
            if not pending:break
        after=lab.counters();delta=lab.delta(before,after);batch=[]
        for src,dst in jobs:
            key=src['id']+':'+dst['ip'];allowed,block,acl,reason=decision(src,dst);row=outputs[key]
            if not allowed and acl:
                counters={k:v for k,v in delta.items() if k.startswith(acl+' |') and ' deny ' in k}
                row['passed']=row['passed'] and any(v>=4 for v in counters.values())
            else:
                counters={k:v for k,v in delta.items() if k.startswith(campus.ACLS.get(src['vlan'],'WAN-IN')+' |') and ' permit ' in k}
            record=dict(id='PING3-'+str(len(records)+1),testId='P03',sourceDeviceId=src['id'],sourceIp=src['ip'],destinationDeviceId=dst['id'],destinationIp=dst['ip'],expected='allow' if allowed else 'deny',blockingDeviceId=block,enforcementAcl=acl,decisionReason=reason,counterDelta=counters,counterScope='capture-batch',evidenceRef=f'evidence/{RUN_ID}/batch-{bi:02d}.json',**row)
            batch.append(dict(**record,attempts=attempts[key]));records.append(record)
        write(f'batch-{bi:02d}.json',dict(runId=RUN_ID,submissionSha256=sha,observedAt=STAMP(),counterScope='capture-batch',aclBefore=before,aclAfter=after,records=batch))
        mismatches=[r for r in records if not r['passed']]
        print(f'Batch {bi}/62: {len(records)}/3224 commands; mismatches {len(mismatches)}',flush=True)
    assert len(records)==3224
    unchanged=digest(FILE)==sha
    configs_unchanged=all(lab.show(n,'show running-config')==before_configs[n] for n in IOS)
    assert unchanged and configs_unchanged and campus.leases()==lease
    meta.update(completedAt=STAMP(),cases=len(records),passed=sum(r['passed'] for r in records),mismatches=[r['id'] for r in records if not r['passed']],submissionUnchanged=unchanged,iosConfigurationsUnchanged=configs_unchanged,perSource=62)
    write('ping-run.json',meta)
    evidence=[dict(path=p.relative_to(BASE).as_posix(),sha256=digest(p)) for p in sorted(RUN.glob('batch-*.json'))]+[dict(path=(RUN/'ping-run.json').relative_to(BASE).as_posix(),sha256=digest(RUN/'ping-run.json'))]
    payload=dict(schemaVersion=2,**meta,addressContext={h['id']:h['ip'] for h in hs},records=records,evidence=evidence)
    (BASE/'data/ping-matrix.v3.json').write_text(json.dumps(payload,indent=2),encoding='utf-8')
    assert not meta['mismatches'],meta['mismatches']
    print('Complete current-network matrix:',meta['passed'],'/',meta['cases'],flush=True)


def services():
    # Reuse the proven service checks with a fresh evidence directory.
    extension.RUN=RUN;extension.campus.RUN=RUN
    extension.regression('current')
    extension.verify()
    extension.persistence()
    write('completed.json',dict(completedAt=STAMP(),submissionSha256=digest(FILE)))


def reconcile():
    setup()
    path=BASE/'data/ping-matrix.v3.json';payload=json.loads(path.read_text())
    assert digest(FILE)==payload['submissionSha256']
    for record in payload['records']:
        if record['passed']:continue
        name=next(n for n in HOSTS if ident(n)==record['sourceDeviceId'])
        before=lab.counters();lab.start(name,'ping '+record['destinationIp'])
        for _ in range(12):
            js('ipc.appWindow().getRealtimeToolbar().fastForwardTime();return true;');time.sleep(.1)
            output=lab.output(name)
            if 'Sent = 4' in output:break
        changes=lab.delta(before,lab.counters())
        acl=record['enforcementAcl']
        counters={k:v for k,v in changes.items() if acl and k.startswith(acl+' |') and ' deny ' in k}
        m=re.search(r'Sent = (\d+), Received = (\d+)',output)
        passed=bool(m and int(m[1])==4 and int(m[2])==(4 if record['expected']=='allow' else 0))
        if record['expected']=='deny' and acl:passed=passed and any(v>=4 for v in counters.values())
        ref='evidence/'+RUN_ID+'/retry-'+record['id']+'.json'
        record.update(output=output,sent=int(m[1]) if m else 0,received=int(m[2]) if m else 0,counterDelta=counters,counterScope='command',passed=passed,evidenceRef=ref)
        write('retry-'+record['id']+'.json',dict(runId=RUN_ID,submissionSha256=payload['submissionSha256'],observedAt=STAMP(),records=[record]))
        print('Isolated ACL recheck',record['id'],passed,flush=True)
    payload.update(passed=sum(r['passed'] for r in payload['records']),mismatches=[r['id'] for r in payload['records'] if not r['passed']],completedAt=STAMP())
    meta={k:v for k,v in payload.items() if k not in ['schemaVersion','addressContext','records','evidence']};write('ping-run.json',meta)
    paths=list(sorted(RUN.glob('batch-*.json')))+list(sorted(RUN.glob('retry-*.json')))+[RUN/'ping-run.json']
    payload['evidence']=[dict(path=p.relative_to(BASE).as_posix(),sha256=digest(p)) for p in paths]
    path.write_text(json.dumps(payload,indent=2),encoding='utf-8')
    assert not payload['mismatches'] and digest(FILE)==payload['submissionSha256']


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['preflight','matrix','services','reconcile']);a=p.parse_args();globals()[a.stage]()
