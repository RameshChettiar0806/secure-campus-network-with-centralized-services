import { useState } from 'react';
import extension from '../../../data/ospf-pat-extension.v3.json';
import sourceCheck from '../data/source-check.json';
import styles from '../app/App.module.css';
import local from './NetworkExtension.module.css';

const steps = [
  { title: 'Keep the campus', detail: 'The original four VLANs, 50 PCs, DHCP relay, internal portal and department ACLs continue to operate.', command: 'show interfaces trunk', output: 'All 55 original campus links retained. Two external links added.' },
  { title: 'Learn the route', detail: 'R1 and R2 form an area-0 OSPF adjacency. The server network is learned dynamically; no static route supplies it.', command: 'show ip ospf neighbor / show ip route ospf', output: extension.observations.ospf },
  { title: 'Resolve and browse', detail: 'Clients ask the existing campus DNS server for external.campus.test, then request the external web page over HTTP.', command: 'nslookup external.campus.test → http://external.campus.test', output: extension.observations.http },
  { title: 'Share the outside address', detail: 'PAT translates client source addresses to 198.51.100.1. Transport ports or ICMP identifiers distinguish the flows.', command: 'show ip nat translations', output: extension.observations.pat },
  { title: 'Keep access controlled', detail: 'Client ACLs permit HTTP and ping to the test server only. WAN-IN permits OSPF and selected replies, and blocks unsolicited traffic.', command: 'show access-lists', output: extension.observations.policy },
  { title: 'Explain failure and recovery', detail: 'Without PAT, replies cannot return to private clients. Without OSPF, R1 loses the external route. The campus server remains reachable during the OSPF outage.', command: 'Controlled simulator checks; both features restored', output: extension.observations.recovery },
];

export default function NetworkExtension() {
  const [step, setStep] = useState(0);
  const current = steps[step];
  return <section className={styles.dataView}>
    <div className={styles.viewIntro}><span className={styles.sectionLabel}>CAMPUS EXTENSION · 2 NOVEMBER 2026</span><h2>Follow a request through OSPF and PAT</h2><p>One additional router, one external web server, two cables. The campus wiring and IP plan stay intact.</p></div>
    <div className={local.status}>{sourceCheck.matchesRecordedSubmission ? 'Current submission matches the verified network capture.' : 'Recorded results. The current submission differs or is unavailable.'} <span>{extension.inventory.networkDevices} devices · {extension.inventory.links} links · 50 PCs</span></div>
    <div className={local.path} aria-label="Extended packet path">
      <div><strong>50 campus PCs</strong><small>VLANs 10 / 20 / 30</small></div><span>→</span>
      <div><strong>R1-CAMPUS</strong><small>PAT outside · 198.51.100.1</small></div><span>↔</span>
      <div><strong>R2-EXTERNAL</strong><small>OSPF area 0 · 198.51.100.2</small></div><span>→</span>
      <div><strong>SRV-EXTERNAL</strong><small>HTTP · 203.0.113.10</small></div>
    </div>
    <p className={styles.help}>The existing switches and central DHCP/DNS/HTTP server sit behind R1. The external branch is a simulated lab network.</p>
    <div className={local.walkthrough}>
      <div className={local.steps} aria-label="Packet walkthrough steps">{steps.map((item, index) => <button key={item.title} onClick={() => setStep(index)} aria-pressed={step === index}><span>{index + 1}</span>{item.title}</button>)}</div>
      <article className={styles.testDetail}><span className={styles.sectionLabel}>STEP {step + 1} OF {steps.length}</span><h3>{current.title}</h3><p>{current.detail}</p><p><code>{current.command}</code></p><pre className={local.output}>{current.output}</pre></article>
    </div>
    <h3 className={local.heading}>Current network verification</h3>
    <div className={styles.tableWrap}><table><thead><tr><th>Check</th><th>Observed result</th></tr></thead><tbody>{extension.checks.map(check => <tr key={check.label}><td>{check.label}</td><td>{check.result}</td></tr>)}</tbody></table></div>
    <p className={styles.help}>The main topology, addressing, access policies and 3,224-ping lab now use the same current 58-device network capture. The controlled failure/recovery demonstration retains its separately dated evidence.</p>
    <details className={local.evidence}><summary>Open recorded extension evidence</summary><ul>{extension.evidence.map(asset => <li key={asset.path}><a href={`/${asset.path}`} target="_blank" rel="noreferrer">{asset.path.split('/').at(-1)}</a></li>)}</ul></details>
  </section>;
}
