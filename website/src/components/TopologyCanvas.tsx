import { memo, useEffect, useMemo, useRef, useState } from 'react';
import { Background, BackgroundVariant, Controls, MarkerType, Handle, Position, ReactFlow, type Node, type NodeProps, type Edge, type Viewport, type ReactFlowInstance } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import type { NetworkDevice, NetworkSnapshot } from '../models/network';
import { isDeviceHighlighted, isLinkHighlighted, primaryAddress, readPreference, vlanColors, writePreference } from '../lib/network';
import DeviceSymbol from './DeviceSymbol';
import styles from '../app/App.module.css';
import type { PacketPresentation } from '../lib/ping';
import { topologyPositions } from '../lib/topology';

type DeviceFlowNode = Node<{ device: NetworkDevice; dimmed: boolean; address?: string; packetActive?: boolean; blocked?: boolean }, 'device'>;
const DeviceNode = memo(({ data, selected }: NodeProps<DeviceFlowNode>) => {
  const device = data.device;
  return <div className={`${styles.deviceNode} ${selected ? styles.nodeSelected : ''} ${data.dimmed ? styles.dimmed : ''} ${data.packetActive ? styles.packetActive : ''} ${data.blocked ? styles.packetBlocked : ''}`} style={{ '--vlan': vlanColors[device.vlanId ?? 0] ?? '#7d9bad' } as React.CSSProperties}>
    {(['left', 'right', 'top', 'bottom'] as const).map(side => <span key={side}><Handle type="source" id={`s-${side}`} position={Position[side === 'left' ? 'Left' : side === 'right' ? 'Right' : side === 'top' ? 'Top' : 'Bottom']} isConnectable={false}/><Handle type="target" id={`t-${side}`} position={Position[side === 'left' ? 'Left' : side === 'right' ? 'Right' : side === 'top' ? 'Top' : 'Bottom']} isConnectable={false}/></span>)}
    <div className={styles.nodeHeading}><span className={styles.nodeIcon}><DeviceSymbol model={device.model}/></span><span>{device.vlanId ? `VLAN ${device.vlanId}` : device.id === 'r1' ? 'L3 ROUTER' : 'L2 SWITCH'}</span></div>
    <strong>{device.label}</strong><small>{data.address ?? primaryAddress(device)}</small>{data.packetActive && <span className={styles.packetMarker}>{data.blocked ? '⊘ BLOCKED' : '● ICMP'}</span>}
  </div>;
});
const nodeTypes = { device: DeviceNode };
const isViewport = (v: unknown): v is Viewport => !!v && typeof v === 'object' && ['x', 'y', 'zoom'].every(k => typeof (v as Record<string, unknown>)[k] === 'number' && Number.isFinite((v as Record<string, number>)[k])) && (v as Viewport).zoom >= .1 && (v as Viewport).zoom <= 1.8;

