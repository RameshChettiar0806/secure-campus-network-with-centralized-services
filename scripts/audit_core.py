"""Migrate the verified campus to two Packet Tracer multilayer cores."""

import json
import re
import secrets
import time

import audit_remediation as lab


CORE_A = 'SW1-CORE'
CORE_B = 'SW5-CORE'
SERVICES = 'SW6-SERVICES'
EDGE = 'R1-CAMPUS'
UPLINKS = [('SW2-ACCESS', '10,99'), ('SW3-FACULTY', '20,99'),
           ('SW4-STUDENTS', '30,99'), (SERVICES, '40,99')]
# Keep the previous gateways as HSRP virtual addresses.
VLANS = {
    10: ('192.168.10.97', '192.168.10.98', '192.168.10.99', '255.255.255.224', 'ADMIN-IN'),
    20: ('192.168.10.65', '192.168.10.93', '192.168.10.94', '255.255.255.224', 'FACULTY-IN'),
    30: ('192.168.10.1', '192.168.10.61', '192.168.10.62', '255.255.255.192', 'STUDENTS-IN'),
    40: ('192.168.10.129', '192.168.10.131', '192.168.10.132', '255.255.255.240', 'SERVICES-IN'),
    99: ('192.168.10.145', '192.168.10.147', '192.168.10.151', '255.255.255.240', 'MGMT-IN'),
}
CORE_NETS = [('192.168.10.96', '255.255.255.224'), ('192.168.10.64', '255.255.255.224'),
             ('192.168.10.0', '255.255.255.192'), ('192.168.10.128', '255.255.255.240'),
             ('192.168.10.144', '255.255.255.240')]


def checked(tool, **args):
    result = lab.call(tool, args)
    assert result.get('success'), (tool, args, result)
    return result


def add(name, model, x, y):
    checked('addDevice', deviceName=name, deviceModel=model, x=x, y=y)
    lab.js('ipc.network().getDevice(' + json.dumps(name) + ').skipBoot();return true;')


def link(a, ap, b, bp, cable='cross'):
    checked('addLink', device1Name=a, device1Interface=ap,
            device2Name=b, device2Interface=bp, linkType=cable)


def ports(name):
    return lab.js('var d=ipc.network().getDevice(' + json.dumps(name) + '),p=[];'
                  'for(var i=0;i<d.getPortCount();i++)p.push(String(d.getPortAt(i).getName()));return p;')


def ethernet_ports(name, count):
    available = [p for p in ports(name) if re.fullmatch(r'(?:FastEthernet0/\d+|GigabitEthernet(?:1/0/\d+|0/[1-9]))', p)]
    assert len(available) >= count, name + ': insufficient Ethernet interfaces'
    return available[:count]


def fast_forward():
    lab.js('ipc.appWindow().getRealtimeToolbar().fastForwardTime();return true;')
    time.sleep(.3)


def hsrp_probe(names, trunks, model):
    encapsulation = ['switchport trunk encapsulation dot1q'] if model.startswith('3560') else []
    for index, name in enumerate(names):
        commands = ['configure terminal', 'ip routing', 'vlan 997', 'exit',
                    'interface ' + trunks[index], *encapsulation, 'switchport mode trunk',
                    'switchport trunk allowed vlan 997', 'no shutdown', 'exit',
                    'interface Vlan997', f'ip address 10.255.99.{2+index} 255.255.255.0',
                    'standby 97 ip 10.255.99.1', f'standby 97 priority {110-10*index}',
                    'standby 97 preempt', 'no shutdown', 'exit', 'end']
        if any(lab.rejected(r) for r in lab.execute(name, commands, 'iteration5-hsrp-probe-' + model, True)):
            return False
    for _ in range(4):
        fast_forward()
    states = [lab.show(n, 'show standby brief') for n in names]
    lab.write('iteration5-hsrp-probe-' + model + '.json', dict(zip(names, states)))
    return has_role(states[0], 'Active') and has_role(states[1], 'Standby') and all('10.255.99.1' in s for s in states)


