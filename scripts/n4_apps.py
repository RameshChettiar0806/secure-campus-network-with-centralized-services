import json
import re
import time
from n4_runner import *

HOSTS=['PC9-ADMIN','PC5','PC0']

def http_case(n,url,filename):
    before=counters()
    js('if(typeof n4Http==="undefined")n4Http={};if(!n4Http['+json.dumps(n)+']){var c={events:[],done:function(src,args){this.events.push(args);}};n4Http['+json.dumps(n)+']=c;ipc.network().getDevice('+json.dumps(n)+').getProcess("HttpClient").registerEvent("onDone",c,c.done);}n4Http['+json.dumps(n)+'].events=[];ipc.network().getDevice('+json.dumps(n)+').getProcess("HttpClient").go('+json.dumps(url)+');return true;')
    end=time.monotonic()+12
    events=[]
    while time.monotonic()<end:
        events=js('return n4Http['+json.dumps(n)+'].events;')
        if events:break
        time.sleep(.2)
    content=js('return ipc.network().getDevice('+json.dumps(n)+').getProcess("HttpClient").getLastPageContent();')
    after=counters()
    ok=any(e.get('serverIp')=='192.168.10.50' and e.get('url')==url and 'Secure Campus Services Portal' in e.get('content','') for e in events) and 'Secure Campus Services Portal' in content and 'portal.campus.test' in content
    data=dict(source=n,url=url,protocol='HTTP',port=80,events=events,page=content,aclBefore=before,aclAfter=after,counterDelta=delta(before,after),passed=ok,observedAt=now())
    write(filename,data)
    return {k:v for k,v in data.items() if k not in ['page','aclBefore','aclAfter','events']}

def app_tests():
    cases=[];refs=[]
    for n in HOSTS:
        filename='N07-'+n+'.json';cases.append(http_case(n,'http://192.168.10.50',filename));refs.append(filename)
    record('N07','Campus page loads by server IP from all three client VLANs',cases,refs)
    cases=[];refs=[]
    for n in HOSTS:
        before=counters()
        text=command(n,'nslookup portal.campus.test',timeout=12)
        after=counters()
        dns_changes=delta(before,after)
        # A successful query plus request/reply ACL increments distinguishes a fresh DNS exchange from a cache hit.
        dns_ok=(bool(re.search(r'Name:\s+portal\.campus\.test\s+Address:\s+192\.168\.10\.50',text,re.I)) and any(' eq domain' in k and v>0 for k,v in dns_changes.items()) and any(k.startswith('SERVICES-IN |') and ' eq domain' in k and v>0 for k,v in dns_changes.items()))
        filename='N08-'+n+'-dns.json'
        write(filename,dict(source=n,protocol='DNS',port=53,output=text,aclBefore=before,aclAfter=after,counterDelta=dns_changes,passed=dns_ok,observedAt=now()))
        refs.append(filename)
        hname='N08-'+n+'-http.json';h=http_case(n,'http://portal.campus.test',hname);refs.append(hname)
        h['dnsQueryPassed']=dns_ok;h['passed']=h['passed'] and dns_ok;cases.append(h)
    record('N08','Fresh DNS query resolves the hostname and HTTP returns the campus page',cases,refs)

def ssh_positive(source,address,name,filename):
    initial=command(source,'ssh -l netadmin '+address,timeout=20,password=True)
    auth='';status='';ok=False
    if re.search(r'Password:\s*$',initial):
        auth=command(source,SECRET,timeout=10)
        if name+'>' in auth or name+'#' in auth:
            status=command(source,'show ip ssh',timeout=8)
            ok='version 2.0' in status
            command(source,'exit',timeout=5)
    write(filename,dict(source=source,destination=address,protocol='SSH',port=22,initial=initial,authenticated=auth,statusOutput=status,passed=ok,observedAt=now()))
    return dict(source=source,destination=address,protocol='SSH',port=22,passed=ok)

def denied_connection(source,address,protocol,filename,acl=None):
    before=counters()
    cmd=('ssh -l netadmin ' if protocol=='SSH' else 'telnet ')+address
    text=command(source,cmd,timeout=40,password=True)
    after=counters();changes=delta(before,after)
    denied=bool(re.search(r'Connection (?:timed out|refused|closed)|connect failed|connection failed|closed by foreign host',text,re.I))
    # A password prompt is an authorization failure even without authentication.
    ok=denied and 'Password:' not in text
    if acl:ok=ok and any(k.startswith(acl+' |') and ' deny ' in k and v>0 for k,v in changes.items())
    write(filename,dict(source=source,destination=address,protocol=protocol,port=22 if protocol=='SSH' else 23,output=text,aclBefore=before,aclAfter=after,counterDelta=changes,passed=ok,observedAt=now()))
    return dict(source=source,destination=address,protocol=protocol,port=22 if protocol=='SSH' else 23,passed=ok,counterDelta=changes)

def management_tests():
    targets=[('192.168.10.1','R1-CAMPUS'),('192.168.10.3','SW1-CORE'),('192.168.10.4','SW2-ACCESS')]
    cases=[];refs=[]
    for address,name in targets:
        filename='N14-'+name+'.json';cases.append(ssh_positive('PC8-MGMT',address,name,filename));refs.append(filename)
    record('N14','PC8 authenticates by SSH to all three IOS devices',cases,refs)
    cases=[];refs=[]
    for address,name in targets:
        filename='N15-'+name+'.json';cases.append(denied_connection('PC9-ADMIN',address,'SSH',filename));refs.append(filename)
        print('N15 attempted '+name,flush=True)
    record('N15','PC9 cannot access router or same-VLAN switch VTYs',cases,refs+[n+'-preflight.json' for n in IOS])
    cases=[];refs=[]
    for n,acl in [('PC0','STUDENTS-IN'),('PC5','FACULTY-IN')]:
        filename='N16-'+n+'.json';cases.append(denied_connection(n,'192.168.10.1','SSH',filename,acl));refs.append(filename)
        print('N16 attempted '+n,flush=True)
    record('N16','Student and Faculty sources cannot SSH to the router',cases,refs)
    cases=[];refs=[]
    for address,name in targets:
        filename='N17-'+name+'.json';cases.append(denied_connection('PC8-MGMT',address,'Telnet',filename));refs.append(filename)
    record('N17','Authorized management workstation is still denied Telnet to every IOS device',cases,refs+[n+'-preflight.json' for n in IOS])

if __name__=='__main__':
    app_tests()
    management_tests()
