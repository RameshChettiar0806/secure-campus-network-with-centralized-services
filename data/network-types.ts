/** Recorded domain model. It is independent of React Flow and contains no credentials. */
export type DeviceId = 'r1' | 'r2' | `sw${number}` | 'server0' | 'server1' | `pc${number}`;
export type TestStatus = 'not-run' | 'pass' | 'fail' | 'unsupported';
export type InterfaceState = 'up' | 'down' | 'unknown';
export type EvidenceRef = string;

export interface ObservedLease {
  ipv4: string;
  prefixLength: number;
  defaultGateway: string;
  dnsServer: string;
  observedAt: string;
  evidenceRef: EvidenceRef;
}

export interface NetworkInterface {
  name: string;
  kind: 'physical' | 'svi' | 'subinterface';
  administrativeState: 'up' | 'down';
  recordedOperationalState: InterfaceState;
  observedAt: string;
  ipv4?: string;
  prefixLength?: number;
  vlanId?: number;
  mode?: 'access' | 'trunk';
  accessVlan?: number;
  trunkVlans?: number[];
  nativeVlan?: number;
  assignment?: 'static' | 'dhcp';
  poolId?: string;
  observedLease?: ObservedLease;
  defaultGateway?: string;
  dnsServer?: string;
  natRole?: 'inside' | 'outside';
  ospfArea?: number;
  ospfPassive?: boolean;
}

export interface NetworkDevice {
  id: DeviceId;
  label: string;
  model: string;
  role: string;
  position: { x: number; y: number };
  interfaces: NetworkInterface[];
  vlanId?: number;
  configurationRef?: EvidenceRef;
  segment?: 'campus' | 'transit' | 'external';
}

export interface PhysicalLink {
  id: string;
  sourceDeviceId: DeviceId;
  sourceInterface: string;
  targetDeviceId: DeviceId;
  targetInterface: string;
  cableType: 'copper-straight-through' | 'copper-crossover';
  mode: 'access' | 'trunk' | 'routed';
  vlanIds: number[];
}

export interface Vlan {
  id: number;
  name: string;
  subnet: string;
  mask: string;
  wildcard: string;
  gateway: string;
  broadcast: string;
  usableHosts: number;
  poolId?: string;
}

export interface DhcpPool {
  id: string;
  vlanId: number;
  start: string;
  end: string;
  mask: string;
  gateway: string;
  dnsServer: string;
  maxUsers: number;
  purpose: 'client-leases' | 'harmless-simulator-default';
  inUse: boolean;
}

export interface AccessPolicy {
  id: string;
  source: string;
  destination: string;
  protocol: string;
  portOrType: string;
  action: 'permit' | 'deny';
  enforcementPoint: string;
  testIds: string[];
  caveat: string;
}

export interface RecordedTestCase {
  passed: boolean;
  source?: string;
  sourceDeviceId?: DeviceId;
  sourceIp?: string;
  sourceAddressBasis?: string;
  sourceAddressEvidenceRef?: EvidenceRef;
  destination?: string;
  protocol?: string;
  port?: number;
  [key: string]: unknown;
}

export interface RecordedTest {
  id: string;
  runId: string;
  expected: string;
  observed: string;
  status: TestStatus;
  observedAt: string;
  cases: RecordedTestCase[];
  evidenceRefs: EvidenceRef[];
  notes?: string;
}

export interface EvidenceAsset {
  id: string;
  path: EvidenceRef;
  sha256: string;
  mediaType: 'image/png' | 'application/json' | 'text/plain';
}

