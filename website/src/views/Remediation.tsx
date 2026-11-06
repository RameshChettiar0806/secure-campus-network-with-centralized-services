import { lazy, Suspense, useState } from 'react';
import ScenarioLab from '../components/ScenarioLab';
import { deviceLabelsFor, segmentLabel, type Capture } from '../lib/checkpoint';
import styles from './Remediation.module.css';

const Topology = lazy(() => import('../components/CheckpointTopology'));
const files = import.meta.glob<Capture>('../../../data/audit-release.json', { eager: true, import: 'default' });
const capture = Object.values(files)[0];
const labels = deviceLabelsFor(capture?.endpoints ?? []);
const sections = [
  { id: 'overview', label: 'Overview' },
  { id: 'topology', label: 'Topology' },
  { id: 'addressing', label: 'Addressing' },
  { id: 'scenarios', label: 'Packet scenarios' },
  { id: 'verification', label: 'Verification' },
] as const;
type Section = typeof sections[number]['id'];

export interface CheckpointSource {
  matchesRecordedSubmission: boolean;
  verification: {
    checks: { name: string; passed: number; total: number }[];
    outages: { core: string; campusClients: number; externalClients: number; dhcpRenewals: number; isolationPassed: boolean; firstRepliesSeconds: number }[];
  };
}

export default function Remediation({ theme, source, toggleTheme }: {
  theme: 'dark' | 'light'; source: CheckpointSource; toggleTheme: () => void;
}) {
  const [section, setSection] = useState<Section>('overview');
  if (!capture) return <main className="fatal"><h1>Checkpoint unavailable</h1><p>The Version 02 capture could not be loaded.</p></main>;
  return <div className={styles.release}>
    <a className={styles.skip} href="#current-main">Skip to content</a>
    <header className={styles.masthead}>
      <div className={styles.brand}><span aria-hidden="true">⌘</span><strong>campus<span>atlas</span></strong></div>
      <button type="button" className={styles.secondary} onClick={toggleTheme}>{theme === 'dark' ? 'Light mode' : 'Dark mode'}</button>
    </header>
    <nav className={styles.nav} aria-label="Version 02 sections">
      {sections.map(item => <button key={item.id} type="button" aria-current={section === item.id ? 'page' : undefined}
        onClick={() => setSection(item.id)}>{item.label}</button>)}
    </nav>
    <main id="current-main" tabIndex={-1} className={styles.main}>
      {section === 'overview' && <Overview capture={capture} onNavigate={setSection}/>}
      {section === 'topology' && <Suspense fallback={<p>Loading the topology…</p>}><Topology capture={capture} labels={labels} theme={theme}/></Suspense>}
      {section === 'addressing' && <Addressing capture={capture}/>}
      {section === 'scenarios' && <ScenarioLab capture={capture} labels={labels}/>}
      {section === 'verification' && <Verification capture={capture} source={source}/>}
    </main>
    <footer className={styles.footer}>
      <span>Campus Atlas / Version 02</span>
      <span>Packet Tracer Iteration {capture.iteration} · <time dateTime={capture.capturedAt}>{new Date(capture.capturedAt).toLocaleDateString('en-IN', { dateStyle: 'medium', timeZone: 'Asia/Kolkata' })}</time></span>
    </footer>
  </div>;
}

function Overview({ capture, onNavigate }: { capture: Capture; onNavigate: (section: Section) => void }) {
  return <>
    <section className={styles.hero} aria-labelledby="overview-title">
      <div>
        <p className={styles.eyebrow}>Secure campus network / Version 02</p>
        <h1 id="overview-title">The dual-core campus network</h1>
        <p>Explore the verified Packet Tracer design, follow traffic from a student workstation to the external server, and compare the recorded result in the reverse direction.</p>
        <div className={styles.actions}>
          <button type="button" className={styles.primary} onClick={() => onNavigate('scenarios')}>Open packet scenarios <span aria-hidden="true">↗</span></button>
          <button type="button" className={styles.secondary} onClick={() => onNavigate('topology')}>Explore topology</button>
        </div>
      </div>
      <div className={styles.route} aria-label="Core architecture overview">
        <p className={styles.eyebrow}>Campus forwarding</p>
        <div className={styles.routePoint}>Campus Edge Router</div>
        <div className={styles.routeBranches}><div>Primary Core Switch</div><div>Standby Core Switch</div></div>
        <div className={styles.routePoint}>Department and services access</div>
        <small>HSRP gateways · Independent routed uplinks</small>
      </div>
    </section>
    <dl className={styles.metrics}>
      <div><dt>Network devices</dt><dd>{capture.nodes.length}</dd></div>
      <div><dt>Physical links</dt><dd>{capture.links.length}</dd></div>
      <div><dt>Campus VLANs</dt><dd>{capture.networks.length}</dd></div>
      <div><dt>Endpoint tests</dt><dd>{capture.ping.total.toLocaleString('en-IN')}</dd></div>
    </dl>
    <section className={styles.overviewDetails} aria-label="Network design summary">
      <div><h2>Gateways that can recover</h2><p>The core switches share a virtual default gateway on each VLAN. The verification records show how clients recovered after either core was powered off.</p></div>
      <div><h2>Central services, scoped access</h2><p>The campus server supplies DHCP, DNS and the campus portal. Campus ACLs control routed traffic between groups. The edge router uses PAT and authenticated OSPF for external access.</p></div>
    </section>
  </>;
}

