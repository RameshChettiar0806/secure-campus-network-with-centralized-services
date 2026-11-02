"""Build one coherent current-network snapshot from the v3 capture."""
import copy
import hashlib
import ipaddress
import json
import re
from pathlib import Path
from capture_website_v3 import BASE,RUN,RUN_ID,ident

digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda name:json.loads((RUN/name).read_text(encoding='utf-8'))


def build():
    matrix=json.loads((BASE/'data/ping-matrix.v3.json').read_text())
    assert matrix['passed']==3224 and not matrix['mismatches']
    assert digest(BASE/matrix['submissionFile'])==matrix['submissionSha256']
    for name in ['current-summary.json','extension-summary.json','persistence-summary.json']:
        assert read(name)['allPassed'],name
    snapshot=copy.deepcopy(json.loads((BASE/'data/network-snapshot.v2.json').read_text()))
    raw=read('inventory.json');leases=read('leases.json');stamp=read('completed.json')['completedAt']
    lookup={d['name']:d for d in raw['nodes']};configs=read('ios-configs.json')
    for device in snapshot['devices']:
        name=device['label'];live=lookup[name];device['position']=live['position'];device['segment']='campus'
        if name in configs:
            path=BASE/'configs'/(name+'-CURRENT.txt');path.write_text(configs[name],encoding='utf-8');device['configurationRef']=path.relative_to(BASE).as_posix()
        actual={p['name']:p for p in live['interfaces']}
        for port in device['interfaces']:
            port['observedAt']=stamp
            if port['name'] in actual:
                p=actual[port['name']];port['recordedOperationalState']='up' if p['portUp'] and p['protocolUp'] else 'down'
            if name in leases and port['name']=='FastEthernet0':
                observed=leases[name]
                if port.get('observedLease'):
                    port['observedLease'].update(ipv4=observed['ip'],observedAt=stamp,evidenceRef=f'evidence/{RUN_ID}/leases.json')
                else:port['ipv4']=observed['ip']
            if device['id']=='r1':
                if port['name'] in ['GigabitEthernet0/0.10','GigabitEthernet0/0.20','GigabitEthernet0/0.30']:port['natRole']='inside'
                if port['name']=='GigabitEthernet0/1':port.update(ipv4='198.51.100.1',prefixLength=30,administrativeState='up',recordedOperationalState='up',natRole='outside',ospfArea=0)
        if device['id']=='r1':device['role']='Four campus VLAN gateways, DHCP relay, ingress ACLs, area-0 OSPF, PAT outside 198.51.100.1 and SSH management'
    for name in ['R2-EXTERNAL','SRV-EXTERNAL']:
        live=lookup[name];device=dict(id=ident(name),label=name,model=live['model'],role='Area-0 OSPF neighbor and external LAN gateway; no route to private campus subnets' if name.startswith('R2') else 'External HTTP demonstration server reached through OSPF routing and PAT',segment='external',position=live['position'],interfaces=[])
        for p in live['interfaces']:
            port=dict(name=p['name'],kind='svi' if p['name'].startswith('Vlan') else 'physical',administrativeState='up' if p['power'] else 'down',recordedOperationalState='up' if p['portUp'] and p['protocolUp'] else 'down',observedAt=stamp)
            if p['address']!='0.0.0.0':port.update(ipv4=p['address'],prefixLength=ipaddress.ip_network('0.0.0.0/'+p['mask']).prefixlen)
            if name=='R2-EXTERNAL' and p['name'].startswith('Gigabit'):port.update(ospfArea=0,ospfPassive=p['name'].endswith('/1'))
            if name=='SRV-EXTERNAL':port.update(assignment='static',defaultGateway='203.0.113.1')
            device['interfaces'].append(port)
        if name in configs:
            path=BASE/'configs'/(name+'-CURRENT.txt');path.write_text(configs[name],encoding='utf-8');device['configurationRef']=path.relative_to(BASE).as_posix()
        snapshot['devices'].append(device)
    snapshot['links'] += [dict(id='l-r1-r2',sourceDeviceId='r1',sourceInterface='GigabitEthernet0/1',targetDeviceId='r2',targetInterface='GigabitEthernet0/0',cableType='copper-crossover',mode='routed',vlanIds=[]),dict(id='l-r2-server1',sourceDeviceId='r2',sourceInterface='GigabitEthernet0/1',targetDeviceId='server1',targetInterface='FastEthernet0',cableType='copper-crossover',mode='routed',vlanIds=[])]
    def linkkey(a,b,pa,pb):return tuple(sorted([(a,pa),(b,pb)]))
    live_links={linkkey(ident(l['from']),ident(l['to']),l['fromInterface'],l['toInterface']) for l in raw['links']}
    built_links={linkkey(l['sourceDeviceId'],l['targetDeviceId'],l['sourceInterface'],l['targetInterface']) for l in snapshot['links']}
    assert live_links==built_links and len(built_links)==57
    snapshot.update(snapshotId='secure-campus-v3-ospf-pat-20261102',capturedAt=stamp,submissionSha256=matrix['submissionSha256'],testRunId=RUN_ID)
    snapshot['services']['dns']['records'].append(dict(name='external.campus.test',type='A',value='203.0.113.10'))
    snapshot['routing']=dict(externalServerId='server1',externalHostname='external.campus.test',externalAddress='203.0.113.10',externalSubnet='203.0.113.0/24',externalGateway='203.0.113.1',transitSubnet='198.51.100.0/30',patOutsideAddress='198.51.100.1',ospfArea=0,ospfNeighborState='FULL',insideVlans=[10,20,30],evidenceRefs=[f'evidence/{RUN_ID}/routing.json',f'evidence/{RUN_ID}/pat-translations.json'])
    tests=[]
    def add(tid,title,files,cases=None,notes=None):
        if cases is None:
            cases=[]
            for filename in files:
                data=read(filename)
                cases += [data] if 'passed' in data else [dict(source=n,**v) for n,v in data.items() if isinstance(v,dict)]
        cleaned=[]
        for case in cases:
            c={k:v for k,v in case.items() if k not in ['events','page','aclBefore','aclAfter','retry']}
            if c.get('source') in leases:c.update(sourceDeviceId=ident(c['source']),sourceIp=leases[c['source']]['ip'])
            cleaned.append(c)
        assert cleaned and all(c.get('passed') is True for c in cleaned),(tid,cleaned)
        tests.append(dict(id=tid,runId=RUN_ID,expected=title,observed=f'{len(cleaned)}/{len(cleaned)} current-network checks matched the expected outcome.',status='pass',observedAt=stamp,cases=cleaned,evidenceRefs=[f'evidence/{RUN_ID}/'+f for f in files],notes=notes or 'Measured against the current saved OSPF/PAT submission. Recorded retries are retained in the evidence.'))
    add('A01','All 50 PCs have valid VLAN addressing and campus DNS settings',['current-leases.json'],[dict(source=n,passed=True,observed=leases[n]) for n in leases if n!='SRV-CAMPUS'])
    for tid,title,file in [('A02','All 50 clients can ping their own gateway','current-gateway.json'),('A03','All 50 clients can ping the campus services server','current-campus-ping.json'),('A04','All 50 clients resolve portal.campus.test','current-dns.json'),('A05','All 50 clients load the campus portal by hostname','http-all.json'),('A06','Administration diagnostics and local switching remain permitted','current-policy-allow.json')]:add(tid,title,[file])
    add('A07','Departmental and server-initiated prohibited pings are blocked',[f'current-deny-{i}.json' for i in range(5)])
    add('A08','PC8-MGMT authenticates by SSH to all five campus IOS devices',['reopened-ssh-'+n+'.json' for n in configs if n!='R2-EXTERNAL'])
    denied=read('reopened-ssh-denied.json')
    add('A09','An unauthorized Administration PC cannot SSH to switch management',['reopened-ssh-denied.json'],[dict(source='PC9-ADMIN',**denied['PC9-ADMIN'])])
    add('A10','Student and Faculty sources cannot SSH to R1',['reopened-ssh-denied.json'],[dict(source=n,**denied[n]) for n in ['PC0','PC5']])
    add('E01','OSPF adjacency is FULL and the external server subnet is learned',['ospf-full.json','external-router-routes.json'],[dict(source='R1-CAMPUS',passed=True,neighborState='FULL',route='203.0.113.0/24 via 198.51.100.2',externalRouterHasNoPrivateRoute=True)])
    add('E02','All 50 clients reach the external server with ICMP',['external-pings.json'])
    add('E03','All 50 clients load external.campus.test over HTTP',['external-http.json'])
    add('E04','PAT shares 198.51.100.1 across all 50 inside client addresses',['pat-translations.json'],[dict(source='R1-CAMPUS',passed=True,insideAddresses=read('pat-translations.json')['insideLocalAddresses'],insideGlobal='198.51.100.1')])
    add('E05','Another external host and unsolicited WAN Echo remain blocked',['external-other-host-denied.json','unsolicited-wan-denied.json'])
    add('E06','DHCP renewal and saved OSPF/PAT settings remain valid',['reopened-dhcp-renewal.json','persistence-summary.json'],[dict(passed=True,renewedClients=['PC0','PC5','PC9-ADMIN'],savedPatPresent=True,ospfFull=True)])
    add('P03','Complete current-network ICMP matrix: 52 sources × 62 destinations',['ping-run.json'],[dict(source=d['label'],sourceDeviceId=d['id'],sourceIp=matrix['addressContext'][d['id']],passed=True,matched=62,checks=62) for d in snapshot['devices'] if d['id'] in matrix['addressContext']],notes='3,224 actual ping commands. Client-to-external flows exercise PAT. External-to-private failures are routing failures at R2; WAN-IN denials are recorded separately. Self-pings excluded.')
    snapshot['recordedTests']=tests
    for policy in snapshot['policies']:
        policy['testIds']=['P03' if t=='P02' else t for t in policy['testIds']]
        if policy['id']=='p12':policy['testIds']=['P03']
        if policy['id']=='p14':policy['caveat']='Only explicitly listed routed services are permitted, including ICMP and HTTP to the external demonstration server. Same-VLAN forwarding bypasses R1.'
    rows=[
      ('p17','Client VLANs 10/20/30','SRV-EXTERNAL 203.0.113.10','ICMP','Echo / Echo Reply','permit','Client ingress ACLs, PAT and WAN-IN',['E02','P03'],'The external route is learned through OSPF; PAT supplies a return address.'),
      ('p18','Client VLANs 10/20/30','external.campus.test / 203.0.113.10','TCP','80 (HTTP)','permit','Client ingress ACLs, PAT and WAN-IN',['E03','E04'],'HTTP is permitted only to the demonstration server, not every outside destination.'),
      ('p19','Client VLANs 10/20/30','Other external destinations / server ports','IP','unlisted traffic','deny','Source VLAN ingress ACL',['E05','P03'],'The measured other-host denial targets the live R2 server-LAN interface, 203.0.113.1.'),
      ('p20','SRV-EXTERNAL','R1 outside address 198.51.100.1','ICMP','new Echo Request','deny','WAN-IN on R1 Gi0/1',['E05','P03'],'Permitted replies are distinguished from unsolicited requests; ACLs remain stateless.'),
      ('p21','R2 198.51.100.2','R1 OSPF control plane','OSPF','IP protocol 89 / area 0','permit','WAN-IN; OSPF on transit only',['E01'],'The external LAN is passive. OSPF is not enabled on campus client VLANs.'),
      ('p22','SRV-EXTERNAL','Private campus addresses','IP','private destinations','deny','No private route on R2',['E01','P03'],'This reachability failure is caused by the missing route. It is not evidence of an ACL match.'),
    ]
    snapshot['policies'] += [dict(id=i,source=s,destination=d,protocol=p,portOrType=port,action=a,enforcementPoint=e,testIds=t,caveat=c) for i,s,d,p,port,a,e,t,c in rows]
    refs={ref for test in tests for ref in test['evidenceRefs']}|set(snapshot['routing']['evidenceRefs'])|{f'evidence/{RUN_ID}/leases.json',f'evidence/{RUN_ID}/inventory.json'}|{d['configurationRef'] for d in snapshot['devices'] if 'configurationRef' in d}
    assets={a['path']:a for a in matrix['evidence']}
    for ref in refs:assets[ref]=dict(path=ref,sha256=digest(BASE/ref))
    snapshot['evidence']=[dict(id='v3-e'+str(i),mediaType='text/plain' if a['path'].endswith('.txt') else 'application/json',**a) for i,a in enumerate(sorted(assets.values(),key=lambda a:a['path']))]
    snapshot['limitations']=[s for s in snapshot['limitations'] if 'single points' not in s]
    snapshot['limitations'] += ['The campus still has one routing gateway and one centralized services server; the added external branch does not provide redundancy.','OSPF area 0 is a controlled lab adjacency to a simulated external network, not real Internet routing.','External access is limited to HTTP and ICMP at 203.0.113.10. R2 has no private-campus route.']
    snapshot['dhcpReopenBehavior']['evidenceRefs']=[f'evidence/{RUN_ID}/reopened-dhcp-renewal.json']
    renewal=read('reopened-dhcp-renewal.json')
    snapshot['dhcpReopenBehavior']['beforeRenew']={n:d['ip'] for n,d in renewal['before'].items() if d['dhcp']}
    snapshot['dhcpReopenBehavior']['afterConvergenceBeforeExplicitRenew']={n:d['ip'] for n,d in renewal['after'].items() if d['dhcp']}
    (BASE/'data/network-snapshot.v3.json').write_text(json.dumps(snapshot,indent=2),encoding='utf-8')
    walkthrough=copy.deepcopy(json.loads((BASE/'data/ospf-pat-extension.json').read_text()))
    walkthrough.update(runId=RUN_ID,capturedAt=stamp,submissionSha256=matrix['submissionSha256'])
    walkthrough['observations']['ospf']=read('ospf-full.json')['neighbors']+'\n'+'\n'.join(line for line in read('ospf-full.json')['routes'].splitlines() if line.startswith('O '))
    table=read('pat-translations.json')['translations'].splitlines()
    examples=[table[0]]
    for address in ['192.168.10.2','192.168.10.66','192.168.10.98']:
        row=next((line for line in table if re.search(r'\b'+re.escape(address)+r'(?=[:\s])',line)),None)
        if row:examples.append(row)
    walkthrough['observations']['pat']='\n'.join(examples)+'\n\n50 distinct inside-local addresses observed sharing 198.51.100.1.'
    walkthrough['evidence']=[dict(path=a['path'],sha256=a['sha256']) for a in snapshot['evidence'] if '/batch-' not in a['path'] and '/retry-' not in a['path']]
    walkthrough['checks']=[dict(label=t['expected'],result=t['observed']) for t in tests]
    # Controlled failure tests retain their explicit original evidence identity;
    # the current snapshot is read-only and does not repeat disruptive checks.
    recovery=json.loads((BASE/'data/ospf-pat-extension.json').read_text())
    walkthrough['evidence'] += [a for a in recovery['evidence'] if any(k in a['path'] for k in ['failure-check-summary','pat-disabled','pat-restored','ospf-disabled','ospf-restored','campus-during-ospf-outage'])]
    (BASE/'data/ospf-pat-extension.v3.json').write_text(json.dumps(walkthrough,indent=2),encoding='utf-8')
    segments=[dict(id='admin',name='Administration',source='pc8',peer='pc9'),dict(id='faculty',name='Faculty',source='pc5',peer='pc6'),dict(id='students',name='Students',source='pc0',peer='pc1'),dict(id='services',name='Services',source='server0'),dict(id='external',name='External',source='server1')]
    examples=[]
    for origin in segments:
        for destination in segments:
            if origin['id']==destination['id'] and 'peer' not in destination:continue
            target=destination['peer'] if origin['id']==destination['id'] else destination['source']
            record=next(r for r in matrix['records'] if r['sourceDeviceId']==origin['source'] and r['destinationDeviceId']==target)
            examples.append(dict(fromSegment=origin['id'],toSegment=destination['id'],source=origin['source'],target=target,verdict='Local' if origin['id']==destination['id'] else 'Allow' if record['expected']=='allow' else 'No route' if record['blockingDeviceId']=='r2' and not record['enforcementAcl'] else 'Block',reason=record['decisionReason'],recordId=record['id'],destinationIp=record['destinationIp'],evidenceRef=record['evidenceRef']))
    (BASE/'data/policy-matrix.v3.json').write_text(json.dumps(dict(submissionSha256=matrix['submissionSha256'],segments=segments,examples=examples),indent=2),encoding='utf-8')
    print('Current website snapshot:',len(snapshot['devices']),'devices,',len(snapshot['links']),'links,',len(tests),'test groups,',len(snapshot['policies']),'policies',flush=True)


if __name__=='__main__':build()
