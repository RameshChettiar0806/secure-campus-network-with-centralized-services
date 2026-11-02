import { useState } from 'react';
import type { NetworkSnapshot } from '../models/network';
import { shortName } from '../lib/network';
import DeviceSymbol from './DeviceSymbol';
import styles from '../app/App.module.css';
import guide from './Teaching.module.css';

const examples: Record<number, { device: string; description: string }> = {
  10: { device: 'pc8', description: 'Administrative PCs can initiate diagnostic pings into Faculty and Students. PC8-MGMT has the reserved address .98 and is the authorized SSH workstation.' },
  20: { device: 'pc5', description: 'Faculty PCs share one local network. They can use the campus server and reply to Administration diagnostics. R1 filters new requests toward other departments.' },
  30: { device: 'pc0', description: 'Student lab PCs can communicate locally and open the campus portal. A Student initiating a ping to an Administration PC reaches a policy boundary at R1.' },
  40: { device: 'server0', description: 'The shared server supplies IP settings through DHCP, resolves portal.campus.test through DNS, and delivers the portal page through HTTP.' },
};

export default function TopologyGuide({ snapshot, inspect }: { snapshot: NetworkSnapshot; inspect: (id: string, vlan: number | null) => void }) {
  const [selected, setSelected] = useState(30);
  const vlan = snapshot.vlans.find(v => v.id === selected)!;
  const example = snapshot.devices.find(d => d.id === examples[selected].device)!;
  const wire = snapshot.links.find(l => l.sourceDeviceId === example.id || l.targetDeviceId === example.id)!;
  const switchId = wire.sourceDeviceId === example.id ? wire.targetDeviceId : wire.sourceDeviceId;
  const access = snapshot.devices.find(d => d.id === switchId)!;
  const count = snapshot.devices.filter(d => d.vlanId === selected).length;
  return <section className={styles.dataView}>
    <div className={styles.viewIntro}><div className={styles.sectionLabel}>TOPOLOGY GUIDE</div><h2>How the campus is connected</h2><p>Start with a department, follow its cable to a switch, then see where its traffic can go.</p></div>
    <div className={guide.choices} aria-label="Choose a network segment">{snapshot.vlans.map(v => <button key={v.id} aria-pressed={v.id === selected} onClick={() => setSelected(v.id)}>{shortName(v.name)} · VLAN {v.id}</button>)}</div>
    <article className={guide.panel}><h3>{shortName(vlan.name)}</h3><p>{examples[selected].description}</p>
      <div className={guide.flow}><div><DeviceSymbol model={example.model}/><strong>{example.label}</strong><small>Example of {count} {selected === 40 ? 'server' : 'PCs'}</small></div><span aria-hidden="true">→</span><div><DeviceSymbol model={access.model}/><strong>{access.label}</strong><small>Access port · VLAN {selected}</small></div></div>
      <p><strong>Local subnet</strong> <code>{vlan.subnet}</code> · <strong>Default gateway</strong> <code>{vlan.gateway}</code></p>
      <button className={styles.outlineButton} onClick={() => inspect(example.id, selected)}>Locate {example.label} on the topology →</button>
    </article>
    {snapshot.routing && <article className={guide.panel}><h3>The external branch</h3><p>Client traffic crosses its access switch and SW1 to R1. An OSPF-learned route sends permitted requests to R2. PAT changes the private source to 198.51.100.1; R2 then forwards to the external server. Replies use the PAT entry to return to the original client.</p><div className={guide.flow}><div><DeviceSymbol model="1941"/><strong>R1-CAMPUS</strong><small>PAT · 198.51.100.1</small></div><span>↔</span><div><DeviceSymbol model="1941"/><strong>R2-EXTERNAL</strong><small>OSPF area 0 · .2</small></div><span>→</span><div><DeviceSymbol model="Server-PT"/><strong>SRV-EXTERNAL</strong><small>203.0.113.10 · HTTP</small></div></div><button className={styles.outlineButton} onClick={() => inspect('r2',null)}>Locate R2 and the external branch →</button></article>}
    <h3>What the components do</h3>
    <div className={guide.cards}>{[
      ['Client PC', 'A PC sends and receives traffic. Its subnet mask tells it whether a destination is local. For a remote subnet, it sends the frame to its default gateway.'],
      ['Access switch and VLAN', 'SW2 connects Administration, SW3 connects Faculty, and SW4 connects Students. Each PC plugs into an access port assigned to one VLAN. The switch forwards local frames using MAC addresses.'],
      ['Core switch and trunks', 'SW1 joins the access switches, server and router. A trunk carries tagged VLAN traffic over one cable. For example, the SW1–SW4 trunk carries Student VLAN 30 and management VLAN 10.'],
      ['Router and gateway', 'R1 has one physical link to SW1 and a logical interface for each VLAN. When a Student reaches the server, SW1 sends the frame up to R1 in VLAN 30. R1 routes it back down the same cable in VLAN 40.'],
      ['Services server', 'A new PC requests settings from DHCP. R1 relays that request to the server. Later the PC asks DNS for the portal address and opens an HTTP connection to that address.'],
      ['Access rules and management', 'An access control list (ACL) at R1 checks traffic arriving from each VLAN. A separate rule on each router or switch management terminal restricts SSH to PC8-MGMT, including connections switched locally.'],
      ['OSPF and PAT boundary', 'R1 and R2 exchange OSPF information on 198.51.100.0/30. R2 advertises the server LAN but receives no private campus prefixes. PAT allows replies to return to R1’s outside address; WAN-IN filters incoming traffic.'],
    ].map(([title, body]) => <article key={title}><h4>{title}</h4><p>{body}</p></article>)}</div>
  </section>;
}