export interface NetworkSnapshot {
  schemaVersion: '1.0.0';
  snapshotId: string;
  capturedAt: string;
  packetTracerVersion: string;
  submissionFile: string;
  submissionSha256: string;
  testRunId: string;
  projectTitle: string;
  recordingMode: 'verified-snapshot';
  devices: NetworkDevice[];
  links: PhysicalLink[];
  vlans: Vlan[];
  dhcpPools: DhcpPool[];
  policies: AccessPolicy[];
  recordedTests: RecordedTest[];
  evidence: EvidenceAsset[];
  services: {
    serverDeviceId: DeviceId;
    ipv4: string;
    dns: { enabled: boolean; records: Array<{name: string; type: 'A'; value: string}>; verifiedTransports: string[]; unverifiedTransports: string[] };
    http: { enabled: boolean; url: string; port: number };
    dhcp: { enabled: boolean; poolIds: string[] };
    ssh: { deviceIds: DeviceId[]; version: number; configuredRsaModulusBits: number; authorizedSourceDeviceId: DeviceId; port: number };
  };
  limitations: string[];
  routing?: {
    externalServerId: DeviceId;
    externalHostname: string;
    externalAddress: string;
    externalSubnet: string;
    externalGateway: string;
    transitSubnet: string;
    patOutsideAddress: string;
    ospfArea: number;
    ospfNeighborState: string;
    insideVlans: number[];
    evidenceRefs: EvidenceRef[];
  };
  dhcpReopenBehavior: {
    stpConvergenceSeconds: number | null;
    beforeRenew: Record<string, string>;
    afterConvergenceBeforeExplicitRenew: Record<string, string>;
    recoveryAction: string;
    evidenceRefs: EvidenceRef[];
  };
}

/** Small runtime guard for the viewer boundary; the offline validator checks all network invariants. */
export function assertSnapshot(value: unknown): asserts value is NetworkSnapshot {
  if (!value || typeof value !== 'object') throw new Error('Snapshot must be an object');
  const s = value as Record<string, unknown>;
  if (s.schemaVersion !== '1.0.0' || s.recordingMode !== 'verified-snapshot') throw new Error('Unsupported snapshot contract');
  for (const key of ['snapshotId', 'capturedAt', 'packetTracerVersion', 'submissionFile', 'submissionSha256', 'testRunId']) {
    if (typeof s[key] !== 'string' || !(s[key] as string).length) throw new Error(`Missing snapshot field: ${key}`);
  }
  if (!/^[a-f0-9]{64}$/i.test(s.submissionSha256 as string)) throw new Error('Invalid submission hash');
  for (const key of ['devices', 'links', 'vlans', 'dhcpPools', 'policies', 'recordedTests', 'evidence']) {
    if (!Array.isArray(s[key])) throw new Error(`Missing snapshot collection: ${key}`);
  }
  const devices = s.devices as NetworkDevice[];
  const ids = new Set(devices.map(d => d.id));
  if (!devices.length || ids.size !== devices.length) throw new Error('Invalid device inventory');
  for (const d of devices) {
    if (!d.label || !d.model || !d.role || !Array.isArray(d.interfaces)) throw new Error('Invalid device record');
  }
  const links = s.links as PhysicalLink[];
  if (!links.length || new Set(links.map(l => l.id)).size !== links.length) throw new Error('Invalid link inventory');
  for (const l of links) {
    const a = devices.find(d => d.id === l.sourceDeviceId);
    const b = devices.find(d => d.id === l.targetDeviceId);
    if (!a?.interfaces.some(p => p.name === l.sourceInterface) || !b?.interfaces.some(p => p.name === l.targetInterface)) throw new Error(`Broken link endpoint: ${l.id}`);
  }
  const tests = s.recordedTests as RecordedTest[];
  if (!tests.length || new Set(tests.map(t => t.id)).size !== tests.length) throw new Error('Incomplete acceptance matrix');
  for (const t of tests) {
    if (!['not-run', 'pass', 'fail', 'unsupported'].includes(t.status) || t.runId !== s.testRunId || !Array.isArray(t.evidenceRefs)) throw new Error('Invalid recorded test');
    if (t.status === 'pass' && (!t.cases.length || t.cases.some(c => c.passed !== true))) throw new Error('Passing test contains an unverified case');
  }
}
