import { useState } from 'react';
import type { DeviceId, NetworkSnapshot } from '../models/network';
import matrix from '../../../data/policy-matrix.v3.json';
import ui from './Teaching.module.css';
import styles from '../app/App.module.css';

export type PingPair = { source: DeviceId; target: DeviceId };

export default function PolicyExplorer({ snapshot, openPing, openTest }: { snapshot: NetworkSnapshot; openPing: (pair: PingPair) => void; openTest: (id: string) => void }) {
  const [pair, setPair] = useState({from: 'students', to: 'admin'});
  const examples = matrix.examples;
  const current = examples.find(r => r.fromSegment === pair.from && r.toSegment === pair.to)!;
  const segment = (id: string) => matrix.segments.find(s => s.id === id)!;
  const label = (id: string) => snapshot.devices.find(d => d.id === id)!.label;
  const explanation = current.verdict === 'Local' ? 'The two clients share a VLAN. Their switch forwards locally, bypassing the routed ACLs.'
    : current.verdict === 'No route' ? 'R2 does not have a route to private campus prefixes. The request stops at R2; this result is not an ACL match.'
    : current.toSegment === 'external' && current.verdict === 'Allow' ? 'The client ingress ACL permits Echo to 203.0.113.10. R1 uses its OSPF-learned route and PAT, so replies can return through the outside address.'
    : current.reason;
  return <>
    <p className={ui.intro}>These ICMP decisions come from the current 3,224-command capture. Choose a cell to inspect the reason and replay its measured result. HTTP, SSH and OSPF have separate service rules.</p>
    <div className={ui.matrixLayout}><div className={ui.panel}><h3>Who can start a ping?</h3><p>Read from the sender’s row to the destination column. External represents SRV-EXTERNAL, not every outside address.</p>
      <div className={ui.scroll}><table className={ui.matrix}><caption>Measured ICMP Echo between campus and external endpoints</caption><thead><tr><th scope="col">Sender ↓ / To →</th>{matrix.segments.map(s => <th scope="col" key={s.id}>{s.name}</th>)}</tr></thead><tbody>{matrix.segments.map(a => <tr key={a.id}><th scope="row">{a.name}</th>{matrix.segments.map(b => { const row=examples.find(r => r.fromSegment === a.id && r.toSegment === b.id); return <td key={b.id}>{row ? <button aria-label={`${a.name} to ${b.name}, ${row.verdict}`} aria-pressed={pair.from === a.id && pair.to === b.id} data-result={row.verdict === 'No route' ? 'Block' : row.verdict} onClick={() => setPair({from:a.id,to:b.id})}>{row.verdict}</button> : <small>One server</small>}</td>; })}</tr>)}</tbody></table></div>
    </div><article className={ui.panel} aria-live="polite"><div className={styles.sectionLabel}>SELECTED MEASURED EXCHANGE</div><h3>{segment(pair.from).name} → {segment(pair.to).name}</h3><strong className={ui.verdict} data-result={current.verdict === 'No route' ? 'Block' : current.verdict}>{current.verdict === 'Local' ? 'Switched locally' : current.verdict === 'Allow' ? 'Request permitted' : current.verdict === 'No route' ? 'R2 has no private route' : 'R1 ACL blocks request'}</strong><p>{explanation}</p><p><code>{current.recordId}</code> · <code>ping {current.destinationIp}</code></p><button className={styles.outlineButton} onClick={() => openPing({source:current.source as DeviceId,target:current.target as DeviceId})}>Replay {label(current.source)} → {label(current.target)} in Ping lab</button></article></div>
    <h3>Service access and WAN boundaries</h3><div className={ui.cards}>
      <article><h4>Campus DHCP, DNS and HTTP</h4><p>The campus server continues to supply addresses, resolve names and serve the internal portal. A ping alone does not prove that these application services work.</p><button onClick={() => openTest('A04')}>DNS checks ↗</button> <button onClick={() => openTest('A05')}>Campus HTTP ↗</button></article>
      <article><h4>External HTTP through PAT</h4><p>All three client VLANs may reach 203.0.113.10 on TCP 80 and with ICMP Echo. Other outside destinations and unlisted ports remain blocked. NAT-CLIENTS selects translations; the extended ACLs enforce access.</p><button onClick={() => openTest('E03')}>External HTTP ↗</button> <button onClick={() => openTest('E04')}>PAT evidence ↗</button></article>
      <article><h4>Unsolicited outside traffic</h4><p>WAN-IN allows OSPF from R2 and selected replies from the external server. A new Echo Request to R1’s outside address is denied. Private campus destinations fail earlier at R2 because it has no route.</p><button onClick={() => openPing({source:'server1',target:'r1'})}>Replay WAN denial ↗</button> <button onClick={() => openTest('E05')}>WAN policy checks ↗</button></article>
      <article><h4>OSPF and management</h4><p>OSPF protocol 89 is permitted on the transit link. The outside server LAN is passive. PC8-MGMT remains the only authorized SSH source for the five campus IOS devices.</p><button onClick={() => openTest('E01')}>OSPF adjacency ↗</button> <button onClick={() => openTest('A08')}>Authorized SSH ↗</button></article>
    </div>
  </>;
}
