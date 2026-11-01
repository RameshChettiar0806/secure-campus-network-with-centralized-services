import { useState } from 'react';
import type { DeviceId, NetworkSnapshot } from '../models/network';
import { shortName } from '../lib/network';
import ui from './Teaching.module.css';
import styles from '../app/App.module.css';

export type PingPair = { source: DeviceId; target: DeviceId };
const representatives: Record<number, DeviceId> = {10: 'pc8', 20: 'pc5', 30: 'pc0', 40: 'server0'};
const localPeers: Record<number, DeviceId> = {10: 'pc9', 20: 'pc6', 30: 'pc1'};
function decision(from: number, to: number) {
  if (from === to) return 'Local';
  if (from === 10 || to === 40) return 'Allow';
  return 'Block';
}

export default function PolicyExplorer({ snapshot, openPing, openTest }: { snapshot: NetworkSnapshot; openPing: (pair: PingPair) => void; openTest: (id: string) => void }) {
  const [pair, setPair] = useState({from: 30, to: 10});
  const name = (id: number) => shortName(snapshot.vlans.find(v => v.id === id)!.name);
  const result = decision(pair.from, pair.to);
  const source = representatives[pair.from];
  const target = pair.from === pair.to ? localPeers[pair.to] : representatives[pair.to];
  const label = (id: DeviceId) => snapshot.devices.find(d => d.id === id)!.label;
  const why = result === 'Local' ? 'Both PCs share a subnet. Their switch forwards the frame within the VLAN, so the request never enters R1’s routed ACL.'
    : result === 'Allow' ? pair.to === 40 ? 'The client VLAN permits echo requests to the services server. The Services ACL permits the echo reply back to the client.' : 'Administration may initiate diagnostic pings into Faculty and Students. The departmental ACL permits the echo reply back to Administration.'
    : pair.from === 40 ? 'The Services ACL permits replies to client requests. A new echo request initiated by the server hits its deny rule at R1.' : 'The source department may use shared services, but its ingress ACL at R1 blocks this new request into another department.';
  return <>
    <p className={ui.intro}>A rule depends on who starts the exchange, where the packet is going and which protocol it uses.</p>
    <div className={ui.matrixLayout}><div className={ui.panel}><h3>Who can start a ping?</h3><p>Read from the sender’s row to the destination column. Select a cell to see the decision.</p>
      <div className={ui.scroll}><table className={ui.matrix}><caption>ICMP echo requests between endpoints</caption><thead><tr><th scope="col">Sender ↓ / To →</th>{snapshot.vlans.map(v => <th scope="col" key={v.id}>{shortName(v.name)}</th>)}</tr></thead><tbody>{snapshot.vlans.map(a => <tr key={a.id}><th scope="row">{shortName(a.name)}</th>{snapshot.vlans.map(b => <td key={b.id}>{a.id === 40 && b.id === 40 ? <small>One server</small> : <button aria-label={name(a.id)+' to '+name(b.id)+', '+decision(a.id,b.id)} aria-pressed={pair.from === a.id && pair.to === b.id} data-result={decision(a.id,b.id)} onClick={() => setPair({from:a.id,to:b.id})}>{decision(a.id,b.id)}</button>}</td>)}</tr>)}</tbody></table></div>
    </div><article className={ui.panel} aria-live="polite"><div className={styles.sectionLabel}>SELECTED EXCHANGE</div><h3>{name(pair.from)} → {name(pair.to)}</h3><strong className={ui.verdict} data-result={result}>{result === 'Local' ? 'Switched locally' : result === 'Allow' ? 'Router permits request' : 'Router blocks request'}</strong><p>{why}</p><button className={styles.outlineButton} onClick={() => openPing({source,target})}>Replay {label(source)} → {label(target)} in Ping lab</button></article></div>
    <h3>How service access differs</h3><div className={ui.cards}><article><h4>Getting an address and opening the portal</h4><p>DHCP supplies client settings. DNS resolves the portal name and HTTP serves the page. A successful ping establishes ICMP reachability. The DNS and HTTP checks establish that those services work.</p><button onClick={() => openTest('A04')}>DNS checks ↗</button> <button onClick={() => openTest('A05')}>HTTP checks ↗</button></article>
    <article><h4>Signing in to a network device</h4><p>Only PC8-MGMT can open an SSH management session. Another Administration PC can ping a switch on VLAN 10, yet the switch’s own management rule refuses its SSH connection.</p><button onClick={() => openTest('A08')}>Authorized SSH ↗</button> <button onClick={() => openTest('A09')}>Refused SSH ↗</button></article></div>
  </>;
}
