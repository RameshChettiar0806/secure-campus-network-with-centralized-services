"""Functional checks for the Layer 2 controls on the running simulation."""

import ipaddress
import json
import re
import time

import audit_remediation as lab


def address(name):
    return lab.js('return String(ipc.network().getDevice(' + json.dumps(name) +
                  ').getPort("FastEthernet0").getIpAddress());')


def lease(names, timeout=18):
    lab.js('for(var n of ' + json.dumps(names) + '){var p=ipc.network().getDevice(n).getProcess("DhcpClient");'
           'p.dhcpRelease("FastEthernet0");p.dhcpRun("FastEthernet0");}return true;')
    deadline = time.monotonic() + timeout
    while True:
        addresses = lab.js('var out={};for(var n of ' + json.dumps(names) +
                           ')out[n]=String(ipc.network().getDevice(n).getPort("FastEthernet0").getIpAddress());return out;')
        if all(v != '0.0.0.0' for v in addresses.values()) or time.monotonic() > deadline:
            return addresses
        lab.js('ipc.appWindow().getRealtimeToolbar().fastForwardTime();return true;')
        time.sleep(.3)


def rogue_dhcp():
    from audit_core import checked, link
    switch, rogue, client = 'SW2-ACCESS', 'AUDIT-ROGUE', 'AUDIT-DHCP-CLIENT'
    created = []
    result = {}
    try:
        for name, model in [(rogue, 'Server-PT'), (client, 'PC-PT')]:
            checked('addDevice', deviceName=name, deviceModel=model, x=100, y=250)
            created.append(name)
        link(rogue, 'FastEthernet0', switch, 'FastEthernet0/13', 'straight')
        link(client, 'FastEthernet0', switch, 'FastEthernet0/14', 'straight')
        lab.execute(switch, ['configure terminal', 'vlan 997', 'name ISOLATED_DHCP_TEST', 'exit',
                    'interface range FastEthernet0/13 - 14', 'switchport access vlan 997', 'spanning-tree portfast',
                    'no shutdown', 'end'], 'iteration3-rogue-isolated')
        checked('configurePcIp', deviceName=rogue, dhcpEnabled=False, ipaddress='192.0.2.2',
                subnetMask='255.255.255.0', defaultGateway='192.0.2.1', dnsServer='192.0.2.2')
        checked('configurePcIp', deviceName=client, dhcpEnabled=True)
        lab.js('var d=ipc.network().getDevice("AUDIT-ROGUE");'
               'var s=d.getProcess("DhcpServerMain").getDhcpServerProcessByPortName("FastEthernet0");'
               's.addNewPool("AUDIT", "192.0.2.1", "192.0.2.2", "192.0.2.10", "255.255.255.0", 4, "0.0.0.0", "0.0.0.0");'
               's.setEnable(true);return true;')
        result['unprotectedLease'] = lease([client])[client]
        if ipaddress.ip_address(result['unprotectedLease']) in ipaddress.ip_network('192.0.2.0/24'):
            lab.execute(switch, ['configure terminal', 'ip dhcp snooping vlan 997', 'end'], 'iteration3-rogue-enforce')
            result['protectedLease'] = lease([client], 8)[client]
            result['passed'] = result['protectedLease'] == '0.0.0.0'
        else:
            result['status'] = 'unverified because the unprotected control did not receive a lease'
    except (AssertionError, RuntimeError) as exc:
        result['status'] = 'unverified'
        result['reason'] = str(exc)
    finally:
        if created:
            checked('removeDevice', deviceNames=created)
        lab.execute(switch, ['configure terminal', 'no ip dhcp snooping vlan 997',
                    'interface range FastEthernet0/13 - 14', 'switchport access vlan 998',
                    'shutdown', 'exit', 'no vlan 997', 'end'], 'iteration3-rogue-cleanup', True)
    lab.write('iteration3-rogue-dhcp.json', result)


def enforce_dai():
    from audit_core import checked
    switches = {10: 'SW2-ACCESS', 20: 'SW3-FACULTY', 30: 'SW4-STUDENTS'}
    findings = json.loads((lab.RUN / 'iteration3-binding-protection-capabilities.json').read_text())
    if not all(findings[name]['dai'] for name in switches.values()):
        return
    result = {'bindings': {}, 'configured': False}
    for vlan, switch in switches.items():
        names = [n for n in lab.GROUPS[vlan] if n != 'PC8-MGMT']
        renewed = {}
        for offset in range(0, len(names), 8):
            renewed.update(lease(names[offset:offset + 8]))
        bindings = set(re.findall(r'\b192\.168\.10\.\d+\b', lab.show(switch, 'show ip dhcp snooping binding')))
        missing = [name for name, ip in renewed.items() if ip not in bindings]
        for name in missing:
            renewed.update(lease([name]))
        if missing:
            bindings = set(re.findall(r'\b192\.168\.10\.\d+\b', lab.show(switch, 'show ip dhcp snooping binding')))
        result['bindings'][switch] = len([ip for ip in renewed.values() if ip in bindings])
        if result['bindings'][switch] != len(names):
            lab.write('iteration3-dai-behavior.json', {**result, 'reason': 'Incomplete dynamic binding table'})
            return
    for vlan, switch in switches.items():
        lab.execute(switch, ['configure terminal', f'ip arp inspection vlan {vlan}', 'end'], 'iteration3-dai-enabled')
    result['configured'] = True
    lab.collectors()
    pc, peer = 'PC9-ADMIN', 'PC40'
    target = 'ping ' + address(peer)
    control = lab.pings({pc: target}, 'iteration3-dai-control')
    if control[pc]['passed']:
        assigned = {address(name) for name in lab.GROUPS[10]}
        forged = next(f'192.168.10.{i}' for i in range(125, 103, -1) if f'192.168.10.{i}' not in assigned)
        try:
            checked('configurePcIp', deviceName=pc, dhcpEnabled=False, ipaddress=forged,
                    subnetMask='255.255.255.224', defaultGateway='192.168.10.97', dnsServer=lab.SERVER)
            lab.batch({pc: 'arp -d'}, 'iteration3-dai-clear-arp', 5)
            spoof = lab.pings({pc: target}, 'iteration3-dai-spoof', False, 45)
            result['spoofBlocked'] = spoof[pc]['passed']
            result['statistics'] = lab.show(switches[10], 'show ip arp inspection statistics')
        finally:
            checked('configurePcIp', deviceName=pc, dhcpEnabled=True)
            result['restoredLease'] = lease([pc])[pc]
    result['restoredTraffic'] = lab.pings({pc: target}, 'iteration3-dai-restored')[pc]['passed']
    if not control[pc]['passed'] or not result.get('spoofBlocked') or not result['restoredTraffic']:
        for vlan, switch in switches.items():
            lab.execute(switch, ['configure terminal', f'no ip arp inspection vlan {vlan}', 'end'],
                        'iteration3-dai-rollback')
        result['configured'] = False
        result['reason'] = 'DAI behavior did not meet all simulator checks'
    lab.write('iteration3-dai-behavior.json', result)
