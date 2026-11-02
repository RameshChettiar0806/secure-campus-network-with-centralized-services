import type { DeviceId, NetworkSnapshot } from '../models/network';

export interface PingRecord {
  id: string;
  testId: string;
  sourceDeviceId: DeviceId;
  sourceIp: string;
  destinationDeviceId: DeviceId;
  destinationIp: string;
  addressContext: Record<string, string>;
  expected: 'allow' | 'deny';
  sent: number;
  received: number;
  output: string;
  counterDelta: Record<string, number>;
  evidenceRef: string;
  counterScope?: 'command' | 'capture-batch';
  blockingDeviceId?: DeviceId | null;
  enforcementAcl?: string | null;
  decisionReason?: string;
}
export interface HopNote { concept: string; detail: string }
export interface PingStep {
  deviceId: DeviceId;
  phase: 'request' | 'reply' | 'blocked';
  notes: HopNote[];
}
export interface PacketPresentation { steps: PingStep[]; step: number; addresses: Record<string, string>; destinationDeviceId: DeviceId; expected: 'allow' | 'deny' }

export function assertPingRecords(value: unknown): asserts value is PingRecord[] {
  if (!Array.isArray(value) || !value.length) throw new Error('No lab ping examples');
  for (const row of value) {
    if (!row || typeof row !== 'object') throw new Error('Invalid ping example');
    for (const key of ['id', 'testId', 'sourceDeviceId', 'sourceIp', 'destinationDeviceId', 'destinationIp', 'output', 'evidenceRef']) if (typeof row[key] !== 'string' || !row[key]) throw new Error(`Missing ping field: ${key}`);
    if (!['allow', 'deny'].includes(row.expected) || !Number.isInteger(row.sent) || row.sent <= 0 || !Number.isInteger(row.received) || row.received < 0 || row.received > row.sent) throw new Error('Invalid ping outcome');
    if (!row.counterDelta || typeof row.counterDelta !== 'object' || Object.values(row.counterDelta).some(v => typeof v !== 'number' || !Number.isFinite(v) || v < 0)) throw new Error('Invalid ACL counter');
    if (!row.addressContext || typeof row.addressContext !== 'object' || Object.values(row.addressContext).some(v => typeof v !== 'string')) throw new Error('Missing ping address context');
  }
}

export function loadPingRecords(value: unknown): PingRecord[] { assertPingRecords(value); return value; }

export function physicalPath(network: NetworkSnapshot, start: DeviceId, end: DeviceId): DeviceId[] {
  const queue: DeviceId[][] = [[start]];
  const visited = new Set<DeviceId>([start]);
  while (queue.length) {
    const route = queue.shift()!;
    const current = route.at(-1)!;
    if (current === end) return route;
    for (const link of network.links) {
      const next = link.sourceDeviceId === current ? link.targetDeviceId : link.targetDeviceId === current ? link.sourceDeviceId : undefined;
      if (next && !visited.has(next)) { visited.add(next); queue.push([...route, next]); }
    }
  }
  throw new Error(`No physical path between ${start} and ${end}`);
}

export function pingRoute(network: NetworkSnapshot, record: PingRecord): DeviceId[] {
  const source = network.devices.find(d => d.id === record.sourceDeviceId);
  const target = network.devices.find(d => d.id === record.destinationDeviceId);
  if (!source || !target) throw new Error('Unknown ping endpoint');
  const ipNumber = (address: string) => address.split('.').reduce((n, part) => n * 256 + Number(part), 0);
  const port = source.interfaces.find(p => (p.observedLease?.ipv4 ?? p.ipv4) === record.sourceIp);
  const prefix = port?.observedLease?.prefixLength ?? port?.prefixLength ?? 32;
  const local = Math.floor(ipNumber(record.sourceIp) / 2 ** (32 - prefix)) === Math.floor(ipNumber(record.destinationIp) / 2 ** (32 - prefix));
  if (local) return physicalPath(network, source.id, target.id);
  if (record.expected === 'deny') return physicalPath(network, source.id, record.blockingDeviceId ?? 'r1');
  const gateway: DeviceId = source.segment === 'external' ? 'r2' : 'r1';
  const toRouter = physicalPath(network, source.id, gateway);
  if (target.id === gateway) return toRouter;
  return [...toRouter, ...physicalPath(network, gateway, target.id).slice(1)];
}

