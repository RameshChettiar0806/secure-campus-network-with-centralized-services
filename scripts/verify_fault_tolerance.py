"""Audit recorded fault-tolerance evidence and the saved submission (no live calls)."""
import hashlib
import ipaddress
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
RUN = BASE / 'evidence' / 'FAULT-TOLERANCE-20261105'


def normalize(value):
    if isinstance(value, list):
        return [normalize(v) for v in value]
    if isinstance(value, dict):
        if 'length' in value and all(k == 'length' or k.isdigit() for k in value):
            return [normalize(value[str(i)]) for i in range(value['length'])]
        return {k: normalize(v) for k, v in value.items()}
    return value


def read(name):
    return normalize(json.loads((RUN / name).read_text(encoding='utf-8-sig')))


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def ping(output, sent=None, received=None):
    m = re.search(r'Sent = (\d+), Received = (\d+)', output)
    return bool(m and (sent is None or int(m[1]) == sent)
                and (int(m[2]) > 0 if received is None else int(m[2]) == received))


def http_pass(first, retry, address, marker):
    return {n: any(e.get('serverIp') == address and marker in e.get('content', '')
                   for e in d['events'] + retry.get(n, {}).get('events', []))
            for n, d in first.items()}


def link_key(link):
    return tuple(sorted(((link['from'], link['port']), (link['to'], link['peer']))))


