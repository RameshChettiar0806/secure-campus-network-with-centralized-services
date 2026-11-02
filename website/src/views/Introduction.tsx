import type { NetworkSnapshot } from '../models/network';
import styles from './Introduction.module.css';

const technologies = [
  ['Ethernet and switching', 'Switches connect the wired PCs and forward local frames using MAC addresses, so devices in the same VLAN can communicate directly.'],
  ['VLANs and 802.1Q trunks', 'VLANs separate Administration, Faculty, Students and Services into distinct broadcast domains. Trunks carry the required VLANs between switches and the router over shared cables.'],
  ['IPv4 and VLSM', 'Each VLAN has its own subnet and gateway. Different subnet sizes, /26, /27 and /28, provide address capacity for each group without giving every segment the same allocation.'],
  ['Router-on-a-stick', 'R1 uses a logical subinterface for each VLAN over one trunk. This lets PCs reach services in another subnet and gives routed traffic a place to be filtered.'],
  ['DHCP and DHCP relay', 'DHCP automatically supplies an IP address, subnet mask, gateway and DNS server. R1 relays client requests to the central server, which serves three departmental pools.'],
  ['DNS', 'The lab DNS server resolves portal.campus.test to the services server’s IP address, so users can open the portal by a readable name.'],
  ['HTTP', 'The services server delivers the internal portal over TCP port 80. Opening it by hostname demonstrates DNS and web access working together. The lab page uses unencrypted HTTP.'],
  ['Extended access control lists (ACLs)', 'Rules on R1 permit required services and replies while blocking prohibited departmental requests. They check individual packets and do not isolate traffic switched within the same VLAN.'],
  ['SSHv2 and VTY access control', 'SSH encrypts device administration. A source rule on each device’s remote terminal permits only PC8-MGMT, including sessions that reach a switch without going through R1.'],
] as const;

export default function Introduction({ snapshot, openTopology, openPing }: {
  snapshot: NetworkSnapshot;
  openTopology: () => void;
  openPing: () => void;
}) {
  const pcCount = snapshot.devices.filter(device => device.model === 'PC-PT').length;
  const portal = snapshot.services.dns.records[0].name;
  return <section className={styles.introduction} aria-labelledby="project-introduction-title">
    <div className={styles.overview}>
      <div>
        <p className={styles.eyebrow}>ABOUT THE PROJECT</p>
        <h2 id="project-introduction-title">Shared campus services, controlled access</h2>
        <p>A campus needs Administration, Faculty and Students to share services while keeping departmental access under control. This project connects {pcCount} PCs in Cisco Packet Tracer, separates them into departmental networks, and places DHCP, DNS and the campus portal on one central server.</p>
        <p><strong>Our objective:</strong> make client setup consistent, provide access to shared services, and restrict routed traffic and device administration to the intended users.</p>
        <div className={styles.actions}>
          <button onClick={openTopology}>Explore the topology <span aria-hidden="true">→</span></button>
          <button onClick={openPing}>Follow a packet <span aria-hidden="true">→</span></button>
        </div>
      </div>
      <aside className={styles.example} aria-labelledby="portal-example-title">
        <h3 id="portal-example-title">What happens when a student opens the portal?</h3>
        <ol>
          <li><strong>Get connected</strong><span>DHCP supplies the PC’s network settings through R1’s relay.</span></li>
          <li><strong>Find the server</strong><span>DNS looks up <code>{portal}</code>.</span></li>
          <li><strong>Request the page</strong><span>R1 routes the HTTP request to Services. ACLs permit the request and its reply.</span></li>
        </ol>
      </aside>
    </div>

    <div className={styles.technologies}>
      <h2>Technologies used and why</h2>
      <p>Each part has a specific job: connect devices, organize addresses, share services or control access.</p>
      <div className={styles.tableWrap}>
        <table>
          <caption>Networking technologies implemented in the campus lab</caption>
          <thead><tr><th scope="col">Technology</th><th scope="col">What it does and why we use it</th></tr></thead>
          <tbody>{technologies.map(([name, purpose]) => <tr key={name}><th scope="row">{name}</th><td>{purpose}</td></tr>)}</tbody>
        </table>
      </div>
    </div>

    <p className={styles.companion}><strong>How this website helps:</strong> inspect devices in Topology, compare subnets in Addressing table, and explore permissions in Access policy. Ping lab replays captured Packet Tracer commands, while Lab results links to the recorded evidence. The website explains the lab using React, TypeScript, Vite and React Flow.</p>
  </section>;
}