export function pingSteps(network: NetworkSnapshot, record: PingRecord): PingStep[] {
  const route = pingRoute(network, record);
  const device = (id: DeviceId) => network.devices.find(d => d.id === id)!;
  const source = device(record.sourceDeviceId), target = device(record.destinationDeviceId);
  const sourceVlan = network.vlans.find(v => v.id === source.vlanId);
  const sourcePort = source.interfaces.find(p => (p.observedLease?.ipv4 ?? p.ipv4) === record.sourceIp);
  const targetVlan = target.vlanId ?? target.interfaces.find(p => p.ipv4 === record.destinationIp)?.vlanId;
  const externalRequest = target.id === 'server1' && source.vlanId !== undefined;
  const routerIndex = route.indexOf('r1');
  function switchNotes(id: DeviceId, next: DeviceId, vlan: number | undefined): HopNote[] {
    const link = network.links.find(l => (l.sourceDeviceId === id && l.targetDeviceId === next) || (l.targetDeviceId === id && l.sourceDeviceId === next))!;
    const port = link.sourceDeviceId === id ? link.sourceInterface : link.targetInterface;
    return [{ concept: 'Layer 2 switching', detail: `The destination MAC selects the outgoing port${vlan ? ` in VLAN ${vlan}` : ''}.` },
      { concept: link.mode === 'trunk' ? '802.1Q trunk' : 'Access port', detail: `${port} forwards the frame to ${device(next).label}.` }];
  }
  const steps: PingStep[] = [];
  for (const [i, id] of route.entries()) {
    let notes: HopNote[];
    if (record.expected === 'deny' && i === route.length - 1) {
      const acl = record.enforcementAcl ?? (id === 'r1' ? 'source ingress ACL' : null);
      steps.push({ deviceId: id, phase: 'blocked', notes: [
        { concept: acl ? 'Ingress ACL' : 'No route', detail: record.decisionReason ?? `${device(id).label} drops the echo request to ${record.destinationIp}.` },
        { concept: 'Ping result', detail: `No destination echo reply: ${record.received} of ${record.sent} received.${acl ? ` Enforcement: ${acl}.` : ' R2 has no private campus route; this is not an ACL denial.'}` },
      ] });
      return steps;
    }
    if (i === 0) {
      const local = source.vlanId !== undefined && source.vlanId === targetVlan;
      notes = [{ concept: 'ICMP Echo Request', detail: `Type 8 from ${record.sourceIp} to ${record.destinationIp}.` },
        { concept: 'Ethernet destination', detail: local ? `Same subnet. Resolve ${target.label} by ARP.` : `Use ARP for the next hop; the configured gateway is ${sourcePort?.defaultGateway ?? sourceVlan?.gateway ?? '203.0.113.1'}.` }];
    } else if (i === route.length - 1) {
      notes = [{ concept: 'Local delivery', detail: `${device(id).label} accepts ${record.destinationIp} as its own address.` },
        { concept: 'ICMP Echo Reply', detail: externalRequest ? `Reply to translated address ${network.routing?.patOutsideAddress ?? '198.51.100.1'}, using the translated ICMP identifier.` : `Type 0 from ${record.destinationIp} back to ${record.sourceIp}.` }];
    } else if (id === 'r1') {
      notes = externalRequest ? [
        { concept: 'Ingress ACL', detail: `The VLAN ${source.vlanId} ACL permits ICMP Echo specifically to ${record.destinationIp}.` },
        { concept: 'OSPF-learned route', detail: '203.0.113.0/24 is reached via R2 at 198.51.100.2 on the routed transit link.' },
        { concept: 'PAT / NAT overload', detail: `Translate ${record.sourceIp} to ${network.routing?.patOutsideAddress ?? '198.51.100.1'}; an ICMP identifier distinguishes this flow.` },
      ] : [{ concept: 'Ingress ACL', detail: `R1 permits the request arriving from VLAN ${source.vlanId}.` },
        { concept: 'Layer 3 routing', detail: `R1 builds a new Ethernet frame for VLAN ${targetVlan}.` }];
    } else if (id === 'r2') {
      notes = [{ concept: 'Connected route', detail: source.segment === 'external' ? 'R2 forwards the request over the directly connected transit network toward R1.' : 'R2 forwards the request to the directly connected external server LAN, 203.0.113.0/24.' }];
    } else notes = switchNotes(id, route[i + 1], routerIndex >= 0 && i > routerIndex ? targetVlan : source.vlanId);
    steps.push({ deviceId: id, phase: 'request', notes });
  }
  for (let i = route.length - 2; i >= 0; i--) {
    const id = route[i];
    let notes: HopNote[];
    if (i === 0) notes = [{ concept: 'ICMP Echo Reply', detail: `${source.label} receives Type 0 from ${record.destinationIp}.` }, { concept: 'Ping result', detail: `${record.received} of ${record.sent} replies received.` }];
    else if (id === 'r1') notes = externalRequest ? [
      { concept: 'WAN-IN', detail: 'The outside ACL permits Echo Reply from the external server to 198.51.100.1.' },
      { concept: 'Reverse PAT', detail: `The translation table maps the reply and ICMP identifier back to ${record.sourceIp}.` },
      { concept: 'Return route', detail: `R1 forwards the restored private destination into VLAN ${source.vlanId}.` },
    ] : [{ concept: 'Ingress ACL', detail: `R1 permits the reply arriving from VLAN ${targetVlan}.` }, { concept: 'Return route', detail: `R1 routes to ${record.sourceIp} on VLAN ${source.vlanId}.` }];
    else if (id === 'r2') notes = [{ concept: 'Return route', detail: 'R2 routes the reply to 198.51.100.1 over the directly connected transit network. It has no route to private campus clients.' }];
    else notes = switchNotes(id, route[i - 1], routerIndex >= 0 && i > routerIndex ? targetVlan : source.vlanId);
    steps.push({ deviceId: id, phase: 'reply', notes });
  }
  return steps;
}

