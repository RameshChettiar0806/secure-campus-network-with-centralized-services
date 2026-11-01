"""Record actual service, policy, and SSH checks on the expanded simulation."""
import json
import re
import time
import scale50 as s
import n4_runner as lab
from n4_apps import ssh_positive

lab.ALL_HOSTS=s.HOSTS
lab.CLIENTS=[n for n in s.HOSTS if n!='SRV-CAMPUS']
lab.IOS=s.IOS
lab.RUN=s.RUN
lab.RUN_ID='SCALE50-20261031'

def batch(commands,label,timeout=18):
    lab.js('var jobs='+json.dumps(commands)+';for(var n in jobs){n4Collectors[n].text="";ipc.network().getDevice(n).getCommandPrompt().enterCommand(jobs[n]);}return true;')
    deadline=time.monotonic()+timeout
    while True:
        outputs=lab.js('var out={};for(var n of '+json.dumps(list(commands))+')out[n]=n4Collectors[n].text;return out;')
        if all(re.search(r'C:\\>\s*$',t) for t in outputs.values()) or time.monotonic()>deadline:break
        time.sleep(.3)
    data={n:dict(command=commands[n],output=t.replace(lab.SECRET,'[REDACTED]')) for n,t in outputs.items()}
    s.write(label+'.json',data)
    return data

def ping_batch(commands,label,allowed=True):
    outputs=batch(commands,label)
    failed=[]
    for n,d in outputs.items():
        m=re.search(r'Sent = (\d+), Received = (\d+)',d['output'])
        d['passed']=bool(m and (int(m[2])>0 if allowed else int(m[1])==4 and int(m[2])==0))
        if not d['passed']:failed.append(n)
    if allowed and failed:
        retry=batch({n:commands[n] for n in failed},label+'-retry')
        for n,d in retry.items():
            m=re.search(r'Sent = (\d+), Received = (\d+)',d['output'])
            outputs[n]['retry']=d
            outputs[n]['passed']=bool(m and int(m[2])>0)
    s.write(label+'.json',outputs)
    print(label,sum(d['passed'] for d in outputs.values()),'/',len(outputs),flush=True)
    return outputs

def layout():
    notes=[(480,10,'SECURE CAMPUS NETWORK | 50 PCs | 56 NETWORK DEVICES'),
           (90,360,'ADMINISTRATION | VLAN 10 | 12 PCs\n192.168.10.96/27 | Gateway .97\nPC8-MGMT: static .98 | SSH authorized source'),
           (680,360,'FACULTY | VLAN 20 | 18 PCs\n192.168.10.64/27 | Gateway .65'),
           (1270,360,'STUDENTS | VLAN 30 | 20 PCs\n192.168.10.0/26 | Gateway .1'),
           (1040,220,'SERVICES | VLAN 40 | 192.168.10.128/28\nServer .130 | Gateway .129\nDHCP, DNS, HTTP | portal.campus.test'),
           (400,170,'802.1Q trunks | R1 routes all VLANs\nVLSM | Central DHCP relay | Extended ACLs\nSwitch management .99-.102 in VLAN 10'),
           (50,1300,'POLICY: Departments reach DNS/HTTP and their own gateways.\nAdministration may initiate departmental ping diagnostics.\nStudent/Faculty routed initiation is restricted; same-VLAN traffic is switched locally.\nFaculty/Student trunks: 100 Mb/s | No redundant paths.')]
    lab.js('var w=ipc.appWindow().getActiveWorkspace().getLogicalWorkspace();var ids=w.getCanvasNoteIds();for(var id of ids)w.removeCanvasItem(id);for(var n of '+json.dumps(notes)+')w.addNote(n[0],n[1],w.getUnusedLayer(),n[2]);return true;')

def http_all():
    lab.js('scaleHttp={};for(var n of '+json.dumps(lab.CLIENTS)+'){var c={events:[],done:function(src,args){this.events.push(args);}};scaleHttp[n]=c;var h=ipc.network().getDevice(n).getProcess("HttpClient");h.registerEvent("onDone",c,c.done);h.go("http://portal.campus.test");}return true;')
    deadline=time.monotonic()+18
    while True:
        outputs=lab.js('var out={};for(var n in scaleHttp)out[n]={events:scaleHttp[n].events,page:ipc.network().getDevice(n).getProcess("HttpClient").getLastPageContent()};return out;')
        if all(v['events'] for v in outputs.values()) or time.monotonic()>deadline:break
        time.sleep(.3)
    for n,v in outputs.items():
        v['passed']=any(e.get('serverIp')==s.SERVER and e.get('url')=='http://portal.campus.test' and 'Secure Campus Services Portal' in e.get('content','') for e in v['events'])
    for n,v in outputs.items():
        if v['passed']:continue
        lab.js('scaleHttp['+json.dumps(n)+'].events=[];ipc.network().getDevice('+json.dumps(n)+').getProcess("HttpClient").go("http://portal.campus.test");return true;')
        deadline=time.monotonic()+15
        while True:
            retry=lab.js('return {events:scaleHttp['+json.dumps(n)+'].events,page:ipc.network().getDevice('+json.dumps(n)+').getProcess("HttpClient").getLastPageContent()};')
            if retry['events'] or time.monotonic()>deadline:break
            time.sleep(.3)
        v['retry']=retry
        v['passed']=any(e.get('serverIp')==s.SERVER and 'Secure Campus Services Portal' in e.get('content','') for e in retry['events'])
    s.write('http-all.json',outputs)
    print('Hostname HTTP',sum(v['passed'] for v in outputs.values()),'/',len(outputs),flush=True)
    return outputs

