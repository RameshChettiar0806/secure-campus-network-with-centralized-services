"""Add and verify the smallest OSPF/PAT branch on the existing campus.

Requires the local pt_bridge.py server and the session PROJECT: scripting adapter.
Stages never rebuild the campus or renew all DHCP leases unnecessarily.
"""
import argparse
import hashlib
import ipaddress
import json
import re
import time
import zipfile
from pathlib import Path

from project_api import js, BASE
from pt_client import call
import scale50 as campus
import n4_runner as lab
import scale50_verify as checks

RUN = BASE / 'evidence' / 'OSPF-PAT-20261102'
FILE = BASE / 'Secure_Campus_Network_Submission.pkt'
ROUTER = 'R2-EXTERNAL'
SERVER = 'SRV-EXTERNAL'
TARGET = '203.0.113.10'
PUBLIC = '198.51.100.1'
RUN.mkdir(exist_ok=True)
campus.RUN = RUN


def write(name, value):
    def sanitize(item):
        if isinstance(item, dict): return {k:sanitize(v) for k,v in item.items()}
        if isinstance(item, list): return [sanitize(v) for v in item]
        if isinstance(item, str):
            return '\n'.join('[REDACTED LAB CREDENTIAL]' if re.search(r'^\s*(?:enable secret|username .* secret|password \d)',line) else line for line in item.split('\n')).replace(lab.SECRET,'[REDACTED]')
        return item
    text = json.dumps(sanitize(value), indent=2)
    (RUN / name).write_text(text, encoding='utf-8')


def initialize():
    campus.RUN = RUN
    lab.RUN = RUN
    lab.RUN_ID = 'OSPF-PAT-20261102'
    lab.ALL_HOSTS = campus.HOSTS
    lab.CLIENTS = [n for n in campus.HOSTS if n != 'SRV-CAMPUS']
    lab.IOS = campus.IOS
    lab.initialize()


def inventory():
    return js('var net=ipc.network(),a=[];for(var i=0;i<net.getDeviceCount();i++){var d=net.getDeviceAt(i);a.push({name:d.getName(),type:d.getType()});}return {file:ipc.appWindow().getActiveFile().getSavedFilename(),devices:a,links:net.getLinkCount()};')


def command(device, cmds):
    campus.execute(device, cmds)


def show(device, cmd):
    return campus.show(device, cmd)


def backup():
    assert Path(inventory()['file']).resolve() == FILE.resolve()
    archive = RUN / 'campus-before-ospf-pat.zip'
    if not archive.exists():
        paths = [FILE, BASE/'SUBMISSION_SHA256.txt']
        paths += list((BASE/'configs').glob('*.txt'))
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
            for p in paths:
                if p.exists(): z.write(p, p.relative_to(BASE))
        assert zipfile.ZipFile(archive).testzip() is None
    write('before-inventory.json', inventory())
    write('before-leases.json', campus.leases())
    write('before-router.json', {c: show('R1-CAMPUS', c) for c in ['show running-config','show startup-config','show ip route','show access-lists']})
    print('Recovery archive ready; original campus inventory and leases recorded', flush=True)