def has_role(output, role):
    return any(role in line.split() for line in output.splitlines() if line.strip().startswith('Vl'))


def has_all_gateway_roles(output, role):
    return sum(role in line.split() for line in output.splitlines()
               if line.strip().startswith('Vl')) == len(VLANS)


def wait_for_peer_roles(seconds=210):
    until = time.monotonic() + seconds
    consecutive = 0
    while time.monotonic() < until:
        pair = {name: lab.show(name, 'show standby brief') for name in (CORE_A, CORE_B)}
        primary = {p[0]: p for line in pair[CORE_A].splitlines() if (p := line.split()) and p[0].startswith('Vl')}
        backup = {p[0]: p for line in pair[CORE_B].splitlines() if (p := line.split()) and p[0].startswith('Vl')}
        stable = all(
            primary.get(f'Vl{vlan}', [])[4:8] == ['Active', 'local', ip_b, vip]
            and backup.get(f'Vl{vlan}', [])[4:8] == ['Standby', ip_a, 'local', vip]
            for vlan, (vip, ip_a, ip_b, _, _) in VLANS.items()
        )
        consecutive = consecutive + 1 if stable else 0
        if consecutive == 3:
            return pair
        time.sleep(4)
    raise AssertionError('The HSRP peers did not remain active and standby for all gateways')


def trunk(port, allowed, description, encapsulation=()):
    return ['interface ' + port, 'description ' + description, *encapsulation, 'switchport mode trunk',
            'switchport trunk allowed vlan ' + allowed, 'switchport trunk native vlan 999',
            'switchport nonegotiate', 'no shutdown', 'exit']


def credentials_for_new_devices():
    private = lab.credentials()
    for name in [CORE_B, SERVICES]:
        private.setdefault(name, {'username': 'ramesh-admin', 'loginSecret': 'Cn9_' + secrets.token_urlsafe(20),
                         'enableSecret': 'En9_' + secrets.token_urlsafe(20), 'sharedSecret': secrets.token_hex(10)})
    (lab.BASE / 'LAB_CREDENTIALS_V2.json').write_text(json.dumps(private, indent=2), encoding='utf-8')
    return private


def access_baseline(name, secret):
    return ['hostname ' + name, 'ip domain-name campus.test', 'service password-encryption',
            'enable secret ' + secret['enableSecret'], 'username ' + secret['username'] + ' secret ' + secret['loginSecret'],
            'crypto key generate rsa general-keys modulus 2048', 'ip ssh version 2',
            'access-list 1 permit host 192.168.10.146', 'access-list 1 deny any',
            'line console 0', 'login local', 'exec-timeout 5 0', 'exit',
            'line vty 0 ' + ('4' if name == EDGE else '15'), 'login local', 'access-class 1 in',
            'transport input ssh', 'exec-timeout 5 0', 'exit']


def policies(config):
    result = {v[4]: lab.acl_rules(config, v[4])[:-1] for v in VLANS.values()}
    # Relays use physical SVI addresses. HSRP supplies the clients' default gateway.
    for vlan in (10, 20, 30):
        for ip in VLANS[vlan][1:3]:
            result['SERVICES-IN'].append(f'permit udp host {lab.SERVER} eq bootps host {ip} eq bootps')
    for ip in ('192.168.10.147', '192.168.10.151', '192.168.10.161', '192.168.10.165'):
        result['MGMT-IN'].append(f'permit tcp host 192.168.10.146 host {ip} eq 22')
        result['MGMT-IN'].append(f'permit icmp host 192.168.10.146 host {ip} echo')
    for ip in ('192.168.10.131', '192.168.10.132', '192.168.10.161', '192.168.10.165', '192.168.10.152'):
        result['SERVICES-IN'] += [f'permit udp host {lab.SERVER} eq {port} host {ip}' for port in (123, 1645, 1812)]
    for ip in ('192.168.10.151', '192.168.10.152'):
        result['MGMT-IN'] += [f'permit udp host {ip} host {lab.SERVER} eq {port}' for port in (123, 514, 1645, 1812)]
    return result


