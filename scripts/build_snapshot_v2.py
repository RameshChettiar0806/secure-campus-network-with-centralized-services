"""Build the expanded website snapshot from the captured simulator/evidence."""
import hashlib
import ipaddress
import json
import re
from pathlib import Path
from datetime import datetime,timezone,timedelta
from scale50 import BASE,NETS,GROUPS,IOS,FILE
from capture_ping_v2 import ident
from build_snapshot import config_interfaces,policy_rows

def read(path):return json.loads((BASE/path).read_text(encoding='utf-8'))
def build():
    matrix=read('data/ping-matrix.v2.json');assert matrix['cases']==2958 and matrix['passed']==2958 and not matrix['mismatches']
    assert hashlib.sha256(FILE.read_bytes()).hexdigest()==matrix['submissionSha256']
    run='SCALE50-20261031';prefix=f'evidence/{run}/';pingprefix='evidence/PING-20261031/'
    raw=read(pingprefix+'inventory.json');lease=read(pingprefix+'leases.json');oldlease=read(prefix+'leases.json')
    stamp=matrix['completedAt'];acceptance_at=re.search(r'Verified: (\S+)',(BASE/'SCALE_50_ACCEPTANCE.md').read_text(encoding='utf-8'))[1]
    config={n:(BASE/'configs'/(n+'.txt')).read_text(encoding='utf-8') for n in IOS}
    roles={'r1':'Four VLAN gateways, centralized DHCP relay, ingress ACL enforcement and SSH management',
           'sw1':'Layer 2 campus aggregation and Services access','sw2':'Administration access and VLAN 10 management',
           'sw3':'Faculty access and VLAN 10 management','sw4':'Student access and VLAN 10 management',
           'server0':'Centralized DHCP, DNS and internal HTTP services','pc8':'Authorized static management workstation'}
    vlan_by_name={n:v for v,names in GROUPS.items() for n in names};vlan_by_name['SRV-CAMPUS']=40
    nodes=[]
    for r in raw['nodes']:
        name=r['name'];device_id=ident(name);vlan=vlan_by_name.get(name)
        role=roles.get(device_id,({10:'Administration',20:'Faculty',30:'Student'}.get(vlan,'')+' DHCP client'))
        node=dict(id=device_id,label=name,model=r['model'],role=role,position=r['position'],interfaces=[])
        if vlan:node['vlanId']=vlan
        if name in config:node['configurationRef']='configs/'+name+'.txt'
        blocks=config_interfaces(config.get(name,''))
        for p in r['interfaces']:
            if vlan and p['name']!='FastEthernet0':continue
            block=blocks.get(p['name'],'');kind='subinterface' if '.' in p['name'] else 'svi' if p['name'].startswith('Vlan') else 'physical'
            port=dict(name=p['name'],kind=kind,administrativeState='down' if re.search(r'^ shutdown$',block,re.M) else 'up',recordedOperationalState='up' if p['portUp'] and p['protocolUp'] else 'down',observedAt=stamp)
            if p.get('address') not in (None,'','0.0.0.0'):
                port.update(ipv4=p['address'],prefixLength=ipaddress.ip_network('0.0.0.0/'+p['mask']).prefixlen)
            trunk=re.search(r'^ switchport trunk allowed vlan ([\d,]+)$',block,re.M)
            if re.search(r'^ switchport mode trunk$',block,re.M):
                assert trunk,(name,p['name'])
                port.update(mode='trunk',trunkVlans=[int(v) for v in trunk[1].split(',')],nativeVlan=1)
            elif name.startswith('SW') and kind=='physical':
                access=re.search(r'^ switchport access vlan (\d+)$',block,re.M)
                port.update(mode='access',accessVlan=int(access[1]) if access else 1)
            if kind=='subinterface':port['vlanId']=int(p['name'].split('.')[-1])
            if kind=='svi' and p['name']=='Vlan10':port.update(vlanId=10,defaultGateway=NETS[10][3])
            if vlan:
                observed=lease[name];prefixlen=ipaddress.ip_network('0.0.0.0/'+NETS[vlan][1]).prefixlen
                port.update(assignment='dhcp' if observed['dhcp'] else 'static',vlanId=vlan,defaultGateway=NETS[vlan][3],dnsServer=observed['dns'])
                if observed['dhcp']:
                    port.pop('ipv4',None);port.pop('prefixLength',None)
                    port.update(poolId={10:'ADMIN_POOL',20:'FACULTY_POOL',30:'STUDENT_POOL'}[vlan],observedLease=dict(ipv4=observed['ip'],prefixLength=prefixlen,defaultGateway=NETS[vlan][3],dnsServer=observed['dns'],observedAt=stamp,evidenceRef=pingprefix+'leases.json'))
                else:port.update(ipv4=observed['ip'],prefixLength=prefixlen)
            node['interfaces'].append(port)
        nodes.append(node)
    nodes.sort(key=lambda d:(0 if d['id']=='r1' else 1 if d['id'].startswith('sw') else 2 if d['id']=='server0' else 3,int(re.search(r'\d+',d['id'])[0])))
    lookup={n['id']:n for n in nodes};links=[]
    for r in raw['links']:
        a,b=ident(r['from']),ident(r['to']);trunk=r['from'] in IOS and r['to'] in IOS
        if trunk:
            pa=next(p for p in lookup[a]['interfaces'] if p['name']==r['fromInterface']);pb=next(p for p in lookup[b]['interfaces'] if p['name']==r['toInterface'])
            vlans=pa.get('trunkVlans') or pb.get('trunkVlans');lid='l-'+a+'-'+b
        else:
            endpoint=a if a.startswith('pc') or a=='server0' else b;vlans=[lookup[endpoint]['vlanId']];lid='l-'+endpoint
        links.append(dict(id=lid,sourceDeviceId=a,sourceInterface=r['fromInterface'],targetDeviceId=b,targetInterface=r['toInterface'],cableType={8100:'copper-straight-through',8101:'copper-crossover'}[r['cable']],mode='trunk' if trunk else 'access',vlanIds=vlans))
    vlans=[]
    for v,label in [(10,'ADMINISTRATION'),(20,'FACULTY'),(30,'STUDENTS'),(40,'SERVICES')]:
        net,mask,wild,gw,bc=NETS[v];subnet=ipaddress.ip_network(net+'/'+mask)
        item=dict(id=v,name=label,subnet=str(subnet),mask=mask,wildcard=wild,gateway=gw,broadcast=bc,usableHosts=subnet.num_addresses-2)
        if v!=40:item['poolId']={10:'ADMIN_POOL',20:'FACULTY_POOL',30:'STUDENT_POOL'}[v]
        vlans.append(item)
    pools=[]
    for p in read(prefix+'reopened-dhcp-pools.json'):
        v={'ADMIN_POOL':10,'FACULTY_POOL':20,'STUDENT_POOL':30,'serverPool':40}[p['name']]
        pools.append(dict(id=p['name'],vlanId=v,start=p['start'],end=p['end'],mask=p['mask'],gateway=p['gateway'],dnsServer=p['dns'],maxUsers=p['maxUsers'],purpose='client-leases' if v!=40 else 'harmless-simulator-default',inUse=v!=40))
    summary=read(prefix+'test-summary.json');assert summary['allPassed']
    definitions=[('A01','ipconfig','All 50 PCs have correct IP, subnet, gateway and DNS settings',['ipconfig-all.json']),
                 ('A02','gatewayPing','All 50 PCs can ping their own gateway',['gateway-pings.json']),
                 ('A03','serverPing','All 50 PCs can ping the centralized server',['server-pings.json']),
                 ('A04','dns','All 50 PCs resolve portal.campus.test to 192.168.10.130',['dns-all.json']),
                 ('A05','http','All 50 PCs load the campus website using its DNS hostname',['http-all.json']),
                 ('A06','policyAllowed','Administration diagnostics, same-VLAN forwarding and server gateway checks pass',['policy-allowed.json']),
                 ('A07','policyDenied','Student, Faculty and server initiation is denied with ACL counter evidence',[f'deny-{i}.json' for i in range(5)]),
                 ('A08','sshAllowed','PC8-MGMT authenticates by SSHv2 to the router and all four switches',['ssh-allow-'+n+'.json' for n in IOS]),
                 ('A09','sshDeniedAdmin','Other Administration PCs cannot access the five network-device VTYs',['ssh-denied-admin.json']),
                 ('A10','sshDeniedDepartments','Student and Faculty clients cannot SSH to router management',['ssh-denied-departments.json'])]
    tests=[]
    for testid,key,title,files in definitions:
        cases=[]
        for filename in files:
            data=read(prefix+filename)
            if 'source' in data:cases.append(data)
            else:cases.extend(dict(source=n,**value) for n,value in data.items())
        assert len(cases)==summary[key]['total'] and all(c['passed'] for c in cases),(key,len(cases))
        cleaned=[]
        for c in cases:
            source=c.get('source');selected=c.get('retry',c)
            if source in oldlease:c={**c,'sourceDeviceId':ident(source),'sourceIp':oldlease[source]['ip'],'sourceAddressBasis':'Reopened acceptance-run address context','sourceAddressEvidenceRef':prefix+'leases.json'}
            if 'command' in selected:c={**c,'command':selected['command'],'output':selected.get('output',c.get('output',''))}
            # Detailed raw transactions remain in the evidence viewer, not repeated in the initial snapshot.
            c={k:v for k,v in c.items() if k not in ('aclBefore','aclAfter','page','events','retry')}
            cleaned.append(c)
        tests.append(dict(id=testid,runId=run,expected=title,observed=f"{len(cases)}/{len(cases)} checks matched the expected outcome after reopening.",status='pass',observedAt=acceptance_at,cases=cleaned,evidenceRefs=[prefix+f for f in files],notes='Recorded retries are retained in the evidence files where an initial command timed out.'))
    tests.append(dict(id='P02',runId=run,expected='Complete directed ICMP matrix across the expanded campus',observed=f"{matrix['passed']:,}/{matrix['cases']:,} source/address pairs matched policy.",status='pass',observedAt=stamp,cases=[dict(source=n['label'],sourceDeviceId=n['id'],sourceIp=matrix['addressContext'][n['id']],passed=True,matched=58,checks=58,protocol='ICMP') for n in nodes if n['id'] in matrix['addressContext']],evidenceRefs=[pingprefix+'run.json']+[e['path'] for e in matrix['evidence'] if '/batch-' in e['path'] or '/retry-' in e['path']],notes='51 endpoint sources × 58 destinations each. Each case below summarizes one source. Self-pings are excluded; all four router gateway addresses are included. Open Ping lab for individual commands. ACL counters are captured per batch, with an isolated command recheck retained where needed.'))
    policies=policy_rows();testmap={'N01':['A01'],'N02':['A01'],'N03':['A01'],'N04':['A01'],'N05':['A02'],'N06':['A03'],'N07':['A05'],'N08':['A04','A05'],'N09':['A06'],'N10':['A07','P02'],'N11':['A07','P02'],'N12':['A06'],'N13':['A07'],'N14':['A08'],'N15':['A09'],'N16':['A10'],'N17':[],'N18':['A06','P02']}
    for policy in policies:policy['testIds']=list(dict.fromkeys(t for old in policy['testIds'] for t in testmap[old]))
    policies[6].update(source='PC8-MGMT 192.168.10.98',destination='Router .97 and four switches .99-.102')
    policies[7]['caveat']='Administration clients and all switch management addresses share VLAN 10; their packets bypass the router.'
    policies[11]['destination']='Own gateway 192.168.10.129'
    policies[14].update(destination='Router and all four switches',caveat='SSH-only VTY transport is configured on all five IOS devices; an expanded Telnet transaction was not recorded.')
    refs={ref for t in tests for ref in t['evidenceRefs']}|{prefix+'leases.json',prefix+'test-summary.json',prefix+'topology.png',prefix+'inventory.json',prefix+'reopened-dhcp-pools.json',prefix+'reopened-before-renew.json',pingprefix+'inventory.json',pingprefix+'leases.json'}
    refs.update(n['configurationRef'] for n in nodes if 'configurationRef' in n)
    evidence=[dict(id=f'v2-e{i}',path=path,sha256=hashlib.sha256((BASE/path).read_bytes()).hexdigest(),mediaType='image/png' if path.endswith('.png') else 'text/plain' if path.endswith('.txt') else 'application/json') for i,path in enumerate(sorted(refs))]
    before=read(prefix+'reopened-before-renew.json')
    snapshot=dict(schemaVersion='1.0.0',snapshotId='secure-campus-v2-50pc-20261031',capturedAt=stamp,packetTracerVersion='9.0.1',submissionFile=FILE.name,submissionSha256=matrix['submissionSha256'],testRunId=run,projectTitle='Design and Implementation of a Secure Campus Network with Centralized Services',recordingMode='verified-snapshot',devices=nodes,links=links,vlans=vlans,dhcpPools=pools,policies=policies,recordedTests=tests,evidence=evidence,
        services=dict(serverDeviceId='server0',ipv4='192.168.10.130',dns=dict(enabled=True,records=[dict(name='portal.campus.test',type='A',value='192.168.10.130')],verifiedTransports=['UDP'],unverifiedTransports=['TCP']),http=dict(enabled=True,url='http://portal.campus.test',port=80),dhcp=dict(enabled=True,poolIds=[p['id'] for p in pools]),ssh=dict(deviceIds=[ident(n) for n in IOS],version=2,configuredRsaModulusBits=2048,authorizedSourceDeviceId='pc8',port=22)),
        limitations=['Recorded Packet Tracer results; the website does not send live packets.','VLSM: /26 Students, /27 Faculty and Administration, /28 Services.','Same-VLAN forwarding bypasses routed ACLs.','ACLs are stateless; TCP ACK/RST and ICMP reply rules do not prove connection state.','TCP DNS is configured by ACL but was not exercised end to end.','Faculty and Student aggregation trunks use 100 Mb/s FastEthernet; router and Administration trunks use Gigabit ports.','The router and centralized services are single points of failure.','HTTP content is unencrypted.'],
        dhcpReopenBehavior=dict(stpConvergenceSeconds=None,beforeRenew={n:v['ip'] for n,v in before.items() if v['dhcp']},afterConvergenceBeforeExplicitRenew={n:v['ip'] for n,v in lease.items() if v['dhcp']},recoveryAction='Allow around a minute for trunks and DHCP recovery; renew any remaining dynamic client. PC8-MGMT remains static. Exact convergence time was not measured.',evidenceRefs=[prefix+'reopened-before-renew.json',pingprefix+'leases.json']))
    out=BASE/'data/network-snapshot.v2.json';out.write_text(json.dumps(snapshot,indent=2),encoding='utf-8')
    print('Expanded snapshot:',len(nodes),'devices,',len(links),'links,',len(tests),'test groups,',len(evidence),'evidence assets')

if __name__=='__main__':build()
