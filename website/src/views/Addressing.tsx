import { useState } from 'react';
import { shortName, vlanColors } from '../lib/network';
import type { NetworkSnapshot } from '../models/network';
import styles from '../app/App.module.css';

export default function Addressing({ snapshot }: { snapshot: NetworkSnapshot }) {
  const [query, setQuery] = useState('');
  const search = query.trim().toLowerCase();
  const rows = snapshot.devices.flatMap(device =>
    device.interfaces
      .filter(port => port.ipv4 || port.observedLease)
      .map(port => ({ device, port, address: port.observedLease?.ipv4 ?? port.ipv4 }))
  ).filter(({ device, address }) =>
    device.label.toLowerCase().includes(search) || address?.includes(search)
  );
  return <section className={styles.dataView}><div className={styles.viewIntro}><div className={styles.sectionLabel}>ADDRESSING PLAN</div><h2>VLANs and routed networks</h2><p>Four campus VLANs retain their VLSM addressing. Two additional routed networks carry the OSPF transit and external server LAN.</p></div>
    <div className={styles.vlanCards}>{snapshot.vlans.map(v => { const pool = snapshot.dhcpPools.find(p => p.id === v.poolId); return <article key={v.id} className={styles.vlanCard} style={{ borderTopColor: vlanColors[v.id] }}><span style={{ color: vlanColors[v.id] }}>VLAN {v.id}</span><h3>{shortName(v.name)}</h3><code>{v.subnet}</code><dl className={styles.facts}><dt>Gateway</dt><dd>{v.gateway}</dd><dt>Mask</dt><dd>{v.mask}</dd><dt>Broadcast</dt><dd>{v.broadcast}</dd><dt>DHCP range</dt><dd>{pool ? `${pool.start} – ${pool.end}` : 'Static addressing'}</dd><dt>Connected endpoints</dt><dd>{snapshot.devices.filter(d => d.vlanId === v.id).length}</dd><dt>Usable hosts</dt><dd>{v.usableHosts}</dd><dt>Pool capacity</dt><dd>{pool ? `${pool.maxUsers} addresses` : '—'}</dd></dl></article>; })}</div>
    {snapshot.routing && <div className={styles.vlanCards}>
      <article className={styles.vlanCard} style={{borderTopColor:'#67cdd6'}}><span>ROUTED ETHERNET · AREA 0</span><h3>OSPF / PAT transit</h3><code>{snapshot.routing.transitSubnet}</code><dl className={styles.facts}><dt>R1 Gi0/1</dt><dd>198.51.100.1/30 · PAT outside</dd><dt>R2 Gi0/0</dt><dd>198.51.100.2/30</dd><dt>Encapsulation</dt><dd>Ethernet · no VLAN trunk</dd></dl></article>
      <article className={styles.vlanCard} style={{borderTopColor:'#67cdd6'}}><span>ROUTED ETHERNET · EXTERNAL LAN</span><h3>External server network</h3><code>{snapshot.routing.externalSubnet}</code><dl className={styles.facts}><dt>R2 Gi0/1</dt><dd>{snapshot.routing.externalGateway}/24</dd><dt>Server</dt><dd>{snapshot.routing.externalAddress}/24</dd><dt>DNS name</dt><dd>{snapshot.routing.externalHostname}</dd><dt>OSPF</dt><dd>Advertised subnet · passive LAN</dd></dl></article>
    </div>}
    <label className={styles.selectLabel}>Find an address
      <input type="search" placeholder="Device name or IP" value={query} onChange={event => setQuery(event.target.value)}/>
    </label>
    <div className={styles.tableWrap}><table><caption>Client and infrastructure addresses · {rows.length} matches</caption><thead><tr><th>Device</th><th>Interface</th><th>VLAN</th><th>Address / prefix</th><th>Assignment</th><th>Gateway</th></tr></thead><tbody>{rows.map(({ device: d, port: p, address }) => <tr key={`${d.id}-${p.name}`}><td>{d.label}</td><td><code>{p.name}</code></td><td>{p.vlanId ?? d.vlanId ?? '—'}</td><td><code>{address}/{p.observedLease?.prefixLength ?? p.prefixLength}</code></td><td>{p.assignment === 'dhcp' ? 'DHCP' : 'Static'}</td><td><code>{p.defaultGateway ?? '—'}</code></td></tr>)}{rows.length === 0 && <tr><td colSpan={6}>No matching devices. Try an IP prefix or clear the search.</td></tr>}</tbody></table></div>
    <p className={styles.help}>Three DHCP pools serve Administration, Faculty and Students. Services use static addressing. DHCP addresses can change after renewal.</p>
  </section>;
}