def regression(prefix):
    initialize()
    lease = campus.leases()
    write(prefix+'-leases.json', lease)
    assert len(set(v['ip'] for v in lease.values())) == 51
    for vlan, names in campus.GROUPS.items():
        subnet = ipaddress.ip_network(campus.NETS[vlan][0]+'/'+campus.NETS[vlan][1])
        for name in names:
            d = lease[name]
            assert ipaddress.ip_address(d['ip']) in subnet
            assert d['mask'] == campus.NETS[vlan][1] and d['dns'] == campus.SERVER
    groups = {}
    groups['gateway'] = checks.ping_batch({n:'ping '+campus.NETS[v][3] for v,names in campus.GROUPS.items() for n in names},prefix+'-gateway')
    groups['campusPing'] = checks.ping_batch({n:'ping '+campus.SERVER for n in lab.CLIENTS},prefix+'-campus-ping')
    dns = checks.batch({n:'nslookup portal.campus.test' for n in lab.CLIENTS},prefix+'-dns',12)
    for n,d in dns.items():
        d['passed'] = bool(re.search(r'Name:\s+portal\.campus\.test\s+Address:\s+192\.168\.10\.130',d['output'],re.I))
        if not d['passed']:
            retry=checks.batch({n:'nslookup portal.campus.test'},prefix+'-dns-retry-'+n,12)[n]
            d['retry']=retry
            d['passed']=bool(re.search(r'Name:\s+portal\.campus\.test\s+Address:\s+192\.168\.10\.130',retry['output'],re.I))
    write(prefix+'-dns.json',dns)
    groups['dns']=dns
    groups['http']=checks.http_all()
    positive=checks.ping_batch({'PC8-MGMT':'ping '+lease['PC0']['ip'],'PC9-ADMIN':'ping '+lease['PC5']['ip'],'PC0':'ping '+lease['PC24']['ip'],'PC5':'ping '+lease['PC39']['ip']},prefix+'-policy-allow')
    groups['policyAllow']=positive
    denied=[]
    for source,target,acl in [('PC0',campus.MGMT,'STUDENTS-IN'),('PC0',lease['PC5']['ip'],'STUDENTS-IN'),('PC5',campus.MGMT,'FACULTY-IN'),('PC5',lease['PC0']['ip'],'FACULTY-IN'),('SRV-CAMPUS',lease['PC0']['ip'],'SERVICES-IN')]:
        denied.append(lab.ping_case(source,target,False,prefix+'-deny-'+str(len(denied))+'.json',acl))
    groups['policyDeny']={str(i):v for i,v in enumerate(denied)}
    summary={k:{'passed':sum(bool(d.get('passed')) for d in g.values()),'total':len(g)} for k,g in groups.items()}
    summary['allPassed']=all(d.get('passed') for g in groups.values() for d in g.values())
    write(prefix+'-summary.json',summary)
    print(json.dumps(summary),flush=True)
    assert summary['allPassed'], 'Campus regression failed'


def build():
    active=inventory()
    assert Path(active['file']).resolve()==FILE.resolve()
    names={d['name'] for d in active['devices']}
    for name,model,x,y in [(ROUTER,'1941',850,25),(SERVER,'Server-PT',1160,25)]:
        if name not in names:
            r=call('addDevice',dict(deviceName=name,deviceModel=model,x=x,y=y))
            assert r.get('success'),r
    if inventory()['links']==55:
        for a,pa,b,pb in [('R1-CAMPUS','GigabitEthernet0/1',ROUTER,'GigabitEthernet0/0'),(ROUTER,'GigabitEthernet0/1',SERVER,'FastEthernet0')]:
            r=call('addLink',dict(device1Name=a,device1Interface=pa,device2Name=b,device2Interface=pb,linkType='cross'))
            assert r.get('success'),r
    assert inventory()['links']==57
    r=call('configurePcIp',dict(deviceName=SERVER,dhcpEnabled=False,ipaddress=TARGET,subnetMask='255.255.255.0',defaultGateway='203.0.113.1',dnsServer=campus.SERVER))
    assert r.get('success'),r
    page='<html><head><title>Campus External Connectivity Lab</title></head><body><h1>External Connectivity Demonstration</h1><p>This simulated external web server is reached through an OSPF-learned route and campus PAT.</p><p>Server: 203.0.113.10 | Shared campus outside address: 198.51.100.1</p><p>The internal campus portal and department security policy remain available.</p></body></html>'
    js('var s=ipc.network().getDevice('+json.dumps(SERVER)+');s.getProcess("HttpServer").setEnable(true);s.getProcess("HttpServer").setPageContents("index.html",'+json.dumps(page)+');ipc.network().getDevice("SRV-CAMPUS").getProcess("DnsServer").addARecordToNameServerDb("external.campus.test","'+TARGET+'");return true;')
    command(ROUTER,['enable','configure terminal','hostname '+ROUTER,'no ip domain-lookup','interface gigabitEthernet0/0','description OSPF_TRANSIT_TO_R1_Gi0_1','ip address 198.51.100.2 255.255.255.252','no shutdown','exit','interface gigabitEthernet0/1','description EXTERNAL_WEB_SERVER','ip address 203.0.113.1 255.255.255.0','no shutdown','exit','router ospf 1','router-id 2.2.2.2','passive-interface default','no passive-interface gigabitEthernet0/0','network 198.51.100.0 0.0.0.3 area 0','network 203.0.113.0 0.0.0.255 area 0','end','write memory'])
    command('R1-CAMPUS',['enable','configure terminal','interface gigabitEthernet0/1','description OSPF_PAT_TRANSIT_TO_R2_EXTERNAL','ip address 198.51.100.1 255.255.255.252','ip nat outside','no shutdown','exit','router ospf 1','router-id 1.1.1.1','passive-interface default','no passive-interface gigabitEthernet0/1','network 198.51.100.0 0.0.0.3 area 0','exit','ip access-list standard NAT-CLIENTS','permit 192.168.10.0 0.0.0.63','permit 192.168.10.64 0.0.0.31','permit 192.168.10.96 0.0.0.31','exit','ip nat inside source list NAT-CLIENTS interface gigabitEthernet0/1 overload']+[c for v in (10,20,30) for c in [f'interface gigabitEthernet0/0.{v}','ip nat inside','exit']]+['end','write memory'])
    # Insert only destination-specific external permissions before each existing final deny.
    for v in (10,20,30):
        acl=campus.ACLS[v]
        rows=show('R1-CAMPUS','show access-lists '+acl)
        assert 'deny ip any any' in rows,(acl,rows)
        src=campus.NETS[v][0]+' '+campus.NETS[v][2]
        # This Packet Tracer image omits sequence numbers. Keep every existing
        # permit and move only the explicit final deny after the two additions.
        command('R1-CAMPUS',['enable','configure terminal','ip access-list extended '+acl,'no deny ip any any',f'permit tcp {src} host {TARGET} eq www',f'permit icmp {src} host {TARGET} echo','deny ip any any','end','write memory'])
    command('R1-CAMPUS',['enable','configure terminal','ip access-list extended WAN-IN','permit ospf host 198.51.100.2 any',f'permit tcp host {TARGET} eq www host {PUBLIC} established',f'permit icmp host {TARGET} host {PUBLIC} echo-reply','deny ip any any','exit','interface gigabitEthernet0/1','ip access-group WAN-IN in','end','write memory'])
    write('after-inventory.json',inventory())
    print('Added two devices/two links; configured OSPF, scoped PAT, and destination-specific ACL permissions',flush=True)


