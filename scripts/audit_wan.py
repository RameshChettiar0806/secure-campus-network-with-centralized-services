"""Apply and verify the Packet Tracer WAN inspection policy."""

import audit_remediation as lab


EDGE = 'R1-CAMPUS'
OUTSIDE = '203.0.113.10'
PROBE = '192.168.10.162'


def policy_commands():
    allowed = []
    for source in ['192.168.10.96 0.0.0.31', '192.168.10.64 0.0.0.31', '192.168.10.0 0.0.0.63']:
        allowed += [f'permit tcp {source} host 203.0.113.10 eq 80',
                    f'permit icmp {source} host 203.0.113.10 echo']
    return ['configure terminal', *lab.install_acl('STATEFUL-DEMO-OUT', allowed),
            'class-map type inspect match-all DEMO-TRAFFIC', 'match access-group name STATEFUL-DEMO-OUT', 'exit',
            'policy-map type inspect CAMPUS-INTERNET', 'class type inspect DEMO-TRAFFIC', 'inspect',
            'exit', 'class class-default', 'drop', 'exit', 'exit',
            'zone security CAMPUS', 'exit', 'zone security DEMO-WAN', 'exit',
            'zone-pair security CAMPUS-TO-DEMO source CAMPUS destination DEMO-WAN',
            'service-policy type inspect CAMPUS-INTERNET', 'exit', 'end']


def zone_membership(ports, undo=False):
    commands = ['configure terminal']
    prefix = 'no ' if undo else ''
    for port, zone in ports:
        commands += ['interface ' + port, prefix + 'zone-member security ' + zone, 'exit']
    return commands + ['end']


def remove_firewall(ports):
    lab.execute(EDGE, zone_membership(ports, undo=True), 'iteration6-detach-firewall', True)
    lab.execute(EDGE, ['configure terminal', 'no zone-pair security CAMPUS-TO-DEMO',
        'no zone security DEMO-WAN', 'no zone security CAMPUS',
        'no policy-map type inspect CAMPUS-INTERNET', 'no class-map type inspect DEMO-TRAFFIC',
        'no ip access-list extended STATEFUL-DEMO-OUT', 'end'], 'iteration6-rollback-firewall', True)


def require_security_package():
    version = lab.show(EDGE, 'show version')
    lab.write('iteration6-edge-package-before.json', version)
    current = next((line.split() for line in version.splitlines()
                    if line.strip().lower().startswith('security ')), [])
    assert len(current) >= 2 and current[1].lower() == 'securityk9', (
        'The simulated edge security package requires interactive evaluation license acceptance'
    )


def firewall():
    lab.require_verified(5)
    require_security_package()
    ports = [('GigabitEthernet0/0', 'CAMPUS'), ('GigabitEthernet0/2', 'CAMPUS'),
             ('GigabitEthernet0/1', 'DEMO-WAN')]
    result = {'configured': False}
    wan_rules = lab.acl_rules(lab.show(EDGE, 'show running-config'), 'WAN-IN')
    probe_route = 'ip route ' + PROBE + ' 255.255.255.255 198.51.100.1'
    probe_rule = 'permit icmp host ' + OUTSIDE + ' host ' + PROBE + ' echo'
    probe = {'SRV-EXTERNAL': 'ping ' + PROBE}
    try:
        lab.extend_acl(EDGE, 'WAN-IN', [probe_rule], 'iteration6-probe-wan-acl')
        lab.execute('R2-EXTERNAL', ['configure terminal', probe_route, 'end'], 'iteration6-probe-route')
        lab.collectors()
        result['unsolicitedPositiveControl'] = lab.pings(probe, 'iteration6-firewall-positive-control')['SRV-EXTERNAL']['passed']
        assert result['unsolicitedPositiveControl'], 'The temporary routed test path failed before firewall inspection'
        commands = lab.execute(EDGE, policy_commands(), 'iteration6-firewall-policy', True)
        assert not any(lab.rejected(row) for row in commands), 'IOS image rejected zone firewall policy'
        commands = lab.execute(EDGE, zone_membership(ports), 'iteration6-firewall-interfaces', True)
        assert not any(lab.rejected(row) for row in commands), 'IOS image rejected zone membership'
        result['configured'] = True
        lab.collectors()
        sample = {'PC9-ADMIN': 'ping 203.0.113.10', 'PC5': 'ping 203.0.113.10', 'PC0': 'ping 203.0.113.10'}
        result['permittedTraffic'] = all(v['passed'] for v in lab.pings(sample, 'iteration6-firewall-permit').values())
        result['permittedHttp'] = all(v['passed'] for v in lab.http(list(sample), 'iteration6-firewall-http', True).values())
        result['unsolicitedBlocked'] = lab.pings(probe,
                                                 'iteration6-firewall-unsolicited', False)['SRV-EXTERNAL']['passed']
        result['ospfFull'] = 'FULL/' in lab.wait_ospf(True)
        result['inspectOutput'] = lab.show(EDGE, 'show policy-map type inspect zone-pair session')
        result['policyOutput'] = lab.show(EDGE, 'show policy-map type inspect zone-pair')
        assert all(result[k] for k in ('permittedTraffic', 'permittedHttp', 'unsolicitedBlocked', 'ospfFull')), 'WAN service or isolation regression'
        result['passed'] = True
    except AssertionError as exc:
        remove_firewall(ports)
        result.update(configured=False, passed=False, reason=str(exc))
    finally:
        lab.execute('R2-EXTERNAL', ['configure terminal', 'no ' + probe_route, 'end'], 'iteration6-probe-route-cleanup')
        lab.extend_acl(EDGE, 'WAN-IN', wan_rules, 'iteration6-probe-wan-acl-cleanup', replace=True)
    lab.write('iteration6-firewall-behavior.json', result)
    print('WAN inspection:', result.get('passed', False), flush=True)
    return result['passed']
