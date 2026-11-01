"""Capture the full 50-PC campus ICMP matrix without saving/reconfiguring IOS."""
import hashlib
import json
import re
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta
import scale50 as s
import n4_runner as lab
from build_snapshot import raw_inventory

RUN_ID='PING-20261031'
RUN=s.BASE/'evidence'/RUN_ID
RUN.mkdir(exist_ok=True)
lab.ALL_HOSTS=s.HOSTS
lab.RUN=RUN
lab.RUN_ID=RUN_ID
STAMP=lambda:datetime.now(timezone(timedelta(hours=5,minutes=30))).isoformat(timespec='seconds')
def write(name,value):(RUN/name).write_text(json.dumps(value,indent=2),encoding='utf-8')
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def ident(name):return {'R1-CAMPUS':'r1','SW1-CORE':'sw1','SW2-ACCESS':'sw2','SW3-FACULTY':'sw3','SW4-STUDENTS':'sw4','SRV-CAMPUS':'server0','PC8-MGMT':'pc8','PC9-ADMIN':'pc9'}.get(name,name.lower())
def expected(src,dst):return src['vlan']==dst['vlan'] or (src['vlan']==10 and (dst['vlan'] in (20,30) or dst['id']=='server0')) or (src['vlan'] in (20,30) and dst['id']=='server0')

def reconcile():
    path=s.BASE/'data/ping-matrix.v2.json';matrix=json.loads(path.read_text())
    assert digest(s.FILE)==matrix['submissionSha256']
    lab.initialize()
    for record in matrix['records']:
        if record['passed']:continue
        name=next(n for n in s.HOSTS if ident(n)==record['sourceDeviceId'])
        before=lab.counters();lab.start(name,'ping '+record['destinationIp'])
        for _ in range(8):
            lab.js('ipc.appWindow().getRealtimeToolbar().fastForwardTime();return true;');time.sleep(.05)
            output=lab.output(name)
            if 'Sent = 4' in output:break
        after=lab.counters();delta=lab.delta(before,after);m=re.search(r'Sent = (\d+), Received = (\d+)',output)
        passed=bool(m and int(m[1])==4 and int(m[2])==(4 if record['expected']=='allow' else 0))
        if record['expected']=='deny':passed=passed and any(' deny ' in rule and count>=4 for rule,count in delta.items())
        ref=f'evidence/{RUN_ID}/retry-'+record['id']+'.json'
        record.update(output=output,sent=int(m[1]) if m else 0,received=int(m[2]) if m else 0,passed=passed,counterDelta=delta,counterScope='command',evidenceRef=ref)
        write(Path(ref).name,dict(runId=RUN_ID,submissionSha256=matrix['submissionSha256'],observedAt=STAMP(),aclBefore=before,aclAfter=after,records=[record]))
        print('Isolated recheck',name,record['destinationIp'],passed,flush=True)
    matrix.update(passed=sum(r['passed'] for r in matrix['records']),mismatches=[r['id'] for r in matrix['records'] if not r['passed']],completedAt=STAMP())
    meta={k:v for k,v in matrix.items() if k not in ('schemaVersion','addressContext','records','evidence')};write('run.json',meta)
    matrix['evidence']=[dict(path=str(p.relative_to(s.BASE)).replace('\\','/'),sha256=digest(p)) for p in sorted(RUN.glob('*.json'))]
    path.write_text(json.dumps(matrix,indent=2),encoding='utf-8')
    assert digest(s.FILE)==matrix['submissionSha256'] and not matrix['mismatches']

