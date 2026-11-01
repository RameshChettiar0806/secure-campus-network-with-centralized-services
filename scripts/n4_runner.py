import datetime as dt
import hashlib
import ipaddress
import json
import re
import time
from pathlib import Path

from project_api import js, BASE

RUN_ID = 'N4-20261030'
RUN = BASE / 'evidence' / RUN_ID
SECRET = re.search(r'SSH and enable secret: (.+)', (BASE / 'LAB_CREDENTIALS.txt').read_text()).group(1).strip()
CLIENTS = [f'PC{i}' for i in range(8)] + ['PC8-MGMT', 'PC9-ADMIN']
IOS = ['R1-CAMPUS', 'SW1-CORE', 'SW2-ACCESS']
ALL_HOSTS = CLIENTS + ['SRV-CAMPUS']

def now():
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=5, minutes=30))).isoformat(timespec='seconds')

def write(name, data):
    RUN.mkdir(exist_ok=True)
    text = json.dumps(data, indent=2, ensure_ascii=False).replace(SECRET, '[REDACTED]')
    (RUN / name).write_text(text, encoding='utf-8')

def read(name, default=None):
    p = RUN / name
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else default

def initialize():
    code = '''
    if(typeof n4Collectors !== 'undefined') {
      for(var n in n4Collectors) { try {var t=ipc.network().getDevice(n).getCommandPrompt(), c=n4Collectors[n];t.unregisterEvent('outputWritten',c,c.onOutput);}catch(e){} }
    }
    n4Collectors={};
    for(var n of NAMES){var c={text:'',onOutput:function(src,args){this.text+=args.newOutput;}};n4Collectors[n]=c;ipc.network().getDevice(n).getCommandPrompt().registerEvent('outputWritten',c,c.onOutput);}
    return true;
    '''.replace('NAMES', json.dumps(ALL_HOSTS))
    js(code)

def start(n, c):
    return js('n4Collectors['+json.dumps(n)+'].text="";return ipc.network().getDevice('+json.dumps(n)+').getCommandPrompt().enterCommand('+json.dumps(c)+');')

def output(n):
    return js('return n4Collectors['+json.dumps(n)+'].text;').replace(SECRET, '[REDACTED]')

def wait(n, timeout=25, password=False):
    end = time.monotonic()+timeout
    more = 0
    while time.monotonic() < end:
        text = output(n)
        count = text.count('--More--')
        if count > more:
            js('ipc.network().getDevice('+json.dumps(n)+').getCommandPrompt().enterChar(32,0);return true;')
            more = count
        elif password and re.search(r'Password:\s*$', text):
            return text
        elif re.search(r'(?:C:\\>|[A-Za-z0-9-]+[>#])\s*$', text):
            return text
        time.sleep(.2)
    return output(n)

def command(n, c, timeout=25, password=False):
    start(n, c)
    return wait(n, timeout, password)

def show(n, c):
    return js('return ipc.network().getDevice('+json.dumps(n)+').enterCommand('+json.dumps(c)+',"enable").second;')

def counters():
    return show('R1-CAMPUS', 'show access-lists')

def parse_counters(text):
    result = {}
    acl = None
    for line in text.splitlines():
        header = re.match(r'(?:Extended|Standard) IP access list (\S+)', line)
        if header:
            acl = header.group(1)
        elif acl and re.match(r'\s*\d+\s', line):
            m = re.search(r'\((\d+) match', line)
            rule = re.sub(r'\s*\(\d+ match.*', '', line.strip())
            result[acl+' | '+rule] = int(m.group(1)) if m else 0
    return result

def delta(before, after):
    a, b = parse_counters(before), parse_counters(after)
    return {k:v-a.get(k,0) for k,v in b.items() if v-a.get(k,0)}

def leases():
    return js('var out={};for(var n of '+json.dumps(ALL_HOSTS)+'){var d=ipc.network().getDevice(n),p=d.getPort("FastEthernet0");out[n]={address:p.getIpAddress(),mask:p.getSubnetMask(),dns:d.getProcess("DnsClient").getServerIp(),dhcp:p.isDhcpClientOn(),observedAt:'+json.dumps(now())+'};}return out;')

