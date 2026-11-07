import type { Capture } from './checkpoint';

export type TopologyView = 'simplified' | 'complete';
export type PhysicalLink = Capture['links'][number];

const simplifiedPositions: Record<string, [number, number]> = {
  'R1-CAMPUS': [515, 30], 'R2-EXTERNAL': [760, 30], 'SRV-EXTERNAL': [1005, 30],
  'SW1-CORE': [355, 200], 'SW5-CORE': [705, 200],
  'SW2-ACCESS': [20, 390], 'SW3-FACULTY': [350, 390], 'SW4-STUDENTS': [680, 390], 'SW6-SERVICES': [1010, 390],
  'PC8-MGMT': [20, 500], 'SRV-CAMPUS': [1010, 500],
};
const accessVlans: Record<string, number> = { 'SW2-ACCESS': 10, 'SW3-FACULTY': 20, 'SW4-STUDENTS': 30, 'SW6-SERVICES': 40 };
// Physical SVI addresses from the saved Iteration 5 configuration exports.
const managementIPs: Record<string, string> = {
  'SW1-CORE': '192.168.10.147', 'SW2-ACCESS': '192.168.10.148', 'SW3-FACULTY': '192.168.10.149',
  'SW4-STUDENTS': '192.168.10.150', 'SW5-CORE': '192.168.10.151', 'SW6-SERVICES': '192.168.10.152',
};

export function topologyFor(capture: Capture, view: TopologyView) {
  const nodes = capture.nodes.filter(node => view === 'complete' || node.name in simplifiedPositions)
    .map(node => ({ ...node, position: view === 'complete'
      // A uniform expansion preserves the Packet Tracer layout and leaves room for full device names.
      ? { x: node.x * 1.6, y: node.y * 1.6 }
      : { x: simplifiedPositions[node.name][0], y: simplifiedPositions[node.name][1] } }));
  const visible = new Set(nodes.map(node => node.name));
  return { nodes, links: capture.links.filter(link => visible.has(link.from) && visible.has(link.to)) };
}

export function connectionFor(capture: Capture, link: PhysicalLink) {
  const endpoint = capture.endpoints.find(item => item.name === link.from || item.name === link.to);
  if (endpoint) return { kind: 'access' as const,
    title: endpoint.segment === 'External' ? 'External LAN' : `Access · VLAN ${endpoint.segment}`,
    detail: endpoint.segment === 'External' ? 'Untagged Ethernet · 203.0.113.0/24' :
      `Untagged endpoint traffic · ${capture.networks.find(network => network.vlan === endpoint.segment)?.name}` };
  const vlan = accessVlans[link.from] ?? accessVlans[link.to];
  if (link.from.startsWith('SW') && link.to.startsWith('SW')) return { kind: 'trunk' as const,
    title: '802.1Q trunk', detail: `Allowed VLANs ${vlan ? `${vlan}, 99` : '10, 20, 30, 40, 99'} · native VLAN 999` };
  const subnet = link.from === 'R2-EXTERNAL' || link.to === 'R2-EXTERNAL' ? '198.51.100.0/30' :
    link.from === 'SW1-CORE' || link.to === 'SW1-CORE' ? '192.168.10.160/30' : '192.168.10.164/30';
  return { kind: 'routed' as const, title: 'Routed Ethernet', detail: subnet === '198.51.100.0/30'
    ? `${subnet} · authenticated OSPF adjacency` : `${subnet} · core-to-edge transit` };
}

interface DeviceLesson {
  role: string;
  what: string;
  purpose: string;
  forwarding: string;
  failure: string;
  concepts: string[];
  facts: { label: string; value: string }[];
  question: string;
  answer: string;
}

