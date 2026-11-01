import { describe, expect, it, vi } from 'vitest';
import raw from '../../../data/network-snapshot.v2.json';
import { assertSnapshot, type NetworkSnapshot } from '../models/network';
import { deviceVlans, isDeviceHighlighted, isLinkHighlighted, readPreference, validateNetwork, writePreference } from './network';

function snapshot(): NetworkSnapshot { const value = structuredClone(raw); assertSnapshot(value); return value; }
describe('verified snapshot invariants', () => {
  it('accepts the expanded 56-device, 55-link inventory', () => { expect(snapshot().devices).toHaveLength(56); expect(snapshot().links).toHaveLength(55); expect(validateNetwork(snapshot())).toEqual([]); });
  it('rejects duplicate device IDs at the runtime boundary', () => { const s = snapshot(); s.devices[1].id = s.devices[0].id; expect(() => assertSnapshot(s)).toThrow('inventory'); });
  it('rejects a missing link endpoint', () => { const s = snapshot(); s.links[0].sourceInterface = 'MissingPort'; expect(() => assertSnapshot(s)).toThrow('endpoint'); expect(validateNetwork(s)).toContain(`Broken endpoint ${s.links[0].id}`); });
  it('rejects a passing test with a failed case', () => { const s = snapshot(); s.recordedTests[0].cases[0].passed = false; expect(() => assertSnapshot(s)).toThrow('unverified'); });
  it('rejects duplicate addresses', () => { const s = snapshot(); s.devices.find(d => d.id === 'pc1')!.interfaces[0].observedLease!.ipv4 = s.devices.find(d => d.id === 'pc0')!.interfaces[0].observedLease!.ipv4; expect(validateNetwork(s)).toContain('Duplicate IP addresses'); });
  it('rejects overlapping subnets', () => { const s = snapshot(); s.vlans[1].subnet = s.vlans[0].subnet; expect(validateNetwork(s)).toContain('Overlapping subnets'); });
  it('rejects DHCP pool endings outside their subnet', () => { const s = snapshot(); s.dhcpPools.find(p => p.id === 'ADMIN_POOL')!.end = '192.168.11.254'; expect(validateNetwork(s)).toContain('Invalid pool ADMIN_POOL'); });
  it('keeps static addresses out of dynamic pools', () => { const s = snapshot(); s.dhcpPools.find(p => p.id === 'ADMIN_POOL')!.start = '192.168.10.98'; expect(validateNetwork(s)).toContain('Static address in DHCP pool ADMIN_POOL'); });
  it('rejects leases outside their named pool', () => { const s = snapshot(); s.devices.find(d => d.id === 'pc0')!.interfaces[0].observedLease!.ipv4 = '192.168.11.100'; expect(validateNetwork(s)).toContain('Lease outside its pool'); });
  it('rejects missing evidence references', () => { const s = snapshot(); s.recordedTests[0].evidenceRefs.push('missing.json'); expect(validateNetwork(s)).toContain('Missing evidence missing.json'); });
  it('rejects empty data', () => { const s = snapshot(); s.devices = []; expect(validateNetwork(s)).toContain('Empty topology'); });
  it('rejects a VLAN advertised on a trunk but absent from its switch endpoint', () => { const s = snapshot(); const trunk = s.links.find(l => l.id === 'l-sw1-sw3')!; trunk.vlanIds.push(30); expect(validateNetwork(s)).toContain('Trunk endpoint VLAN mismatch l-sw1-sw3'); });
});
describe('VLAN highlighting preserves shared context', () => {
  it('highlights aggregation for every VLAN and department switches only for their carried VLANs', () => { const s = snapshot(); for (const vlan of s.vlans) for (const id of ['r1', 'sw1']) expect(isDeviceHighlighted(s.devices.find(d => d.id === id)!, vlan.id)).toBe(true); expect(isDeviceHighlighted(s.devices.find(d => d.id === 'sw3')!, 20)).toBe(true); expect(isDeviceHighlighted(s.devices.find(d => d.id === 'sw3')!, 30)).toBe(false); });
  it('highlights only the VLANs actually carried on each trunk and access link', () => { const s = snapshot(); for (const vlan of s.vlans) { expect(s.links.filter(l => l.mode === 'trunk' && isLinkHighlighted(l, vlan.id))).toHaveLength(({10:4,20:2,30:2,40:1} as Record<number,number>)[vlan.id]); for (const l of s.links.filter(l => l.mode === 'access')) expect(isLinkHighlighted(l, vlan.id)).toBe(l.vlanIds.includes(vlan.id)); } });
  it('highlights a Student endpoint only in VLAN 30', () => { const d = snapshot().devices.find(d => d.id === 'pc0')!; expect(deviceVlans(d)).toEqual([30]); expect(isDeviceHighlighted(d, 30)).toBe(true); expect(isDeviceHighlighted(d, 10)).toBe(false); expect(isDeviceHighlighted(d, null)).toBe(true); });
});
describe('optional browser storage', () => {
  it('survives storage being blocked', () => { vi.stubGlobal('localStorage', { getItem() { throw new Error('blocked'); }, setItem() { throw new Error('blocked'); } }); expect(readPreference('theme', 'dark', (v): v is string => typeof v === 'string')).toBe('dark'); expect(() => writePreference('theme', 'light')).not.toThrow(); vi.unstubAllGlobals(); });
  it('ignores malformed stored JSON', () => { vi.stubGlobal('localStorage', { getItem: () => '{broken' }); expect(readPreference('theme', 'dark', (v): v is string => typeof v === 'string')).toBe('dark'); vi.unstubAllGlobals(); });
});
