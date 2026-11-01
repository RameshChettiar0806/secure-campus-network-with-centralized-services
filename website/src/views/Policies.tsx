import { useState } from 'react';
import PolicyExplorer, { type PingPair } from '../components/PolicyExplorer';
import type { NetworkSnapshot } from '../models/network';
import styles from '../app/App.module.css';

export default function Policies({ snapshot, openTest, openPing }: { snapshot: NetworkSnapshot; openPing: (pair: PingPair) => void; openTest: (id: string) => void }) {
  const [action, setAction] = useState('all');
  const rules = snapshot.policies.filter(p => action === 'all' || p.action === action);
  return <section className={styles.dataView}><div className={styles.viewIntro}><div className={styles.sectionLabel}>ACCESS POLICY</div><h2>Which connections does the campus allow?</h2></div>
    <PolicyExplorer snapshot={snapshot} openPing={openPing} openTest={openTest}/>
    <details className={styles.ruleDetails}><summary>View detailed rules · {snapshot.policies.length}</summary>
    <label className={styles.selectLabel}>Show rules <select value={action} onChange={e => setAction(e.target.value)}><option value="all">All actions</option><option value="permit">Permit</option><option value="deny">Deny</option></select></label>
    <div className={styles.tableWrap}><table><caption>{rules.length} policy rules</caption><thead><tr><th>Action</th><th>Source → Destination</th><th>Protocol / service</th><th>Enforcement</th><th>Lab checks</th></tr></thead><tbody>{rules.map(p => <tr key={p.id}><td><span className={p.action === 'permit' ? styles.permit : styles.deny}>{p.action === 'permit' ? '↗ Permit' : '⊘ Deny'}</span></td><td><strong>{p.source}</strong><div className={styles.muted}>→ {p.destination}</div><small>{p.caveat}</small></td><td>{p.protocol}<br/><code>{p.portOrType}</code></td><td>{p.enforcementPoint}</td><td><div className={styles.testLinks}>{p.testIds.map(id => <button key={id} onClick={() => openTest(id)}>{id}</button>)}{!p.testIds.length && <span className={styles.muted}>Not tested</span>}</div></td></tr>)}</tbody></table></div>
    </details>
  </section>;
}
