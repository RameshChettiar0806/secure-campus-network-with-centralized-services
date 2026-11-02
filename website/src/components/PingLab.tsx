import { lazy, Suspense, useEffect, useMemo, useRef, useState } from 'react';
import type { DeviceId, NetworkSnapshot } from '../models/network';
import HopNotes from './HopNotes';
import PingWalkthrough from './PingWalkthrough';
import type { PingPair } from './PolicyExplorer';
import pingIndex from '../data/ping-index.json';
import { decodePingSource, pingSteps, resolvePingCommand, type PacketPresentation, type PingRecord } from '../lib/ping';
import { assetUrl, primaryAddress } from '../lib/network';
import { pingTopology } from '../lib/pingTopology';
import pane from './PingLab.module.css';
import styles from '../app/App.module.css';
const TopologyCanvas = lazy(() => import('./TopologyCanvas'));
const sourceCache = new Map<string, PingRecord[]>();

export default function PingLab({ snapshot, theme, initial }: { initial: PingPair; snapshot: NetworkSnapshot; theme: 'dark' | 'light' }) {
  const mapTitle = useRef<HTMLHeadingElement>(null);
  const [sourceId, setSourceId] = useState<DeviceId>(initial.source);
  const [targetId, setTargetId] = useState<DeviceId>(initial.target);
  const [command, setCommand] = useState(`ping ${primaryAddress(snapshot.devices.find(d => d.id === initial.target)!)}`);
  const [records, setRecords] = useState<PingRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [mapView, setMapView] = useState<'route' | 'campus'>('route');
  const [loadError, setLoadError] = useState('');
  const [reload, setReload] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    const key = `${snapshot.submissionSha256}:${sourceId}`;
    setLoading(true); setLoadError(''); setRecords([]);
    const cached = sourceCache.get(key);
    if (cached) { setRecords(cached); setLoading(false); return () => controller.abort(); }
    const path = pingIndex.sources[sourceId as keyof typeof pingIndex.sources];
    fetch(assetUrl(path), { signal: controller.signal }).then(response => {
      if (!response.ok) throw new Error(`Ping records could not be loaded (${response.status}).`);
      return response.json() as Promise<unknown>;
    }).then(value => {
      const rows = decodePingSource(value, sourceId, snapshot.submissionSha256);
      if (rows.length !== pingIndex.perSource) throw new Error('Incomplete source ping coverage.');
      if (controller.signal.aborted) return;
      sourceCache.set(key, rows); setRecords(rows); setLoading(false);
    }).catch((error: unknown) => {
      if (controller.signal.aborted) return;
      setLoadError(error instanceof Error ? error.message : 'Could not load ping records.'); setLoading(false);
    });
    return () => controller.abort();
  }, [sourceId, snapshot.submissionSha256, reload]);
  const [active, setActive] = useState<PingRecord | null>(null);
  const [step, setStep] = useState(-1);
  const [playing, setPlaying] = useState(false);
  const [error, setError] = useState('');
  const [inspected, setInspected] = useState<string>(initial.source);
  const [inspectedLink, setInspectedLink] = useState<string | null>(null);
  const targetRecords = records.filter(r => r.sourceDeviceId === sourceId && r.destinationDeviceId === targetId);
  const commandIp = /^\s*ping\s+(\S+)\s*$/i.exec(command)?.[1];
  const selectedRecord = records.find(r => r.sourceDeviceId === sourceId && r.destinationIp === commandIp);
  const shown = active ?? selectedRecord;
  const steps = useMemo(() => shown ? pingSteps(snapshot, shown) : [], [snapshot, shown]);
  const focused = useMemo(() => shown ? pingTopology(snapshot, shown.sourceDeviceId, shown.destinationDeviceId, steps) : null, [snapshot, shown, steps]);
  const complete = !!active && step === steps.length - 1;
  const currentStep = steps[step];
  const packet: PacketPresentation | undefined = shown ? { steps, step, addresses: { ...shown.addressContext, [shown.destinationDeviceId]: shown.destinationIp }, destinationDeviceId: shown.destinationDeviceId, expected: shown.expected } : undefined;
  const endpoints = snapshot.devices.filter(d => d.model === 'PC-PT' || d.model === 'Server-PT');
  const targets = snapshot.devices.filter(d => d.id !== sourceId);
  const label = (id: string) => snapshot.devices.find(d => d.id === id)?.label ?? id;
  const clear = () => { setPlaying(false); setActive(null); setStep(-1); setError(''); setInspectedLink(null); };
  const choose = (source: DeviceId, target: DeviceId) => {
    if (source !== sourceId) setLoading(true);
    clear(); setSourceId(source); setTargetId(target); setInspected(source);
    const sourceDevice = snapshot.devices.find(d => d.id === source)!;
    const gateway = snapshot.vlans.find(v => v.id === sourceDevice.vlanId)?.gateway;
    const preferred = target === 'r1' ? gateway ?? snapshot.routing?.patOutsideAddress : target === 'r2' ? sourceDevice.segment === 'external' ? '203.0.113.1' : '198.51.100.2' : primaryAddress(snapshot.devices.find(d => d.id === target)!);
    const matches = records.filter(r => r.sourceDeviceId === source && r.destinationDeviceId === target);
    const record = matches.find(r => r.destinationIp === preferred) ?? matches[0];
    setCommand(`ping ${record?.destinationIp ?? preferred}`);
  };
  const run = () => {
    const result = resolvePingCommand(records, sourceId, command);
    if (!result.record) { clear(); setError(result.error!); return; }
    if (window.matchMedia('(max-width: 720px)').matches) {
      mapTitle.current?.focus({ preventScroll: true });
      mapTitle.current?.scrollIntoView({ block: 'start' });
    }
    setError(''); setActive(result.record); setTargetId(result.record.destinationDeviceId); setStep(0); setPlaying(true); setInspectedLink(null);
  };
  useEffect(() => {
    if (!playing || !active || complete) return;
    const timer = setTimeout(() => setStep(i => Math.min(i + 1, steps.length - 1)), 1250);
    return () => clearTimeout(timer);
  }, [playing, active, complete, step, steps.length]);
  const jump = (index: number) => { if (!shown) return; setActive(shown); setTargetId(shown.destinationDeviceId); setStep(index); setPlaying(false); setError(''); };
  const link = snapshot.links.find(l => l.id === inspectedLink);
  const device = snapshot.devices.find(d => d.id === inspected);

  return <section className={styles.pingLab}>
    <div className={styles.pingIntro}><div><div className={styles.sectionLabel}>INTERACTIVE PING LAB</div><h2>Can the sender get a reply?</h2><p>Ping sends an ICMP echo request to an IP address. A reply shows the destination was reachable in both directions. Run a command in the console and follow its request and reply on the map.</p></div><span className={styles.demoLabel}>{pingIndex.cases.toLocaleString('en-IN')} recorded pings · {pingIndex.perSource} per source</span></div>
    <div className={pane.workspace}>
      <section className={pane.column} aria-labelledby="ping-console-title">
        <header className={pane.heading}><div><span className={styles.sectionLabel}>01 / COMMAND</span><h3 id="ping-console-title">Ping console</h3></div></header>
        <div className={pane.fields}><label>Source device<select value={sourceId} onChange={e => choose(e.target.value as DeviceId, targetId === e.target.value ? 'r1' : targetId)}>{[10,20,30,40].map(v => <optgroup key={v} label={snapshot.vlans.find(x => x.id === v)?.name}>{endpoints.filter(d => d.vlanId === v).map(d => <option key={d.id} value={d.id}>{d.label} · {primaryAddress(d)}</option>)}</optgroup>)}<optgroup label="EXTERNAL LAN">{endpoints.filter(d => d.segment === 'external').map(d => <option key={d.id} value={d.id}>{d.label} · {primaryAddress(d)}</option>)}</optgroup></select></label><label>Destination<select value={targetId} onChange={e => choose(sourceId, e.target.value as DeviceId)}>{targets.map(d => <option key={d.id} value={d.id}>{d.label}</option>)}</select></label></div>
        {['r1','r2'].includes(targetId) && targetRecords.length > 1 && <label className={pane.routerField}>Router interface<select aria-label="Router interface" value={selectedRecord?.destinationIp ?? ''} onChange={e => { clear(); setCommand(`ping ${e.target.value}`); }}>{targetRecords.map(r => <option key={r.destinationIp} value={r.destinationIp}>{r.destinationIp} · {snapshot.devices.find(d => d.id === targetId)?.interfaces.find(p => p.ipv4 === r.destinationIp)?.name}</option>)}</select></label>}
        <form onSubmit={e => { e.preventDefault(); run(); }}><div className={styles.terminalBar}><span className={styles.tinyDot}/>{label(sourceId)} · COMMAND PROMPT</div><label className={styles.commandLine}><span>C:\&gt;</span><input aria-label="Ping command" spellCheck={false} autoComplete="off" value={command} onChange={e => { clear(); setCommand(e.target.value); const match = resolvePingCommand(records, sourceId, e.target.value).record; if (match) setTargetId(match.destinationDeviceId); }}/></label><button className={styles.runPing} type="submit" disabled={loading || !!loadError}>▶ {loading ? 'Loading commands…' : active ? 'Replay ping' : 'Run recorded ping'}</button></form>
        <div className={pane.presets}><span>Try a scenario</span><button onClick={() => choose('pc0', 'server0')}>Campus portal</button><button onClick={() => choose('pc0', 'server1')}>External via PAT</button><button onClick={() => choose('server1', 'r1')}>Unsolicited WAN</button><button onClick={() => choose('server1', 'pc0')}>External → private</button><button onClick={() => choose('pc0', 'pc8')}>Blocked access</button><button onClick={() => choose('pc0', 'pc1')}>Within Students</button><button onClick={() => choose('pc8', 'pc39')}>Admin → Faculty</button><button onClick={() => choose('pc49', 'sw4')}>Ping a switch</button><button onClick={() => choose('pc24', 'r1')}>Router gateways</button></div>
        <p className={styles.pingDisclosure}>Results come from recorded Packet Tracer commands. The topology replays one echo exchange from the selected command.</p>
      {loading && <p role="status" className={styles.help}>Loading {label(sourceId)}’s {pingIndex.perSource} recorded commands…</p>}
      {loadError && <p role="alert" className={styles.pingError}>{loadError} <button onClick={() => setReload(v => v + 1)}>Retry loading</button></p>}
      {error && <p role="alert" className={styles.pingError}>{error}</p>}
      {!active && !error && !loading && !loadError && <div className={styles.pingReady}><span className={styles.sectionLabel}>{selectedRecord ? 'READY TO DEMONSTRATE' : 'ADDITIONAL TEST NEEDED'}</span><h3>{label(sourceId)} → {label(targetId)}</h3><p>{selectedRecord ? 'Run the command to see the request, routing decision and reply path.' : 'Test this pair in Packet Tracer before adding a result here. The existing examples remain available above.'}</p></div>}
        {active && <><div id="ping-results" tabIndex={-1} className={styles.pingCounts}><div><span>Sent</span><strong>{complete ? active.sent : '—'}</strong></div><div><span>Received</span><strong>{complete ? active.received : '—'}</strong></div><div><span>Loss</span><strong>{complete ? `${Math.round((active.sent - active.received) / active.sent * 100)}%` : '—'}</strong></div></div>
      {complete && <><pre className={styles.pingOutput} tabIndex={0} aria-label="Packet Tracer ping output">{active.output}</pre>{Object.keys(active.counterDelta).length > 0 && <details className={styles.case}><summary>{active.counterScope === 'capture-batch' ? 'Batch ACL observations' : 'ACL rules matched'}</summary>{active.counterScope === 'capture-batch' && <p>Counter changes include other pings in the same capture batch. Packet counts above belong to this command.</p>}{Object.entries(active.counterDelta).map(([rule, count]) => <p className={styles.counterRule} key={rule}><code>{rule}</code><span>+{count} matches</span></p>)}</details>}</>}
</>}
      </section>
      <section className={pane.column} aria-labelledby="ping-map-title">
        <header className={pane.heading}><div><span className={styles.sectionLabel}>02 / TOPOLOGY</span><h3 id="ping-map-title" tabIndex={-1} ref={mapTitle}>Follow the packet</h3></div>
          <div className={pane.switcher} role="group" aria-label="Topology view">{(['route','campus'] as const).map(v => <button key={v} aria-pressed={v === mapView} onClick={() => setMapView(v)}>{v === 'route' ? 'Ping route' : 'Full campus'}</button>)}</div>
        </header>
        <div className={pane.status} data-phase={currentStep?.phase} role="status">
          <strong>{active && currentStep ? (currentStep.phase === 'blocked' ? currentStep.notes.some(n => n.concept === 'No route') ? 'No private route' : 'Blocked by ACL' : currentStep.phase === 'reply' ? complete ? 'Reply received' : 'Echo reply' : 'Echo request') + ' · ' + label(currentStep.deviceId) : shown ? label(sourceId) + ' → ' + label(shown.destinationDeviceId) : 'Waiting for a recorded route'}</strong>
          <span>{currentStep ? 'Hop ' + (step + 1) + ' / ' + steps.length : shown ? 'Ready to replay' : 'No active ping'}</span>
        </div>
        <div className={pane.map}>{(mapView === 'campus' || focused) ? <Suspense fallback={<p className={pane.placeholder}>Loading topology…</p>}><TopologyCanvas key={mapView === 'campus' ? 'campus' : shown!.id} snapshot={mapView === 'campus' ? snapshot : focused!} pingView={mapView} vlan={null} selected={inspected} select={id => { setInspected(id); setInspectedLink(null); }} selectLink={setInspectedLink} theme={theme} packet={packet} moving={playing && !complete}/></Suspense> : <p className={pane.placeholder}>{loading ? 'Loading the selected route…' : 'Choose a recorded destination to display its route.'}</p>}</div>
        <HopNotes notes={currentStep?.notes ?? [
          { concept: 'Echo request', detail: 'Run a ping to trace the ICMP packet from the sender.' },
          { concept: 'Outcome', detail: 'Follow the echo reply back, or see where the router drops the request.' },
        ]}/>
        {active && <div className={styles.pingPlayback}><button onClick={() => { if (complete) { setStep(0); setPlaying(true); } else setPlaying(v => !v); }}>{complete ? '↻ Replay' : playing ? 'Ⅱ Pause' : '▶ Resume'}</button><button disabled={step === 0} onClick={() => jump(step - 1)}>← Previous step</button><button disabled={complete} onClick={() => { setPlaying(false); setStep(i => Math.min(i + 1, steps.length - 1)); }}>Next hop →</button><button onClick={clear}>Reset</button></div>}
        {complete && <a className={pane.mobileResult} href="#ping-results">View command output ↑</a>}
        <div className={styles.pingInspection}><span className={styles.sectionLabel}>SELECTED {link ? 'LINK' : 'DEVICE'}</span>{link ? <p>{label(link.sourceDeviceId)} {link.sourceInterface} ↔ {label(link.targetDeviceId)} {link.targetInterface}<br/>{link.mode === 'routed' ? 'Routed Ethernet · ' + (link.id === 'l-r1-r2' ? snapshot.routing?.transitSubnet : snapshot.routing?.externalSubnet) : `${link.mode} · VLAN ${link.vlanIds.join(' / ')}`}</p> : <p>{device?.label} · {device?.model} · {device?.role}</p>}</div>
        {shown && (
          <details className={styles.case}>
            <summary>Explain the request and reply, step by step</summary>
            <PingWalkthrough snapshot={snapshot} record={shown} steps={steps} step={active ? step : -1} jump={jump}/>
          </details>
        )}
      </section>
    </div>
    <p className={styles.help}>DHCP addresses can vary between lab runs. This replay uses the addresses from the recorded command.</p>
  </section>;
}
