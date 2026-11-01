from n4_runner import *

IDS={'R1-CAMPUS':'r1','SW1-CORE':'sw1','SW2-ACCESS':'sw2','SRV-CAMPUS':'server0','PC8-MGMT':'pc8','PC9-ADMIN':'pc9',**{f'PC{i}':f'pc{i}' for i in range(8)}}
ROLES={'r1':'VLAN gateways, DHCP relay, ingress ACL enforcement and SSH management','sw1':'Layer 2 campus aggregation; Administration and Services access','sw2':'Layer 2 Faculty and Student access','server0':'Centralized DHCP, DNS and HTTP','pc8':'Authorized static management workstation','pc9':'Administration DHCP client and unauthorized-management test source'}

def config_interfaces(config):
    return {m.group(1):m.group(2) for m in re.finditer(r'^interface (\S+)\n(.*?)(?=^interface |^!|\Z)',config,re.M|re.S)}

def raw_inventory():
    code='''var net=ipc.network(),nodes=[],links=[];
    for(var i=0;i<net.getDeviceCount();i++){
      var d=net.getDeviceAt(i);if(d.getType()===45)continue;
      var ports=[];
      for(var j=0;j<d.getPortCount();j++){
        var p=d.getPortAt(j);if(p.getName()==='Bluetooth')continue;
        var o={name:p.getName(),power:p.getPower(),portUp:p.isPortUp(),protocolUp:p.isProtocolUp()};
        try{o.address=p.getIpAddress();o.mask=p.getSubnetMask();}catch(e){}
        ports.push(o);
      }
      nodes.push({name:d.getName(),model:d.getModel(),type:d.getType(),position:{x:d.getXCoordinate(),y:d.getYCoordinate()},interfaces:ports});
    }
    for(var i=0;i<net.getLinkCount();i++){
      var l=net.getLinkAt(i),p=l.getPort1(),q=l.getPort2();
      links.push({from:p.getOwnerDevice().getName(),fromInterface:p.getName(),to:q.getOwnerDevice().getName(),toInterface:q.getName(),cable:l.getConnectionType()});
    }
    return {nodes:nodes,links:links};'''
    return js(code)

def policy_rows():
    # Explicit transcription of the agreed policy; protocol support is distinguished from tested behavior.
    rows=[
      ('p01','Client VLANs 10/20/30','DHCP server through relay/renewal','UDP','68 → 67','permit','Client ingress ACLs and SERVICES-IN','N01,N02,N03,N04','Server responses use 67 → 67 for relay and 67 → 68 for direct client replies.'),
      ('p02','Client VLANs 10/20/30','SRV-CAMPUS','DNS','UDP/TCP 53','permit','Client ingress ACLs and SERVICES-IN','N08','UDP DNS was exercised; TCP DNS remains not-run.'),
      ('p03','Client VLANs 10/20/30','SRV-CAMPUS','TCP','80','permit','Client ingress ACLs and SERVICES-IN','N07,N08','HTTP is unencrypted; this is a connectivity demonstration.'),
      ('p04','Client VLANs 10/20/30','SRV-CAMPUS','ICMP','echo / echo-reply','permit','Client ingress ACLs and SERVICES-IN','N06','Server echo requests toward clients are handled separately.'),
      ('p05','Each client VLAN','Own gateway','ICMP','echo','permit','Source subinterface ingress ACL','N05','Gateway diagnosis is allowed.'),
      ('p06','Administration VLAN 10','Faculty and Student subnets','ICMP','echo / echo-reply','permit','ADMIN-IN with departmental reply permits','N09','This does not permit arbitrary Administration-initiated application sessions.'),
      ('p07','PC8-MGMT 192.168.10.2','R1 .1, SW1 .3, SW2 .4','TCP','22','permit','ADMIN-IN where routed; VTY ACL 1 on all IOS devices','N14','Local user authentication and SSHv2 are still required.'),
      ('p08','Any source except PC8-MGMT','Network-device VTYs','TCP','22','deny','VTY ACL 1; routed ingress ACLs where applicable','N15,N16','PC9-to-switch controls share VLAN 10 and bypass the router.'),
      ('p09','Faculty VLAN 20','Administration and Students','IP','new routed traffic','deny','FACULTY-IN','N11','Echo replies to Administration and allowed DHCP traffic are exceptions.'),
      ('p10','Students VLAN 30','Administration and Faculty','IP','new routed traffic','deny','STUDENTS-IN','N10','Echo replies to Administration and allowed DHCP traffic are exceptions.'),
      ('p11','SRV-CAMPUS','Client subnets','UDP/TCP/ICMP','DHCP; DNS replies; HTTP replies; echo-reply','permit','SERVICES-IN','N04,N06,N07,N08','Stateless packet matching; TCP established checks ACK/RST flags.'),
      ('p12','SRV-CAMPUS','Own gateway 192.168.10.49','ICMP','echo / echo-reply','permit','SERVICES-IN','N12','Allowed for server gateway diagnosis.'),
      ('p13','SRV-CAMPUS','Client subnets','IP','new application sessions / ICMP echo','deny','SERVICES-IN','N13','The ICMP initiation case was exercised against a known-live Student PC.'),
      ('p14','Any routed source','Traffic not explicitly listed','IP','any other traffic','deny','Explicit final deny in all four routed ingress ACLs','N10,N11,N13,N16','Router ACLs do not inspect same-VLAN forwarding.'),
      ('p15','PC8-MGMT','R1, SW1 and SW2','TCP','23','deny','SSH-only VTY transport; ingress ACL where applicable','N17','Telnet is not enabled even for the management workstation.'),
      ('p16','Two endpoints in the same VLAN','Each other','Layer 2/IP','ordinary local communication','permit','Layer 2 switching; router ACLs are not traversed','N18','Students are not isolated from other Students in this design.'),
    ]
    return [dict(id=i,source=s,destination=d,protocol=p,portOrType=port,action=a,enforcementPoint=e,testIds=tests.split(','),caveat=c) for i,s,d,p,port,a,e,tests,c in rows]

