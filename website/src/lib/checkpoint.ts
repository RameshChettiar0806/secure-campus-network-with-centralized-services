export interface Capture {
  iteration: number;
  capturedAt: string;
  submissionSha256: string;
  nodes: { name: string; model: string; x: number; y: number }[];
  links: { from: string; to: string; port: string; peer: string }[];
  networks: { vlan: number; name: string; subnet: string; gateway: string }[];
  endpoints: { name: string; ip: string; segment: number | string; dhcp: boolean }[];
  ping: { total: number; matched: number; rows: Probe[] };
}

export type Endpoint = Capture['endpoints'][number];
export type Probe = { source: string; target: string; expected: string; observed: string; sent: number; received: number };
export type EndpointPair = Pick<Probe, 'source' | 'target'>;

export function resolveCheckpointPing(capture: Capture, source: string, command: string) {
  const match = /^\s*ping\s+(\S+)\s*$/i.exec(command);
  if (!match) return { error: 'Enter a command in the form ping followed by a captured IPv4 address.' };
  const destination = capture.endpoints.find(endpoint => endpoint.ip === match[1]);
  if (!destination) return { error: 'That address has no endpoint test in this capture. Choose a destination from the list.' };
  if (destination.name === source) return { error: 'Choose a destination other than the source device.' };
  const record = capture.ping.rows.find(row => row.source === source && row.target === destination.name);
  return record ? { record } : { error: 'This source and destination pair has no recorded test.' };
}

export const groups = [
  { segment: 30, name: 'Student', workstation: 'Student' },
  { segment: 20, name: 'Faculty', workstation: 'Faculty' },
  { segment: 10, name: 'Administration', workstation: 'Administration' },
  { segment: 99, name: 'Management Workstation', workstation: 'Management' },
  { segment: 40, name: 'Campus Services Server', workstation: 'Services' },
  { segment: 'External', name: 'External Server', workstation: 'External' },
] as const;

const deviceLabels: Record<string, string> = {
  'R1-CAMPUS': 'Campus Edge Router',
  'R2-EXTERNAL': 'External Router',
  'SW1-CORE': 'Primary Core Switch',
  'SW5-CORE': 'Standby Core Switch',
  'SW2-ACCESS': 'Administration Access Switch',
  'SW3-FACULTY': 'Faculty Access Switch',
  'SW4-STUDENTS': 'Student Access Switch',
  'SW6-SERVICES': 'Campus Services Switch',
  'PC8-MGMT': 'PC49-MGMT',
  'SRV-CAMPUS': 'Campus Services Server',
  'SRV-EXTERNAL': 'External Server',
};

export function segmentLabel(segment: Endpoint['segment']) {
  return groups.find(group => group.segment === segment)?.name ?? String(segment);
}

export function deviceLabelsFor(endpoints: Endpoint[]) {
  const labels = new Map(Object.entries(deviceLabels));
  // Keep historical capture keys; display the submission's November 7 PC numbering.
  for (const [segment, firstNumber] of [[30, 0], [20, 20], [10, 38]] as const) {
    endpoints.filter(endpoint => endpoint.segment === segment)
      .sort((a, b) => a.name.localeCompare(b.name, 'en', { numeric: true }))
      .forEach((endpoint, index) => labels.set(endpoint.name, `PC${firstNumber + index}`));
  }
  return labels;
}

export interface Scenario {
  number: number;
  from: Endpoint['segment'];
  to: Endpoint['segment'];
  name: string;
  rows: Probe[];
}

export function buildScenarios(capture: Capture): Scenario[] {
  const segments = new Map(capture.endpoints.map(endpoint => [endpoint.name, endpoint.segment]));
  const byPair = new Map<string, Probe[]>();
  for (const row of capture.ping.rows) {
    const key = JSON.stringify([segments.get(row.source), segments.get(row.target)]);
    const rows = byPair.get(key) ?? [];
    rows.push(row);
    byPair.set(key, rows);
  }
  const scenarios: Scenario[] = [];
  const add = (from: Endpoint['segment'], to: Endpoint['segment']) => {
    const rows = byPair.get(JSON.stringify([from, to]));
    if (rows?.length) scenarios.push({ number: scenarios.length + 1, from, to, name: `${segmentLabel(from)} → ${segmentLabel(to)}`, rows });
  };
  add(30, 'External');
  for (const source of groups) {
    for (const target of groups) {
      if (source.segment !== 30 || target.segment !== 'External') add(source.segment, target.segment);
    }
  }
  return scenarios;
}

export function flowFor(capture: Capture, source: Endpoint, target: Endpoint, expected: string) {
  const attachment = (endpoint: Endpoint) => {
    const link = capture.links.find(link => link.from === endpoint.name || link.to === endpoint.name);
    return link?.from === endpoint.name ? link.to : link?.from;
  };
  const ingress = attachment(source);
  const egress = attachment(target);
  const route = (hops: (string | undefined)[]) => hops.filter((id): id is string => id !== undefined);
  const access = route([source.name, ingress]);
  const campus = [...access, 'SW1-CORE'];
  const destination = route([egress, target.name]);
  if (source.segment === target.segment) {
    const local = [...new Set([...access, ...destination])];
    return { path: local, route: local,
      explanation: 'Both workstations share a VLAN. The access switch forwards the echo request locally at Layer 2. The reply stays in the same VLAN.' };
  }
  if (source.segment === 'External') return {
    path: access,
    route: [...access, 'R1-CAMPUS', 'SW1-CORE', ...destination],
    explanation: 'The external router has no route to the private campus subnets. This externally initiated echo request stops before reaching the campus edge.',
  };
  const fullRoute = target.segment === 'External'
    ? [...campus, 'R1-CAMPUS', ...destination]
    : [...campus, ...destination];
  if (expected === 'deny') return {
    path: campus,
    route: fullRoute,
    explanation: 'The source sends the echo request to its campus gateway. The source VLAN’s ingress policy on the active core denies this direction.',
  };
  if (target.segment === 'External') return {
    path: fullRoute,
    route: fullRoute,
    explanation: 'The primary core routes toward the campus edge. The edge translates the client source with PAT and forwards via the OSPF route to the external router. The echo reply follows the translation back to the client.',
  };
  return {
    path: fullRoute,
    route: fullRoute,
    explanation: 'The active core routes the echo request between the two VLANs. The campus policy permits the request in this direction and the corresponding echo reply.',
  };
}
