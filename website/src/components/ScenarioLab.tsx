import { useMemo, useState } from 'react';
import { buildScenarios, flowFor, groups, type Capture, type Scenario } from '../lib/checkpoint';
import styles from '../views/Remediation.module.css';

const scenarioId = (number: number) => String(number).padStart(2, '0');

export default function ScenarioLab({ capture, labels }: { capture: Capture; labels: ReadonlyMap<string, string> }) {
  const scenarios = useMemo(() => buildScenarios(capture), [capture]);
  const [active, setActive] = useState(1);
  const [sourceFilter, setSourceFilter] = useState('');
  const [targetFilter, setTargetFilter] = useState('');
  const current = scenarios.find(scenario => scenario.number === active);
  const filtered = scenarios.filter(scenario =>
    (!sourceFilter || String(scenario.from) === sourceFilter) && (!targetFilter || String(scenario.to) === targetFilter));
  const selected = filtered.find(scenario => scenario === current) ?? filtered[0];
  const reverse = selected && scenarios.find(scenario => scenario.number !== selected.number && scenario.from === selected.to && scenario.to === selected.from);
  return <section aria-labelledby="scenario-heading">
    <div className={styles.sectionIntro}>
      <p className={styles.eyebrow}>Connectivity lab</p>
      <h2 id="scenario-heading">Follow a packet</h2>
      <p>Explore {scenarios.length} directional scenarios covering every distinct source and destination in the {capture.ping.total.toLocaleString('en-IN')} recorded endpoint ping tests.</p>
    </div>
    <div className={styles.lab}>
      <aside className={styles.scenarios} aria-label="Scenario directory">
        <div className={styles.panelHeading}><h3>Scenarios</h3><span>{filtered.length} of {scenarios.length}</span></div>
        <div className={styles.fieldGrid}>
          <label>Source group<select value={sourceFilter} onChange={event => setSourceFilter(event.target.value)}>
            <option value="">All sources</option>
            {groups.map(group => <option key={group.segment} value={group.segment}>{group.name}</option>)}
          </select></label>
          <label>Destination group<select value={targetFilter} onChange={event => setTargetFilter(event.target.value)}>
            <option value="">All destinations</option>
            {groups.map(group => <option key={group.segment} value={group.segment}>{group.name}</option>)}
          </select></label>
        </div>
        <div className={styles.scenarioList}>
          {filtered.map(scenario => <button key={scenario.number} type="button"
            aria-pressed={scenario === selected} onClick={() => setActive(scenario.number)}>
            <code>{scenarioId(scenario.number)}</code>
            <span>{scenario.name}<small>{scenario.rows.length} {scenario.rows.length === 1 ? 'pair' : 'pairs'}</small></span>
          </button>)}
        </div>
        {!filtered.length && <p className={styles.muted}>This combination has no distinct endpoint pair.</p>}
      </aside>
      {selected && <ScenarioDetail key={selected.number} scenario={selected} capture={capture} labels={labels}
        reverse={reverse ? () => { setSourceFilter(''); setTargetFilter(''); setActive(reverse.number); } : undefined}/>}
    </div>
  </section>;
}

function ScenarioDetail({ scenario, capture, labels, reverse }: {
  scenario: Scenario; capture: Capture; labels: ReadonlyMap<string, string>; reverse?: () => void;
}) {
  const name = (id: string) => labels.get(id) ?? id;
  const sorted = (ids: string[]) => [...new Set(ids)].sort((a, b) => name(a).localeCompare(name(b), 'en', { numeric: true }));
  const sources = sorted(scenario.rows.map(row => row.source));
  const [source, setSource] = useState(sources[0]);
  const targets = sorted(scenario.rows.filter(row => row.source === source).map(row => row.target));
  const [target, setTarget] = useState(targets[0]);
  const activeTarget = targets.includes(target) ? target : targets[0];
  const result = scenario.rows.find(row => row.source === source && row.target === activeTarget)!;
  const from = capture.endpoints.find(endpoint => endpoint.name === source)!;
  const to = capture.endpoints.find(endpoint => endpoint.name === activeTarget)!;
  const flow = flowFor(capture, from, to, result.expected);
  const matchCount = scenario.rows.filter(row => row.expected === row.observed).length;
  const allowed = result.observed === 'allow';
  const outcome = allowed ? 'Reachable' : result.observed === 'deny' ? 'Blocked' : 'Incomplete';
  return <article className={styles.scenarioDetail} aria-labelledby="scenario-title">
    <div className={styles.scenarioTitle}>
      <div>
        <p className={styles.eyebrow}>Scenario {scenarioId(scenario.number)} · ICMP echo</p>
        <h3 id="scenario-title">{scenario.name}</h3>
      </div>
      {reverse && <button type="button" className={styles.secondary} onClick={reverse}>Reverse direction</button>}
    </div>
    <p className={styles.muted}>{matchCount} of {scenario.rows.length} recorded {scenario.rows.length === 1 ? 'pair matched' : 'pairs matched'} the expected policy.</p>
    <div className={styles.fieldGrid}>
      <label>Source device<select value={source} onChange={event => setSource(event.target.value)}>
        {sources.map(id => <option key={id} value={id}>{name(id)}</option>)}
      </select></label>
      <label>Destination device<select value={activeTarget} onChange={event => setTarget(event.target.value)}>
        {targets.map(id => <option key={id} value={id}>{name(id)}</option>)}
      </select></label>
    </div>
    <div className={styles.result} aria-live="polite">
      <div><span className={styles.muted}>Observed outcome</span><strong className={allowed ? styles.allow : styles.block}>{outcome}</strong></div>
      <div><span className={styles.muted}>Echo replies</span><strong>{result.received} / {result.sent}</strong></div>
      <div><span className={styles.muted}>Expected policy</span><strong>{result.expected === 'allow' ? 'Allow' : 'Deny'}</strong></div>
    </div>
    <p className={styles.command}><code>{from.ip}</code><span aria-hidden="true">→</span><code>ping {to.ip}</code></p>
    <h4>Illustrated request path</h4>
    <p className={styles.muted}>Derived from the normal topology and policy for this direction. The recorded test measures end-to-end ICMP replies.</p>
    <ol className={styles.flow} aria-label="Illustrated request path">
      {flow.path.map((id, index) => id && <li key={index}>{name(id)}</li>)}
    </ol>
    <p>{flow.explanation}</p>
    <details className={styles.details}>
      <summary>View all {scenario.rows.length} recorded {scenario.rows.length === 1 ? 'pair' : 'pairs'}</summary>
      <div className={styles.tableWrap}><table>
        <thead><tr><th scope="col">Source</th><th scope="col">Destination</th><th scope="col">Expected</th><th scope="col">Observed</th><th scope="col">Replies</th></tr></thead>
        <tbody>{scenario.rows.map(row => <tr key={`${row.source}:${row.target}`}>
          <td>{name(row.source)}</td><td>{name(row.target)}</td><td>{row.expected}</td><td>{row.observed}</td><td>{row.received} / {row.sent}</td>
        </tr>)}</tbody>
      </table></div>
    </details>
  </article>;
}