export default function TopologyCanvas({ snapshot, vlan, selected, select, selectLink, theme, packet, addresses, pingView, moving }: { snapshot: NetworkSnapshot; vlan: number | null; selected: string; select: (id: string) => void; selectLink: (id: string) => void; theme: 'dark' | 'light'; packet?: PacketPresentation; addresses?: Record<string, string>; pingView?: 'route' | 'campus'; moving?: boolean }) {
  const instance = useRef<ReactFlowInstance<DeviceFlowNode, Edge> | null>(null);
  const canvasRef = useRef<HTMLDivElement | null>(null);
  const positions = useMemo(() => pingView === 'route' ? Object.fromEntries(snapshot.devices.map(d => [d.id, d.position])) : topologyPositions(snapshot), [snapshot, pingView]);
  const viewportKey = `campus-viewport-${snapshot.snapshotId}-${packet ? 'ping' : 'topology'}`;
  const [savedViewport, setSavedViewport] = useState(() => pingView ? null : readPreference<Viewport | null>(viewportKey, null, (v): v is Viewport | null => isViewport(v)));
  const savedSize = useRef(readPreference<{ width: number; height: number } | null>('campus-viewport-size', null, (v): v is { width: number; height: number } => !!v && typeof v === 'object' && typeof (v as { width?: unknown }).width === 'number' && typeof (v as { height?: unknown }).height === 'number'));
  useEffect(() => {
    const element = canvasRef.current;
    if (!element) return;
    let width = element.clientWidth, height = element.clientHeight;
    const observer = new ResizeObserver(() => {
      if (Math.abs(element.clientWidth - width) > 20 || Math.abs(element.clientHeight - height) > 20) void instance.current?.fitView({ padding: .13 });
      width = element.clientWidth; height = element.clientHeight;
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);
  const packetPath = packet ? [...new Set([...packet.steps.map(s => s.deviceId), packet.destinationDeviceId])].join(',') : '';
  useEffect(() => {
    if (!instance.current || pingView) return;
    const ids = packetPath ? packetPath.split(',') : vlan === null ? [] : snapshot.devices.filter(d => isDeviceHighlighted(d, vlan)).map(d => d.id);
    void instance.current.fitView({ nodes: ids.length ? ids.map(id => ({ id })) : undefined, padding: .2, duration: 250 });
  }, [vlan, packetPath, snapshot, pingView]);
  const nodes = useMemo<DeviceFlowNode[]>(() => snapshot.devices.map(device => ({ id: device.id, type: 'device', data: { device, address: packet?.addresses[device.id] ?? addresses?.[device.id], packetActive: packet?.steps[packet.step]?.deviceId === device.id, blocked: packet?.steps[packet.step]?.deviceId === device.id && packet.steps[packet.step].phase === 'blocked', dimmed: packet ? !packet.steps.some(s => s.deviceId === device.id) && packet.destinationDeviceId !== device.id : !isDeviceHighlighted(device, vlan) }, position: positions[device.id] ?? device.position, selected: device.id === selected, ariaLabel: `${device.label}, ${device.role}` })), [snapshot, selected, vlan, packet, addresses]);
  const edges = useMemo<Edge[]>(() => snapshot.links.map(link => {
    const a = positions[link.sourceDeviceId], b = positions[link.targetDeviceId];
    const vertical = Math.abs(b.y - a.y) > Math.abs(b.x - a.x);
    const side = vertical ? b.y > a.y ? 'bottom' : 'top' : b.x > a.x ? 'right' : 'left';
    const opposite = { bottom: 'top', top: 'bottom', left: 'right', right: 'left' };
    const pathContainsLink = packet?.steps.some((step, index) => { const previous = packet.steps[index - 1]; return previous && ((previous.deviceId === link.sourceDeviceId && step.deviceId === link.targetDeviceId) || (previous.deviceId === link.targetDeviceId && step.deviceId === link.sourceDeviceId)); });
    const previous = packet?.steps[packet.step - 1]?.deviceId, current = packet?.steps[packet.step]?.deviceId;
    const activeLink = !!previous && ((previous === link.sourceDeviceId && current === link.targetDeviceId) || (previous === link.targetDeviceId && current === link.sourceDeviceId));
    const reverse = activeLink && current === link.sourceDeviceId;
    const color = packet?.steps[packet.step]?.phase === 'blocked' ? '#ed927d' : packet?.steps[packet.step]?.phase === 'reply' ? '#7faaf2' : '#65dac7';
    return { id: link.id, source: reverse ? link.targetDeviceId : link.sourceDeviceId, target: reverse ? link.sourceDeviceId : link.targetDeviceId,
      sourceHandle: `s-${reverse ? opposite[side] : side}`, targetHandle: `t-${reverse ? side : opposite[side]}`, type: 'smoothstep', label: pingView !== 'route' && link.mode === 'trunk' ? `802.1Q · ${link.vlanIds.join(' / ')}` : undefined,
      animated: activeLink && !!moving, markerEnd: activeLink ? { type: MarkerType.ArrowClosed, color, width: 5, height: 5 } : undefined, style: { stroke: activeLink ? color : link.mode === 'trunk' ? '#8297b4' : vlanColors[link.vlanIds[0]], strokeWidth: activeLink ? 4 : link.mode === 'trunk' ? 2.5 : 1.8, opacity: packet ? pathContainsLink ? 1 : .12 : isLinkHighlighted(link, vlan) ? 1 : .15 },
      labelStyle: { fill: theme === 'dark' ? '#c4d2e7' : '#283f5a', fontSize: 11 }, labelBgStyle: { fill: theme === 'dark' ? '#101a2a' : '#f4f7fb' }, interactionWidth: 24, ariaLabel: `${link.mode} link ${link.id}`, focusable: true,
    };
  }), [snapshot, vlan, theme, packet, positions, moving, pingView]);
  return <div ref={canvasRef} className={styles.canvas} aria-label="Campus network topology">
    <ReactFlow<DeviceFlowNode> nodes={nodes} edges={edges} nodeTypes={nodeTypes} onInit={flow => { instance.current = flow; const size = savedSize.current; if (savedViewport && (!size || Math.abs((canvasRef.current?.clientWidth ?? 0) - size.width) > 20 || Math.abs((canvasRef.current?.clientHeight ?? 0) - size.height) > 20)) void flow.fitView({ padding: .13 }); }} defaultViewport={savedViewport ?? undefined} fitView={!savedViewport} fitViewOptions={{ padding: .13 }}
      nodesDraggable={false} nodesConnectable={false} edgesReconnectable={false} deleteKeyCode={null} minZoom={.1} maxZoom={1.8} colorMode={theme}
      onNodeClick={(_, node) => select(node.id)} onEdgeClick={(_, edge) => selectLink(edge.id)} onMoveEnd={(_, viewport) => { if (pingView) return; writePreference(viewportKey, viewport); if (canvasRef.current) writePreference('campus-viewport-size', { width: canvasRef.current.clientWidth, height: canvasRef.current.clientHeight }); }}>
      <Background variant={BackgroundVariant.Dots} gap={22} size={1} color={theme === 'dark' ? '#253044' : '#d5dce7'}/>
      <Controls showInteractive={false}/>
    </ReactFlow>
    <div className={styles.canvasLabel}><span className={styles.tinyDot}/>{pingView === 'route' ? 'PING ROUTE' : 'PHYSICAL TOPOLOGY'}</div>
    <div className={styles.canvasActions}><button onClick={() => { const p = positions[selected]; if (p) void instance.current?.setCenter(p.x + 57, p.y + 40, { zoom: 1.1, duration: 250 }); }}>Focus selected</button><button onClick={() => { setSavedViewport(null); if (!pingView) writePreference(viewportKey, null); void instance.current?.fitView({ padding: .13 }); }}>{pingView === 'route' ? 'Fit route' : `Fit all ${snapshot.devices.length}`}</button></div>
    <div className={styles.canvasNote}>Scroll to zoom · Drag to pan · Select to inspect</div>
  </div>;
}