export function resolvePingCommand(records: PingRecord[], sourceId: string, command: string): { record?: PingRecord; error?: string } {
  const match = /^\s*ping\s+((?:\d{1,3}\.){3}\d{1,3})\s*$/i.exec(command);
  if (!match || match[1].split('.').some(p => +p > 255)) return { error: 'Enter ping followed by an IPv4 address, for example: ping 192.168.10.130' };
  const record = records.find(r => r.sourceDeviceId === sourceId && r.destinationIp === match[1]);
  return record ? { record } : { error: 'This source/address pair has no lab result yet. Choose one of the available examples, or test this pair in Packet Tracer first.' };
}

export function decodePingSource(value: unknown, sourceId: string, submissionSha256: string): PingRecord[] {
  if (!value || typeof value !== 'object') throw new Error('Invalid source ping data');
  const data = value as { schemaVersion?: number; sourceDeviceId?: string; submissionSha256?: string; addressContext?: Record<string, string>; records?: unknown[] };
  if (data.schemaVersion !== 2 || data.sourceDeviceId !== sourceId || data.submissionSha256 !== submissionSha256 || !data.addressContext || !Array.isArray(data.records)) throw new Error('Ping data belongs to another source or submission');
  const records = data.records.map(row => ({ ...(row as Record<string, unknown>), addressContext: data.addressContext }));
  assertPingRecords(records);
  if (records.some(r => r.sourceDeviceId !== sourceId || r.sourceIp !== r.addressContext[sourceId])) throw new Error('Ping source/address context mismatch');
  return records;
}
