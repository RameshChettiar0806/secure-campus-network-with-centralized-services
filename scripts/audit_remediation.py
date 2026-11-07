"""Staged live Packet Tracer remediation, with separate immutable evidence per run.

Uses the existing loopback project adapter. Never run an old capture script to
verify a new topology: old scripts contain milestone-specific assumptions.
"""
import argparse
import datetime as dt
import hashlib
import ipaddress
from itertools import takewhile
import json
import re
import secrets
import sys
import time
from urllib.error import HTTPError
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

from project_api import js as bridge_js, BASE
from pt_client import call

FILE = BASE / 'Secure_Campus_Network_Submission.pkt'
IOS = ['R1-CAMPUS', 'R2-EXTERNAL', 'SW1-CORE', 'SW2-ACCESS', 'SW3-FACULTY', 'SW4-STUDENTS']
GROUPS = {
    10: ['PC8-MGMT', 'PC9-ADMIN'] + [f'PC{i}' for i in range(40, 50)],
    20: [f'PC{i}' for i in range(5, 8)] + [f'PC{i}' for i in range(25, 40)],
    30: [f'PC{i}' for i in range(5)] + [f'PC{i}' for i in range(10, 25)],
}
CLIENTS = sum(GROUPS.values(), [])
HOSTS = CLIENTS + ['SRV-CAMPUS', 'SRV-EXTERNAL']
SERVER = '192.168.10.130'
SECRET_LINE = re.compile(r'^\s*(?:enable .*secret|enable password|username .* (?:secret|password)|password\b|.*message-digest-key\b|ntp authentication-key\b|radius-server .*\bkey\b|tacacs-server .*\bkey\b|key-string\b)', re.I)
RUN = None


def now():
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=5, minutes=30))).isoformat(timespec='seconds')


def js(code):
    """Serialize in PT before crossing Qt's mutable object boundary."""
    value = bridge_js('return JSON.stringify((function(){' + code + '})());')
    return json.loads(value)


def credentials():
    p = BASE / 'LAB_CREDENTIALS_V2.json'
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}


def sanitize(value, private=None):
    if private is None:
        old = (BASE / 'LAB_CREDENTIALS.txt').read_text(encoding='utf-8')
        match = re.search(r'SSH and enable secret: (.+)', old)
        private = [match[1].strip()] if match else []
        for record in credentials().values():
            if isinstance(record, dict):
                private.extend(v for k, v in record.items() if k in ('loginSecret', 'enableSecret', 'sharedSecret'))
    if isinstance(value, dict):
        return {k: sanitize(v, private) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize(v, private) for v in value]
    if isinstance(value, str):
        value = '\n'.join('[REDACTED LAB CREDENTIAL]' if SECRET_LINE.search(line) else line for line in value.split('\n'))
        for secret in private:
            if secret:
                value = value.replace(secret, '[REDACTED]')
        return value
    return value


def write(name, value):
    (RUN / name).write_text(json.dumps(sanitize(value), indent=2, ensure_ascii=False), encoding='utf-8')


def show(name, command):
    return js('return String(ipc.network().getDevice(' + json.dumps(name) + ').enterCommand(' + json.dumps(command) + ',"enable").second);')


def execute(name, commands, label, allow_errors=False):
    result = js('var d=ipc.network().getDevice(' + json.dumps(name) + '),out=[];d.enterCommand("end","enable");for(var c of ' + json.dumps(commands) + '){var r=d.enterCommand(c,"");out.push({command:String(c),output:String(r.second),status:Number(r.first)});}return out;')
    write(label + '-' + name + '.json', result)
    errors = [v for v in result if rejected(v)]
    if errors and not allow_errors:
        raise RuntimeError(sanitize({'device': name, 'errors': errors}))
    return result


def rejected(result):
    return result['status'] != 0 or bool(re.search(
        r'% (?:Invalid|Incomplete|Ambiguous|Error)|overlaps with|Error:', result['output']
    ))


