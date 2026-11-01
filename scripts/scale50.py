"""Expand the existing submission through Packet Tracer's local scripting API."""
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
from n4_runner import SECRET as LAB_SECRET

RUN = BASE / 'evidence' / 'SCALE50-20261031'
RUN.mkdir(exist_ok=True)
FILE = BASE / 'Secure_Campus_Network_Submission.pkt'
IOS = ['R1-CAMPUS', 'SW1-CORE', 'SW2-ACCESS', 'SW3-FACULTY', 'SW4-STUDENTS']
GROUPS = {10: ['PC8-MGMT', 'PC9-ADMIN'] + [f'PC{i}' for i in range(40, 50)],
          20: [f'PC{i}' for i in range(5, 8)] + [f'PC{i}' for i in range(25, 40)],
          30: [f'PC{i}' for i in range(5)] + [f'PC{i}' for i in range(10, 25)]}
HOSTS = sum(GROUPS.values(), []) + ['SRV-CAMPUS']
NETS = {10: ('192.168.10.96', '255.255.255.224', '0.0.0.31', '192.168.10.97', '192.168.10.127'),
        20: ('192.168.10.64', '255.255.255.224', '0.0.0.31', '192.168.10.65', '192.168.10.95'),
        30: ('192.168.10.0', '255.255.255.192', '0.0.0.63', '192.168.10.1', '192.168.10.63'),
        40: ('192.168.10.128', '255.255.255.240', '0.0.0.15', '192.168.10.129', '192.168.10.143')}
ACLS = {10: 'ADMIN-IN', 20: 'FACULTY-IN', 30: 'STUDENTS-IN', 40: 'SERVICES-IN'}
SERVER = '192.168.10.130'
MGMT = '192.168.10.98'

def write(name, obj):
    (RUN / name).write_text(json.dumps(obj, indent=2), encoding='utf-8')

def checked(name, args):
    result = call(name, args)
    assert result.get('success'), result
    return result

def execute(name, commands):
    commands = [s.strip() for s in commands if s.strip()]
    out = js('var d=ipc.network().getDevice('+json.dumps(name)+');d.skipBoot();d.enterCommand("end","enable");var out=[];for(var c of '+json.dumps(commands)+'){var r=d.enterCommand(c,"");out.push({command:c,output:r.second,status:r.first});}return out;')
    errors = [r for r in out if re.search(r'% (Invalid|Incomplete|Ambiguous)|overlaps with|Error:', r['output'])]
    safe = [{**r, 'command': '[REDACTED]' if re.search(r'\b(secret|password)\b', r['command']) else r['command'],
             'output': '\n'.join('[REDACTED]' if re.search(r'\b(secret|password)\b', s) else s for s in r['output'].splitlines())} for r in out]
    write(name+'-last-commands.json', safe)
    assert not errors, [(r['command'], r['output']) for r in errors]
    print(name, len(commands), 'commands accepted', flush=True)

def show(name, command):
    return js('return ipc.network().getDevice('+json.dumps(name)+').enterCommand('+json.dumps(command)+',"enable").second;')

def backup():
    archive = RUN / 'campus-before-expansion.zip'
    if archive.exists():
        print('Existing pre-expansion archive retained', flush=True)
        return
    paths = [FILE, BASE/'Secure_Campus_Network.pkt', BASE/'evidence/N3-checkpoint.pkt',
             BASE.parent/'Project/Secure_Campus_Network.pkt', BASE.parent/'Project/Secure_Campus_Network_Final.pkt',
             BASE.parent/'Lab/Packet Tracer/Secure_Campus_Network.pkt']
    manifest=[]
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in paths:
            if p.exists():
                rel=str(p.relative_to(BASE.parent))
                data=p.read_bytes()
                z.writestr(rel, data)
                manifest.append(dict(path=rel, bytes=len(data), sha256=hashlib.sha256(data).hexdigest()))
    write('original-files.json', manifest)
    assert zipfile.ZipFile(archive).testzip() is None
    print('Archived', len(manifest), 'original campus files', flush=True)

def inventory():
    return js('var net=ipc.network();var a=[];for(var i=0;i<net.getDeviceCount();i++){var d=net.getDeviceAt(i);a.push({name:d.getName(),type:d.getType()});}return {file:ipc.appWindow().getActiveFile().getSavedFilename(),devices:a,links:net.getLinkCount()};')

