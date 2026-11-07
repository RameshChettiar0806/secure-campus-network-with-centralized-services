import { useMemo, useRef, useState } from 'react';
import { Background, ConnectionMode, Controls, MiniMap, Position, ReactFlow, type Edge, type ReactFlowInstance } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { checkpointNodeTypes, type CampusNode } from './CheckpointDevice';
import DeviceSymbol from './DeviceSymbol';
import type { Capture } from '../lib/checkpoint';
import { connectionFor, deviceLessonFor, topologyFor, type TopologyView } from '../lib/checkpointTopology';
import styles from '../views/Remediation.module.css';

const shortPort = (port: string) => port.replace('GigabitEthernet', 'Gi').replace('FastEthernet', 'Fa');
const linkColors = { access: 'var(--muted)', trunk: 'var(--topology-trunk)', routed: 'var(--topology-routed)' };

export default function CheckpointTopology({ capture, labels, theme }: {
  capture: Capture; labels: ReadonlyMap<string, string>; theme: 'dark' | 'light';
}) {
  const [view, setView] = useState<TopologyView>('simplified');
  const [showPorts, setShowPorts] = useState(false);
  const [selected, setSelected] = useState('SW1-CORE');
  const graph = useRef<ReactFlowInstance<CampusNode, Edge> | null>(null);
  const visible = useMemo(() => topologyFor(capture, view), [capture, view]);
  const { nodes, edges } = useMemo(() => {
    const nodes: CampusNode[] = visible.nodes.map(node => ({
      id: node.name, type: 'campusDevice', position: node.position, width: 146, height: 59, selected: node.name === selected,
      ariaLabel: `${labels.get(node.name) ?? node.name}. Select for its device guide.`,
      data: { label: labels.get(node.name) ?? node.name, model: node.model },
    }));
    const positions = new Map(nodes.map(node => [node.id, node.position]));
    const edges: Edge[] = visible.links.map(link => {
      const from = positions.get(link.from)!;
      const to = positions.get(link.to)!;
      const dx = to.x - from.x;
      const dy = to.y - from.y;
      const [sourceHandle, targetHandle] = Math.abs(dy) < 100
        ? dx > 0 ? [Position.Right, Position.Left] : [Position.Left, Position.Right]
        : dy > 0 ? [Position.Bottom, Position.Top] : [Position.Top, Position.Bottom];
      const active = link.from === selected || link.to === selected;
      const connection = connectionFor(capture, link);
      return { id: `${link.from}:${link.port}`, source: link.from, target: link.to, sourceHandle, targetHandle, type: 'straight',
        selectable: false, focusable: false, zIndex: active ? 1 : 0,
        label: showPorts ? `${shortPort(link.port)} ↔ ${shortPort(link.peer)}` : undefined,
        labelStyle: { fill: 'var(--text)', fontSize: 10 }, labelBgStyle: { fill: 'var(--surface)' },
        style: { stroke: active ? 'var(--accent)' : linkColors[connection.kind], opacity: active ? 1 : .5, strokeWidth: active ? 2.5 : 1.5 } };
    });
    return { nodes, edges };
  }, [visible, labels, selected, showPorts, capture]);
  const selectedDevice = capture.nodes.find(node => node.name === selected)!;
  const lesson = deviceLessonFor(capture, selected)!;
  const links = capture.links.filter(link => link.from === selected || link.to === selected);
  const allDevices = [...capture.nodes].sort((a, b) => (labels.get(a.name) ?? a.name).localeCompare(labels.get(b.name) ?? b.name));
  const changeView = (next: TopologyView) => {
    setView(next);
    if (!topologyFor(capture, next).nodes.some(node => node.name === selected)) setSelected('SW1-CORE');
  };
  const inspect = (id: string) => {
    setSelected(id);
    if (!visible.nodes.some(node => node.name === id)) setView('complete');
  };
  const focusDevice = () => {
    const node = nodes.find(item => item.id === selected)!;
    void graph.current?.setCenter(node.position.x + 73, node.position.y + 30, { zoom: 1, duration: 300 });
  };

  return <section aria-labelledby="topology-heading" className={styles.topologySection}>
    <div className={styles.sectionIntro}>
      <p className={styles.eyebrow}>Physical topology</p>
      <h2 id="topology-heading">Dual-core physical topology</h2>
      <p>Explore the network, then select a device to learn what it does, why it is needed and how it connects. Both views use the same verified capture.</p>
    </div>
    <div className={styles.topologyViews} role="group" aria-label="Topology views">
      <button type="button" aria-pressed={view === 'simplified'} onClick={() => changeView('simplified')}>
        <span>View 01</span><strong>Simplified view</strong><small>Infrastructure and management</small>
      </button>
      <button type="button" aria-pressed={view === 'complete'} onClick={() => changeView('complete')}>
        <span>View 02</span><strong>Complete topology</strong><small>Every device in the Packet Tracer layout</small>
      </button>
    </div>
    <div className={styles.topologyToolbar}>
      <p role="status"><strong>{nodes.length} devices · {edges.length} links</strong><span>{view === 'complete'
        ? 'All 50 PCs, both servers and all 8 network devices.' : '49 departmental workstations are hidden in this overview.'}</span></p>
      <div className={styles.actions}>
        <label className={styles.toggle}><input type="checkbox" checked={showPorts} onChange={event => setShowPorts(event.target.checked)}/> Interface labels</label>
        <button type="button" className={styles.secondary} onClick={focusDevice}>Focus selected device</button>
        <button type="button" className={styles.secondary} onClick={() => void graph.current?.fitView({ padding: .13, duration: 300 })}>Fit topology</button>
      </div>
    </div>
    <p className={styles.topologyHint}>{view === 'complete'
      ? 'Device positions follow the saved Packet Tracer canvas, expanded evenly for readable names. Zoom or use Focus selected device to inspect the complete map.'
      : 'This is the existing compact layout. Choose View 02 to see every workstation and its physical connection.'}</p>
    <div className={`${styles.graph} ${view === 'complete' ? styles.completeGraph : ''}`} aria-label={`${view === 'complete' ? 'Complete' : 'Simplified'} physical topology`}>
      <ReactFlow<CampusNode, Edge> key={view} nodes={nodes} edges={edges} nodeTypes={checkpointNodeTypes} fitView colorMode={theme}
        connectionMode={ConnectionMode.Loose} nodesDraggable={false} nodesConnectable={false} minZoom={0.08} fitViewOptions={{ padding: .13 }}
        onInit={instance => { graph.current = instance; }} onNodeClick={(_, node) => inspect(node.id)}
        onKeyDown={event => {
          const id = (event.target as HTMLElement).closest('.react-flow__node')?.getAttribute('data-id');
          if (id && (event.key === 'Enter' || event.key === ' ')) { event.preventDefault(); inspect(id); }
        }}>
        <Background/><Controls showInteractive={false}/>
        {view === 'complete' && <MiniMap pannable zoomable ariaLabel="Complete topology overview" nodeColor="var(--accent)" maskColor="var(--topology-mask)"/>}
      </ReactFlow>
    </div>
    <div className={styles.topologyLegend} aria-label="Connection legend">
      <span data-kind="access">Endpoint Ethernet</span><span data-kind="trunk">802.1Q trunk</span>
      <span data-kind="routed">Routed Ethernet</span><span data-kind="selected">Selected device connections</span>
    </div>
    <div className={styles.selectedSummary}>
      <p aria-live="polite">Selected: <strong>{labels.get(selected)}</strong></p>
      <a href="#device-guide">Read device guide ↓</a>
    </div>
    <article id="device-guide" aria-labelledby="device-guide-title" className={styles.deviceGuide}>
      <div className={styles.deviceGuideHeader}>
        <div className={styles.deviceIdentity}><DeviceSymbol model={selectedDevice.model} size={36}/><div>
          <p className={styles.eyebrow}>Device guide · {selectedDevice.model}</p>
          <h3 id="device-guide-title">{labels.get(selected)}</h3><p>{lesson.role}</p>
        </div></div>
        <label>Inspect a device<select value={selected} onChange={event => inspect(event.target.value)}>
          {allDevices.map(node => <option key={node.name} value={node.name}>{labels.get(node.name)}</option>)}
        </select></label>
      </div>
      <div className={styles.deviceLesson}>
        <div className={styles.deviceExplanation}>
          <section><h4>What is this device?</h4><p>{lesson.what}</p></section>
          <section><h4>Why is it needed?</h4><p>{lesson.purpose}</p></section>
          <section><h4>How does it handle traffic?</h4><p>{lesson.forwarding}</p></section>
          <section><h4>What happens if it fails?</h4><p>{lesson.failure}</p></section>
        </div>
        <aside className={styles.deviceFacts} aria-label="Device addressing and learning notes">
          <h4>Addressing and role</h4>
          <dl>{lesson.facts.map(fact => <div key={fact.label}><dt>{fact.label}</dt><dd>{fact.value}</dd></div>)}</dl>
          <h4>Concepts to learn</h4>
          <ul className={styles.conceptTags}>{lesson.concepts.map(concept => <li key={concept}>{concept}</li>)}</ul>
          <details key={selected} className={styles.learningQuestion}><summary>Check your understanding</summary>
            <p><strong>{lesson.question}</strong></p><p>{lesson.answer}</p>
          </details>
        </aside>
      </div>
      <section aria-labelledby="device-connections-title" className={styles.deviceConnections}>
        <h4 id="device-connections-title">What is it connected to? <span>{links.length} direct connections</span></h4>
        <p>Local port belongs to the selected device. Select a neighbor to explore its role. This list includes connections hidden by the simplified view.</p>
        <div className={styles.tableWrap}><table>
          <thead><tr><th scope="col">Connected device</th><th scope="col">Local port</th><th scope="col">Neighbor port</th><th scope="col">Connection purpose</th></tr></thead>
          <tbody>{links.map(link => {
            const from = link.from === selected;
            const other = from ? link.to : link.from;
            const connection = connectionFor(capture, link);
            return <tr key={`${link.from}:${link.port}`}>
              <th scope="row"><button type="button" onClick={() => inspect(other)}>{labels.get(other)} <span aria-hidden="true">↗</span></button></th>
              <td><code>{shortPort(from ? link.port : link.peer)}</code></td>
              <td><code>{shortPort(from ? link.peer : link.port)}</code></td>
              <td><strong>{connection.title}</strong><small>{connection.detail}</small></td>
            </tr>;
          })}</tbody>
        </table></div>
      </section>
      <p className={styles.captureNote}>Layout, links and endpoint addresses: {new Date(capture.capturedAt).toLocaleDateString('en-IN', { dateStyle: 'long', timeZone: 'Asia/Kolkata' })} capture. Role notes use the saved Iteration {capture.iteration} configurations. Highlighted links show physical connections, not live forwarding or link health.</p>
    </article>
  </section>;
}
