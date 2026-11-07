import { Handle, Position, type Node, type NodeProps } from '@xyflow/react';
import DeviceSymbol from './DeviceSymbol';
import styles from '../views/Remediation.module.css';

export type PacketPhase = 'request' | 'reply' | 'blocked';
export type CampusNode = Node<{
  label: string;
  model: string;
  phase?: PacketPhase;
  dimmed?: boolean;
}, 'campusDevice'>;

const sides = [Position.Top, Position.Right, Position.Bottom, Position.Left];

function CheckpointDevice({ data, selected }: NodeProps<CampusNode>) {
  return <div className={`${styles.device} ${selected ? styles.selectedDevice : ''}`}
    data-phase={data.phase} data-dimmed={data.dimmed || undefined}>
    {sides.map(side => <Handle key={side} id={side} type="source" position={side}/>)}
    <DeviceSymbol model={data.model} size={22}/>
    <span><strong>{data.label}</strong><small>{data.model}</small></span>
    {data.phase && <span className={styles.packetMarker}>
      {data.phase === 'blocked' ? '⊘ Stopped' : data.phase === 'reply' ? '● Echo reply' : '● Echo request'}
    </span>}
  </div>;
}

export const checkpointNodeTypes = { campusDevice: CheckpointDevice };