def capture(label):
    data={}
    for device in ['R1-CAMPUS',ROUTER]:
        commands=['show running-config','show startup-config','show ip interface brief','show ip route','show ip ospf neighbor','show ip protocols','show access-lists']
        if device=='R1-CAMPUS':commands+=['show ip nat translations','show ip nat statistics']
        data[device]={c:show(device,c) for c in commands}
    write(label+'.json',data)
    return data


def wait_ospf():
    deadline=time.monotonic()+55
    while time.monotonic()<deadline:
        routes=show('R1-CAMPUS','show ip route')
        neighbors=show('R1-CAMPUS','show ip ospf neighbor')
        if re.search(r'^O\s+203\.0\.113\.0/24',routes,re.M) and 'FULL' in neighbors:
            return {'routes':routes,'neighbors':neighbors}
        js('ipc.appWindow().getRealtimeToolbar().fastForwardTime();return true;')
        time.sleep(.3)
    raise AssertionError({'routes':routes,'neighbors':neighbors})


def external_http(names,label):
    js('externalHttp={};for(var n of '+json.dumps(names)+'){var c={events:[],done:function(src,args){this.events.push(args);}};externalHttp[n]=c;var h=ipc.network().getDevice(n).getProcess("HttpClient");h.registerEvent("onDone",c,c.done);h.go("http://external.campus.test");}return true;')
    deadline=time.monotonic()+20
    while True:
        data=js('var out={};for(var n in externalHttp)out[n]={events:externalHttp[n].events,page:ipc.network().getDevice(n).getProcess("HttpClient").getLastPageContent()};return out;')
        if all(d['events'] for d in data.values()) or time.monotonic()>deadline:break
        time.sleep(.3)
    for name,d in data.items():
        d['passed']=any(e.get('serverIp')==TARGET and e.get('url')=='http://external.campus.test' and 'External Connectivity Demonstration' in e.get('content','') for e in d['events'])
        if not d['passed']:
            js('externalHttp['+json.dumps(name)+'].events=[];ipc.network().getDevice('+json.dumps(name)+').getProcess("HttpClient").go("http://external.campus.test");return true;')
            deadline=time.monotonic()+15
            while time.monotonic()<deadline:
                retry=js('return externalHttp['+json.dumps(name)+'].events;')
                if retry:break
                time.sleep(.3)
            d['retry']=retry
            d['passed']=any(e.get('serverIp')==TARGET and 'External Connectivity Demonstration' in e.get('content','') for e in retry)
    write(label+'.json',data)
    print(label,sum(d['passed'] for d in data.values()),'/',len(data),flush=True)
    return data


