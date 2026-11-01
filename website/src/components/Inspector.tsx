import { useState } from 'react';
import type { NetworkSnapshot } from '../models/network';
import { primaryAddress } from '../lib/network';
import DeviceSymbol from './DeviceSymbol';
import EvidenceAsset from './EvidenceAsset';
import styles from '../app/App.module.css';

export default function Inspector({ snapshot, selected, linkId, select }: { snapshot: NetworkSnapshot; selected: string; linkId: string | null; select: (id: string) => void }) {
  const [showConfig, setShowConfig] = useState(false);
  const [showInactive, setShowInactive] = useState(false);
  const device = snapshot.devices.find(d => d.id === selected)!;
  const inactiveCount = device.interfaces.filter(p => p.recordedOperationalState === 'down').length;
  const link = snapshot.links.find(l => l.id === linkId);
  if (link) return <aside className={styles.inspector} aria-label="Link inspector"><div className={styles.sectionLabel}>LINK INSPECTOR</div><h2>{link.mode === 'trunk' ? '802.1Q trunk' : 'Access link'}</h2><p className={styles.muted}>{link.id}</p>
    {[{ id: link.sourceDeviceId, port: link.sourceInterface }, { id: link.targetDeviceId, port: link.targetInterface }].map((endpoint, i) => <div className={styles.portCard} key={endpoint.id}><span className={styles.sectionLabel}>ENDPOINT {i + 1}</span><button className={styles.textButton} onClick={() => select(endpoint.id)}>{snapshot.devices.find(d => d.id === endpoint.id)?.label} ↗</button><code>{endpoint.port}</code></div>)}
    <dl className={styles.facts}><dt>Cable</dt><dd>{link.cableType.replace('copper-', '').replaceAll('-', ' ')}</dd><dt>Mode</dt><dd>{link.mode}</dd><dt>Carried VLANs</dt><dd>{link.vlanIds.join(', ')}</dd></dl><p className={styles.help}>Access links carry one VLAN. Each trunk carries the VLANs listed above; departmental trunks also carry management VLAN 10.</p></aside>;
  return <aside className={styles.inspector} aria-label="Device inspector"><div className={styles.sectionLabel}>DEVICE INSPECTOR</div><div className={styles.inspectorIcon}><DeviceSymbol model={device.model} size={34}/></div><h2>{device.label}</h2><p className={styles.muted}>{device.role}</p>
    <dl className={styles.facts}><dt>Model</dt><dd>{device.model}</dd><dt>Primary address</dt><dd><code>{primaryAddress(device)}</code></dd></dl>
    <h3>Interfaces <span>{device.interfaces.length} total</span></h3>{inactiveCount > 0 && <button className={styles.textButton} style={{ fontSize: 10, marginBottom: 12 }} onClick={() => setShowInactive(v => !v)} aria-expanded={showInactive}>{showInactive ? 'Hide' : 'Show'} {inactiveCount} inactive interfaces</button>}<div className={styles.ports}>{device.interfaces.filter(port => showInactive || port.recordedOperationalState !== 'down').map(port => <div className={styles.portCard} key={port.name}><div className={styles.portHeading}><code>{port.name}</code><span className={port.recordedOperationalState === 'up' ? styles.statusUp : styles.muted}>{port.recordedOperationalState}</span></div>
      <small>{port.kind}{port.mode ? ` · ${port.mode}` : ''}{port.accessVlan ? ` · VLAN ${port.accessVlan}` : ''}{port.vlanId ? ` · VLAN ${port.vlanId}` : ''}</small>
      {port.ipv4 && <code>{port.ipv4}/{port.prefixLength} · static</code>}
      {port.observedLease && <><code>{port.observedLease.ipv4}/{port.observedLease.prefixLength}</code><small>DHCP-assigned address</small></>}
      {port.trunkVlans && <small>Tagged VLANs {port.trunkVlans.join(' / ')} · native {port.nativeVlan ?? 1}</small>}
      {port.defaultGateway && <small>Gateway {port.defaultGateway}</small>}{port.dnsServer && <small>DNS {port.dnsServer}</small>}
      <small>Administrative state: {port.administrativeState}</small>
    </div>)}</div>
    {device.configurationRef && <><button className={styles.outlineButton} onClick={() => setShowConfig(v => !v)} aria-expanded={showConfig}>{showConfig ? 'Hide' : 'View'} sanitized configuration ↗</button>{showConfig && <EvidenceAsset path={device.configurationRef} snapshot={snapshot}/>}</>}
    <p className={styles.help}>DHCP-assigned addresses can change after renewal.</p>
  </aside>;
}
