import { useMemo } from 'react';
import { buildScenarios, groups, type Capture, type EndpointPair } from '../lib/checkpoint';
import styles from './Remediation.module.css';

const services = [
  ['DHCP', 'Administration, Faculty and Students', 'Campus Services Server through the core relays', 'UDP 67/68'],
  ['Campus DNS and HTTP', 'Departmental PCs and Management Workstation', 'Campus Services Server', 'DNS 53 · HTTP 80'],
  ['External HTTP and ICMP', 'Administration, Faculty and Students', 'External Server through the edge and PAT', 'HTTP 80 · ICMP echo'],
  ['SSH management', 'Management Workstation', 'Seven campus IOS devices', 'TCP 22'],
  ['Monitoring', 'Managed campus devices', 'Campus Services Server', 'NTP 123 · Syslog 514'],
];

export default function CheckpointPolicy({ capture, onPing }: { capture: Capture; onPing: (pair: EndpointPair) => void }) {
  const scenarios = useMemo(() => buildScenarios(capture), [capture]);
  return <section aria-labelledby="access-policy-title">
    <div className={styles.sectionIntro}>
      <p className={styles.eyebrow}>Access policy</p>
      <h2 id="access-policy-title">Which direction is permitted?</h2>
      <p>The matrix shows recorded ICMP echo initiation between endpoint groups. Select a populated cell to inspect an example in Ping Lab.</p>
    </div>
    <div className={`${styles.tableWrap} ${styles.policyMatrix}`}>
      <table>
        <caption>Source groups appear down the left. Destination groups appear across the top.</caption>
        <thead><tr><th scope="col">Source → Destination</th>{groups.map(group => <th scope="col" key={group.segment}>{group.name}</th>)}</tr></thead>
        <tbody>{groups.map(source => <tr key={source.segment}>
          <th scope="row">{source.name}</th>
          {groups.map(target => {
            const scenario = scenarios.find(item => item.from === source.segment && item.to === target.segment);
            if (!scenario) return <td key={target.segment}><span className={styles.muted}>—<small>No distinct pair</small></span></td>;
            const allowed = scenario.rows.every(row => row.observed === 'allow');
            const denied = scenario.rows.every(row => row.observed === 'deny');
            const verdict = allowed ? 'Allow' : denied ? 'Deny' : 'Mixed';
            return <td key={target.segment}>
              <button type="button" className={`${styles.policyCell} ${allowed ? styles.allow : styles.block}`}
                aria-label={`${source.name} to ${target.name}: ${verdict}. Open Ping Lab`}
                onClick={() => onPing(scenario.rows[0])}>
                <strong>{verdict}</strong><small>{scenario.rows.length} recorded {scenario.rows.length === 1 ? 'pair' : 'pairs'}</small>
              </button>
            </td>;
          })}
        </tr>)}</tbody>
      </table>
    </div>
    <div className={styles.guideCards}>
      <article><h3>Direction matters</h3><p>Administration can initiate diagnostics toward Faculty and Students. Those groups can return the echo replies, while new diagnostics in the reverse direction meet their own ingress policy.</p></article>
      <article><h3>Same-VLAN traffic</h3><p>Local endpoint traffic is switched within its VLAN. The inter-VLAN ACLs apply when traffic enters the routed gateway.</p></article>
      <article><h3>External initiation</h3><p>The External Router has no route to the private campus endpoints. Its denied matrix entries describe that routing boundary. Departmental requests can return through the edge’s PAT translations.</p></article>
    </div>
    <h3>Service permissions</h3>
    <p className={styles.muted}>These permissions summarize the saved configuration. The matrix above measures ICMP. The Verification tab records separate DNS, HTTP and SSH checks.</p>
    <div className={styles.tableWrap}><table>
      <thead><tr><th scope="col">Service</th><th scope="col">Source</th><th scope="col">Destination</th><th scope="col">Protocol</th></tr></thead>
      <tbody>{services.map(([service, from, to, protocol]) => <tr key={service}><th scope="row">{service}</th><td>{from}</td><td>{to}</td><td>{protocol}</td></tr>)}</tbody>
    </table></div>
    <p className={styles.muted}>Both cores retain the departmental ACLs. The edge retains its WAN ACL, and device VTY rules restrict SSH. The verified design uses explicit request and reply rules for these flows.</p>
  </section>;
}