def verify():
    initialize()
    ospf=wait_ospf();write('ospf-full.json',ospf)
    r2routes=show(ROUTER,'show ip route');assert '192.168.10.' not in r2routes
    write('external-router-routes.json',{'output':r2routes,'noPrivateRoute':True})
    pings=checks.ping_batch({n:'ping '+TARGET for n in lab.CLIENTS},'external-pings')
    http=external_http(lab.CLIENTS,'external-http')
    pat=show('R1-CAMPUS','show ip nat translations')
    stats=show('R1-CAMPUS','show ip nat statistics')
    locals=set(re.findall(r'\b192\.168\.10\.\d+\b',pat))
    assert PUBLIC in pat and len(locals)>=3,pat
    write('pat-translations.json',{'translations':pat,'statistics':stats,'insideLocalAddresses':sorted(locals),'sharedInsideGlobal':PUBLIC})
    # Prove a live but unauthorized external destination remains blocked.
    denied=lab.ping_case('PC0','203.0.113.1',False,'external-other-host-denied.json','STUDENTS-IN')
    original_hosts=lab.ALL_HOSTS
    lab.ALL_HOSTS=campus.HOSTS+[SERVER];lab.initialize()
    wan_before=show('R1-CAMPUS','show access-lists')
    inbound=lab.command(SERVER,'ping '+PUBLIC)
    wan_after=show('R1-CAMPUS','show access-lists')
    changes=lab.delta(wan_before,wan_after)
    wan_pass=bool(re.search(r'Sent = 4, Received = 0',inbound)) and any(k.startswith('WAN-IN |') and ' deny ' in k and v>=4 for k,v in changes.items())
    write('unsolicited-wan-denied.json',{'output':inbound,'counterDelta':changes,'passed':wan_pass})
    lab.ALL_HOSTS=original_hosts;lab.initialize()
    summary={'ospfFull':True,'externalRouteLearned':True,'externalRouterHasNoPrivateRoute':True,'externalPing':{'passed':sum(d['passed'] for d in pings.values()),'total':len(pings)},'externalHttp':{'passed':sum(d['passed'] for d in http.values()),'total':len(http)},'patMultipleInsideAddresses':len(locals),'otherExternalHostDenied':denied['passed'],'unsolicitedWanDenied':wan_pass}
    summary['allPassed']=all(d['passed'] for d in pings.values()) and all(d['passed'] for d in http.values()) and denied['passed'] and wan_pass
    write('extension-summary.json',summary);print(json.dumps(summary),flush=True)
    assert summary['allPassed']


def failure_checks():
    initialize()
    wait_ospf()
    names=['PC0','PC5','PC8-MGMT']
    nat_rule='ip nat inside source list NAT-CLIENTS interface gigabitEthernet0/1 overload'
    try:
        command('R1-CAMPUS',['enable','clear ip nat translation *','configure terminal','no '+nat_rule,'end'])
        off=controlled_ping(names,'pat-disabled',False)
        write('pat-disabled-state.json',{'routes':show('R1-CAMPUS','show ip route'),'translations':show('R1-CAMPUS','show ip nat translations')})
        assert all(d['passed'] for d in off.values())
    finally:
        command('R1-CAMPUS',['enable','configure terminal',nat_rule,'end'])
    on=checks.ping_batch({n:'ping '+TARGET for n in names},'pat-restored')
    assert all(d['passed'] for d in on.values())
    try:
        command('R1-CAMPUS',['enable','configure terminal','router ospf 1','passive-interface gigabitEthernet0/1','end'])
        for _ in range(12):
            js('ipc.appWindow().getRealtimeToolbar().fastForwardTime();return true;')
            route=show('R1-CAMPUS','show ip route')
            if not re.search(r'^O\s+203\.0\.113\.0/24',route,re.M):break
            time.sleep(.1)
        assert not re.search(r'^O\s+203\.0\.113\.0/24',route,re.M)
        write('ospf-disabled-state.json',{'routes':route,'interfaces':show('R1-CAMPUS','show ip interface brief'),'neighbors':show('R1-CAMPUS','show ip ospf neighbor')})
        off=controlled_ping(['PC0'],'ospf-disabled',False)
        assert off['PC0']['passed']
        internal=checks.ping_batch({'PC0':'ping '+campus.SERVER},'campus-during-ospf-outage')
        assert internal['PC0']['passed']
    finally:
        command('R1-CAMPUS',['enable','configure terminal','router ospf 1','no passive-interface gigabitEthernet0/1','end'])
    wait_ospf()
    restored=checks.ping_batch({n:'ping '+TARGET for n in names},'ospf-restored')
    assert all(d['passed'] for d in restored.values())
    write('failure-check-summary.json',{'patDisabledFails':True,'patRestoredWorks':True,'ospfDisabledRemovesRoute':True,'ospfDisabledFails':True,'internalServiceDuringOutageWorks':True,'ospfRestoredWorks':True,'allPassed':True})
    print('Controlled PAT and OSPF failure/restoration checks passed',flush=True)


