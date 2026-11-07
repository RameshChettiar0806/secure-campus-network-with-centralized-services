import { useEffect, useRef, useState } from 'react';
import { Background, ConnectionMode, Controls, MarkerType, Position, ReactFlow, type Edge } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import type { Capture, flowFor } from '../lib/checkpoint';
import { checkpointNodeTypes, type CampusNode, type PacketPhase } from './CheckpointDevice';
import styles from '../views/Remediation.module.css';

type Hop = { device: string; phase: PacketPhase };
const phaseNames = { request: 'Echo request', reply: 'Echo reply', blocked: 'Request stopped' };
const linkKey = (a: string, b: string) => a < b ? `${a}:${b}` : `${b}:${a}`;

export default function ScenarioPacketFlow({ capture, labels, flow, theme, denied, received, autoPlay = false }: {
  capture: Capture; labels: ReadonlyMap<string, string>; flow: ReturnType<typeof flowFor>;
  theme: 'dark' | 'light'; denied: boolean; received: number; autoPlay?: boolean;
}) {
  const [step, setStep] = useState(autoPlay ? 0 : -1);
  const [playing, setPlaying] = useState(autoPlay);
  const [columns, setColumns] = useState(3);
  const map = useRef<HTMLDivElement>(null);
  const request: Hop[] = flow.path.map((device, index) => ({
    device, phase: denied && index === flow.path.length - 1 ? 'blocked' : 'request',
  }));
  const reply: Hop[] = !denied && received > 0
    ? [...flow.path].reverse().slice(1).map(device => ({ device, phase: 'reply' }))
    : [];
  const hops = [...request, ...reply];
  const current = hops[step];
  const previous = hops[step - 1];
  const finished = step === hops.length - 1;

  useEffect(() => {
    const element = map.current;
    if (!element) return;
    const fit = () => setColumns(element.clientWidth < 520 ? 2 : 3);
    fit();
    const observer = new ResizeObserver(fit);
    observer.observe(element);
    return () => observer.disconnect();
  }, []);
  useEffect(() => {
    if (!playing || finished) return;
    const timer = window.setTimeout(() => setStep(index => index + 1), 1100);
    return () => window.clearTimeout(timer);
  }, [playing, finished, step]);

  const name = (id: string) => labels.get(id) ?? id;
  const visited = new Set(flow.path);
  const nodes = [...new Set(flow.route)].map((id, index): CampusNode => {
    const row = Math.floor(index / columns);
    const column = row % 2 ? columns - 1 - index % columns : index % columns;
    return { id, type: 'campusDevice', position: { x: column * 185, y: row * 120 },
      data: { label: name(id), model: capture.nodes.find(device => device.name === id)?.model ?? '',
        phase: current?.device === id ? current.phase : undefined, dimmed: !visited.has(id) },
      ariaLabel: name(id), selectable: false, focusable: false };
  });
  const positions = new Map(nodes.map(node => [node.id, node.position]));
  const routeLinks = new Set(flow.route.slice(1).map((id, index) => linkKey(flow.route[index], id)));
  const requestLinks = new Set(flow.path.slice(1).map((id, index) => linkKey(flow.path[index], id)));
  const activeLink = previous && current ? linkKey(previous.device, current.device) : undefined;
  const color = current?.phase === 'blocked' ? '#d9725d'
    : current?.phase === 'reply' ? (theme === 'dark' ? '#90baff' : '#225caa')
    : theme === 'dark' ? '#65dac7' : '#087f73';
  const edges: Edge[] = capture.links.flatMap(link => {
    const key = linkKey(link.from, link.to);
    if (!routeLinks.has(key)) return [];
    const active = key === activeLink;
    const source = active && previous ? previous.device : link.from;
    const target = source === link.from ? link.to : link.from;
    const a = positions.get(source)!;
    const b = positions.get(target)!;
    const [sourceHandle, targetHandle] = a.y === b.y
      ? b.x > a.x ? [Position.Right, Position.Left] : [Position.Left, Position.Right]
      : b.y > a.y ? [Position.Bottom, Position.Top] : [Position.Top, Position.Bottom];
    return [{ id: key, source, target, sourceHandle, targetHandle, type: 'straight',
      animated: active && playing && !finished,
      markerEnd: active ? { type: MarkerType.ArrowClosed, color, width: 15, height: 15 } : undefined,
      style: { stroke: active ? color : 'var(--muted)', strokeWidth: active ? 3 : 1.5,
        opacity: active || requestLinks.has(key) ? 1 : .35, strokeDasharray: !requestLinks.has(key) ? '5 5' : undefined },
      selectable: false, focusable: false }];
  });
  const jump = (index: number) => { setPlaying(false); setStep(index); };
  const play = () => {
    if (!current || finished) { setStep(0); setPlaying(true); }
    else setPlaying(!playing);
  };
  const state = current
    ? `${finished && current.phase === 'reply' ? 'Reply received' : phaseNames[current.phase]} · ${name(current.device)}`
    : 'Ready to replay';
  return <section className={styles.packetReplay} aria-labelledby="packet-map-title">
    <h4 id="packet-map-title">Visual packet flow</h4>
    <p className={styles.muted}>Replay one illustrated ICMP exchange along the selected route. The measured reply count above comes from Packet Tracer.
      {denied && ' Dimmed devices show the physical route beyond the stop.'}</p>
    <div className={styles.playback} role="group" aria-label="Packet playback">
      <button type="button" className={styles.primary} onClick={play}>{finished ? 'Replay packet' : !current ? 'Play packet flow' : playing ? 'Pause' : 'Resume'}</button>
      <button type="button" className={styles.secondary} disabled={step <= 0} onClick={() => jump(step - 1)}>Previous hop</button>
      <button type="button" className={styles.secondary} disabled={finished} onClick={() => jump(step + 1)}>Next hop</button>
      <button type="button" className={styles.secondary} disabled={step < 0} onClick={() => jump(-1)}>Reset</button>
    </div>
    <div className={styles.packetStatus} data-phase={current?.phase} role="status">
      <strong>{state}</strong>
      {current && <span>Hop {step + 1} of {hops.length}</span>}
    </div>
    <div ref={map} className={`${styles.graph} ${styles.packetMap}`} role="group" aria-label="Packet route map">
      <ReactFlow key={columns} nodes={nodes} edges={edges} nodeTypes={checkpointNodeTypes} colorMode={theme}
        connectionMode={ConnectionMode.Loose} fitView fitViewOptions={{ padding: .23 }} minZoom={.2} maxZoom={1.6}
        nodesDraggable={false} nodesConnectable={false} elementsSelectable={false}>
        <Background/><Controls showInteractive={false}/>
      </ReactFlow>
    </div>
    {[{ title: 'Echo request hops', leg: request, start: 0 }, { title: 'Echo reply hops', leg: reply, start: request.length }]
      .filter(({ leg }) => leg.length > 0).map(({ title, leg, start }) => <div key={title} className={styles.hopList}>
        <strong>{title}</strong>
        <ol aria-label={title}>{leg.map((hop, index) => <li key={index}>
          <button type="button" aria-pressed={step === start + index} data-phase={hop.phase} onClick={() => jump(start + index)}>{name(hop.device)}</button>
        </li>)}</ol>
      </div>)}
    <p>{flow.explanation}</p>
  </section>;
}
