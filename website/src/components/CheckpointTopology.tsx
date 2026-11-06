import { useMemo, useState } from 'react';
import { Background, ConnectionMode, Controls, Handle, Position, ReactFlow, type Edge, type Node, type NodeProps } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import DeviceSymbol from './DeviceSymbol';
import type { Capture } from '../lib/checkpoint';
import styles from '../views/Remediation.module.css';

type CampusNode = Node<{ label: string; model: string }, 'campusDevice'>;
const sides = [Position.Top, Position.Right, Position.Bottom, Position.Left];
const nodeTypes = { campusDevice: CampusDevice };

function CampusDevice({ data, selected }: NodeProps<CampusNode>) {
  return <div className={`${styles.device} ${selected ? styles.selectedDevice : ''}`}>
    {sides.map(side => <Handle key={side} id={side} type="source" position={side}/>)}
    <DeviceSymbol model={data.model} size={22}/>
    <span><strong>{data.label}</strong><small>{data.model}</small></span>
  </div>;
}

const infrastructure: Record<string, [number, number]> = {
  'R1-CAMPUS': [515, 30], 'R2-EXTERNAL': [760, 30], 'SRV-EXTERNAL': [1005, 30],
  'SW1-CORE': [355, 200], 'SW5-CORE': [705, 200],
  'SW2-ACCESS': [20, 390], 'SW3-FACULTY': [350, 390], 'SW4-STUDENTS': [680, 390], 'SW6-SERVICES': [1010, 390],
  'PC8-MGMT': [20, 500], 'SRV-CAMPUS': [1010, 500],
};
const deskColumns = new Map<number | string, number>([[10, 20], [20, 350], [30, 680]]);
const shortPort = (port: string) => port.replace('GigabitEthernet', 'Gi').replace('FastEthernet', 'Fa');

export default function CheckpointTopology({ capture, labels, theme }: {
  capture: Capture; labels: ReadonlyMap<string, string>; theme: 'dark' | 'light';
}) {
  const [showPCs, setShowPCs] = useState(false);
  const [selected, setSelected] = useState('SW1-CORE');
  const { nodes, edges } = useMemo(() => {
    const coordinates = new Map(Object.entries(infrastructure));
    for (const [segment, column] of deskColumns) {
      capture.endpoints.filter(endpoint => endpoint.segment === segment)
        .sort((a, b) => (labels.get(a.name) ?? a.name).localeCompare(labels.get(b.name) ?? b.name))
        .forEach((endpoint, index) => coordinates.set(endpoint.name, [column + index % 2 * 154, 605 + Math.floor(index / 2) * 75]));
    }
    const nodes: CampusNode[] = capture.nodes.filter(node => showPCs || node.model !== 'PC-PT' || node.name === 'PC8-MGMT')
      .map(node => {
        const [x, y] = coordinates.get(node.name) ?? [node.x, node.y];
        return { id: node.name, type: 'campusDevice', position: { x, y }, selected: node.name === selected,
          ariaLabel: labels.get(node.name) ?? node.name, data: { label: labels.get(node.name) ?? node.name, model: node.model } };
      });
    const visible = new Map(nodes.map(node => [node.id, node.position]));
    const edges: Edge[] = capture.links.flatMap((link, index) => {
      const from = visible.get(link.from);
      const to = visible.get(link.to);
      if (!from || !to) return [];
      const dx = to.x - from.x;
      const dy = to.y - from.y;
      const [sourceHandle, targetHandle] = Math.abs(dy) < 100
        ? dx > 0 ? [Position.Right, Position.Left] : [Position.Left, Position.Right]
        : dy > 0 ? [Position.Bottom, Position.Top] : [Position.Top, Position.Bottom];
      const active = link.from === selected || link.to === selected;
      return [{ id: String(index), source: link.from, target: link.to, sourceHandle, targetHandle, type: 'straight',
        selectable: false, focusable: false, style: { stroke: active ? 'var(--accent)' : 'var(--muted)', opacity: active ? 1 : .45, strokeWidth: active ? 2.5 : 1.5 } }];
    });
    return { nodes, edges };
  }, [capture, labels, selected, showPCs]);
  const selectedDevice = capture.nodes.find(node => node.name === selected);
  const links = capture.links.filter(link => link.from === selected || link.to === selected);

  return <section aria-labelledby="topology-heading">
    <div className={styles.sectionIntro}>
      <p className={styles.eyebrow}>Physical topology</p>
      <h2 id="topology-heading">Dual-core physical topology</h2>
      <p>Each access switch connects to both cores. The campus edge router has a separate routed uplink to each core.</p>
    </div>
    <label className={styles.toggle}>
      <input type="checkbox" checked={showPCs} onChange={event => {
        const checked = event.target.checked;
        setShowPCs(checked);
        if (!checked && !infrastructure[selected]) setSelected('SW1-CORE');
      }}/> Show all workstations
    </label>
    <div className={styles.graph} aria-label="Verified physical topology">
      <ReactFlow key={String(showPCs)} nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView colorMode={theme}
        connectionMode={ConnectionMode.Loose} nodesDraggable={false} nodesConnectable={false} minZoom={0.12} fitViewOptions={{ padding: .13 }}
        onNodeClick={(_, node) => setSelected(node.id)}>
        <Background/><Controls showInteractive={false}/>
      </ReactFlow>
    </div>
    <div className={styles.topologyDetail}>
      <div>
        <p className={styles.eyebrow}>Device connections</p>
        <h3>{labels.get(selected) ?? selected} <small>{selectedDevice?.model}</small></h3>
        <label>Inspect a device<select value={selected} onChange={event => setSelected(event.target.value)}>
          {[...nodes].sort((a, b) => a.data.label.localeCompare(b.data.label)).map(node => <option key={node.id} value={node.id}>{node.data.label}</option>)}
        </select></label>
      </div>
      <ul>{links.map(link => {
        const from = link.from === selected;
        const other = from ? link.to : link.from;
        return <li key={`${link.from}:${link.port}`}><span>{labels.get(other) ?? other}</span>
          <code>{shortPort(from ? link.port : link.peer)} ↔ {shortPort(from ? link.peer : link.port)}</code></li>;
      })}</ul>
    </div>
  </section>;
}
