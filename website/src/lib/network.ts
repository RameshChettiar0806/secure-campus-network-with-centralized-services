import type { NetworkDevice, NetworkSnapshot, PhysicalLink } from '../models/network';

export const vlanColors: Record<number, string> = { 10: '#a78bfa', 20: '#47b8f5', 30: '#f5b55a', 40: '#35d6a4' };
export const shortName = (value: string) => value.charAt(0) + value.slice(1).toLowerCase();
export const assetUrl = (path: string) => `${import.meta.env.BASE_URL}${path}`;
export const dateTime = (value: string) => new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'Asia/Kolkata' }).format(new Date(value));

export function deviceVlans(device: NetworkDevice): number[] {
  return [...new Set([device.vlanId, ...device.interfaces.flatMap(p => [p.vlanId, p.accessVlan, ...(p.trunkVlans ?? [])])].filter((v): v is number => v !== undefined))];
}

export function isDeviceHighlighted(device: NetworkDevice, vlan: number | null) {
  return vlan === null || deviceVlans(device).includes(vlan) || (device.segment === 'external' && [10,20,30].includes(vlan));
}

export function isLinkHighlighted(link: PhysicalLink, vlan: number | null) {
  return vlan === null || link.vlanIds.includes(vlan) || (link.mode === 'routed' && [10,20,30].includes(vlan));
}

export function primaryAddress(device: NetworkDevice) {
  const port = device.interfaces.find(p => p.observedLease || p.ipv4);
  return port?.observedLease?.ipv4 ?? port?.ipv4 ?? 'No IP address';
}

export function readPreference<T>(key: string, fallback: T, validate: (v: unknown) => v is T): T {
  try {
    const raw: unknown = JSON.parse(localStorage.getItem(key) ?? 'null');
    return validate(raw) ? raw : fallback;
  } catch { return fallback; }
}

export function writePreference(key: string, value: unknown) {
  try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* Preferences are optional. */ }
}

export function validateNetwork(snapshot: NetworkSnapshot): string[] {
  const errors: string[] = [];
  const unique = (values: string[], label: string) => {
    if (new Set(values).size !== values.length) errors.push(`Duplicate ${label}`);
  };
  unique(snapshot.devices.map(d => d.id), 'device IDs');
  unique(snapshot.links.map(l => l.id), 'link IDs');
  const ip = (text: string): number => {
    const parts = text.split('.');
    if (parts.length !== 4 || parts.some(p => !/^\d+$/.test(p) || +p > 255)) throw new Error(`Invalid IPv4 address: ${text}`);
    return parts.reduce((n, part) => n * 256 + +part, 0);
  };
  try {
    const ranges = snapshot.vlans.map(v => {
      const [address, prefixText] = v.subnet.split('/');
      const prefix = Number(prefixText);
      if (!Number.isInteger(prefix) || prefix < 1 || prefix > 30) throw new Error('Invalid subnet prefix');
      const start = ip(address), end = start + 2 ** (32 - prefix) - 1;
      if (start % 2 ** (32 - prefix) !== 0) errors.push(`Unaligned subnet ${v.id}`);
      if (ip(v.gateway) <= start || ip(v.gateway) >= end || ip(v.broadcast) !== end) errors.push(`Invalid subnet boundaries ${v.id}`);
      return { id: v.id, start, end };
    });
    ranges.forEach((a, i) => ranges.slice(i + 1).forEach(b => {
      if (a.start <= b.end && b.start <= a.end) errors.push('Overlapping subnets');
    }));
    const statics = snapshot.devices.flatMap(d => d.interfaces.flatMap(p => p.ipv4 ? [p.ipv4] : []));
    const leases = snapshot.devices.flatMap(d => d.interfaces.flatMap(p => p.observedLease ? [p.observedLease.ipv4] : []));
    unique([...statics, ...leases], 'IP addresses');
    for (const pool of snapshot.dhcpPools) {
      const subnet = ranges.find(r => r.id === pool.vlanId);
      const start = ip(pool.start), end = ip(pool.end);
      if (!subnet || start <= subnet.start || end >= subnet.end || start > end || end - start + 1 !== pool.maxUsers) errors.push(`Invalid pool ${pool.id}`);
      if (statics.some(address => ip(address) >= start && ip(address) <= end)) errors.push(`Static address in DHCP pool ${pool.id}`);
    }
    for (const device of snapshot.devices) for (const port of device.interfaces) {
      if (port.assignment === 'dhcp' && port.ipv4) errors.push('DHCP address stored as permanent configuration');
      if (port.observedLease) {
        const pool = snapshot.dhcpPools.find(p => p.id === port.poolId);
        const address = ip(port.observedLease.ipv4);
        if (!pool || address < ip(pool.start) || address > ip(pool.end)) errors.push('Lease outside its pool');
      }
    }
  } catch (error) { errors.push(String(error)); }
  for (const link of snapshot.links) {
    for (const [id, name] of [[link.sourceDeviceId, link.sourceInterface], [link.targetDeviceId, link.targetInterface]]) {
      if (!snapshot.devices.find(d => d.id === id)?.interfaces.some(p => p.name === name)) errors.push(`Broken endpoint ${link.id}`);
    }
    if (link.mode === 'trunk') {
      if (!link.vlanIds.length || link.vlanIds.some(v => !snapshot.vlans.some(s => s.id === v))) errors.push(`Invalid trunk VLANs ${link.id}`);
      for (const [id, name] of [[link.sourceDeviceId, link.sourceInterface], [link.targetDeviceId, link.targetInterface]]) {
        const port = snapshot.devices.find(d => d.id === id)?.interfaces.find(p => p.name === name);
        if (port?.trunkVlans && link.vlanIds.some(v => !port.trunkVlans!.includes(v))) errors.push(`Trunk endpoint VLAN mismatch ${link.id}`);
      }
    }
    if (link.mode === 'routed') {
      if (link.vlanIds.length) errors.push(`Routed link carries VLAN tags ${link.id}`);
      const ports = [[link.sourceDeviceId,link.sourceInterface],[link.targetDeviceId,link.targetInterface]].map(([id,name]) => snapshot.devices.find(d => d.id === id)?.interfaces.find(p => p.name === name));
      if (ports.some(p => !p?.ipv4 || !p.prefixLength)) errors.push(`Unaddressed routed endpoint ${link.id}`);
      else {
        const block = 2 ** (32 - ports[0]!.prefixLength!);
        if (ports[0]!.prefixLength !== ports[1]!.prefixLength || Math.floor(ip(ports[0]!.ipv4!) / block) !== Math.floor(ip(ports[1]!.ipv4!) / block)) errors.push(`Routed endpoint network mismatch ${link.id}`);
      }
    }
  }
  const paths = new Set(snapshot.evidence.map(e => e.path));
  const refs = [...snapshot.recordedTests.flatMap(t => t.evidenceRefs), ...snapshot.devices.flatMap(d => d.configurationRef ? [d.configurationRef] : [])];
  for (const ref of refs) if (!paths.has(ref)) errors.push(`Missing evidence ${ref}`);
  if (!snapshot.devices.length || !snapshot.links.length) errors.push('Empty topology');
  return errors;
}