def pools():
    return js('var s=ipc.network().getDevice("SRV-CAMPUS"),dh=s.getProcess("DhcpServerMain").getDhcpServerProcessByPortName("FastEthernet0"),out=[];for(var i=0;i<dh.getPoolCount();i++){var p=dh.getPoolAt(i);out.push({name:p.getDhcpPoolName(),start:p.getStartIp(),end:p.getEndIp(),mask:p.getSubnetMask(),gateway:p.getDefaultRouter(),dns:p.getDnsServerIp(),maxUsers:p.getMaxUsers()});}return out;')

def record(test_id, expected, cases, evidence, status=None, notes=None):
    data = read('results.json', {})
    passing = all(c.get('passed') is True for c in cases)
    r = dict(id=test_id, runId=RUN_ID, expected=expected, status=status or ('pass' if passing else 'fail'), cases=cases, evidenceRefs=evidence, observedAt=now())
    if notes:r['notes']=notes
    data[test_id]=r
    write('results.json',data)
    print(test_id,r['status'],flush=True)
    return r

def ping_case(source, address, allowed, evidence_name, acl=None):
    before = counters()
    text = command(source, 'ping '+address, timeout=25)
    after = counters()
    changes = delta(before,after)
    m = re.search(r'Sent = (\d+), Received = (\d+)', text)
    sent, received = (int(m.group(1)),int(m.group(2))) if m else (None,None)
    passed = (received is not None and received>0) if allowed else (sent==4 and received==0)
    if acl and not allowed:
        passed = passed and any(k.startswith(acl+' |') and ' deny ' in k and v>0 for k,v in changes.items())
    data=dict(source=source,destination=address,protocol='ICMP',expected='allow' if allowed else 'deny',output=text,aclBefore=before,aclAfter=after,counterDelta=changes,sent=sent,received=received,passed=passed,observedAt=now())
    write(evidence_name,data)
    return {k:v for k,v in data.items() if k not in ['output','aclBefore','aclAfter']}

def preflight():
    meta=js('return {version:ipc.appWindow().getVersion(),file:ipc.appWindow().getActiveFile().getSavedFilename(),simulation:ipc.simulation().isSimulationMode()};')
    assert meta['file'].endswith('/Secure_Campus_Network.pkt'), meta
    js('ipc.simulation().setSimulationMode(false);return true;')
    meta.update(runId=RUN_ID,startedAt=now(),initialFileSha256=hashlib.sha256((BASE/'Secure_Campus_Network.pkt').read_bytes()).hexdigest())
    write('run.json',meta)
    initialize()
    for n in IOS:
        cmds=['show running-config','show startup-config','show ip interface brief','show access-lists','show ip ssh','show line']
        cmds+=['show ip route'] if n=='R1-CAMPUS' else ['show vlan brief','show interfaces trunk','show interfaces status','show spanning-tree vlan 10']
        values={c:show(n,c) for c in cmds}
        for c in ['show running-config','show startup-config']:
            values[c]='\n'.join('[REDACTED LAB CREDENTIAL]' if re.search(r'\b(secret|password)\b',l) else l for l in values[c].splitlines())
        write(n+'-preflight.json',values)
    print('Preflight captured',flush=True)

