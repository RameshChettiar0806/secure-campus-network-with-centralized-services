import { useRef, useState } from 'react';
import CheckpointPingResult from '../components/CheckpointPingResult';
import { resolveCheckpointPing, type Capture, type EndpointPair, type Probe } from '../lib/checkpoint';
import styles from './Remediation.module.css';

export default function CheckpointPingLab({ capture, labels, theme, initial }: {
  capture: Capture; labels: ReadonlyMap<string, string>; theme: 'dark' | 'light'; initial: EndpointPair;
}) {
  const endpoints = [...capture.endpoints].sort((a, b) => labels.get(a.name)!.localeCompare(labels.get(b.name)!));
  const ip = (id: string) => endpoints.find(endpoint => endpoint.name === id)!.ip;
  const [source, setSource] = useState(initial.source);
  const [target, setTarget] = useState(initial.target);
  const [command, setCommand] = useState(`ping ${ip(initial.target)}`);
  const [run, setRun] = useState<{ record: Probe; number: number } | null>(null);
  const [error, setError] = useState('');
  const sequence = useRef(0);
  const resultTitle = useRef<HTMLHeadingElement>(null);
  const selected = capture.ping.rows.find(row => row.source === source && row.target === target)!;
  const shown = run?.record ?? selected;
  const choose = (nextSource: string, nextTarget: string) => {
    setSource(nextSource); setTarget(nextTarget); setCommand(`ping ${ip(nextTarget)}`);
    setRun(null); setError('');
  };
  const submit = () => {
    const resolved = resolveCheckpointPing(capture, source, command);
    if (!resolved.record) { setRun(null); setError(resolved.error!); return; }
    setTarget(resolved.record.target);
    setCommand(`ping ${ip(resolved.record.target)}`);
    setError('');
    setRun({ record: resolved.record, number: ++sequence.current });
    if (window.matchMedia('(max-width: 720px)').matches) {
      resultTitle.current?.focus({ preventScroll: true });
      resultTitle.current?.scrollIntoView({ block: 'start' });
    }
  };
  const examples = [
    { label: 'Student → External', source: 'PC0', target: 'SRV-EXTERNAL' },
    { label: 'Student → Campus server', source: 'PC0', target: 'SRV-CAMPUS' },
    { label: 'External → Student', source: 'SRV-EXTERNAL', target: 'PC0' },
    { label: 'Management → Student', source: 'PC8-MGMT', target: 'PC0' },
  ];
  return <section aria-labelledby="ping-lab-title">
    <div className={styles.sectionIntro}>
      <p className={styles.eyebrow}>Interactive ping lab</p>
      <h2 id="ping-lab-title">Recorded ping lab</h2>
      <p>Choose any two of the 52 captured endpoints or enter a destination IP. Replay the recorded result and follow an illustrated request, reply, or forwarding stop.</p>
    </div>
    <div className={styles.pingWorkspace}>
      <section className={styles.scenarios} aria-labelledby="ping-console-title">
        <h3 id="ping-console-title">Ping console</h3>
        <div className={styles.consoleFields}>
          <label>Source device<select value={source} onChange={event => {
            const next = event.target.value;
            choose(next, next === target ? endpoints.find(endpoint => endpoint.name !== next)!.name : target);
          }}>{endpoints.map(endpoint => <option key={endpoint.name} value={endpoint.name}>{labels.get(endpoint.name)} · {endpoint.ip}</option>)}</select></label>
          <label>Destination device<select value={target} onChange={event => choose(source, event.target.value)}>
            {endpoints.filter(endpoint => endpoint.name !== source).map(endpoint => <option key={endpoint.name} value={endpoint.name}>{labels.get(endpoint.name)} · {endpoint.ip}</option>)}
          </select></label>
        </div>
        <form onSubmit={event => { event.preventDefault(); submit(); }} className={styles.pingConsole}>
          <label htmlFor="checkpoint-ping-command">Ping command</label>
          <div><span aria-hidden="true">C:\&gt;</span><input id="checkpoint-ping-command" value={command}
            spellCheck={false} autoComplete="off" onChange={event => { setCommand(event.target.value); setRun(null); setError(''); }}/></div>
          <button type="submit" className={styles.primary}>Run recorded ping</button>
        </form>
        {error && <p role="alert" className={styles.block}>{error}</p>}
        <div className={styles.presets} role="group" aria-label="Ping examples">
          <h4>Try an example</h4>
          {examples.map(example => <button key={example.label} className={styles.secondary} type="button" onClick={() => choose(example.source, example.target)}>{example.label}</button>)}
        </div>
        <p className={styles.muted}>Each result comes from the verified Packet Tracer capture. The visualization explains one echo exchange from that result.</p>
      </section>
      <article className={styles.scenarioDetail} aria-labelledby="ping-result-title">
        <div className={styles.scenarioTitle}><h3 id="ping-result-title" tabIndex={-1} ref={resultTitle}>{labels.get(shown.source)} → {labels.get(shown.target)}</h3></div>
        <CheckpointPingResult capture={capture} labels={labels} result={shown} theme={theme}
          autoPlay={!!run} replayId={run?.number}/>
      </article>
    </div>
  </section>;
}