def build():
    active=inventory()
    assert Path(active['file']).resolve()==FILE.resolve(), active['file']
    backup()
    write('before.json', active)
    for i in range(10, 50):
        if f'PC{i}' not in {d['name'] for d in inventory()['devices']}:
            checked('addDevice', dict(deviceName=f'PC{i}', deviceModel='PC-PT', x=100, y=100))
        if i%10==9: print('PCs created through PC'+str(i), flush=True)
    names={d['name'] for d in inventory()['devices']}
    for n in IOS[3:]:
        if n not in names: checked('addDevice', dict(deviceName=n, deviceModel='2960-24TT', x=100, y=100))
    # Replace the old cable map as part of the authorized in-place expansion.
    js('var net=ipc.network();for(var i=net.getLinkCount()-1;i>=0;i--)net.getLinkAt(i).getPort1().deleteLink();return net.getLinkCount();')
    links=[('R1-CAMPUS','GigabitEthernet0/0','SW1-CORE','GigabitEthernet0/1','straight'),
           ('SW1-CORE','GigabitEthernet0/2','SW2-ACCESS','GigabitEthernet0/1','cross'),
           ('SW1-CORE','FastEthernet0/23','SW3-FACULTY','GigabitEthernet0/1','cross'),
           ('SW1-CORE','FastEthernet0/24','SW4-STUDENTS','GigabitEthernet0/1','cross'),
           ('SRV-CAMPUS','FastEthernet0','SW1-CORE','FastEthernet0/1','straight')]
    for vlan, sw in [(10,'SW2-ACCESS'),(20,'SW3-FACULTY'),(30,'SW4-STUDENTS')]:
        links.extend((n,'FastEthernet0',sw,f'FastEthernet0/{i+1}','straight') for i,n in enumerate(GROUPS[vlan]))
    for a,pa,b,pb,t in links:
        checked('addLink', dict(device1Name=a,device1Interface=pa,device2Name=b,device2Interface=pb,linkType=t))
    positions={'R1-CAMPUS':(850,120),'SW1-CORE':(850,260),'SRV-CAMPUS':(1150,140),
               'SW2-ACCESS':(260,460),'SW3-FACULTY':(850,460),'SW4-STUDENTS':(1440,460)}
    for vlan,left in [(10,40),(20,630),(30,1220)]:
        for i,n in enumerate(GROUPS[vlan]): positions[n]=(left+(i%4)*125,630+(i//4)*125)
    for n,(x,y) in positions.items(): checked('moveDevice', dict(deviceName=n,x=x,y=y))
    write('port-map.json', links)
    write('after-topology.json', inventory())
    print('Topology: 50 PCs, four switches, router, server;',len(links),'links',flush=True)

def configure():
    for idx,n in enumerate(IOS[1:]):
        cmds=['enable','configure terminal',f'hostname {n}','no ip domain-lookup','ip domain-name campus.test',
              'service password-encryption',f'enable secret {LAB_SECRET}',f'username netadmin secret {LAB_SECRET}']
        for v,label in [(10,'ADMINISTRATION'),(20,'FACULTY'),(30,'STUDENTS'),(40,'SERVICES')]:
            cmds += [f'vlan {v}',f'name {label}','exit']
        cmds += ['interface range fastEthernet0/1 - 24','shutdown','switchport mode access','switchport access vlan 1',
                 'no spanning-tree portfast','no spanning-tree bpduguard enable','exit',
                 'interface range gigabitEthernet0/1 - 2','shutdown','switchport mode access','switchport access vlan 1','exit']
        trunks = [('gigabitEthernet0/1','10,20,30,40'),('gigabitEthernet0/2','10'),('fastEthernet0/23','10,20'),('fastEthernet0/24','10,30')] if idx==0 else [('gigabitEthernet0/1',{1:'10',2:'10,20',3:'10,30'}[idx])]
        for p,vlans in trunks:
            cmds += [f'interface {p}','switchport mode trunk',f'switchport trunk allowed vlan {vlans}','no shutdown','exit']
        vlan,count=(40,1) if idx==0 else {1:(10,12),2:(20,18),3:(30,20)}[idx]
        cmds += [f'interface range fastEthernet0/1 - {count}' if count>1 else 'interface fastEthernet0/1',
                 'switchport mode access',f'switchport access vlan {vlan}','spanning-tree portfast','spanning-tree bpduguard enable','no shutdown','exit',
                 'interface vlan 10','no ip address',f'ip address 192.168.10.{99+idx} 255.255.255.224','no shutdown','exit',
                 'ip default-gateway 192.168.10.97','no access-list 1',f'access-list 1 permit host {MGMT}','access-list 1 deny any',
                 'line vty 0 15','login local','transport input ssh','access-class 1 in','exec-timeout 5 0','exit']
        if idx>=2:cmds+=['crypto key generate rsa general-keys modulus 2048']
        cmds += ['ip ssh version 2','ip ssh time-out 60','ip ssh authentication-retries 2','end','write memory']
        execute(n,cmds)
    cmds=['enable','configure terminal']
    for v in (10,20,30,40):
        cmds += [f'interface gigabitEthernet0/0.{v}',f'no ip access-group {ACLS[v]} in','no ip address']
        if v!=40:cmds+=['no ip helper-address 192.168.10.50']
        cmds+=['exit']
    for acl in ACLS.values():cmds += [f'no ip access-list extended {acl}']
    cmds += ['no access-list 1',f'access-list 1 permit host {MGMT}','access-list 1 deny any']
    for v,(net,mask,wild,gw,bc) in NETS.items():
        cmds += [f'interface gigabitEthernet0/0.{v}',f'encapsulation dot1Q {v}',f'ip address {gw} {mask}']
        if v!=40:cmds += [f'ip helper-address {SERVER}']
        cmds += [f'ip access-group {ACLS[v]} in','exit']
    for v in (10,20,30):
        net,mask,wild,gw,bc=NETS[v]; src=f'{net} {wild}'
        cmds += [f'ip access-list extended {ACLS[v]}',
                 'permit udp any eq bootpc host 255.255.255.255 eq bootps',f'permit udp any eq bootpc host {bc} eq bootps',
                 f'permit udp {src} eq bootpc host {SERVER} eq bootps',f'permit icmp {src} host {gw} echo']
        if v==10:cmds += [f'permit tcp host {MGMT} host {gw} eq 22']
        cmds += [f'permit udp {src} host {SERVER} eq domain',f'permit tcp {src} host {SERVER} eq domain',
                 f'permit tcp {src} host {SERVER} eq www',f'permit icmp {src} host {SERVER} echo']
        if v==10:
            for dest in (20,30):cmds += [f'permit icmp {src} {NETS[dest][0]} {NETS[dest][2]} echo']
        else:cmds += [f'permit icmp {src} {NETS[10][0]} {NETS[10][2]} echo-reply']
        cmds += ['deny ip any any','exit']
    cmds += ['ip access-list extended SERVICES-IN']
    for v in (10,20,30):
        net,mask,wild,gw,bc=NETS[v];dest=f'{net} {wild}'
        cmds += [f'permit udp host {SERVER} eq bootps host {gw} eq bootps',f'permit udp host {SERVER} eq bootps {dest} eq bootpc',
                 f'permit udp host {SERVER} eq domain {dest}',f'permit tcp host {SERVER} eq domain {dest} established',
                 f'permit tcp host {SERVER} eq www {dest} established',f'permit icmp host {SERVER} {dest} echo-reply']
    cmds += [f'permit udp host {SERVER} eq bootps host 255.255.255.255 eq bootpc',
             f'permit icmp host {SERVER} host 192.168.10.129 echo',f'permit icmp host {SERVER} host 192.168.10.129 echo-reply',
             'deny ip any any','exit','interface gigabitEthernet0/0','no shutdown','exit','end','write memory']
    execute('R1-CAMPUS',cmds)

def services():
    checked('configurePcIp',dict(deviceName='SRV-CAMPUS',dhcpEnabled=False,ipaddress=SERVER,subnetMask=NETS[40][1],defaultGateway=NETS[40][3],dnsServer=SERVER))
    checked('configurePcIp',dict(deviceName='PC8-MGMT',dhcpEnabled=False,ipaddress=MGMT,subnetMask=NETS[10][1],defaultGateway=NETS[10][3],dnsServer=SERVER))
    js('for(var n of ["SRV-CAMPUS","PC8-MGMT"])ipc.network().getDevice(n).getProcess("DnsClient").setServerIp('+json.dumps(SERVER)+');return true;')
    pools=[('ADMIN_POOL',10,103,24),('FACULTY_POOL',20,66,29),('STUDENT_POOL',30,2,61)]
    code='var s=ipc.network().getDevice("SRV-CAMPUS");var dh=s.getProcess("DhcpServerMain").getDhcpServerProcessByPortName("FastEthernet0");var names=[];for(var i=0;i<dh.getPoolCount();i++)names.push(dh.getPoolAt(i).getDhcpPoolName());for(var n of names)dh.removePool(n);'
    for name,v,start,count in pools:
        args=[name,NETS[v][3],SERVER,f'192.168.10.{start}',NETS[v][1],count,'0.0.0.0','0.0.0.0']
        code+='dh.addNewPool('+','.join(json.dumps(x) for x in args)+');'
    code+='dh.setEnable(true);var dns=s.getProcess("DnsServer");dns.setEnable(true);dns.removeARecordFromNameServerDb("portal.campus.test","192.168.10.50");dns.addARecordToNameServerDb("portal.campus.test","'+SERVER+'");s.getProcess("HttpServer").setEnable(true);return true;'
    js(code)
    # Packet Tracer recreates this built-in pool when a file is loaded unless
    # it is saved explicitly. Keep it bounded and outside the client VLANs.
    js('var dh=ipc.network().getDevice("SRV-CAMPUS").getProcess("DhcpServerMain").getDhcpServerProcessByPortName("FastEthernet0");var p=dh.getPool("serverPool");if(!p){dh.addNewPool("serverPool","192.168.10.129","192.168.10.130","192.168.10.131","255.255.255.240",1,"0.0.0.0","0.0.0.0");p=dh.getPool("serverPool");}p.setNetworkMask("192.168.10.128","255.255.255.240");p.setStartIp("192.168.10.131");p.setEndIp("192.168.10.131");p.setMaxUsers(1);p.setDefaultRouter("192.168.10.129");p.setDnsServerIp("192.168.10.130");p.setNextAvailableIpAddress("192.168.10.131");return true;')
    page=(BASE/'campus_index.html').read_text(encoding='utf-8').replace('192.168.10.50',SERVER)
    js('ipc.network().getDevice("SRV-CAMPUS").getProcess("HttpServer").setPageContents("index.html",'+json.dumps(page)+');return true;')
    for n in HOSTS:
        if n in ('PC8-MGMT','SRV-CAMPUS'):continue
        checked('configurePcIp',dict(deviceName=n,dhcpEnabled=True))
        js('var d=ipc.network().getDevice('+json.dumps(n)+');d.getProcess("DhcpClient").dhcpRelease("FastEthernet0");d.getProcess("DhcpClient").dhcpRun("FastEthernet0");return true;')
    print('Requested 49 DHCP leases; server and management remain static',flush=True)

def leases():
    return js('var out={};for(var n of '+json.dumps(HOSTS)+'){var d=ipc.network().getDevice(n),p=d.getPort("FastEthernet0");out[n]={ip:p.getIpAddress(),mask:p.getSubnetMask(),dns:d.getProcess("DnsClient").getServerIp(),dhcp:p.isDhcpClientOn()};}return out;')

def capture():
    state=leases();write('leases.json',state)
    for v,names in GROUPS.items():
        subnet=ipaddress.ip_network(NETS[v][0]+'/'+NETS[v][1])
        for n in names:
            assert ipaddress.ip_address(state[n]['ip']) in subnet.hosts(), (n,state[n])
            assert state[n]['mask']==NETS[v][1] and state[n]['dns']==SERVER,(n,state[n])
    assert len({d['ip'] for d in state.values()})==51
    inv=inventory();assert len([d for d in inv['devices'] if d['type']==8])==50
    assert len([d for d in inv['devices'] if d['type'] in (0,1,8,9)])==56
    assert inv['links']==55
    write('inventory.json',inv)
    for n in IOS:
        data={c:show(n,c) for c in ['show running-config','show startup-config','show ip interface brief','show ip ssh']+(['show interfaces trunk','show vlan brief'] if n!='R1-CAMPUS' else ['show access-lists'])}
        data={c:'\n'.join('[REDACTED LAB CREDENTIAL]' if re.search(r'\b(secret|password)\b',s) else s for s in t.splitlines()) for c,t in data.items()}
        write(n+'-verification.json',data)
        (BASE/'configs'/(n+'.txt')).write_text(data['show running-config'],encoding='utf-8')
    print('Validated 50 PCs, 56 network devices, 55 links, 51 unique endpoint addresses',flush=True)

def save():
    js('for(var n of '+json.dumps(IOS)+')ipc.network().getDevice(n).enterCommand("write memory","enable");ipc.appWindow().fileSave();return true;')
    sha=hashlib.sha256(FILE.read_bytes()).hexdigest().upper()
    (BASE/'SUBMISSION_SHA256.txt').write_text(sha+'  '+FILE.name+'\n',encoding='utf-8')
    write('submission.json',dict(file=FILE.name,sha256=sha,bytes=FILE.stat().st_size))
    print('Saved existing submission:',FILE.name,FILE.stat().st_size,'bytes',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['build','configure','services','capture','save','leases'])
    args=parser.parse_args()
    if args.stage=='leases':print(json.dumps(leases(),indent=2))
    else:globals()[args.stage]()