def run():
    assert s.inventory()['file'].replace('\\','/').endswith('/'+s.FILE.name)
    sha=digest(s.FILE)
    ios_before={n:lab.show(n,'show running-config') for n in s.IOS}
    leases=s.leases();assert len({v['ip'] for v in leases.values()})==51 and all(v['ip']!='0.0.0.0' for v in leases.values())
    inventory=raw_inventory();write('inventory.json',inventory);write('leases.json',leases)
    hosts=[dict(name=n,id=ident(n),ip=leases[n]['ip'],vlan=v) for v,names in s.GROUPS.items() for n in names]+[dict(name='SRV-CAMPUS',id='server0',ip=s.SERVER,vlan=40)]
    extras=[dict(name=n,id=ident(n),ip=f'192.168.10.{99+i}',vlan=10) for i,n in enumerate(s.IOS[1:])]+[dict(name='R1-CAMPUS',id='r1',ip=s.NETS[v][3],vlan=v) for v in (10,20,30,40)]
    context={h['id']:h['ip'] for h in hosts}
    meta=dict(runId=RUN_ID,startedAt=STAMP(),submissionFile=s.FILE.name,submissionSha256=sha,method='Actual Packet Tracer command prompts. One outstanding command per source; built-in realtime fast-forward. ACL counters are observed across each capture batch.',counterScope='capture-batch')
    write('run.json',meta)
    lab.initialize()
    records=[];mismatches=[]
    batches=[[(src,hosts[(i+offset)%len(hosts)]) for i,src in enumerate(hosts)] for offset in range(1,len(hosts))]
    batches += [[(src,target) for src in hosts] for target in extras]
    for bi,jobs in enumerate(batches,1):
        before=lab.counters()
        pending=list(jobs);outputs={};attempts={}
        for attempt in range(3):
            lab.js('for(var job of '+json.dumps([(a['name'],b['ip']) for a,b in pending])+'){var n=job[0];n4Collectors[n].text="";ipc.network().getDevice(n).getCommandPrompt().enterCommand("ping "+job[1]);}return true;')
            for _ in range(8):
                lab.js('ipc.appWindow().getRealtimeToolbar().fastForwardTime();return true;')
                time.sleep(.05)
                data=lab.js('var out={};for(var n of '+json.dumps([a['name'] for a,b in pending])+')out[n]=n4Collectors[n].text;return out;')
                if all('Sent = 4' in output for output in data.values()):break
            retry=[]
            for source,target in pending:
                text=data[source['name']]
                key=source['id']+':'+target['ip'];attempts.setdefault(key,[]).append(text)
                m=re.search(r'Sent = (\d+), Received = (\d+)',text)
                good=bool(m and int(m[1])==4 and int(m[2])==(4 if expected(source,target) else 0))
                outputs[key]=dict(output=text,sent=int(m[1]) if m else 0,received=int(m[2]) if m else 0,passed=good)
                if not good:retry.append((source,target))
            pending=retry
            if not pending:break
        after=lab.counters();delta=lab.delta(before,after)
        batch=[]
        for source,target in jobs:
            key=source['id']+':'+target['ip'];row=outputs[key];allow=expected(source,target)
            acl=s.ACLS[source['vlan']]
            counters={rule:count for rule,count in delta.items() if rule.startswith(acl+' |') and (' deny ' in rule if not allow else ' permit ' in rule)}
            if not allow and not any(' deny ' in rule and count>=4 for rule,count in counters.items()):row['passed']=False
            record=dict(id='PING2-'+str(len(records)+1),testId='P02',sourceDeviceId=source['id'],sourceIp=source['ip'],destinationDeviceId=target['id'],destinationIp=target['ip'],expected='allow' if allow else 'deny',counterDelta=counters,counterScope='capture-batch',evidenceRef=f'evidence/{RUN_ID}/batch-{bi:02d}.json',**row)
            batch.append(dict(**record,attempts=attempts[key]));records.append(record)
            if not row['passed']:mismatches.append(key)
        write(f'batch-{bi:02d}.json',dict(runId=RUN_ID,submissionSha256=sha,observedAt=STAMP(),counterScope='capture-batch',aclBefore=before,aclAfter=after,records=batch))
        print(f'Batch {bi}/{len(batches)}: {len(records)}/2958 commands; mismatches {len(mismatches)}',flush=True)
    assert len(records)==2958
    unchanged=digest(s.FILE)==sha
    ios_unchanged=all(lab.show(n,'show running-config')==ios_before[n] for n in s.IOS)
    assert unchanged and ios_unchanged
    assert s.leases()==leases,'DHCP context changed during capture'
    evidence=[]
    meta.update(completedAt=STAMP(),cases=len(records),passed=len(records)-len(mismatches),mismatches=mismatches,submissionUnchanged=unchanged,iosConfigurationsUnchanged=ios_unchanged)
    write('run.json',meta)
    for path in sorted(RUN.glob('*.json')):evidence.append(dict(path=str(path.relative_to(s.BASE)).replace('\\','/'),sha256=digest(path)))
    matrix=dict(schemaVersion=2,**meta,addressContext=context,records=records,evidence=evidence)
    (s.BASE/'data/ping-matrix.v2.json').write_text(json.dumps(matrix,indent=2),encoding='utf-8')
    print('Complete:',meta['passed'],'/',meta['cases'],'submission unchanged',unchanged,flush=True)
    if mismatches:reconcile()

if __name__=='__main__':run()
