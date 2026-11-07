import { lazy, Suspense } from 'react';
import { flowFor, type Capture, type Probe } from '../lib/checkpoint';
import styles from '../views/Remediation.module.css';

const ScenarioPacketFlow = lazy(() => import('./ScenarioPacketFlow'));

export default function CheckpointPingResult({ capture, labels, result, theme, autoPlay = false, replayId = 0 }: {
  capture: Capture; labels: ReadonlyMap<string, string>; result: Probe;
  theme: 'dark' | 'light'; autoPlay?: boolean; replayId?: number;
}) {
  const from = capture.endpoints.find(endpoint => endpoint.name === result.source)!;
  const to = capture.endpoints.find(endpoint => endpoint.name === result.target)!;
  const flow = flowFor(capture, from, to, result.expected);
  const outcome = result.observed === 'allow' ? 'Reachable' : result.observed === 'deny' ? 'Blocked' : 'Incomplete';
  return <>
    <div className={styles.result} aria-live="polite">
      <div><span className={styles.muted}>Observed outcome</span><strong className={result.observed === 'allow' ? styles.allow : styles.block}>{outcome}</strong></div>
      <div><span className={styles.muted}>Echo replies</span><strong>{result.received} / {result.sent}</strong></div>
      <div><span className={styles.muted}>Expected policy</span><strong>{result.expected === 'allow' ? 'Allow' : 'Deny'}</strong></div>
    </div>
    <p className={styles.command}><code>{from.ip}</code><span aria-hidden="true">→</span><code>ping {to.ip}</code></p>
    <Suspense fallback={<p className={styles.muted}>Loading the packet route map…</p>}>
      <ScenarioPacketFlow key={`${result.source}:${result.target}:${replayId}`} capture={capture} labels={labels} flow={flow}
        theme={theme} denied={result.expected === 'deny'} received={result.received} autoPlay={autoPlay}/>
    </Suspense>
  </>;
}