def monitoring_base():
    return ['service timestamps log datetime msec', 'logging buffered 16384',
            'logging host ' + lab.SERVER]


def configure_core(name, index, core_ports, config, private, model):
    encapsulation = ['switchport trunk encapsulation dot1q'] if model.startswith('3560') else []
    commands = ['configure terminal', 'no interface Vlan997', 'no vlan 997',
                *access_baseline(name, private[name]), *monitoring_base(),
                'ntp server ' + lab.SERVER, 'ip routing', 'spanning-tree mode rapid-pvst']
    for vlan in [*VLANS, 998, 999]:
        commands += [f'vlan {vlan}', 'exit']
        if vlan in VLANS:
            commands.append(f'spanning-tree vlan {vlan} priority {4096+4096*index}')
    for port, (peer, allowed) in zip(core_ports, UPLINKS):
        commands += trunk(port, allowed, 'TRUNK_TO_' + peer, encapsulation)
    for port in ethernet_ports(name, 24):
        if port not in core_ports:
            commands += ['interface ' + port, 'switchport mode access', 'switchport access vlan 998', 'shutdown', 'exit']
    commands += trunk(core_ports[4], '10,20,30,40,99', 'INTERCORE_TRUNK', encapsulation)
    local, edge = [('192.168.10.162', '192.168.10.161'), ('192.168.10.166', '192.168.10.165')][index]
    commands += ['interface ' + core_ports[5], 'description ROUTED_TO_R1_CAMPUS', 'no switchport',
                 'ip address ' + local + ' 255.255.255.252', 'no shutdown', 'exit',
                 'ip route 0.0.0.0 0.0.0.0 ' + edge]
    access = policies(config)
    for vlan, (vip, ip_a, ip_b, mask, acl) in VLANS.items():
        local, peer = (ip_a, ip_b) if index == 0 else (ip_b, ip_a)
        rules = [f'permit udp host {peer} host 224.0.0.2 eq 1985', *access[acl], 'deny ip any any']
        commands += lab.install_acl(acl, rules)
        commands += [f'interface Vlan{vlan}', f'ip address {local} {mask}',
                     f'ip access-group {acl} in', f'standby {vlan} ip {vip}',
                     f'standby {vlan} priority {110-10*index}', f'standby {vlan} preempt',
                     f'standby {vlan} timers 3 40']
        if vlan in (10, 20, 30):
            commands.append('ip helper-address ' + lab.SERVER)
        commands += ['no shutdown', 'exit']
    lab.execute(name, commands + ['end'], 'iteration5-core')


def configure_edge(config, private):
    commands = ['configure terminal', *access_baseline(EDGE, private[EDGE]),
                *monitoring_base(), 'ntp authentication-key 1 md5 ' + private['ntp']['sharedSecret'],
                'ntp authenticate', 'ntp trusted-key 1', 'ntp server ' + lab.SERVER + ' key 1',
                'line aux 0', 'no exec', 'exit']
    for port, address in [('GigabitEthernet0/0', '192.168.10.161'), ('GigabitEthernet0/2', '192.168.10.165')]:
        commands += ['interface ' + port, 'description ROUTED_TO_CAMPUS_CORE',
                     'ip address ' + address + ' 255.255.255.252', 'ip nat inside', 'no shutdown', 'exit']
    commands += lab.install_acl('WAN-IN', lab.acl_rules(config, 'WAN-IN'))
    commands += ['interface GigabitEthernet0/1', 'description OSPF_PAT_TRANSIT_TO_R2_EXTERNAL',
                 'ip address 198.51.100.1 255.255.255.252', 'ip access-group WAN-IN in',
                 'ip nat outside', 'no shutdown']
    if 'ip ospf authentication message-digest' in config:
        commands += ['ip ospf authentication message-digest', 'ip ospf message-digest-key 1 md5 ' + private['routing']['sharedSecret']]
    commands += ['exit', 'router ospf 1', 'router-id 1.1.1.1', 'passive-interface default',
                 'no passive-interface GigabitEthernet0/1', 'network 198.51.100.0 0.0.0.3 area 0', 'exit',
                 'ip access-list standard NAT-CLIENTS', 'permit 192.168.10.0 0.0.0.63',
                 'permit 192.168.10.64 0.0.0.31', 'permit 192.168.10.96 0.0.0.31', 'exit',
                 'ip nat inside source list NAT-CLIENTS interface GigabitEthernet0/1 overload']
    for subnet, mask in CORE_NETS:
        commands += [f'ip route {subnet} {mask} 192.168.10.162',
                     f'ip route {subnet} {mask} 192.168.10.166 10']
    lab.execute(EDGE, commands + ['end'], 'iteration5-edge')