def controlled_ping(names,label,allowed):
    js('for(var n of '+json.dumps(names)+'){n4Collectors[n].text="";ipc.network().getDevice(n).getCommandPrompt().enterCommand("ping '+TARGET+'");}return true;')
    for _ in range(12):
        js('ipc.appWindow().getRealtimeToolbar().fastForwardTime();return true;')
        time.sleep(.1)
        data=js('var out={};for(var n of '+json.dumps(names)+')out[n]=n4Collectors[n].text;return out;')
        if all('Sent = 4' in text for text in data.values()):break
    output={}
    for name,text in data.items():
        m=re.search(r'Sent = (\d+), Received = (\d+)',text)
        output[name]={'command':'ping '+TARGET,'output':text,'passed':bool(m and int(m[1])==4 and (int(m[2])>0 if allowed else int(m[2])==0))}
    write(label+'.json',output)
    print(label,sum(d['passed'] for d in output.values()),'/',len(output),flush=True)
    return output


def save():
    for device in campus.IOS+[ROUTER]:
        show(device,'write memory')
    js('ipc.appWindow().fileSave();return true;')
    digest=hashlib.sha256(FILE.read_bytes()).hexdigest()
    write('submission.json',dict(file=FILE.name,sha256=digest,bytes=FILE.stat().st_size))
    (BASE/'SUBMISSION_SHA256.txt').write_text(digest.upper()+'  '+FILE.name+'\n')
    for device in ['R1-CAMPUS',ROUTER]:
        config=show(device,'show running-config')
        safe='\n'.join('[REDACTED LAB CREDENTIAL]' if re.search(r'\b(secret|password)\b',line) else line for line in config.splitlines())
        filename = device+'-OSPF-PAT.txt' if device=='R1-CAMPUS' else device+'.txt'
        (BASE/'configs'/filename).write_text(safe,encoding='utf-8')
    print('Saved existing submission; SHA-256 '+digest,flush=True)


def layout():
    # Only the newly added devices move. Existing campus devices retain positions.
    for name,x,y in [(ROUTER,560,100),(SERVER,260,100)]:
        r=call('moveDevice',dict(deviceName=name,x=x,y=y));assert r.get('success'),r
    notes=[(480,10,'SECURE CAMPUS | 50 PCs | 58 NETWORK DEVICES | 57 LINKS'),
           (80,30,'EXTERNAL DEMONSTRATION | +1 router, +1 server\nOSPF area 0 + PAT | external.campus.test'),
           (170,170,'203.0.113.10/24 | HTTP test server\nR2 server gateway: 203.0.113.1'),
           (520,150,'R2 .2 <-> R1 .1 | 198.51.100.0/30\nOSPF transit | PAT outside: 198.51.100.1'),
           (90,360,'ADMINISTRATION | VLAN 10 | 12 PCs\n192.168.10.96/27 | Gateway .97\nPC8-MGMT: static .98 | SSH authorized source'),
           (680,360,'FACULTY | VLAN 20 | 18 PCs\n192.168.10.64/27 | Gateway .65'),
           (1270,360,'STUDENTS | VLAN 30 | 20 PCs\n192.168.10.0/26 | Gateway .1'),
           (1040,220,'SERVICES | VLAN 40 | 192.168.10.128/28\nServer .130 | Gateway .129\nDHCP, DNS, HTTP | portal.campus.test'),
           (400,240,'Existing campus: 802.1Q trunks | VLSM | DHCP relay\nExtended ACLs | Switch management .99-.102 in VLAN 10'),
           (50,1300,'POLICY: Existing department restrictions remain. External access: HTTP/ICMP to 203.0.113.10 only.\nNAT-CLIENTS selects three client subnets; WAN-IN blocks unsolicited inbound traffic.\nFaculty/Student trunks: 100 Mb/s | No redundant paths | Simulated external network, not real Internet.')]
    js('var w=ipc.appWindow().getActiveWorkspace().getLogicalWorkspace();var ids=w.getCanvasNoteIds();for(var id of ids)w.removeCanvasItem(id);for(var n of '+json.dumps(notes)+')w.addNote(n[0],n[1],w.getUnusedLayer(),n[2]);return true;')
    from build_snapshot import raw_inventory
    current=raw_inventory()
    original=json.loads((BASE/'evidence/PING-20261031/inventory.json').read_text())
    def key(link):
        return tuple(sorted([(link['from'],link['fromInterface']),(link['to'],link['toInterface'])]))
    old={key(l) for l in original['links']}
    new={key(l) for l in current['links']}
    assert old <= new and len(new-old)==2,(len(old-new),len(new-old))
    oldpos={d['name']:d['position'] for d in original['nodes']}
    unchanged=all(d['position']==oldpos[d['name']] for d in current['nodes'] if d['name'] in oldpos)
    # Wiring is the invariant; positions may have been adjusted by the user since capture.
    write('topology-preservation.json',{'all55OriginalLinksRetained':True,'addedLinks':2,'networkDevices':len(current['nodes']),'links':len(current['links']),'positionsMatchOctoberCapture':unchanged})
    write('final-inventory.json',current)
    print('Confirmed all 55 original campus links retained; exactly two links added',flush=True)


