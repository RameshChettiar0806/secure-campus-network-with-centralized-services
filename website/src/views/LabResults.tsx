import { useEffect, useState } from 'react';
import type { NetworkSnapshot, TestStatus } from '../models/network';
import { dateTime } from '../lib/network';
import EvidenceAsset from '../components/EvidenceAsset';
import topologyLab from '../../../output/pdf/01-topology-and-addressing.pdf?no-inline';
import servicesLab from '../../../output/pdf/02-centralized-services.pdf?no-inline';
import policyLab from '../../../output/pdf/03-access-policy.pdf?no-inline';
import styles from '../app/App.module.css';

const walkthroughs = [
  { title: 'Trace a campus connection', url: topologyLab },
  { title: 'Open the campus portal', url: servicesLab },
  { title: 'Test a policy in both directions', url: policyLab },
];

export default function LabResults({ snapshot, selectedTest, selectTest }: { snapshot: NetworkSnapshot; selectedTest: string; selectTest: (id: string) => void }) {
  const [status, setStatus] = useState<TestStatus | 'all'>('all');
  const [asset, setAsset] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [showAllEvidence, setShowAllEvidence] = useState(false);
  
  const visible = snapshot.recordedTests.filter(t => status === 'all' || t.status === status);
  const test = visible.find(t => t.id === selectedTest) ?? visible[0];
  useEffect(() => { setPage(0); setAsset(null); setShowAllEvidence(false); }, [test?.id]);
  return <section className={styles.dataView}><div className={styles.viewIntro}><div className={styles.sectionLabel}>LAB VERIFICATION</div><h2>Recorded lab results</h2><p>272 acceptance checks and a complete 2,958-pair ICMP matrix from the expanded Packet Tracer network.</p></div>
    <section className={styles.walkthroughs} aria-labelledby="walkthrough-title">
      <h3 id="walkthrough-title">Printable lab walkthroughs</h3>
      <ul>{walkthroughs.map(({ title, url }) => (
        <li key={url}><a href={url}>{title} <small>(PDF)</small></a></li>
      ))}</ul>
    </section>
    <label className={styles.selectLabel}>Test status <select value={status} onChange={e => setStatus(e.target.value as TestStatus | 'all')}><option value="all">All checks</option>{(['pass', 'fail', 'not-run', 'unsupported'] as const).map(s => <option key={s}>{s}</option>)}</select></label>
    <div className={styles.testLayout}><div className={styles.testList} aria-label="Lab check list">{visible.map(t => <button key={t.id} aria-pressed={t.id === test.id} className={t.id === test.id ? styles.testActive : ''} onClick={() => { selectTest(t.id); setAsset(null); }}><span><code>{t.id}</code><span className={t.status === 'pass' ? styles.statusUp : styles.muted}>{t.status === 'pass' ? '✓ ' : ''}{t.status}</span></span><strong>{t.expected}</strong></button>)}{visible.length === 0 && <p className={styles.help}>No lab checks have this status.</p>}</div>
    {test && <article className={styles.testDetail}><div className={styles.sectionLabel}>{test.id} · {test.status.toUpperCase()}</div><h3>{test.expected}</h3><p>{test.observed}</p><small className={styles.muted}>Tested in Packet Tracer · {dateTime(test.observedAt)} IST</small>{test.notes && <p className={styles.help}>{test.notes}</p>}
      <h3>Test cases <span>{test.cases.length}</span></h3>{test.cases.slice(page * 15, (page + 1) * 15).map((c, i) => <details key={`${test.id}-${i}`} className={styles.case}><summary>{c.passed ? '✓' : '×'} Case {page * 15 + i + 1}{c.source ? ` · ${c.source}` : ''}{c.destination ? ` → ${c.destination}` : ''}</summary>{c.sourceIp && <p>Command source address: <code>{c.sourceIp}</code></p>}<pre tabIndex={0}>{JSON.stringify(c, null, 2)}</pre></details>)}
      {test.cases.length > 15 && <div className={styles.casePagination}><button disabled={page === 0} onClick={() => setPage(p => p - 1)}>← Previous</button><span>Cases {page * 15 + 1}–{Math.min((page + 1) * 15, test.cases.length)} of {test.cases.length}</span><button disabled={(page + 1) * 15 >= test.cases.length} onClick={() => setPage(p => p + 1)}>Next →</button></div>}
      <h3>Evidence files <span>{test.evidenceRefs.length}</span></h3><div className={styles.evidenceList}>{test.evidenceRefs.slice(0, showAllEvidence ? undefined : 6).map(path => <button key={path} aria-pressed={asset === path} onClick={() => setAsset(asset === path ? null : path)}><span>{path.endsWith('.png') ? '▧' : '≡'}</span>{path.split('/').at(-1)}<span>↗</span></button>)}</div>
      {test.evidenceRefs.length > 6 && <button className={styles.outlineButton} onClick={() => setShowAllEvidence(v => !v)} aria-expanded={showAllEvidence}>{showAllEvidence ? 'Show fewer files' : `Show all ${test.evidenceRefs.length} evidence files`}</button>}
      {asset && test.evidenceRefs.includes(asset) && <EvidenceAsset key={asset} path={asset} snapshot={snapshot}/>}
    </article>}</div>
  </section>;
}