def dhcp_reservations():
    # Existing gateways remain in DHCP options. Reduce pools only at their high end.
    lab.js('''var dh=ipc.network().getDevice("SRV-CAMPUS").getProcess("DhcpServerMain").getDhcpServerProcessByPortName("FastEthernet0");
        for(var p of [["FACULTY_POOL","192.168.10.92",27],["STUDENT_POOL","192.168.10.60",59]]){
            var pool=dh.getPool(p[0]);pool.setEndIp(p[1]);pool.setMaxUsers(p[2]);
        }
        var service=dh.getPool("serverPool");service.setStartIp("192.168.10.133");service.setEndIp("192.168.10.133");
        service.setMaxUsers(1);service.setNextAvailableIpAddress("192.168.10.133");return true;''')


def refresh_canvas(iteration):
    wan = ('Stateful WAN inspection with a scoped HTTP/ICMP policy' if iteration >= 6
           else 'WAN ACL permits the OSPF neighbor and scoped HTTP/ICMP replies')
    notes = [
        (480, 10, f'SECURE CAMPUS | ITERATION {iteration} | 50 PCs | 60 DEVICES | 64 LINKS'),
        (80, 30, 'EXTERNAL DEMONSTRATION\nAuthenticated OSPF area 0 and PAT'),
        (170, 170, '203.0.113.10/24 | external.campus.test\nR2 gateway 203.0.113.1'),
        (660, 175, 'R1 EDGE | PAT outside 198.51.100.1\nRouted campus links .161 and .165'),
        (425, 305, 'TWO MULTILAYER CORES\nHSRP virtual gateways and routed departmental ACLs'),
        (90, 360, 'ADMINISTRATION | VLAN 10 | 11 PCs\n192.168.10.96/27 | HSRP .97'),
        (680, 360, 'FACULTY | VLAN 20 | 18 PCs\n192.168.10.64/27 | HSRP .65'),
        (1270, 360, 'STUDENTS | VLAN 30 | 20 PCs\n192.168.10.0/26 | HSRP .1'),
        (1230, 220, 'SERVICES | VLAN 40 | HSRP .129\nSRV-CAMPUS .130 | DHCP, DNS, HTTP, syslog, NTP'),
        (90, 430, 'MANAGEMENT | VLAN 99 | HSRP .145\nPC8-MGMT .146 | Authorized SSH source'),
        (50, 1300, 'Each access switch connects to both cores. Rapid PVST+ selects a forwarding path.\n'
         + wan + '.\nR1, SRV-CAMPUS and individual access switches remain single-device dependencies.'),
    ]
    lab.js('var w=ipc.appWindow().getActiveWorkspace().getLogicalWorkspace();'
           'for(var id of w.getCanvasNoteIds())w.removeCanvasItem(id);'
           'for(var n of ' + json.dumps(notes) + ')w.addNote(n[0],n[1],w.getUnusedLayer(),n[2]);return true;')