def capture(label):
    state = js('''
        var net=ipc.network(),devices=[],links=[],configs={},endpoints={},servers={};
        for(var i=0;i<net.getDeviceCount();i++){
            var d=net.getDeviceAt(i),name=String(d.getName()),type=Number(d.getType());
            devices.push({name:name,type:type});
            if(type===0||type===1||type===16){
                configs[name]={running:String(d.enterCommand("show running-config","enable").second),startup:String(d.enterCommand("show startup-config","enable").second)};
            } else if(type===8||type===9){
                var p=d.getPort("FastEthernet0");
                endpoints[name]={ip:String(p.getIpAddress()),mask:String(p.getSubnetMask()),mac:String(p.getMacAddress()),dhcp:Boolean(p.isDhcpClientOn()),dns:String(d.getProcess("DnsClient").getServerIp())};
                if(type===9)servers[name]=String(d.serializeToXml());
            }
        }
        for(var i=0;i<net.getLinkCount();i++){
            var l=net.getLinkAt(i),p=l.getPort1(),q=l.getPort2();
            links.push({from:String(p.getOwnerDevice().getName()),port:String(p.getName()),to:String(q.getOwnerDevice().getName()),peer:String(q.getName()),type:Number(l.getConnectionType())});
        }
        return {file:String(ipc.appWindow().getActiveFile().getSavedFilename()),devices:devices,links:links,configs:configs,endpoints:endpoints,servers:servers};
    ''')
    assert Path(state['file']).resolve() == FILE.resolve(), 'Wrong active file'
    with zipfile.ZipFile(RUN / (label + '-private.zip'), 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('state.json', json.dumps(state))
    public = {k: v for k, v in state.items() if k != 'servers'}
    public['capturedAt'] = now()
    public['submissionSha256'] = hashlib.sha256(FILE.read_bytes()).hexdigest()
    write(label + '-state.json', public)
    print(label, len([x for x in state['devices'] if x['type'] in (0, 1, 8, 9, 16)]), 'devices,', len(state['links']), 'links;', len(state['endpoints']), 'endpoints', flush=True)
    return state


def collectors():
    return js('''
        if(typeof auditCollectors!=='undefined')for(var n in auditCollectors){try{var p=ipc.network().getDevice(n).getCommandPrompt(),c=auditCollectors[n];p.unregisterEvent("outputWritten",c,c.onOutput);}catch(e){}}
        auditCollectors={};
        for(var n of NAMES){var c={text:'',onOutput:function(src,args){this.text+=String(args.newOutput);}};auditCollectors[n]=c;ipc.network().getDevice(n).getCommandPrompt().registerEvent("outputWritten",c,c.onOutput);}
        return true;
    '''.replace('NAMES', json.dumps(HOSTS)))


def batch(jobs, label, timeout=22, password=False):
    js('var jobs=' + json.dumps(jobs) + ';for(var n in jobs){auditCollectors[n].text="";ipc.network().getDevice(n).getCommandPrompt().enterCommand(jobs[n]);}return true;')
    end = time.monotonic() + timeout
    while True:
        try:
            outputs = js('var out={};for(var n of ' + json.dumps(list(jobs)) + ')out[n]=String(auditCollectors[n].text);return out;')
        except HTTPError as error:
            # Polling is read-only. Do not replay the original CLI commands on a bridge timeout.
            if error.code != 500 or time.monotonic() > end:
                raise
            time.sleep(.5)
            continue
        pattern = r'(?:C:\\>|[A-Za-z0-9-]+[>#]' + (r'|Password:' if password else '') + r')\s*$'
        if all(re.search(pattern, text) for text in outputs.values()) or time.monotonic() > end:
            break
        time.sleep(.3)
    result = {n: {'command': jobs[n], 'output': out, 'observedAt': now()} for n, out in outputs.items()}
    write(label + '.json', result)
    return result


def pings(jobs, label, allowed=True, timeout=32):
    result = batch(jobs, label, timeout)
    for n, item in result.items():
        m = re.search(r'Sent = (\d+), Received = (\d+)', item['output'])
        item['passed'] = bool(m and int(m[1]) == 4 and (int(m[2]) > 0 if allowed else int(m[2]) == 0))
    failed = [n for n, item in result.items() if not item['passed']]
    if allowed and failed:
        retry = pings_once({n: jobs[n] for n in failed}, label + '-retry')
        for n, item in retry.items():
            result[n]['retry'] = item
            result[n]['passed'] = item['passed']
    write(label + '.json', result)
    print(label, sum(x['passed'] for x in result.values()), '/', len(result), flush=True)
    return result


def pings_once(jobs, label):
    result = batch(jobs, label)
    for item in result.values():
        m = re.search(r'Sent = (\d+), Received = (\d+)', item['output'])
        item['passed'] = bool(m and int(m[2]) > 0)
    write(label + '.json', result)
    return result


def http(names, label, external=False):
    url = 'http://external.campus.test' if external else 'http://portal.campus.test'
    target = '203.0.113.10' if external else SERVER
    js('''
        if(typeof auditHttp==='undefined')auditHttp={};
        for(var n of NAMES){if(!auditHttp[n]){var c={events:[],done:function(src,args){this.events.push(JSON.parse(JSON.stringify(args)));}};auditHttp[n]=c;ipc.network().getDevice(n).getProcess("HttpClient").registerEvent("onDone",c,c.done);}auditHttp[n].events=[];ipc.network().getDevice(n).getProcess("HttpClient").go(URL);}
        return true;
    '''.replace('NAMES', json.dumps(names)).replace('URL', json.dumps(url)))
    end = time.monotonic() + 22
    while True:
        events = js('var out={};for(var n of ' + json.dumps(names) + ')out[n]=auditHttp[n].events;return out;')
        if all(events.values()) or time.monotonic() > end:
            break
        time.sleep(.3)
    result = {n: {'url': url, 'events': ev, 'passed': any(e.get('serverIp') == target and '<html' in e.get('content', '').lower() for e in ev)} for n, ev in events.items()}
    write(label + '.json', result)
    print(label, sum(x['passed'] for x in result.values()), '/', len(result), flush=True)
    return result


def ssh_test(device, address, label, username='netadmin', secret=None):
    if secret is None:
        private = credentials()
        record = private.get(device)
        if private.get('central') and 'login authentication CAMPUS-AUTH' in show(device, 'show running-config'):
            record = private['central']
        secret = record['loginSecret'] if record else re.search(r'SSH and enable secret: (.+)', (BASE / 'LAB_CREDENTIALS.txt').read_text())[1].strip()
        username = record['username'] if record else username
    initial = batch({'PC8-MGMT': 'ssh -l ' + username + ' ' + address}, label + '-initial', password=True)['PC8-MGMT']['output']
    authenticated = ''
    status = ''
    if re.search(r'Password:\s*$', initial):
        authenticated = batch({'PC8-MGMT': secret}, label + '-auth', 10)['PC8-MGMT']['output']
        if re.search(re.escape(device) + r'[>#]\s*$', authenticated):
            status = batch({'PC8-MGMT': 'show ip ssh'}, label + '-status', 8)['PC8-MGMT']['output']
            batch({'PC8-MGMT': 'exit'}, label + '-exit', 5)
        elif not re.search(r'C:\\>\s*$', authenticated):
            js('ipc.network().getDevice("PC8-MGMT").getCommandPrompt().enterChar(3,0);return true;')
    result = {'device': device, 'destination': address, 'initial': initial, 'authenticated': authenticated, 'status': status, 'passed': 'version 2.0' in status, 'observedAt': now()}
    write(label + '.json', result)
    print(label, result['passed'], flush=True)
    return result


def primary_failure(label, management=False):
    ports = ['GigabitEthernet0/2', 'FastEthernet0/23', 'FastEthernet0/24']
    execute('SW1-CORE', ['configure terminal'] + sum(([f'interface {p}', 'shutdown', 'exit'] for p in ports), []) + ['end'], label + '-fail')
    try:
        time.sleep(2)
        results = {'stp': {n: show(n, 'show spanning-tree') for n in IOS[2:]}}
        results['campus'] = pings({n: 'ping ' + SERVER for n in CLIENTS}, label + '-campus')
        permitted = [n for n in CLIENTS if not management or n != 'PC8-MGMT']
        results['external'] = pings({n: 'ping 203.0.113.10' for n in permitted}, label + '-external')
        results['portal'] = http(CLIENTS, label + '-http')
        failed = [n for n, v in results['portal'].items() if not v['passed']]
        if failed:
            retry = http(failed, label + '-http-retry')
            for n, v in retry.items():
                results['portal'][n]['retry'] = v
                results['portal'][n]['passed'] = v['passed']
        results['ssh'] = ssh_test('SW4-STUDENTS', '192.168.10.150' if management else '192.168.10.102', label + '-ssh')
        results['passed'] = all(v['passed'] for key in ['campus', 'external', 'portal'] for v in results[key].values()) and results['ssh']['passed']
        write(label + '-summary.json', results)
        assert results['passed'], 'Backup-path regression failed'
    finally:
        execute('SW1-CORE', ['configure terminal'] + sum(([f'interface {p}', 'no shutdown', 'exit'] for p in ports), []) + ['end'], label + '-restore')
    recovered = pings({'PC9-ADMIN': 'ping ' + SERVER, 'PC5': 'ping ' + SERVER, 'PC0': 'ping ' + SERVER}, label + '-restored')
    assert all(v['passed'] for v in recovered.values())


def server_summary(state):
    services = {}
    for name, xml in state['servers'].items():
        root = ET.fromstring(xml)
        enabled = {}
        for node in root.iter():
            if node.tag in ('TFTP_SERVER', 'NTP_SERVER', 'HTTP_SERVER', 'HTTPS_SERVER', 'FTP_SERVER', 'SYSLOG_SERVER', 'DNS_SERVER', 'DHCP_SERVER'):
                flag = node.find('ENABLED')
                if flag is None:
                    flag = node.find('HTTPSENABLED')
                if flag is not None:
                    enabled[node.tag] = flag.text == '1'
            if node.tag in ('SMTP_ENABLED', 'POP3_ENABLED'):
                enabled[node.tag] = node.text == '1'
        services[name] = enabled
    return services


def baseline_controls():
    collectors()
    targets = [('R1-CAMPUS', '192.168.10.97')] + [(n, f'192.168.10.{99+i}') for i, n in enumerate(IOS[2:])]
    results = [ssh_test(n, ip, 'iteration0-ssh-' + n) for n, ip in targets]
    assert all(v['passed'] for v in results)
    ospf = {n: show(n, 'show ip ospf neighbor') for n in IOS[:2]}
    assert all('FULL/' in s for s in ospf.values())
    write('iteration0-ospf.json', ospf)
    primary_failure('iteration0-backup')
    state = capture('iteration0-final')
    write('iteration0-server-services.json', server_summary(state))
    signatures = [line.split(' secret ', 1)[1] for pair in state['configs'].values() for line in pair['running'].splitlines() if ' secret ' in line]
    write('iteration0-credential-review.json', {'storedSecretCount': len(signatures), 'uniqueStoredSecretCount': len(set(signatures)), 'credentialValuesPublished': False})
    print('Baseline management, OSPF and backup-path controls passed', flush=True)


def checkpoint(label, iteration):
    for name in configured_devices():
        output = show(name, 'write memory')
        assert '[OK]' in output or 'Building configuration' in output, name
    assert js('return ipc.appWindow().fileSave();')
    # Saving is synchronous, and the checkpoint contains the exact saved bytes.
    data = FILE.read_bytes()
    with zipfile.ZipFile(RUN / (label + '-checkpoint-private.zip'), 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr(FILE.name, data)
        if (BASE / 'LAB_CREDENTIALS_V2.json').exists():
            z.write(BASE / 'LAB_CREDENTIALS_V2.json', 'LAB_CREDENTIALS_V2.json')
    meta = {'file': FILE.name, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data), 'savedAt': now(), 'iteration': iteration}
    write(label + '-submission.json', meta)
    progress = json.loads((RUN / 'progress.json').read_text())
    progress['iterations'][str(iteration)] = 'saved; reopening verification pending'
    progress['currentCheckpoint'] = meta
    write('progress.json', progress)
    print('Checkpoint saved:', label, len(data), 'bytes', flush=True)
    return meta


def configured_devices():
    return js('var net=ipc.network(),names=[];for(var i=0;i<net.getDeviceCount();i++){'
              'var d=net.getDeviceAt(i);if([0,1,16].indexOf(Number(d.getType()))>=0)names.push(String(d.getName()));}'
              'return names;')


def reopen(label, management=False):
    result = js('return Number(ipc.appWindow().fileOpen(' + json.dumps(str(FILE).replace('\\', '/')) + '));')
    write(label + '-reopen.json', {'result': result, 'openedAt': now()})
    assert result == 0, 'Packet Tracer failed to reopen the checkpoint'
    time.sleep(3)
    js('auditHttp={};return true;')
    collectors()
    end = time.monotonic() + 60
    while True:
        leases = js('var out={};for(var n of ' + json.dumps(CLIENTS) + '){var d=ipc.network().getDevice(n);out[n]=String(d.getPort("FastEthernet0").getIpAddress());}return out;')
        if all(ip != '0.0.0.0' for ip in leases.values()) or time.monotonic() > end:
            break
        js('ipc.appWindow().getRealtimeToolbar().fastForwardTime();return true;')
        time.sleep(.5)
    for name, ip in leases.items():
        if ip == '0.0.0.0' and name != 'PC8-MGMT':
            js('ipc.network().getDevice(' + json.dumps(name) + ').getProcess("DhcpClient").dhcpRun("FastEthernet0");return true;')
    checks = pings({n: 'ping ' + SERVER for n in CLIENTS}, label + '-reopened-campus')
    assert all(v['passed'] for v in checks.values())
    check = ssh_test('SW4-STUDENTS', '192.168.10.150' if management else '192.168.10.102', label + '-reopened-ssh')
    assert check['passed']
    state = capture(label + '-reopened')
    verify_reopened(label, state, checks, check)


def verify_reopened(label, state, checks, check):
    meta = json.loads((RUN / (label + '-submission.json')).read_text())
    assert hashlib.sha256(FILE.read_bytes()).hexdigest() == meta['sha256'], 'File changed during reopening checks'
    assert len(checks) == len(CLIENTS) and all(v['passed'] for v in checks.values()) and check['passed']
    assert 'FULL/' in show('R1-CAMPUS', 'show ip ospf neighbor')
    assert len({v['ip'] for v in state['endpoints'].values()}) == 52
    assert all(v['ip'] != '0.0.0.0' for v in state['endpoints'].values())
    for name, pair in state['configs'].items():
        assert pair['running'][pair['running'].index('version '):].strip() == pair['startup'][pair['startup'].index('version '):].strip(), name + ': startup mismatch'
    if label == 'iteration4':
        verify_monitoring_reopen(state)
    if 'SW5-CORE' in state['configs']:
        from audit_core import wait_for_peer_roles
        hsrp = wait_for_peer_roles()
        routes = show('R2-EXTERNAL', 'show ip route')
        assert not re.search(r'\b192\.168\.10\.', routes), 'Campus routes leaked to the external router'
        write(label + '-reopened-routing.json', {'hsrp': hsrp, 'externalRoutes': routes})
    assert hashlib.sha256(FILE.read_bytes()).hexdigest() == meta['sha256'], 'File changed during reopening checks'
    write(label + '-reopened-summary.json', {'passed': True, 'campusClients': len(checks), 'ssh': True, 'ospfFull': True, 'sha256': meta['sha256'], 'observedAt': now()})
    progress = json.loads((RUN / 'progress.json').read_text())
    progress['iterations'][str(meta['iteration'])] = 'passed and verified after reopening'
    progress['status'] = 'verified checkpoint available'
    write('progress.json', progress)
    from verify_audit_remediation import verify
    verify(RUN, record=True)


def harden():
    assert json.loads((RUN / 'iteration0-reopened-summary.json').read_text())['passed']
    before = capture('iteration1-before')
    private = credentials()
    for name in IOS:
        private.setdefault(name, {'username': 'ramesh-admin', 'loginSecret': 'Cn9_' + secrets.token_urlsafe(20), 'enableSecret': 'En9_' + secrets.token_urlsafe(20)})
    (BASE / 'LAB_CREDENTIALS_V2.json').write_text(json.dumps(private, indent=2), encoding='utf-8')
    algorithms = {}
    for name in IOS:
        record = private[name]
        execute(name, ['configure terminal', 'service password-encryption', 'ip domain-name campus.test', 'end'], 'iteration1-base')
        chosen = None
        for algorithm in ['scrypt', 'sha256', None]:
            marker = ('algorithm-type ' + algorithm + ' ') if algorithm else ''
            result = execute(name, ['configure terminal', 'enable ' + marker + 'secret ' + record['enableSecret'], 'username ' + record['username'] + ' ' + marker + 'secret ' + record['loginSecret'], 'end'], 'iteration1-credentials-' + (algorithm or 'legacy'), True)
            if not any(rejected(r) for r in result):
                chosen = algorithm or 'type5'
                break
        assert chosen, name + ': no supported secret command'
        algorithms[name] = chosen
        commands = ['configure terminal', 'no username netadmin', 'line console 0', 'login local', 'exec-timeout 5 0', 'exit']
        if name.startswith('R'):
            commands += ['line aux 0', 'no exec', 'exit']
        commands += ['line vty 0 ' + ('4' if name.startswith('R') else '15'), 'login local', 'exec-timeout 5 0', 'transport input ' + ('none' if name == 'R2-EXTERNAL' else 'ssh'), 'exit', 'end']
        execute(name, commands, 'iteration1-access')
    for name in IOS[2:]:
        config = before['configs'][name]['running']
        ports = re.findall(r'^interface (\S+)\n((?: .*\n)*)', config, re.M)
        commands = ['configure terminal']
        for port, block in ports:
            if 'switchport mode trunk' in block:
                commands += ['interface ' + port, 'switchport nonegotiate', 'exit']
        for link in before['links']:
            peer, port = (link['to'], link['port']) if link['from'] == name else ((link['from'], link['peer']) if link['to'] == name else (None, None))
            if peer in before['endpoints']:
                vlan = next((v for v, names in GROUPS.items() if peer in names), 40)
                commands += ['interface ' + port, 'description ' + peer + '_VLAN' + str(vlan), 'exit']
        execute(name, commands + ['end'], 'iteration1-ports')
    services = js('''
        var out={};
        for(var name of ["SRV-CAMPUS","SRV-EXTERNAL"]){
            var d=ipc.network().getDevice(name);
            var ftp=d.getProcess("FtpServer"),users=ftp.getFtpUserAccountManager(),names=[];
            for(var i=0;i<users.getUsersCount();i++)names.push(String(users.getUsernameAt(i)));
            for(var user of names)users.removeFtpUser(user);
            ftp.setEnabled(false);d.getProcess("TftpServer").setEnabled(false);
            d.getProcess("NtpServer").setEnabled(false);d.getProcess("SmtpServer").setEnable(false);d.getProcess("Pop3Server").setEnable(false);
            d.getProcess("SyslogServer").setEnable(false);d.getProcess("HttpsServer").setHttpsEnable(false);
            d.getProcess("AcsServer").enableACSServerService(false);
            d.getProcess("HttpServer").setEnable(true);
            out[name]={removedFtpAccounts:names.length,requiredHttpEnabled:Boolean(d.getProcess("HttpServer").isEnabled())};
        }return out;
    ''')
    write('iteration1-server-hardening.json', services)
    speed = {}
    for name, port in [('R1-CAMPUS', 'GigabitEthernet0/0'), ('SW1-CORE', 'GigabitEthernet0/1')]:
        result = execute(name, ['configure terminal', 'interface ' + port, 'speed 1000', 'duplex full', 'end'], 'iteration1-speed', True)
        speed[name] = not any(rejected(r) for r in result)
    if not all(speed.values()):
        for name, port in [('R1-CAMPUS', 'GigabitEthernet0/0'), ('SW1-CORE', 'GigabitEthernet0/1')]:
            execute(name, ['configure terminal', 'interface ' + port, 'speed auto', 'duplex auto', 'end'], 'iteration1-speed-rollback')
    write('iteration1-secret-algorithms.json', algorithms)
    write('iteration1-speed-result.json', {'configurationAccepted': speed, 'coreStatus': show('SW1-CORE', 'show interfaces status'), 'routerInterface': show('R1-CAMPUS', 'show interfaces GigabitEthernet0/0')})
    capture('iteration1-after')
    print('Device and server hardening applied; regression and reopening still required', flush=True)


def require_verified(iteration):
    result = json.loads((RUN / f'iteration{iteration}-reopened-summary.json').read_text())
    assert result['passed'] and result['sha256'] == hashlib.sha256(FILE.read_bytes()).hexdigest(), 'Previous checkpoint identity changed'


def acl_rules(config, name):
    header = 'ip access-list extended ' + name
    section = config.split(header + '\n', 1)[1]
    return [line.strip() for line in takewhile(lambda line: line.startswith(' '), section.splitlines())]


def install_acl(name, rules):
    return ['no ip access-list extended ' + name, 'ip access-list extended ' + name, *rules, 'exit']


def management():
    require_verified(1)
    before = capture('iteration2-before')
    r1 = before['configs']['R1-CAMPUS']['running']
    pc = '192.168.10.146'
    server = '192.168.10.130'
    subnets = {'ADMIN-IN': '192.168.10.96 0.0.0.31', 'FACULTY-IN': '192.168.10.64 0.0.0.31', 'STUDENTS-IN': '192.168.10.0 0.0.0.63'}
    commands = ['configure terminal']
    for name, source in subnets.items():
        rules = [line for line in acl_rules(r1, name) if line != 'deny ip any any' and 'host 192.168.10.98' not in line]
        commands += install_acl(name, [*rules, f'permit icmp {source} host {pc} echo-reply', 'deny ip any any'])
    services = [line for line in acl_rules(r1, 'SERVICES-IN') if line != 'deny ip any any']
    commands += install_acl('SERVICES-IN', [*services,
        f'permit udp host {server} eq domain host {pc}',
        f'permit tcp host {server} eq domain host {pc} established',
        f'permit tcp host {server} eq www host {pc} established',
        f'permit icmp host {server} host {pc} echo-reply',
        'deny ip any any'])
    commands += install_acl('MGMT-IN', [
        f'permit tcp host {pc} host 192.168.10.145 eq 22',
        f'permit udp host {pc} host {server} eq domain',
        f'permit tcp host {pc} host {server} eq domain',
        f'permit tcp host {pc} host {server} eq www',
        f'permit icmp host {pc} host {server} echo',
        f'permit icmp host {pc} host 192.168.10.145 echo',
        *[f'permit icmp host {pc} {subnet} echo' for subnet in subnets.values()],
        'deny ip any any'])
    commands += ['interface GigabitEthernet0/0.99', 'description MANAGEMENT_VLAN99',
                 'encapsulation dot1Q 99', 'ip address 192.168.10.145 255.255.255.240',
                 'ip access-group MGMT-IN in', 'no shutdown', 'exit',
                 'no access-list 1', f'access-list 1 permit host {pc}', 'access-list 1 deny any']
    for vlan, name in [(10, 'ADMIN-IN'), (20, 'FACULTY-IN'), (30, 'STUDENTS-IN'), (40, 'SERVICES-IN')]:
        commands += [f'interface GigabitEthernet0/0.{vlan}', f'no ip access-group {name} in',
                     f'ip access-group {name} in', 'exit']
    commands += ['router ospf 1', 'passive-interface GigabitEthernet0/0.99', 'end']
    execute('R1-CAMPUS', commands, 'iteration2-config')
    for i, name in enumerate(IOS[2:]):
        commands = ['configure terminal', 'vlan 99', 'name MANAGEMENT', 'exit']
        if name == 'SW1-CORE':
            commands.append('spanning-tree vlan 99 priority 4096')
        for port, allowed in re.findall(r'^interface (\S+)\n(?:(?: [^\n]*)\n)*? switchport trunk allowed vlan ([\d,]+)', before['configs'][name]['running'], re.M):
            commands += [f'interface {port}', f'switchport trunk allowed vlan {allowed},99']
            if name != 'SW1-CORE' and port == 'GigabitEthernet0/2':
                commands.append('spanning-tree vlan 99 cost 204')
            commands.append('exit')
        if name == 'SW2-ACCESS':
            commands += ['interface FastEthernet0/1', 'description PC8-MGMT_VLAN99', 'switchport access vlan 99', 'exit']
        commands += ['interface Vlan10', 'no ip address', 'shutdown', 'exit',
                     'interface Vlan99', f'ip address 192.168.10.{147+i} 255.255.255.240',
                     'no shutdown', 'exit', 'ip default-gateway 192.168.10.145',
                     'no access-list 1', f'access-list 1 permit host {pc}', 'access-list 1 deny any', 'end']
        execute(name, commands, 'iteration2-config')
    result = call('configurePcIp', {'deviceName': 'PC8-MGMT', 'dhcpEnabled': False, 'ipaddress': pc,
                  'subnetMask': '255.255.255.240', 'defaultGateway': '192.168.10.145', 'dnsServer': server})
    assert result['success'], 'Management workstation address change failed'
    js('ipc.network().getDevice("PC8-MGMT").getProcess("DnsClient").setServerIp("192.168.10.130");return true;')
    state = capture('iteration2-after')
    assert state['endpoints']['PC8-MGMT']['ip'] == pc
    assert state['links'] == before['links']
    print('VLAN 99 and management access policy configured', flush=True)


def connected_ports(state, device):
    ports = {}
    for link in state['links']:
        if link['from'] == device:
            ports[link['port']] = link['to']
        elif link['to'] == device:
            ports[link['peer']] = link['from']
    return ports


def renew_clients(label):
    # Release and reacquire one lease in each user VLAN.
    devices = ['PC9-ADMIN', 'PC5', 'PC0']
    def addresses():
        return js('var out={};for(var n of ' + json.dumps(devices) + '){var p=ipc.network().getDevice(n).getPort("FastEthernet0");'
                  'out[n]={ip:String(p.getIpAddress()),mask:String(p.getSubnetMask())};}return out;')

    clients = 'for(var n of ' + json.dumps(devices) + '){var c=ipc.network().getDevice(n).getProcess("DhcpClient");'
    before = addresses()
    js(clients + 'c.dhcpRelease("FastEthernet0");}return true;')
    released = addresses()
    assert all(item['ip'] == '0.0.0.0' for item in released.values()), 'A DHCP client retained its old lease'
    js(clients + 'c.dhcpRun("FastEthernet0");}return true;')
    subnets = dict(zip(devices, map(ipaddress.ip_network,
                   ('192.168.10.96/27', '192.168.10.64/27', '192.168.10.0/26'))))
    end = time.monotonic() + 45
    while True:
        renewed = addresses()
        if all(ipaddress.ip_address(renewed[n]['ip']) in subnets[n] for n in devices):
            break
        if time.monotonic() >= end:
            raise AssertionError('A departmental client failed to renew its DHCP lease')
        time.sleep(.5)
    checks = {n: {'beforeIp': before[n]['ip'], 'releasedIp': released[n]['ip'],
                  'renewedIp': renewed[n]['ip'], 'mask': renewed[n]['mask']} for n in devices}
    write(label + '-summary.json', checks)


def layer2():
    require_verified(2)
    before = capture('iteration3-before')
    capabilities = {}
    for name in IOS[2:]:
        config = before['configs'][name]['running']
        connected = connected_ports(before, name)
        commands = ['configure terminal', 'vlan 998', 'name PARKING', 'exit',
                    'vlan 999', 'name UNUSED_NATIVE', 'exit']
        for port, block in re.findall(r'^interface (\S+)\n((?: .*\n)*)', config, re.M):
            if not port.startswith(('FastEthernet', 'GigabitEthernet')):
                continue
            commands.append('interface ' + port)
            if 'switchport mode trunk' in block:
                commands.append('switchport trunk native vlan 999')
                if name == 'SW1-CORE' and connected.get(port) in IOS[3:]:
                    commands.append('spanning-tree guard root')
            elif port not in connected:
                commands += ['switchport mode access', 'switchport access vlan 998', 'shutdown']
            commands.append('exit')
        execute(name, commands + ['end'], 'iteration3-trunk-parking')
        commands = ['configure terminal']
        for port, peer in connected.items():
            if peer in CLIENTS:
                mac = re.sub(r'[^0-9a-fA-F]', '', before['endpoints'][peer]['mac'])
                assert len(mac) == 12, peer + ': unexpected hardware address'
                mac = '.'.join(mac[i:i+4] for i in (0, 4, 8))
                commands += ['interface ' + port, 'switchport port-security',
                             'switchport port-security maximum 1',
                             'switchport port-security violation restrict',
                             'switchport port-security mac-address ' + mac, 'exit']
        execute(name, commands + ['end'], 'iteration3-port-security')
        probes = execute(name, ['configure terminal', 'ip dhcp snooping', 'end'], 'iteration3-snooping-probe', True)
        capabilities[name] = {'dhcpSnoopingCommand': not any(rejected(r) for r in probes)}
    execute('R1-CAMPUS', ['configure terminal', 'interface GigabitEthernet0/0.999',
                         'description UNUSED_NATIVE_NO_IP', 'encapsulation dot1Q 999 native',
                         'no ip address', 'exit', 'end'], 'iteration3-native-router')
    if all(v['dhcpSnoopingCommand'] for v in capabilities.values()):
        snooping_ready = True
        for name in IOS[2:]:
            trusted = ['GigabitEthernet0/1', 'FastEthernet0/1'] if name == 'SW1-CORE' else ['GigabitEthernet0/1', 'GigabitEthernet0/2']
            commands = ['configure terminal', 'ip dhcp snooping vlan 10,20,30', 'no ip dhcp snooping information option']
            for port in trusted:
                commands += ['interface ' + port, 'ip dhcp snooping trust', 'exit']
            results = execute(name, commands + ['end'], 'iteration3-snooping', True)
            snooping_ready &= not any(rejected(r) for r in results)
        if snooping_ready:
            collectors()
            try:
                renew_clients('iteration3-snooping-renewal')
            except AssertionError as exc:
                snooping_ready = False
                write('iteration3-snooping-failure.json', {'error': str(exc)})
        for name in IOS[2:]:
            capabilities[name]['bindings'] = show(name, 'show ip dhcp snooping binding')
        # Without populated bindings, DAI and Source Guard could disrupt valid users.
        if not snooping_ready or not all(re.search(r'192\.168\.10\.\d+', capabilities[name]['bindings']) for name in IOS[3:]):
            for name in IOS[2:]:
                execute(name, ['configure terminal', 'no ip dhcp snooping', 'end'], 'iteration3-snooping-rollback', True)
            snooping_ready = False
        write('iteration3-snooping-behavior.json', {'operationalWithBindings': snooping_ready})
    else:
        for name, values in capabilities.items():
            if values['dhcpSnoopingCommand']:
                execute(name, ['configure terminal', 'no ip dhcp snooping', 'end'], 'iteration3-snooping-rollback')
    write('iteration3-capabilities.json', capabilities)
    collectors()
    renew_clients('iteration3-dhcp')
    validate_port_security(before['endpoints']['PC8-MGMT']['mac'])
    capture('iteration3-after')


def validate_port_security(original):
    pc = 'PC8-MGMT'
    gateway = 'ping 192.168.10.145'
    control = pings({pc: gateway}, 'iteration3-mac-control')
    assert control[pc]['passed']
    try:
        attempted = js('var p=ipc.network().getDevice("PC8-MGMT").getPort("FastEthernet0");p.setMacAddress("0200.0000.0099");return String(p.getMacAddress());')
        altered = re.sub(r'[^0-9a-fA-F]', '', attempted).lower() == '020000000099'
        if altered:
            attack = pings({pc: gateway}, 'iteration3-mac-unauthorized', False, 45)
            write('iteration3-mac-violation.json', {'passed': attack[pc]['passed'],
                  'portSecurity': show('SW2-ACCESS', 'show port-security interface FastEthernet0/1')})
            assert attack[pc]['passed'], 'Unauthorized MAC was not blocked'
        else:
            write('iteration3-mac-violation.json', {'status': 'unverified', 'reason': 'Simulator did not change the endpoint MAC'})
    finally:
        js('var p=ipc.network().getDevice("PC8-MGMT").getPort("FastEthernet0");p.setMacAddress(' + json.dumps(original) + ');return String(p.getMacAddress());')
    assert pings({pc: gateway}, 'iteration3-mac-restored')[pc]['passed']


def binding_protections():
    state = capture('iteration3-bindings-before')
    helpers = [('SW2-ACCESS', 10), ('SW3-FACULTY', 20), ('SW4-STUDENTS', 30)]
    findings = {}
    for name, vlan in helpers:
        # Verify that the simulator implements each command before extending it.
        ports = [p for p, peer in connected_ports(state, name).items() if peer in CLIENTS and peer != 'PC8-MGMT']
        dai = execute(name, ['configure terminal', 'ip arp inspection vlan ' + str(vlan),
                      'interface GigabitEthernet0/1', 'ip arp inspection trust', 'exit',
                      'interface GigabitEthernet0/2', 'ip arp inspection trust', 'exit', 'end'],
                      'iteration3-dai', True)
        guard = execute(name, ['configure terminal', 'interface ' + ports[0], 'ip verify source', 'end'],
                        'iteration3-source-guard', True)
        features = {'dai': not any(rejected(r) for r in dai), 'sourceGuard': not any(rejected(r) for r in guard)}
        if features['dai']:
            execute(name, ['configure terminal', 'no ip arp inspection vlan ' + str(vlan), 'end'],
                    'iteration3-dai-probe-cleanup')
        if features['sourceGuard']:
            execute(name, ['configure terminal', 'interface ' + ports[0], 'no ip verify source', 'end'],
                    'iteration3-source-guard-probe-cleanup')
        findings[name] = features
    write('iteration3-binding-protection-capabilities.json', findings)
    print('Binding protection capability check:', findings, flush=True)


def extend_acl(device, name, rules, label, replace=False):
    config = show(device, 'show running-config')
    existing = [] if replace else acl_rules(config, name)
    entries = [line for line in dict.fromkeys([*existing, *rules]) if line != 'deny ip any any']
    commands = ['configure terminal', *install_acl(name, [*entries, 'deny ip any any'])]
    for port, block in re.findall(r'^interface (\S+)\n((?: .*\n)*)', config, re.M):
        if f' ip access-group {name} in\n' in block:
            commands += [f'interface {port}', f'no ip access-group {name} in',
                         f'ip access-group {name} in', 'exit']
    execute(device, commands + ['end'], label)


def wait_ospf(present, seconds=55):
    until = time.monotonic() + seconds
    while True:
        output = show('R1-CAMPUS', 'show ip ospf neighbor')
        if ('FULL/' in output) == present or time.monotonic() > until:
            return output
        time.sleep(2)


def ospf_auth(key, label, allow_errors=False):
    configs = []
    for name, port in [('R1-CAMPUS', 'GigabitEthernet0/1'), ('R2-EXTERNAL', 'GigabitEthernet0/0')]:
        configs.extend(execute(name, ['configure terminal', 'interface ' + port,
                                      'ip ospf authentication message-digest',
                                      'no ip ospf message-digest-key 1',
                                      'ip ospf message-digest-key 1 md5 ' + key, 'end'], label, allow_errors))
    return not any(rejected(row) for row in configs)


def acs_enable(enabled):
    return js('var s=ipc.network().getDevice("SRV-CAMPUS").getProcess("AcsServer");'
              's.enableACSServerService(' + json.dumps(enabled) + ');return Boolean(s.isEnabled());')


def aaa_configure(name, radius_port, key):
    server = execute(name, ['configure terminal', 'radius-server host ' + SERVER +
                            ' auth-port ' + str(radius_port), 'end'], 'iteration4-radius', True)
    if any(rejected(row) for row in server):
        server = execute(name, ['configure terminal', 'radius-server host ' + SERVER, 'end'],
                         'iteration4-radius-default-port', True)
        if any(rejected(row) for row in server):
            return False
    commands = ['configure terminal', 'aaa new-model', 'radius-server key ' + key,
                'aaa authentication login CAMPUS-AUTH group radius local',
                'aaa authentication login CONSOLE-LOCAL local',
                'line console 0', 'login authentication CONSOLE-LOCAL', 'exit',
                'line vty 0 ' + ('4' if name.startswith('R') else '15'),
                'login authentication CAMPUS-AUTH', 'exit', 'end']
    return not any(rejected(r) for r in execute(name, commands, 'iteration4-aaa', True))


def aaa_rollback(name):
    execute(name, ['configure terminal', 'no aaa new-model', 'line console 0', 'login local', 'exit',
                   'line vty 0 ' + ('4' if name.startswith('R') else '15'), 'login local',
                   'transport input ssh', 'exit', 'end'], 'iteration4-aaa-rollback', True)


def verify_aaa(clients, private, radius_port):
    collectors()
    target = 'SW4-STUDENTS'
    test_address = '192.168.10.150'
    managed = []
    results = {}
    try:
        managed.append(target)
        assert aaa_configure(target, radius_port, private[target]['sharedSecret']), 'AAA command rejected'
        results['central'] = ssh_test(target, test_address, 'iteration4-aaa-central')['passed']
        assert results['central'], 'Central credentials failed'
        local = private[target]
        rejected_local = ssh_test(target, test_address, 'iteration4-aaa-rejected-credentials',
                                  local['username'], local['loginSecret'])
        results['reachableServerRejectsLocal'] = not rejected_local['passed'] and bool(
            re.search(r'Password:|denied|fail|closed', rejected_local['authenticated'], re.I))
        assert results['reachableServerRejectsLocal'], 'Reachable server did not reject unknown account'
        assert not acs_enable(False)
        try:
            results['unavailableServerAllowsLocal'] = ssh_test(target, test_address, 'iteration4-aaa-local-fallback',
                                                                local['username'], local['loginSecret'])['passed']
        finally:
            assert acs_enable(True)
        assert results['unavailableServerAllowsLocal'], 'Local fallback failed'
        for name, address in clients:
            if name == target:
                continue
            managed.append(name)
            assert aaa_configure(name, radius_port, private[name]['sharedSecret']), name + ': AAA command rejected'
            if name == 'R1-CAMPUS':
                address = '192.168.10.145'
            assert ssh_test(name, address, 'iteration4-aaa-' + name)['passed'], name + ': central SSH failed'
        results['passed'] = True
        results['devices'] = managed
    except AssertionError as exc:
        for name in managed:
            aaa_rollback(name)
        acs_enable(False)
        results.update({'passed': False, 'status': 'rolled back', 'reason': str(exc)})
    write('iteration4-aaa-behavior.json', results)


def monitoring():
    require_verified(3)
    private = credentials()
    private.setdefault('routing', {'sharedSecret': secrets.token_hex(8)})
    private.setdefault('ntp', {'sharedSecret': secrets.token_hex(4)})
    private.setdefault('central', {'username': 'campus-operator', 'loginSecret': 'Ac9_' + secrets.token_urlsafe(20)})
    for name in ['R1-CAMPUS', *IOS[2:]]:
        private[name].setdefault('sharedSecret', secrets.token_hex(10))
    (BASE / 'LAB_CREDENTIALS_V2.json').write_text(json.dumps(private, indent=2), encoding='utf-8')
    key = private['routing']['sharedSecret']
    supported = ospf_auth(key, 'iteration4-ospf', True)
    matching = wait_ospf(True) if supported else ''
    if supported and 'FULL/' in matching:
        try:
            wrong = '0' * 16 if key != '0' * 16 else '1' * 16
            execute('R2-EXTERNAL', ['configure terminal', 'interface GigabitEthernet0/0', 'shutdown',
                                   'no ip ospf message-digest-key 1',
                                   'ip ospf message-digest-key 1 md5 ' + wrong, 'end'], 'iteration4-ospf-mismatch')
            assert 'FULL/' not in wait_ospf(False)
            execute('R2-EXTERNAL', ['configure terminal', 'interface GigabitEthernet0/0', 'no shutdown', 'end'],
                    'iteration4-ospf-mismatch-restart')
            mismatch = wait_ospf(True, 47)
        finally:
            ospf_auth(key, 'iteration4-ospf-restore')
        restored = wait_ospf(True)
        write('iteration4-ospf-behavior.json', {'matching': matching, 'mismatch': mismatch, 'restored': restored,
              'passed': 'FULL/' not in mismatch and 'FULL/' in restored})
        assert 'FULL/' in restored
    else:
        for name, port in [('R1-CAMPUS', 'GigabitEthernet0/1'), ('R2-EXTERNAL', 'GigabitEthernet0/0')]:
            execute(name, ['configure terminal', 'interface ' + port, 'no ip ospf authentication',
                           'no ip ospf message-digest-key 1', 'end'], 'iteration4-ospf-rollback', True)
        assert 'FULL/' in wait_ospf(True)
        write('iteration4-ospf-behavior.json', {'passed': False, 'status': 'rolled back after simulator support check'})
    ntp_key = private['ntp']['sharedSecret']
    js('var d=ipc.network().getDevice("SRV-CAMPUS");d.getProcess("SyslogServer").setEnable(true);'
       'var n=d.getProcess("NtpServer");n.setKeyID(1);n.setServerMd5Str(' + json.dumps(ntp_key) +
       ');n.setNtpServerAuthentication(true);n.setEnabled(true);return true;')
    clients = [('R1-CAMPUS', '192.168.10.129')] + [(n, f'192.168.10.{147+i}') for i, n in enumerate(IOS[2:])]
    radius_port = js('return Number(ipc.network().getDevice("SRV-CAMPUS").getProcess("RadiusServerProcess").getPort());')
    if not 0 < radius_port < 65536:
        radius_port = js('var s=ipc.network().getDevice("SRV-CAMPUS").getProcess("RadiusServerProcess");'
                         's.setPort(1645);return Number(s.getPort());')
    extend_acl('R1-CAMPUS', 'MGMT-IN', [
        f'permit udp host {address} host {SERVER} eq {port}'
        for _, address in clients[1:] for port in (514, 123, radius_port)
    ], 'iteration4-monitor-policy')
    extend_acl('R1-CAMPUS', 'SERVICES-IN', [
        f'permit udp host {SERVER} eq {port} host {address}'
        for _, address in clients for port in (123, radius_port)
    ], 'iteration4-monitor-returns')
    base = ['configure terminal', 'service timestamps log datetime msec', 'logging buffered 16384']
    for name in IOS:
        commands = list(base)
        if name != 'R2-EXTERNAL':
            commands += ['logging host ' + SERVER, 'ntp authentication-key 1 md5 ' + ntp_key,
                         'ntp authenticate', 'ntp trusted-key 1', 'ntp server ' + SERVER + ' key 1']
        execute(name, commands + ['end'], 'iteration4-monitor', True)
    execute('SW4-STUDENTS', ['configure terminal', 'interface GigabitEthernet0/2', 'shutdown',
                           'no shutdown', 'end'], 'iteration4-logging-event')
    time.sleep(3)
    logs = js('return ipc.network().getDevice("SRV-CAMPUS").getProcess("SyslogServer").getAllEntries();')
    write('iteration4-monitor-status.json', {
        'receivedLogs': logs, 'devices': {n: {'clock': show(n, 'show clock'), 'ntp': show(n, 'show ntp status'),
            'logging': show(n, 'show logging')} for n in IOS}
    })
    try:
        central = private['central']
        registered = js('''var s=ipc.network().getDevice("SRV-CAMPUS").getProcess("AcsServer");
            s.enableACSServerService(true);s.deleteFromUserMap(USERNAME);
            var out={user:Boolean(s.addToUserMap(USERNAME,"Campus operator",PASSWORD)),clients:{}};
            for(var c of CLIENTS){s.deleteFromClientMap(c.address,1);out.clients[c.name]=Boolean(s.addToClientMap(c.address,1,c.name,c.key));}
            return out;
        '''.replace('USERNAME', json.dumps(central['username'])).replace('PASSWORD', json.dumps(central['loginSecret']))
            .replace('CLIENTS', json.dumps([{'name': n, 'address': ip, 'key': private[n]['sharedSecret']} for n, ip in clients])))
        write('iteration4-aaa-registration.json', registered)
        if registered['user'] and all(registered['clients'].values()):
            verify_aaa(clients, private, radius_port)
        else:
            acs_enable(False)
            write('iteration4-aaa-behavior.json', {'passed': False, 'reason': 'Simulator did not register the AAA clients'})
    except Exception as exc:
        # Do not publish API exceptions that might echo secret-bearing arguments.
        js('ipc.network().getDevice("SRV-CAMPUS").getProcess("AcsServer").enableACSServerService(false);return true;')
        write('iteration4-aaa-registration.json', {'status': 'unverified', 'errorType': type(exc).__name__})
    capture('iteration4-monitoring-after')


def retain_switch_time_sync():
    """The simulated 2960 drops its NTP key on reopen; retain scoped time sync."""
    report = {}
    for name in IOS[2:]:
        execute(name, ['configure terminal', 'no ntp server ' + SERVER,
                       'no ntp trusted-key 1', 'no ntp authenticate',
                       'ntp server ' + SERVER, 'end'], 'iteration4-ntp-switch-fallback')
        result = execute(name, ['configure terminal', 'access-list 20 permit host ' + SERVER,
                                'ntp access-group peer 20', 'end'],
                         'iteration4-ntp-source-restriction', True)
        supported = not any(rejected(row) for row in result)
        if not supported:
            execute(name, ['configure terminal', 'no access-list 20', 'end'],
                    'iteration4-ntp-source-restriction-cleanup')
        report[name] = {'clientAuthentication': 'key lost on reopening',
                        'localPeerAclAccepted': supported, 'routerServiceAclRetained': True}
    write('iteration4-ntp-switch-fallback.json', report)


def verify_monitoring_reopen(state):
    names = [IOS[0], *IOS[2:]]
    end = time.monotonic() + 75
    while True:
        status = {n: show(n, 'show ntp status') for n in names}
        if all('Clock is synchronized' in output and SERVER in output for output in status.values()):
            break
        if time.monotonic() >= end:
            raise AssertionError('Campus device time did not synchronize after reopening')
        js('ipc.appWindow().getRealtimeToolbar().fastForwardTime();return true;')
        time.sleep(.5)
    assert 'ntp authenticate' in state['configs'][IOS[0]]['running']
    for name in names:
        assert 'logging ' in state['configs'][name]['running']
    write('iteration4-monitoring-reopened.json', {'ntp': status, 'authenticatedClient': IOS[0],
                                                 'observedAt': now()})


def regression(label):
    collectors()
    state = capture(label + '-regression')
    management = state['endpoints']['PC8-MGMT']['ip'] == '192.168.10.146'
    dual_core = 'SW5-CORE' in state['configs']
    groups = {}
    groups['campus'] = pings({n: 'ping ' + SERVER for n in CLIENTS}, label + '-campus')
    groups['external'] = pings({n: 'ping 203.0.113.10' for n in CLIENTS if not management or n != 'PC8-MGMT'}, label + '-external')
    groups['http'] = http(CLIENTS, label + '-http')
    missing = [n for n, item in groups['http'].items() if not item['passed']]
    if missing:
        retry = http(missing, label + '-http-retry')
        for n, item in retry.items():
            groups['http'][n]['retry'] = item
            groups['http'][n]['passed'] = item['passed']
    groups['dns'] = {}
    for offset in range(0, len(CLIENTS), 8):
        names = CLIENTS[offset:offset + 8]
        results = batch({n: 'nslookup portal.campus.test' for n in names}, label + f'-dns-{offset}', 15)
        for item in results.values():
            item['passed'] = bool(re.search(r'Name:\s+portal\.campus\.test\s+Address:\s+192\.168\.10\.130', item['output'], re.I))
        groups['dns'].update(results)
    write(label + '-dns.json', groups['dns'])
    gateways = {10: '192.168.10.97', 20: '192.168.10.65', 30: '192.168.10.1'}
    groups['gateways'] = pings({n: 'ping ' + ('192.168.10.145' if management and n == 'PC8-MGMT' else gateways[v]) for v, names in GROUPS.items() for n in names}, label + '-gateways')
    groups['denied'] = pings({'PC0': 'ping ' + state['endpoints']['PC9-ADMIN']['ip'], 'PC5': 'ping ' + state['endpoints']['PC0']['ip'], 'SRV-CAMPUS': 'ping ' + state['endpoints']['PC0']['ip']}, label + '-denials', False)
    groups['allowed'] = pings({'PC8-MGMT': 'ping ' + state['endpoints']['PC0']['ip'], 'PC9-ADMIN': 'ping ' + state['endpoints']['PC5']['ip']}, label + '-allowed')
    targets = [('R1-CAMPUS', '192.168.10.145' if management else '192.168.10.97')] + [(n, f'192.168.10.{147+i if management else 99+i}') for i, n in enumerate(IOS[2:])]
    if dual_core:
        targets[0] = ('R1-CAMPUS', '192.168.10.161')
        targets.extend([('SW5-CORE', '192.168.10.151'), ('SW6-SERVICES', '192.168.10.152')])
    groups['ssh'] = {n: ssh_test(n, address, label + '-ssh-' + n) for n, address in targets}
    groups['sshDenied'] = {}
    for node, address in [('PC9-ADMIN', targets[1][1]), ('PC0', targets[0][1])]:
        groups['sshDenied'].update(batch({node: 'ssh -l ramesh-admin ' + address},
                                         label + '-ssh-denied-' + node, 30, password=True))
    for item in groups['sshDenied'].values():
        item['passed'] = bool(re.search(r'Connection (?:timed out|refused|closed)|connect failed|connection failed|closed by foreign host', item['output'], re.I)) and 'Password:' not in item['output']
    write(label + '-ssh-denied.json', groups['sshDenied'])
    if management:
        groups['managementExternalDenied'] = pings({'PC8-MGMT': 'ping 203.0.113.10'}, label + '-management-external-denied', False)
    assert len({v['ip'] for v in state['endpoints'].values()}) == 52
    assert 'FULL/' in show('R1-CAMPUS', 'show ip ospf neighbor')
    result = {k: {'passed': sum(v['passed'] for v in records.values()), 'total': len(records)} for k, records in groups.items()}
    result['allPassed'] = all(v['passed'] for records in groups.values() for v in records.values())
    result['observedAt'] = now()
    write(label + '-regression-summary.json', result)
    print(json.dumps(result), flush=True)
    assert result['allPassed'], 'Regression must pass before checkpoint'


def baseline():
    state = capture('iteration0-before')
    configs = state['configs']
    comparisons = {}
    for n, pair in configs.items():
        def normalize(text):
            return text[text.index('version '):].strip()
        comparisons[n] = {'runningEqualsStartup': normalize(pair['running']) == normalize(pair['startup'])}
    write('iteration0-config-comparison.json', comparisons)
    assert all(v['runningEqualsStartup'] for v in comparisons.values())
    assert len(state['links']) == 60
    assert len(state['endpoints']) == 52
    collectors()
    campus = pings({n: 'ping ' + SERVER for n in CLIENTS}, 'iteration0-campus')
    external = pings({n: 'ping 203.0.113.10' for n in CLIENTS}, 'iteration0-external')
    portal = http(CLIENTS, 'iteration0-http')
    missing = [n for n, v in portal.items() if not v['passed']]
    if missing:
        retry = http(missing, 'iteration0-http-retry')
        for n, item in retry.items():
            portal[n]['retry'] = item
            portal[n]['passed'] = item['passed']
    denied = pings({'PC0': 'ping ' + state['endpoints']['PC9-ADMIN']['ip'], 'PC5': 'ping ' + state['endpoints']['PC0']['ip'], 'SRV-CAMPUS': 'ping ' + state['endpoints']['PC0']['ip']}, 'iteration0-denials', False)
    result = {'campusPassed': sum(v['passed'] for v in campus.values()), 'externalPassed': sum(v['passed'] for v in external.values()), 'portalPassed': sum(v['passed'] for v in portal.values()), 'denialsPassed': sum(v['passed'] for v in denied.values()), 'observedAt': now()}
    result['passed'] = all(v['passed'] for group in [campus, external, portal, denied] for v in group.values())
    write('iteration0-baseline-summary.json', result)
    print(json.dumps(result), flush=True)
    assert result['passed'], 'Baseline checks require investigation before hardening'


def main():
    global RUN
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=['capture', 'baseline', 'baseline-controls', 'checkpoint0', 'reopen0', 'harden', 'management', 'layer2', 'monitoring', 'monitoring-persistence', 'dual-core', 'firewall', 'regression', 'renew', 'backup-test', 'checkpoint', 'reopen', 'verify-reopened'])
    parser.add_argument('--run', default='evidence/AUDIT-REMEDIATION-20261105-182333')
    parser.add_argument('--label', default='iteration1')
    parser.add_argument('--core', choices=['SW1-CORE', 'SW5-CORE'], help='Repeat one dual-core power-loss case')
    args = parser.parse_args()
    RUN = (BASE / args.run).resolve()
    assert RUN.is_relative_to((BASE / 'evidence').resolve()) and RUN.is_dir()
    if args.stage == 'capture':
        capture('inspection')
    elif args.stage == 'baseline':
        baseline()
    elif args.stage == 'baseline-controls':
        baseline_controls()
    elif args.stage == 'checkpoint0':
        checkpoint('iteration0', 0)
    elif args.stage == 'reopen0':
        reopen('iteration0')
    elif args.stage == 'harden':
        harden()
    elif args.stage == 'management':
        management()
    elif args.stage == 'layer2':
        layer2()
    elif args.stage == 'monitoring':
        monitoring()
    elif args.stage == 'monitoring-persistence':
        retain_switch_time_sync()
    elif args.stage == 'dual-core':
        from audit_core import migrate
        if not migrate():
            raise SystemExit('The isolated multilayer switch HSRP capability checks failed')
    elif args.stage == 'firewall':
        from audit_wan import firewall
        if not firewall():
            raise SystemExit('WAN inspection did not pass the behavior checks')
    elif args.stage == 'regression':
        regression(args.label)
    elif args.stage == 'renew':
        collectors()
        renew_clients(args.label + '-dhcp')
    elif args.stage == 'backup-test':
        collectors()
        if args.label == 'iteration3' and not (RUN / 'iteration3-dai-behavior.json').exists():
            from audit_layer2 import enforce_dai, rogue_dhcp
            rogue_dhcp()
            enforce_dai()
        if 'SW5-CORE' in configured_devices():
            from audit_core import verify_failover
            verify_failover(args.label, args.core)
        else:
            address = js('return String(ipc.network().getDevice("PC8-MGMT").getPort("FastEthernet0").getIpAddress());')
            primary_failure(args.label + '-backup', address == '192.168.10.146')
    elif args.stage == 'checkpoint':
        iteration = int(re.search(r'\d+', args.label)[0])
        assert json.loads((RUN / (args.label + '-regression-summary.json')).read_text())['allPassed']
        if iteration >= 5:
            results = json.loads((RUN / (args.label + '-core-failover.json')).read_text())
            assert set(results) == {'SW1-CORE', 'SW5-CORE'}
            assert all(case['failureRecovery']['passed'] and case['restoration']['passed']
                       for case in results.values())
            from audit_core import refresh_canvas
            refresh_canvas(iteration)
        checkpoint(args.label, iteration)
    elif args.stage == 'reopen':
        address = js('return String(ipc.network().getDevice("PC8-MGMT").getPort("FastEthernet0").getIpAddress());')
        reopen(args.label, address == '192.168.10.146')
    elif args.stage == 'verify-reopened':
        records = [json.loads((RUN / (args.label + '-' + kind + '.json')).read_text())
                   for kind in ('reopen', 'reopened-state', 'reopened-campus', 'reopened-ssh')]
        reopened, prior, checks, check = records
        assert reopened['result'] == 0 and prior['capturedAt'] >= reopened['openedAt']
        assert check['observedAt'] >= reopened['openedAt']
        assert all(v['observedAt'] >= reopened['openedAt'] for v in checks.values())
        assert prior['submissionSha256'] == hashlib.sha256(FILE.read_bytes()).hexdigest()
        live = capture(args.label + '-reopened')
        assert sanitize(live['configs']) == prior['configs'] and live['links'] == prior['links']
        verify_reopened(args.label, live, checks, check)


if __name__ == '__main__':
    sys.modules['audit_remediation'] = sys.modules[__name__]
    main()