def network_tests():
    # Reselect DHCP without releasing the statically configured management PC.
    for n in [x for x in CLIENTS if x!='PC8-MGMT']:
        js('var d=ipc.network().getDevice('+json.dumps(n)+');d.setDhcpFlag(true);d.getPort("FastEthernet0").setDhcpClientFlag(true);d.getProcess("DhcpClient").dhcpRun("FastEthernet0");return true;')
    time.sleep(3)
    lease=leases();pool=pools()
    write('leases.json',lease);write('dhcp-pools.json',pool)
    ipconfigs={n:command(n,'ipconfig /all',timeout=4) for n in CLIENTS}
    write('ipconfig-all.json',ipconfigs)
    for tid,names,lo,hi,gw in [('N01',['PC9-ADMIN'],5,14,1),('N02',['PC5','PC6','PC7'],20,30,17),('N03',['PC0','PC1','PC2','PC3','PC4'],36,46,33)]:
        cases=[]
        ips=[lease[n]['address'] for n in names]
        for n in names:
            v=lease[n];address=v['address']
            ok=address.startswith('192.168.10.') and lo<=int(address.split('.')[-1])<=hi and v['mask']=='255.255.255.240' and v['dns']=='192.168.10.50' and v['dhcp'] and len(set(ips))==len(ips) and ('192.168.10.'+str(gw)) in ipconfigs[n]
            cases.append(dict(source=n,observed=v,gateway='192.168.10.'+str(gw),passed=bool(ok)))
        record(tid,'Valid unique centralized DHCP settings in the intended VLAN',cases,['leases.json','dhcp-pools.json','ipconfig-all.json'])
    # Explicit post-ACL reselect: record settings and relay/service rule counters.
    before=counters()
    for n in ['PC9-ADMIN','PC5','PC0']:
        js('ipc.network().getDevice('+json.dumps(n)+').getProcess("DhcpClient").dhcpRun("FastEthernet0");return true;')
    time.sleep(2)
    after=counters();renewed=leases()
    write('N04-renewal.json',dict(before=before,after=after,delta=delta(before,after),leases=renewed))
    record('N04','DHCP still works after ACL attachment',[dict(source=n,observed=renewed[n],passed=renewed[n]['address']!='0.0.0.0' and renewed[n]['dns']=='192.168.10.50') for n in ['PC9-ADMIN','PC5','PC0']],['N04-renewal.json'])
    own=[];refs=[]
    for n,gw in [('PC9-ADMIN','192.168.10.1'),('PC5','192.168.10.17'),('PC0','192.168.10.33')]:
        name='N05-'+n+'.json';own.append(ping_case(n,gw,True,name));refs.append(name)
    record('N05','Each client VLAN can ping its own gateway',own,refs)
    cases=[];refs=[]
    for n in ['PC9-ADMIN','PC5','PC0']:
        name='N06-'+n+'.json';cases.append(ping_case(n,'192.168.10.50',True,name));refs.append(name)
    record('N06','Client-to-server ICMP and server reply pass the ingress ACLs',cases,refs)
    # Liveness controls for protected endpoints precede all denied tests.
    lease=leases();write('leases.json',lease)
    cases=[];refs=[]
    for target in ['PC5','PC0']:
        name='N09-'+target+'.json';cases.append(ping_case('PC8-MGMT',lease[target]['address'],True,name));refs.append(name)
    record('N09','Administration-initiated departmental pings and replies succeed',cases,refs)
    for tid,src,targets,acl in [('N10','PC0',['192.168.10.2',lease['PC5']['address']],'STUDENTS-IN'),('N11','PC5',['192.168.10.2',lease['PC0']['address']],'FACULTY-IN')]:
        cases=[];refs=[]
        for i,target in enumerate(targets):
            name=tid+'-'+str(i+1)+'.json';cases.append(ping_case(src,target,False,name,acl));refs.append(name)
        record(tid,'New routed departmental traffic to known-live protected endpoints is denied',cases,refs+['N09-PC5.json','N09-PC0.json'])
    r=ping_case('SRV-CAMPUS','192.168.10.49',True,'N12-server-gateway.json')
    record('N12','Server can ping its own gateway',[r],['N12-server-gateway.json'])
    r=ping_case('SRV-CAMPUS',lease['PC0']['address'],False,'N13-server-denied.json','SERVICES-IN')
    record('N13','Server cannot initiate an ICMP request to a known-live client',[r],['N13-server-denied.json','N09-PC0.json','N06-PC0.json'])
    r=ping_case('PC0',lease['PC1']['address'],True,'N18-same-vlan.json')
    record('N18','Same-VLAN Student communication bypasses router ACLs and succeeds',[r],['N18-same-vlan.json'])

if __name__=='__main__':
    preflight()
    network_tests()