def migrate():
    lab.require_verified(4)
    before = lab.capture('iteration5-before')
    config = before['configs'][EDGE]['running']
    probe_names = ['AUDIT-CORE-A', 'AUDIT-CORE-B']
    models = ('3650-24PS', '3560-24PS')
    for model in models:
        added = []
        supported = False
        try:
            for index, name in enumerate(probe_names):
                add(name, model, 550 + 440*index, 265)
                added.append(name)
            core_ports = [ethernet_ports(name, 6) for name in probe_names]
            link(probe_names[0], core_ports[0][4], probe_names[1], core_ports[1][4])
            supported = hsrp_probe(probe_names, [p[4] for p in core_ports], model)
        finally:
            if added and not supported:
                checked('removeDevice', deviceNames=added)
        if supported:
            break
    else:
        lab.write('iteration5-capability.json', {'passed': False, 'models': models,
                  'reason': 'The isolated HSRP probes did not establish active and standby gateways'})
        return False
    lab.write('iteration5-capability.json', {'passed': True, 'model': model})
    checked('removeDevice', deviceNames=[EDGE, CORE_A])
    for old, new in zip(probe_names, (CORE_A, CORE_B)):
        checked('renameDevice', deviceName=old, newName=new)
    add(EDGE, '2911', 770, 120)
    add(SERVICES, '2960-24TT', 1160, 400)
    private = credentials_for_new_devices()
    for index, (peer, allowed) in enumerate(UPLINKS):
        for i, name in enumerate((CORE_A, CORE_B)):
            link(name, core_ports[i][index], peer, f'GigabitEthernet0/{i+1}')
        commands = ['configure terminal']
        if peer == SERVICES:
            commands += [*access_baseline(peer, private[peer]), *monitoring_base(),
                         'ntp server ' + lab.SERVER]
            commands += ['spanning-tree mode rapid-pvst']
            for vlan in (40, 99, 998, 999):
                commands += [f'vlan {vlan}', 'exit']
            commands += ['interface FastEthernet0/1', 'description SRV_CAMPUS_VLAN40',
                         'switchport mode access', 'switchport access vlan 40', 'spanning-tree portfast',
                         'spanning-tree bpduguard enable', 'no shutdown', 'exit', 'interface Vlan99',
                         'ip address 192.168.10.152 255.255.255.240', 'no shutdown', 'exit',
                         'ip default-gateway 192.168.10.145']
            for port in ethernet_ports(peer, 24):
                if port.startswith('FastEthernet') and port != 'FastEthernet0/1':
                    commands += ['interface ' + port, 'switchport mode access',
                                 'switchport access vlan 998', 'shutdown', 'exit']
        for i, core in enumerate((CORE_A, CORE_B)):
            commands += trunk(f'GigabitEthernet0/{i+1}', allowed, 'TRUNK_TO_' + core)
        lab.execute(peer, commands + ['end'], 'iteration5-access')
    link('SRV-CAMPUS', 'FastEthernet0', SERVICES, 'FastEthernet0/1', 'straight')
    link(EDGE, 'GigabitEthernet0/0', CORE_A, core_ports[0][5], 'straight')
    link(EDGE, 'GigabitEthernet0/2', CORE_B, core_ports[1][5], 'straight')
    link(EDGE, 'GigabitEthernet0/1', 'R2-EXTERNAL', 'GigabitEthernet0/0')
    for index, name in enumerate((CORE_A, CORE_B)):
        configure_core(name, index, core_ports[index], config, private, model)
    configure_edge(config, private)
    dhcp_reservations()
    for _ in range(5):
        fast_forward()
    lab.collectors()
    # The unchanged gateway IPs now belong to HSRP virtual MAC addresses.
    lab.batch({name: 'arp -d' for name in lab.HOSTS}, 'iteration5-arp-flush')
    lab.renew_clients('iteration5-dhcp')
    lab.capture('iteration5-after')
    return True