def main():
    before = read('before-state.json')
    reopened = read('reopened-state.json')
    final = read('reopened-checks.json')
    expected = {
        (('SW1-CORE', 'FastEthernet0/2'), ('SW2-ACCESS', 'GigabitEthernet0/2')),
        (('SW1-CORE', 'FastEthernet0/3'), ('SW3-FACULTY', 'GigabitEthernet0/2')),
        (('SW1-CORE', 'FastEthernet0/4'), ('SW4-STUDENTS', 'GigabitEthernet0/2')),
    }
    old = {link_key(v) for v in before['links']}
    new = {link_key(v) for v in final['links']}
    require(len(old) == 57 and len(new) == 60 and old <= new and new - old == expected,
            'Original topology or exact three backup links do not match')
    require(reopened['nodes'] == 58 and reopened['links'] == 60, 'Inventory mismatch')
    require(Path(reopened['file']).name == 'Secure_Campus_Network_Submission.pkt',
            'Unexpected reopened submission')

    for name, state in reopened['switches'].items():
        require('spanning-tree mode rapid-pvst' in state['config'], name + ': mode')
        config = state['config'][state['config'].index('version '):].strip()
        startup = state['startup'][state['startup'].index('version '):].strip()
        require(config == startup, name + ': running/startup mismatch')
        if name == 'SW1-CORE':
            for port in ('GigabitEthernet0/2', 'FastEthernet0/23', 'FastEthernet0/24'):
                block = re.search(r'^interface ' + port + r'\n(.*?)(?=^!|\Z)', config, re.M | re.S)
                require(block is not None and not re.search(r'^ shutdown$', block[1], re.M),
                        'Primary uplink left shut down: ' + port)
            continue
        for block in re.split(r'(?=VLAN\d{4}\n)', state['stp']):
            if not block.startswith('VLAN'):
                continue
            require(re.search(r'Gi0/1\s+Root FWD', block) is not None, name + ': primary')
            require(re.search(r'Gi0/2\s+Altn BLK', block) is not None, name + ': standby')
        for vlan, cost in [(10, 200)] + ([(20, 201)] if name == 'SW3-FACULTY' else
                                         [(30, 202)] if name == 'SW4-STUDENTS' else []):
            require(f'spanning-tree vlan {vlan} cost {cost}' in config, name + ': cost persistence')

    failed = read('simultaneous-primary-failure.json')
    require({v['port'] for v in failed['shutdownCommands']} ==
            {'GigabitEthernet0/2', 'FastEthernet0/23', 'FastEthernet0/24'}, 'Failure injection')
    require(len(failed['monitors']) == 3 and all(ping(v['output'], 30, 30)
            for v in failed['monitors'].values()), 'Failure probes must be 90/90')
    policy = read('backup-path-policy-dhcp-stp.json')
    for name, state in policy['switches'].items():
        for text in state.values():
            require(re.search(r'Gi0/2\s+Root FWD', text) is not None, name + ': failure path')
    for source in ('PC0', 'PC5', 'SRV-CAMPUS'):
        require(ping(policy['checks'][source]['output'], 4, 0), 'Expected policy denial: ' + source)
    require(ping(policy['checks']['PC8-MGMT']['output'], 4, 4), 'Allowed policy control')
    for acl in ('STUDENTS-IN', 'FACULTY-IN', 'SERVICES-IN'):
        def denied_count(text):
            section = text.split('Extended IP access list ' + acl + '\n')[1].split('Extended IP access list ')[0]
            m = re.search(r'deny ip any any(?: \((\d+) match\(es\)\))?', section)
            return int(m[1] or 0) if m else -1
        require(denied_count(policy['after']) > denied_count(policy['before']), acl + ': deny counter')

    require(all(ping(v) for v in read('baseline-campus-pings.json').values()), 'Baseline pings')
    for name in ('backup-path-campus-pings.json', 'backup-path-external-pings.json',
                 'reopened-external-pings.json'):
        data = read(name)
        require(len(data) == 50 and all(ping(v['output']) for v in data.values()), name)
    for label, first, retry, address, marker in [
        ('campus', 'backup-path-http.json', 'backup-path-http-retry.json',
         '192.168.10.130', 'Secure Campus Services Portal'),
        ('external', 'backup-path-external-http.json', 'backup-path-external-http-retry.json',
         '203.0.113.10', 'External Connectivity Demonstration')]:
        passed = http_pass(read(first), read(retry), address, marker)
        require(len(passed) == 50 and all(passed.values()), label + ': backup HTTP')
    require(len(final['pings']) == 50 and all(ping(d['output']) for d in final['pings'].values()),
            'Reopened campus pings')
    require(all(http_pass(final['http'], {}, '192.168.10.130',
                          'Secure Campus Services Portal').values()), 'Reopened portal HTTP')
    require(len(final['leases']) == 52 and len({d['ip'] for d in final['leases'].values()}) == 52,
            'Duplicate or missing endpoint addresses')
    require(sum(bool(d['dhcp']) for d in final['leases'].values()) == 49, 'DHCP client count')
    dhcp = read('backup-path-dhcp-dns-management.json')
    for name, network in [('PC9-ADMIN', '192.168.10.96/27'), ('PC6', '192.168.10.64/27'),
                          ('PC1', '192.168.10.0/26')]:
        v = dhcp['leases'][name]
        require(v['dhcp'] and v['dns'] == '192.168.10.130' and
                ipaddress.ip_address(v['ip']) in ipaddress.ip_network(network), name + ': DHCP')
        require(re.search(r'Name:\s+portal\.campus\.test\s+Address:\s+192\.168\.10\.130',
                          dhcp['checks'][name]['output']), name + ': DNS')
    for name in ('backup-path-ssh-authorized.json', 'backup-path-ssh-denied.json'):
        require(read(name)['passed'], name)
    restored = read('primary-restoration.json')
    require(all(ping(v['output'], 20, 16) for v in restored['monitors'].values()),
            'Documented restoration-loss evidence changed')
    require(all(ping(v, 4, 4) for v in read('restored-connectivity.json').values()),
            'Connectivity did not recover after restoration')
    for name, state in final['routers'].items():
        require(state['config'] == before['configs'][name], name + ': router config changed')
        require('FULL/' in state['ospf'], name + ': OSPF adjacency')

    meta = read('submission.json')
    actual_hash = hashlib.sha256((BASE / meta['file']).read_bytes()).hexdigest()
    require(actual_hash == meta['sha256'].lower(), 'Saved .pkt differs from reopened identity')
    require((BASE / 'SUBMISSION_SHA256.txt').read_text(encoding='utf-8-sig').split()[0].lower()
            == actual_hash, 'Submission hash file is stale')
    configs = read('final-configurations.json')
    for name, config in configs.items():
        require((BASE / 'configs' / (name + '-CURRENT.txt')).read_text(encoding='utf-8-sig').strip()
                == config.strip(), name + ': exported config mismatch')
    manifest = read('manifest.json')
    for entry in manifest['files']:
        path = (BASE / entry['path']).resolve()
        require(path.is_relative_to(BASE.resolve()), 'Manifest path escapes project')
        require(hashlib.sha256(path.read_bytes()).hexdigest() == entry['sha256'],
                'Evidence hash mismatch: ' + entry['path'])
    print(json.dumps({'passed': True, 'networkDevices': 58, 'links': 60,
                      'originalLinksRetained': 57, 'backupLinksAdded': 3,
                      'failoverProbes': {'sent': 90, 'received': 90},
                      'restorationProbesPerSource': {'sent': 20, 'received': 16, 'lost': 4},
                      'backupCampusClients': 50, 'backupExternalClients': 50,
                      'reopenedCampusClients': 50, 'reopenedExternalClients': 50,
                      'sha256': actual_hash, 'hashedArtifacts': len(manifest['files'])}, indent=2))


if __name__ == '__main__':
    main()