def run():
    lab.js('ipc.simulation().setSimulationMode(false);return true;')
    lab.initialize()
    lease=s.leases()
    ipconfigs=batch({n:'ipconfig /all' for n in lab.CLIENTS},'ipconfig-all',4)
    for v,names in s.GROUPS.items():
        for n in names:ipconfigs[n]['passed']=s.NETS[v][3] in ipconfigs[n]['output'] and s.SERVER in ipconfigs[n]['output']
    s.write('ipconfig-all.json',ipconfigs)
    gateway=ping_batch({n:'ping '+s.NETS[v][3] for v,names in s.GROUPS.items() for n in names},'gateway-pings')
    server=ping_batch({n:'ping '+s.SERVER for n in lab.CLIENTS},'server-pings')
    dns=batch({n:'nslookup portal.campus.test' for n in lab.CLIENTS},'dns-all',12)
    for n,v in dns.items():v['passed']=bool(re.search(r'Name:\s+portal\.campus\.test\s+Address:\s+192\.168\.10\.130',v['output'],re.I))
    for n,v in dns.items():
        if v['passed']:continue
        retry=batch({n:'nslookup portal.campus.test'},'dns-retry-'+n,12)[n]
        v['retry']=retry
        v['passed']=bool(re.search(r'Name:\s+portal\.campus\.test\s+Address:\s+192\.168\.10\.130',retry['output'],re.I))
    s.write('dns-all.json',dns)
    http=http_all()
    positive=ping_batch({'PC8-MGMT':'ping '+lease['PC0']['ip'],'PC9-ADMIN':'ping '+lease['PC5']['ip'],
                         'PC0':'ping '+lease['PC24']['ip'],'PC5':'ping '+lease['PC39']['ip'],
                         'SRV-CAMPUS':'ping 192.168.10.129'},'policy-allowed')
    policy=[]
    for source,target,acl in [('PC0',s.MGMT,'STUDENTS-IN'),('PC0',lease['PC5']['ip'],'STUDENTS-IN'),
                              ('PC5',s.MGMT,'FACULTY-IN'),('PC5',lease['PC0']['ip'],'FACULTY-IN'),
                              ('SRV-CAMPUS',lease['PC0']['ip'],'SERVICES-IN')]:
        policy.append(lab.ping_case(source,target,False,'deny-'+str(len(policy))+'.json',acl))
        print('Policy denial',source,target,policy[-1]['passed'],flush=True)
    ssh=[]
    targets=[('R1-CAMPUS','192.168.10.97')]+[(n,f'192.168.10.{99+i}') for i,n in enumerate(s.IOS[1:])]
    for name,address in targets:
        result=ssh_positive('PC8-MGMT',address,name,'ssh-allow-'+name+'.json');ssh.append(result)
        print('SSH authorized',name,result['passed'],flush=True)
    denyjobs={source:'ssh -l netadmin '+address for source,(_,address) in zip(['PC9-ADMIN','PC40','PC41','PC42','PC43'],targets)}
    denied=batch(denyjobs,'ssh-denied-admin',25)
    for n,v in denied.items():v['passed']=bool(re.search(r'Connection (?:timed out|refused|closed)|connect failed|connection failed|closed by foreign host',v['output'],re.I)) and 'Password:' not in v['output']
    s.write('ssh-denied-admin.json',denied)
    restricted=batch({'PC0':'ssh -l netadmin 192.168.10.97','PC5':'ssh -l netadmin 192.168.10.97'},'ssh-denied-departments',25)
    for n,v in restricted.items():v['passed']=bool(re.search(r'Connection (?:timed out|refused|closed)|connect failed|connection failed|closed by foreign host',v['output'],re.I)) and 'Password:' not in v['output']
    s.write('ssh-denied-departments.json',restricted)
    groups={'ipconfig':list(ipconfigs.values()),'gatewayPing':list(gateway.values()),'serverPing':list(server.values()),
            'dns':list(dns.values()),'http':list(http.values()),'policyAllowed':list(positive.values()),'policyDenied':policy,
            'sshAllowed':ssh,'sshDeniedAdmin':list(denied.values()),'sshDeniedDepartments':list(restricted.values())}
    summary={label:dict(passed=sum(bool(v.get('passed')) for v in items),total=len(items)) for label,items in groups.items()}
    summary['allPassed']=all(v.get('passed') for items in groups.values() for v in items)
    s.write('test-summary.json',summary)
    print(json.dumps(summary,indent=2),flush=True)
    assert summary['allPassed'],'Inspect failed evidence cases'

if __name__=='__main__':run()