def wait_for_campus(label, seconds=160):
    probes = {'PC9-ADMIN': 'ping ' + lab.SERVER, 'PC5': 'ping ' + lab.SERVER,
              'PC0': 'ping ' + lab.SERVER}
    start = time.monotonic()
    attempt = 0
    while True:
        attempt += 1
        result = lab.pings_once(probes, f'{label}-{attempt}')
        elapsed = round(time.monotonic() - start, 2)
        if all(v['passed'] for v in result.values()):
            return {'passed': True, 'firstSuccessfulProbeBatchSeconds': elapsed, 'attempts': attempt}
        if elapsed >= seconds:
            return {'passed': False, 'lastProbeBatchSeconds': elapsed, 'attempts': attempt}


def verify_failover(label, only=None):
    for name in (CORE_A, CORE_B):
        assert '[OK]' in lab.show(name, 'write memory')
    before = {name: lab.show(name, 'show standby brief') for name in (CORE_A, CORE_B)}
    lab.write(label + '-hsrp-before.json', before)
    assert has_all_gateway_roles(before[CORE_A], 'Active') and has_all_gateway_roles(before[CORE_B], 'Standby')
    report = lab.RUN / (label + '-core-failover.json')
    results = json.loads(report.read_text()) if only and report.exists() else {}
    cases = [(CORE_A, CORE_B), (CORE_B, CORE_A)]
    for failed, surviving in cases:
        if only and failed != only:
            continue
        case = label + '-failure-' + failed
        checked('setPower', deviceName=failed, power=False)
        try:
            status = wait_for_campus(case)
            assert status['passed'], failed + ': campus unreachable during core outage'
            hsrp = lab.show(surviving, 'show standby brief')
            assert has_all_gateway_roles(hsrp, 'Active'), surviving + ': did not take over all gateways'
            campus = lab.pings({n: 'ping ' + lab.SERVER for n in lab.CLIENTS}, case + '-campus')
            outside = lab.pings({n: 'ping 203.0.113.10' for n in lab.CLIENTS if n != 'PC8-MGMT'}, case + '-external')
            addresses = {'PC9-ADMIN': '192.168.10.97', 'PC5': '192.168.10.65',
                         'PC0': '192.168.10.1', 'PC8-MGMT': '192.168.10.145'}
            gateways = lab.pings({n: 'ping ' + ip for n, ip in addresses.items()}, case + '-virtual-gateways')
            target = '192.168.10.165' if failed == CORE_A else '192.168.10.161'
            ssh = lab.ssh_test(EDGE, target, case + '-edge-ssh')
            assert all(v['passed'] for group in (campus, outside, gateways) for v in group.values())
            assert ssh['passed']
            lab.renew_clients(case + '-dhcp')
            portal_clients = ['PC9-ADMIN', 'PC5', 'PC0', 'PC8-MGMT']
            portal = lab.http(portal_clients, case + '-portal')
            external_http = lab.http(portal_clients[:-1], case + '-external-http', external=True)
            assert all(v['passed'] for v in portal.values()), failed + ': campus HTTP regression'
            assert all(v['passed'] for v in external_http.values()), failed + ': external HTTP regression'
            endpoint = lab.js('return String(ipc.network().getDevice("PC9-ADMIN").getPort("FastEthernet0").getIpAddress());')
            assert lab.pings({'PC0': 'ping ' + endpoint}, case + '-isolation', False)['PC0']['passed']
            results[failed] = {'failureRecovery': status, 'survivingCore': surviving, 'hsrp': hsrp,
                               'campusClients': len(campus), 'externalClients': len(outside),
                               'dhcpRenewals': 3, 'portalClients': len(portal),
                               'externalHttpClients': len(external_http), 'isolationPassed': True}
        finally:
            checked('setPower', deviceName=failed, power=True)
        powered_on = time.monotonic()
        restored = wait_for_campus(case + '-restored')
        assert restored['passed']
        # Observe the restored peer separately from ongoing service reachability.
        pair = wait_for_peer_roles(max(1, powered_on + 210 - time.monotonic()))
        results[failed].update(restoration=restored, restoredHsrp=pair,
                               restoredPeerRolesSeconds=round(time.monotonic() - powered_on, 2))
        lab.write(label + '-core-failover.json', results)