def build():
    results=read('results.json');assert len(results)==19 and all(x['status']=='pass' for x in results.values())
    meta=read('run.json');raw=raw_inventory();write('verified-inventory.json',raw)
    live_leases=leases();write('leases-final.json',live_leases)
    raw_pools=pools();write('dhcp-pools-final.json',raw_pools)
    configs={n:show(n,'show running-config') for n in IOS}
    for n,c in configs.items():
        clean='\n'.join('[REDACTED LAB CREDENTIAL]' if re.search(r'\b(secret|password)\b',l) else l for l in c.splitlines())
        (BASE/'configs'/(n+'.txt')).write_text(clean+'\n',encoding='utf-8')
        write(n+'-final-state.json',{'configuration':clean,'interfaces':show(n,'show ip interface brief'),'ssh':show(n,'show ip ssh'),'aclCounters':show(n,'show access-lists')})
    nodes=[]
    observed_time=now()
    vlan_for=lambda i:30 if i<5 else 20 if i<8 else 10
    for r in raw['nodes']:
        name=r['name'];ident=IDS[name]
        blocks=config_interfaces(configs.get(name,''))
        role=ROLES.get(ident,'Student DHCP client' if int(ident[2:])<5 else 'Faculty DHCP client') if ident.startswith('pc') else ROLES[ident]
        node=dict(id=ident,label=name,model=r['model'],role=role,position=r['position'],interfaces=[])
        if name in IOS:node['configurationRef']='configs/'+name+'.txt'
        if ident.startswith('pc'):node['vlanId']=vlan_for(int(ident[2:]))
        if ident=='server0':node['vlanId']=40
        for p in r['interfaces']:
            block=blocks.get(p['name'],'')
            kind='subinterface' if '.' in p['name'] else 'svi' if p['name'].startswith('Vlan') else 'physical'
            admin='down' if re.search(r'^ shutdown$',block,re.M) else 'up'
            port=dict(name=p['name'],kind=kind,administrativeState=admin,recordedOperationalState='up' if p['portUp'] and p['protocolUp'] else 'down',observedAt=observed_time)
            if p.get('address') not in [None,'','0.0.0.0']:
                port['ipv4']=p['address'];port['prefixLength']=ipaddress.ip_network('0.0.0.0/'+p['mask']).prefixlen
            if re.search(r'^ switchport mode trunk$',block,re.M):
                port.update(mode='trunk',trunkVlans=[10,20,30,40],nativeVlan=1)
                assert 'switchport trunk allowed vlan 10,20,30,40' in block,(name,p['name'])
            elif name.startswith('SW') and kind=='physical':
                match=re.search(r'^ switchport access vlan (\d+)$',block,re.M)
                port.update(mode='access',accessVlan=int(match.group(1)) if match else 1)
            if kind=='subinterface':port['vlanId']=int(p['name'].split('.')[-1])
            if ident.startswith('pc') or ident=='server0':
                v=live_leases[name];port['assignment']='dhcp' if v['dhcp'] else 'static';port['vlanId']=node['vlanId']
                port['defaultGateway']={10:'192.168.10.1',20:'192.168.10.17',30:'192.168.10.33',40:'192.168.10.49'}[node['vlanId']]
                port['dnsServer']=v['dns']
                if v['dhcp']:
                    # The lease is an observation, never a promised permanent address.
                    port.pop('ipv4',None);port.pop('prefixLength',None)
                    port.update(poolId={10:'ADMIN_POOL',20:'FACULTY_POOL',30:'STUDENT_POOL'}[node['vlanId']],observedLease=dict(ipv4=v['address'],prefixLength=28,defaultGateway=port['defaultGateway'],dnsServer=v['dns'],observedAt=observed_time,evidenceRef='evidence/'+RUN_ID+'/leases-final.json'))
            node['interfaces'].append(port)
        nodes.append(node)
    links=[]
    for r in raw['links']:
        a,b=IDS[r['from']],IDS[r['to']]
        trunk=(a,b) in [('r1','sw1'),('sw1','sw2')]
        endpoint=a if a.startswith('pc') or a=='server0' else b
        vid=40 if endpoint=='server0' else vlan_for(int(endpoint[2:])) if endpoint.startswith('pc') else None
        lid='l-r1-sw1' if (a,b)==('r1','sw1') else 'l-sw1-sw2' if (a,b)==('sw1','sw2') else 'l-'+endpoint
        links.append(dict(id=lid,sourceDeviceId=a,sourceInterface=r['fromInterface'],targetDeviceId=b,targetInterface=r['toInterface'],cableType={8100:'copper-straight-through',8101:'copper-crossover'}[r['cable']],mode='trunk' if trunk else 'access',vlanIds=[10,20,30,40] if trunk else [vid]))
    vlans=[]
    for vid,name,start,gateway,poolid in [(10,'ADMINISTRATION',0,1,'ADMIN_POOL'),(20,'FACULTY',16,17,'FACULTY_POOL'),(30,'STUDENTS',32,33,'STUDENT_POOL'),(40,'SERVICES',48,49,None)]:
        v=dict(id=vid,name=name,subnet=f'192.168.10.{start}/28',mask='255.255.255.240',wildcard='0.0.0.15',gateway=f'192.168.10.{gateway}',broadcast=f'192.168.10.{start+15}',usableHosts=14)
        if poolid:v['poolId']=poolid
        vlans.append(v)
    normalized_pools=[]
    for p in raw_pools:
        vid={'ADMIN_POOL':10,'FACULTY_POOL':20,'STUDENT_POOL':30,'serverPool':40}[p['name']]
        normalized_pools.append(dict(id=p['name'],vlanId=vid,start=p['start'],end=p['end'],mask=p['mask'],gateway=p['gateway'],dnsServer=p['dns'],maxUsers=p['maxUsers'],purpose='client-leases' if vid!=40 else 'harmless-simulator-default',inUse=vid!=40))
    tests=[]
    for tid,r in sorted(results.items()):
        cases=json.loads(json.dumps(r['cases']))
        context=read('leases-reopened.json') if tid=='N19' else read('N04-renewal.json')['leases']
        context_ref='leases-reopened.json' if tid=='N19' else 'N04-renewal.json'
        for c in cases:
            if c.get('source') in IDS:
                c['sourceDeviceId']=IDS[c['source']]
                observed=c.get('observed',{})
                c['sourceIp']=observed.get('address',context[c['source']]['address'])
                c['sourceAddressBasis']='Recorded run lease/static-address context'
                c['sourceAddressEvidenceRef']='evidence/'+RUN_ID+'/'+('results.json' if observed.get('address') else context_ref)
        t=dict(id=tid,runId=RUN_ID,expected=r['expected'],observed=f"{sum(c.get('passed') is True for c in r['cases'])}/{len(r['cases'])} checks matched the expected outcome.",status=r['status'],observedAt=r['observedAt'],cases=cases,evidenceRefs=['evidence/'+RUN_ID+'/'+ref for ref in r['evidenceRefs']])
        if 'notes' in r:t['notes']=r['notes']
        tests.append(t)
    before=read('N19-before-renew.json');auto=read('N19-before-explicit-renew.json')
    snapshot=dict(schemaVersion='1.0.0',snapshotId='secure-campus-v1-20261030',capturedAt=observed_time,packetTracerVersion=meta['version'],submissionFile=meta['submissionFile'],submissionSha256=meta['submissionSha256'],testRunId=RUN_ID,projectTitle='Design and Implementation of a Secure Campus Network with Centralized Services',recordingMode='verified-snapshot',devices=sorted(nodes,key=lambda x:x['id']),links=links,vlans=vlans,dhcpPools=normalized_pools,policies=policy_rows(),recordedTests=tests,services=dict(serverDeviceId='server0',ipv4='192.168.10.50',dns=dict(enabled=True,records=[dict(name='portal.campus.test',type='A',value='192.168.10.50')],verifiedTransports=['UDP'],unverifiedTransports=['TCP']),http=dict(enabled=True,url='http://portal.campus.test',port=80),dhcp=dict(enabled=True,poolIds=[p['id'] for p in normalized_pools]),ssh=dict(deviceIds=['r1','sw1','sw2'],version=2,configuredRsaModulusBits=2048,authorizedSourceDeviceId='pc8',port=22)),limitations=['This is recorded Packet Tracer evidence, not live network telemetry.','Four equal /28 allocations demonstrate FLSM, not VLSM.','Same-VLAN forwarding bypasses router ACLs; Student-to-Student communication remains permitted.','ACLs are stateless: echo-reply and TCP ACK/RST matching do not prove connection state.','DNS over TCP is configured by ACL but not exercised end to end in this run.','The router, trunks and centralized server are single points of failure.','HTTP carries unencrypted application content.'],dhcpReopenBehavior=dict(stpConvergenceSeconds=read('N19-trunk-convergence.json')['waitSeconds'],beforeRenew={n:before[n]['address'] for n in CLIENTS if n!='PC8-MGMT'},afterConvergenceBeforeExplicitRenew={n:auto[n]['address'] for n in CLIENTS if n!='PC8-MGMT'},recoveryAction='Allow trunk convergence, then reselect DHCP in Desktop > IP Configuration, or use ipconfig /renew; PC8-MGMT remains static.',evidenceRefs=['evidence/'+RUN_ID+'/N19-before-renew.json','evidence/'+RUN_ID+'/N19-before-explicit-renew.json','evidence/'+RUN_ID+'/leases-reopened.json']))
    # Register actual screenshot and protocol evidence with the corresponding test rows.
    additions={'N01':['N01-PC9-DHCP.png'],'N07':['N07-PC9-browser.png'],'N08':['N08-PC9-browser.png','simulation-dns.json','simulation-http.json'],'N04':['simulation-dhcp.json','simulation-dhcp-summary.json'],'N09':['N09-N10-pdu-results.png','simulation-admin-icmp.json'],'N10':['N09-N10-pdu-results.png','simulation-icmp.png','simulation-student-denied.json'],'N19':['N19-reopened.png','N19-PC9-denied-SSH.png']}
    for t in snapshot['recordedTests']:
        for ref in additions.get(t['id'],[]):
            if (RUN/ref).exists():t['evidenceRefs'].append('evidence/'+RUN_ID+'/'+ref)
    refs={r for t in snapshot['recordedTests'] for r in t['evidenceRefs']}
    refs.add('evidence/'+RUN_ID+'/topology.png')
    refs.update('evidence/'+RUN_ID+'/'+f for f in ['results.json','run.json','leases-final.json','simulation-summary.json'])
    refs.update(n['configurationRef'] for n in nodes if 'configurationRef' in n)
    snapshot['evidence']=[dict(id='ev'+str(i+1),path=ref,sha256=hashlib.sha256((BASE/ref).read_bytes()).hexdigest(),mediaType='image/png' if ref.endswith('.png') else 'application/json' if ref.endswith('.json') else 'text/plain') for i,ref in enumerate(sorted(refs))]
    data_path=BASE/'data'/'network-snapshot.v1.json'
    text=json.dumps(snapshot,indent=2,ensure_ascii=False)+'\n'
    assert SECRET not in text and '$1$' not in text
    data_path.write_text(text,encoding='utf-8')
    print('Snapshot written:',len(nodes),'devices,',len(links),'links,',len(tests),'tests',flush=True)

if __name__=='__main__':build()
