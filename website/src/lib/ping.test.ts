import { describe, expect, it } from 'vitest';
import rawNetwork from '../../../data/network-snapshot.v3.json';
import rawMatrix from '../../../data/ping-matrix.v3.json';

import { assertSnapshot } from '../models/network';
import { assertPingRecords, decodePingSource, loadPingRecords, physicalPath, pingRoute, pingSteps, resolvePingCommand } from './ping';
assertSnapshot(rawNetwork);
const network = rawNetwork;
const records = loadPingRecords(rawMatrix.records.map(r => ({ ...r, addressContext: rawMatrix.addressContext })));
const pair = (source: string, target: string) => records.find(r => r.sourceDeviceId === source && r.destinationDeviceId === target)!;

describe('ICMP forwarding explanation', () => {
  it('carries external requests through both routers and explains PAT and reverse PAT', () => {
    const record = pair('pc0','server1');
    expect(pingRoute(network,record)).toEqual(['pc0','sw4','sw1','r1','r2','server1']);
    const steps = pingSteps(network,record);
    expect(steps.find(s => s.deviceId === 'r1' && s.phase === 'request')?.notes.some(n => n.concept === 'PAT / NAT overload')).toBe(true);
    expect(steps.find(s => s.deviceId === 'r1' && s.phase === 'reply')?.notes.some(n => n.concept === 'Reverse PAT')).toBe(true);
  });
  it('stops external-to-private requests at R2 and identifies a routing failure', () => {
    const record = pair('server1','pc0');
    expect(pingRoute(network,record)).toEqual(['server1','r2']);
    const last = pingSteps(network,record).at(-1)!;
    expect(last.phase).toBe('blocked');
    expect(last.notes[0].concept).toBe('No route');
  });
  it('distinguishes unsolicited WAN denial from private-route failure', () => {
    const record = records.find(r => r.sourceDeviceId === 'server1' && r.destinationIp === '198.51.100.1')!;
    expect(pingRoute(network,record)).toEqual(['server1','r2','r1']);
    expect(pingSteps(network,record).at(-1)?.notes.some(n => n.detail.includes('WAN-IN'))).toBe(true);
  });
  it('delivers local external requests to R2 without inventing a campus VLAN', () => {
    const record = records.find(r => r.sourceDeviceId === 'server1' && r.destinationIp === '203.0.113.1')!;
    expect(pingRoute(network,record)).toEqual(['server1','r2']);
    expect(pingSteps(network,record).at(-1)?.phase).toBe('reply');
  });
  it('routes inter-VLAN server access through R1, returning to SW1', () => {
    expect(pingRoute(network, pair('pc0', 'server0'))).toEqual(['pc0', 'sw4', 'sw1', 'r1', 'sw1', 'server0']);
  });
  it('keeps same-VLAN forwarding off the router', () => {
    expect(pingRoute(network, pair('pc0', 'pc1'))).toEqual(['pc0', 'sw4', 'pc1']);
  });
  it('uses the added access switches for new clients and switches management frames without R1', () => {
    expect(pingRoute(network, pair('pc49', 'pc39'))).toEqual(['pc49', 'sw2', 'sw1', 'r1', 'sw1', 'sw3', 'pc39']);
    expect(pingRoute(network, pair('pc49', 'sw4'))).toEqual(['pc49', 'sw2', 'sw1', 'sw4']);
  });
  it('switches Administration management pings locally, even without a device-wide switch VLAN', () => {
    expect(pingRoute(network, pair('pc8', 'sw1'))).toEqual(['pc8', 'sw2', 'sw1']);
    expect(pingRoute(network, pair('pc8', 'sw2'))).toEqual(['pc8', 'sw2']);
    expect(pingRoute(network, pair('pc9', 'sw2'))).toEqual(['pc9', 'sw2']);
  });
  it('stops a denied request at R1 without reaching the target or making replies', () => {
    const steps = pingSteps(network, pair('pc0', 'pc8'));
    expect(steps.map(s => s.deviceId)).toEqual(['pc0', 'sw4', 'sw1', 'r1']);
    expect(steps.at(-1)?.phase).toBe('blocked');
    expect(steps.some(s => s.phase === 'reply')).toBe(false);
  });
  it('returns permitted echo replies along the reverse physical path', () => {
    const record = pair('pc8', 'pc5'), route = pingRoute(network, record);
    const steps = pingSteps(network, record);
    expect(steps.filter(s => s.phase === 'reply').map(s => s.deviceId)).toEqual(route.slice(0, -1).reverse());
    expect(steps.at(-1)?.deviceId).toBe('pc8');
  });
  it('uses actual physical links for every hop, including repeated switch visits', () => {
    for (const record of records) {
      const addresses = Object.values(record.addressContext);
      expect(new Set(addresses).size).toBe(addresses.length);
      const steps = pingSteps(network, record);
      expect(steps.flatMap(s => s.notes).some(n => n.detail.includes('undefined'))).toBe(false);
      steps.slice(1).forEach((s, i) => expect(network.links.some(l => (l.sourceDeviceId === s.deviceId && l.targetDeviceId === steps[i].deviceId) || (l.targetDeviceId === s.deviceId && l.sourceDeviceId === steps[i].deviceId))).toBe(true));
    }
  });
  it('fails explicitly for a disconnected topology', () => { expect(() => physicalPath({ ...network, links: [] }, 'pc0', 'r1')).toThrow('No physical path'); });
});
describe('lab command evidence', () => {
  it('rejects invalid command data and impossible reply counts', () => {
    expect(() => assertPingRecords([])).toThrow('No lab ping examples');
    const broken = structuredClone(records); broken[0].received = broken[0].sent + 1;
    expect(() => assertPingRecords(broken)).toThrow('Invalid ping outcome');
  });
  it('preserves test-time DHCP identities instead of using another run’s leases', () => {
    const context = rawMatrix.addressContext;
    for (const record of records) {
      expect(record.addressContext).toEqual(context);
      expect(record.sourceIp).toBe(context[record.sourceDeviceId as keyof typeof context]);
      if (record.destinationDeviceId in context) expect(record.destinationIp).toBe(context[record.destinationDeviceId as keyof typeof context]);
    }
  });
  it('includes real CLI output with consistent sent/received counts and manifest references', () => {
    const refs = new Set([...network.evidence, ...rawMatrix.evidence].map(e => e.path));
    expect(records).toHaveLength(3224);
    for (const record of records) {
      expect(record.output).toContain(`ping ${record.destinationIp}`);
      expect(record.output).toContain(`Sent = ${record.sent}, Received = ${record.received}`);
      expect(refs.has(record.evidenceRef)).toBe(true);
      expect(record.received > 0).toBe(record.expected === 'allow');
      if (record.expected === 'deny' && record.enforcementAcl) expect(Object.entries(record.counterDelta).some(([rule, count]) => rule.startsWith(record.enforcementAcl! + ' |') && rule.includes(' deny ') && count >= 4)).toBe(true);
      if (record.expected === 'deny' && !record.enforcementAcl) expect(record.blockingDeviceId).toBe('r2');
    }
  });
  it('covers every directed endpoint/device pair and all four router gateway addresses', () => {
    const hosts = network.devices.filter(d => d.model === 'PC-PT' || d.model === 'Server-PT');
    expect(new Set(records.map(r => `${r.sourceDeviceId}:${r.destinationIp}`)).size).toBe(3224);
    for (const source of hosts) {
      const rows = records.filter(r => r.sourceDeviceId === source.id);
      expect(rows).toHaveLength(62);
      for (const target of network.devices.filter(d => d.id !== source.id)) expect(rows.some(r => r.destinationDeviceId === target.id)).toBe(true);
      for (const vlan of network.vlans) expect(resolvePingCommand(records, source.id, `ping ${vlan.gateway}`).record?.destinationDeviceId).toBe('r1');
    }
  });
  it('accepts only a covered source/address pair', () => {
    expect(resolvePingCommand(records, 'pc0', 'ping 192.168.10.130').record?.destinationDeviceId).toBe('server0');
    expect(resolvePingCommand(records, 'pc2', 'ping 192.168.10.130').record?.destinationDeviceId).toBe('server0');
    expect(resolvePingCommand(records, 'pc2', 'ping 192.168.10.254').error).toContain('no lab result');
  });
  it('rejects malformed addresses and extra command syntax', () => {
    for (const command of ['ping 999.1.1.1', 'ping localhost', 'ping 192.168.10.130; ssh', 'tracert 192.168.10.130']) expect(resolvePingCommand(records, 'pc0', command).record).toBeUndefined();
  });
});


describe('source-file loading boundary', () => {
  const payload = () => ({ schemaVersion: 2, sourceDeviceId: 'pc49', submissionSha256: network.submissionSha256, addressContext: rawMatrix.addressContext, records: rawMatrix.records.filter(r => r.sourceDeviceId === 'pc49') });
  it('decodes all 62 records for an added PC', () => { expect(decodePingSource(payload(), 'pc49', network.submissionSha256)).toHaveLength(62); });
  it('rejects a response for another source or submission', () => { expect(() => decodePingSource(payload(), 'pc48', network.submissionSha256)).toThrow('another source'); expect(() => decodePingSource(payload(), 'pc49', '0'.repeat(64))).toThrow('another source'); });
});