function Addressing({ capture }: { capture: Capture }) {
  const [segment, setSegment] = useState('');
  const endpoints = capture.endpoints.filter(endpoint => !segment || String(endpoint.segment) === segment);
  return <section aria-labelledby="addressing-title">
    <div className={styles.sectionIntro}>
      <p className={styles.eyebrow}>Address plan</p>
      <h2 id="addressing-title">Gateways and endpoints</h2>
      <p>The five campus VLANs use HSRP virtual gateways. The endpoint table shows the addresses recorded during verification.</p>
    </div>
    <div className={styles.networks}>
      {capture.networks.map(network => <article key={network.vlan}>
        <span className={styles.eyebrow}>VLAN {network.vlan}</span>
        <h3>{network.name}</h3>
        <code>{network.subnet}</code>
        <p>Gateway <code>{network.gateway}</code></p>
      </article>)}
    </div>
    <div className={styles.panelHeading}>
      <h3>{endpoints.length} endpoint addresses</h3>
      <label>Segment<select value={segment} onChange={event => setSegment(event.target.value)}>
        <option value="">All segments</option>
        {capture.networks.map(network => <option key={network.vlan} value={network.vlan}>{network.name}</option>)}
        <option value="External">External network</option>
      </select></label>
    </div>
    <div className={styles.tableWrap}><table>
      <thead><tr><th scope="col">Device</th><th scope="col">IPv4 address</th><th scope="col">Segment</th><th scope="col">Assignment</th></tr></thead>
      <tbody>{endpoints.sort((a, b) => (labels.get(a.name) ?? a.name).localeCompare(labels.get(b.name) ?? b.name)).map(endpoint => <tr key={endpoint.name}>
        <th scope="row">{labels.get(endpoint.name) ?? endpoint.name}</th><td><code>{endpoint.ip}</code></td>
        <td>{capture.networks.find(network => network.vlan === endpoint.segment)?.name ?? segmentLabel(endpoint.segment)}</td>
        <td>{endpoint.dhcp ? 'DHCP' : 'Static'}</td>
      </tr>)}</tbody>
    </table></div>
  </section>;
}

function Verification({ capture, source }: { capture: Capture; source: CheckpointSource }) {
  return <section aria-labelledby="verification-title">
    <div className={styles.sectionIntro}>
      <p className={styles.eyebrow}>Recorded evidence</p>
      <h2 id="verification-title">What the capture verified</h2>
      <p>{capture.ping.matched.toLocaleString('en-IN')} of {capture.ping.total.toLocaleString('en-IN')} directed endpoint ping tests matched policy.</p>
    </div>
    <div className={styles.overviewDetails}>
      <section>
        <h3>Regression checks</h3>
        <div className={styles.tableWrap}><table>
          <thead><tr><th scope="col">Check</th><th scope="col">Passed</th></tr></thead>
          <tbody>{source.verification.checks.map(check => <tr key={check.name}><th scope="row">{check.name}</th><td>{check.passed} / {check.total}</td></tr>)}</tbody>
        </table></div>
      </section>
      <section>
        <h3>Core outage tests</h3>
        {source.verification.outages.map(run => <article className={styles.outage} key={run.core}>
          <h4>{labels.get(run.core)} powered off</h4>
          <p>First successful probe batch after <strong>{run.firstRepliesSeconds} s</strong>.</p>
          <p>{run.campusClients} campus clients and {run.externalClients} external-access clients reached their destinations after recovery. {run.dhcpRenewals} DHCP renewals passed. The policy denial {run.isolationPassed ? 'held' : 'failed'}.</p>
        </article>)}
      </section>
    </div>
    <div className={styles.identity}>
      <span>Packet Tracer Iteration {capture.iteration} · {source.matchesRecordedSubmission ? 'Local file matched verified capture' : 'Verified release capture'}</span>
      <code title="SHA-256 of the saved Packet Tracer file">{capture.submissionSha256}</code>
    </div>
  </section>;
}