def persistence():
    initialize()
    before=campus.leases()
    deadline=time.monotonic()+70
    while any(d['ip']=='0.0.0.0' for d in campus.leases().values()) and time.monotonic()<deadline:
        js('ipc.appWindow().getRealtimeToolbar().fastForwardTime();return true;')
        time.sleep(.4)
    names=['PC0','PC5','PC9-ADMIN']
    for name in names:
        js('ipc.network().getDevice('+json.dumps(name)+').getProcess("DhcpClient").dhcpRun("FastEthernet0");return true;')
    time.sleep(3)
    after=campus.leases()
    for v,group in campus.GROUPS.items():
        subnet=ipaddress.ip_network(campus.NETS[v][0]+'/'+campus.NETS[v][1])
        for n in group:
            assert ipaddress.ip_address(after[n]['ip']) in subnet and after[n]['mask']==campus.NETS[v][1] and after[n]['dns']==campus.SERVER
    write('reopened-dhcp-renewal.json',{'before':before,'after':after,'renewedClients':names,'all51EndpointAddressesUnique':len(set(d['ip'] for d in after.values()))==51,'passed':True})
    from n4_apps import ssh_positive
    ssh=[]
    for device,address in [('R1-CAMPUS','192.168.10.97')]+[(n,f'192.168.10.{99+i}') for i,n in enumerate(campus.IOS[1:])]:
        result=ssh_positive('PC8-MGMT',address,device,'reopened-ssh-'+device+'.json');ssh.append(result)
        print('Management SSH',device,result['passed'],flush=True)
    assert all(d['passed'] for d in ssh)
    denied=checks.batch({'PC9-ADMIN':'ssh -l netadmin 192.168.10.99','PC0':'ssh -l netadmin 192.168.10.97','PC5':'ssh -l netadmin 192.168.10.97'},'reopened-ssh-denied',35)
    for d in denied.values():
        d['passed']=bool(re.search(r'Connection (?:timed out|refused|closed)|connect failed|connection failed|closed by foreign host',d['output'],re.I)) and 'Password:' not in d['output']
    write('reopened-ssh-denied.json',denied)
    assert all(d['passed'] for d in denied.values())
    wait_ospf()
    data=capture('reopened-verification')
    assert 'ip nat inside source list NAT-CLIENTS interface GigabitEthernet0/1 overload' in data['R1-CAMPUS']['show startup-config']
    write('persistence-summary.json',{'dhcpRenewal':True,'sshAllowed':len(ssh),'sshDenied':len(denied),'ospfFull':True,'startupPatPresent':True,'allPassed':True})
    print('Reopened DHCP, management controls, OSPF and saved PAT configuration verified',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('stage',choices=['backup','baseline','build','capture','regression','save','verify','failure_checks','layout','persistence'])
    stage=parser.parse_args().stage
    if stage=='baseline':regression('baseline')
    elif stage=='regression':regression('after')
    elif stage=='capture':
        data=capture('verification')
        print(data['R1-CAMPUS']['show ip route'])
        print(data['R1-CAMPUS']['show ip ospf neighbor'])
    else:globals()[stage]()