export function deviceLessonFor(capture: Capture, name: string): DeviceLesson | undefined {
  const node = capture.nodes.find(item => item.name === name);
  if (!node) return undefined;
  const endpoint = capture.endpoints.find(item => item.name === name);
  if (endpoint) {
    const network = capture.networks.find(item => item.vlan === endpoint.segment);
    const isManagement = endpoint.segment === 99;
    const isCampusServer = endpoint.segment === 40;
    const isExternal = endpoint.segment === 'External';
    const facts = [
      { label: 'Recorded IPv4 address', value: endpoint.ip },
      { label: 'Address assignment', value: endpoint.dhcp ? 'DHCP lease at capture time' : 'Static' },
      { label: 'Network', value: network ? `VLAN ${network.vlan} · ${network.subnet}` : 'External · 203.0.113.0/24' },
      { label: 'Default gateway', value: network?.gateway ?? '203.0.113.1' },
    ];
    if (isCampusServer) return {
      role: 'Central services · application endpoint',
      what: 'A server is an endpoint that answers requests from other devices. This one hosts the shared campus services in VLAN 40.',
      purpose: 'One place provides departmental DHCP leases, DNS resolution and the internal HTTP portal. It also collects syslog events and provides the campus time service.',
      forwarding: 'DHCP broadcasts from client VLANs reach a core gateway, which relays them to this server. DNS and HTTP requests are routed to its static address through the services switch.',
      failure: 'Existing leases can keep working until renewal is needed, but new DHCP allocations, campus DNS, the portal and monitoring services become unavailable. Two switch uplinks do not duplicate the server.',
      concepts: ['DHCP relay', 'DNS', 'HTTP', 'Syslog', 'NTP'], facts,
      question: 'Why does a client in another VLAN need DHCP relay?',
      answer: 'The initial DHCP discovery is a broadcast that routers do not forward between VLANs. The core relay sends it to the server as a routed request.',
    };
    if (isExternal) return {
      role: 'External HTTP service · application endpoint',
      what: 'A simulated external web server on a separate IPv4 LAN behind the External Router.',
      purpose: 'It gives the campus a controlled outside destination for HTTP and ICMP tests, making the OSPF route and PAT translation observable.',
      forwarding: 'A departmental request arrives through the campus edge with a translated source address. This server sends its reply to the External Router, which routes it back to that translated address.',
      failure: 'The external web and ping demonstrations fail even if campus routing still works. Internal switching, gateways and campus services remain separate.',
      concepts: ['HTTP', 'ICMP', 'Default gateway', 'PAT return path'], facts,
      question: 'Why can this server reply to a campus request but fail to initiate a ping to a private campus address?',
      answer: 'A reply targets the edge router’s translated public address and uses an existing PAT entry. A new request to a private campus subnet has no route on the External Router.',
    };
    return {
      role: isManagement ? 'Management endpoint · VLAN 99' : `Departmental client · VLAN ${endpoint.segment}`,
      what: isManagement ? 'A dedicated administration workstation separated from ordinary departmental clients by management VLAN 99.' :
        `A ${endpoint.segment === 30 ? 'student' : network?.name.toLowerCase()} user workstation. It originates requests and receives replies; it does not route other devices’ traffic.`,
      purpose: isManagement ? 'It provides the authorized source for SSH administration, campus diagnostics and internal DNS/HTTP access.' :
        'It represents an end user accessing campus services and the external test server within the department’s access policy.',
      forwarding: 'For a destination in its own subnet, it resolves the peer’s MAC address with ARP and sends through the access switch. For another subnet, it sends the frame to the HSRP virtual default gateway.',
      failure: 'Only this workstation loses access. Its single cable and access switch are still dependencies even though the campus has two core gateways.',
      concepts: isManagement ? ['Management VLAN', 'SSH source restriction', 'ARP', 'Default gateway'] : ['DHCP', 'ARP', 'Same-VLAN switching', 'Inter-VLAN routing'], facts,
      question: isManagement ? 'Does being in the Administration area make this an ordinary Administration client?' : 'Does traffic to another host in the same VLAN need the core gateway?',
      answer: isManagement ? 'No. Its access port belongs to VLAN 99, with a separate subnet and policy. Physical location does not determine VLAN membership. External access from this workstation is denied.' :
        'No. The access switch forwards the frame within the VLAN. The gateway is used for destinations outside the workstation’s subnet.',
    };
  }
  if (name === 'R1-CAMPUS') return {
    role: 'Campus WAN edge · Layer 3',
    what: 'A 2911 router joining the two campus cores to the simulated external network.',
    purpose: 'It separates internal routing from the external OSPF domain and provides PAT for permitted departmental clients.',
    forwarding: 'Campus requests arrive over one of two routed core links. The edge uses the OSPF-learned external route and translates eligible sources to 198.51.100.1. Return translations and preferred/floating static campus routes deliver replies.',
    failure: 'External access stops. Inter-VLAN campus routing and internal services can continue through the cores. The edge router is a remaining single point of failure.',
    concepts: ['PAT overload', 'Authenticated OSPF', 'Static and floating routes', 'Routed ports'],
    facts: [{ label: 'Primary-core transit', value: '192.168.10.161/30' }, { label: 'Standby-core transit', value: '192.168.10.165/30' }, { label: 'External transit / PAT address', value: '198.51.100.1/30' }],
    question: 'Does the edge router provide the user VLAN default gateways?',
    answer: 'No. The core SVIs share those gateways through HSRP. This router handles traffic between the campus and the external network.',
  };
  if (name === 'R2-EXTERNAL') return {
    role: 'Simulated external router · Layer 3',
    what: 'A 1941 router between the campus edge and the External Server’s LAN.',
    purpose: 'It advertises the external server network through authenticated OSPF and demonstrates why PAT makes private-client return traffic possible.',
    forwarding: 'It routes traffic between 198.51.100.0/30 and 203.0.113.0/24. Private campus routes are deliberately absent; replies to 198.51.100.1 can return, while new private-destination requests cannot.',
    failure: 'The external server becomes unreachable from campus. Internal campus services do not depend on this router. Remote management on this router is disabled.',
    concepts: ['OSPF adjacency', 'External LAN', 'Routing lookup', 'Private return-route dependency'],
    facts: [{ label: 'Campus-edge transit', value: '198.51.100.2/30' }, { label: 'External LAN gateway', value: '203.0.113.1/24' }],
    question: 'Would adding private campus routes change the PAT demonstration?',
    answer: 'Yes. It would remove the intentional missing-private-return-route condition. The current exercise uses PAT so replies target the campus edge’s reachable transit address.',
  };
  const isCore = name === 'SW1-CORE' || name === 'SW5-CORE';
  if (isCore) {
    const primary = name === 'SW1-CORE';
    return {
      role: `${primary ? 'Primary' : 'Standby'} multilayer core · Layers 2 and 3`,
      what: 'A 3650 multilayer switch that both switches Ethernet frames and routes IPv4 traffic between VLAN interfaces (SVIs).',
      purpose: primary ? 'It normally leads campus forwarding as the preferred HSRP gateway and Rapid PVST+ root. It connects every access switch and the campus edge.' :
        'It supplies a separate gateway and physical path when the primary core fails. Each access switch and the edge has its own connection to it.',
      forwarding: 'Same-VLAN traffic is switched at Layer 2. Traffic sent to an active virtual gateway is routed through its SVI, checked against the source VLAN’s ingress ACL, and sent toward another VLAN or the edge. DHCP relay reaches the campus server.',
      failure: 'The other core can take over the shared gateways and spanning-tree forwarding paths. Recovery can lose packets while HSRP and STP converge. Access switches, the server and the edge remain individual dependencies.',
      concepts: ['SVI', 'HSRP', 'Rapid PVST+', 'Ingress ACL', 'DHCP relay'],
      facts: [{ label: 'Management SVI · VLAN 99', value: managementIPs[name] },
        { label: 'Core-to-edge address', value: primary ? '192.168.10.162/30' : '192.168.10.166/30' },
        { label: 'Shared HSRP gateways', value: capture.networks.map(network => `VLAN ${network.vlan}: ${network.gateway}`).join(' · ') }],
      question: 'Is a standby core an idle device with all links shut down?',
      answer: 'No. HSRP controls which device owns the virtual gateway; Rapid PVST+ independently selects loop-free Layer 2 paths. A physical link can be connected while STP holds it as an alternate path.',
    };
  }
  const vlan = accessVlans[name];
  const network = capture.networks.find(item => item.vlan === vlan);
  const attached = capture.links.flatMap(link => link.from === name ? [link.to] : link.to === name ? [link.from] : [])
    .filter(id => capture.endpoints.some(item => item.name === id));
  return {
    role: 'Access switch · Layer 2',
    what: `A 2960 access switch connecting the ${network?.name.toLowerCase()} endpoints to the campus distribution paths.`,
    purpose: 'It groups endpoint ports into the intended VLAN and provides a separate 802.1Q trunk to each core. Its management SVI provides an address for administration, not a user routing gateway.',
    forwarding: `Endpoint frames arrive untagged on an access port. Same-VLAN frames are switched using MAC addresses; off-subnet frames travel toward the active core gateway. The uplinks carry VLANs ${vlan} and 99, with unused native VLAN 999. Rapid PVST+ prevents Layer 2 loops.`,
    failure: 'Every endpoint attached to this switch loses its campus path. Dual core uplinks protect against a core or uplink failure, not failure of the access switch itself.',
    concepts: ['MAC learning', 'Access port', '802.1Q trunk', 'Rapid PVST+', 'Management SVI'],
    facts: [{ label: 'Local endpoint VLAN', value: `VLAN ${vlan} · ${network?.name}` },
      { label: 'Attached endpoints', value: String(attached.length) }, { label: 'Management SVI · VLAN 99', value: managementIPs[name] },
      { label: 'Management default gateway', value: '192.168.10.145' }],
    question: 'Do two core uplinks mean every frame is sent over both links?',
    answer: 'No. Spanning tree chooses a loop-free forwarding topology for each VLAN and can keep an alternative path ready. This design uses independent trunks, not a cross-core EtherChannel.',
  };
}
