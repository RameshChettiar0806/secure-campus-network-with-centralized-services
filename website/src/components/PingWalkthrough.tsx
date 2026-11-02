import type { NetworkSnapshot } from '../models/network';
import type { PingRecord, PingStep } from '../lib/ping';
import { shortName } from '../lib/network';
import HopNotes from './HopNotes';
import DeviceSymbol from './DeviceSymbol';
import ui from './Teaching.module.css';

interface WalkthroughProps {
  snapshot: NetworkSnapshot;
  record: PingRecord;
  steps: PingStep[];
  step: number;
  jump: (index: number) => void;
}

export default function PingWalkthrough({ snapshot, record, steps, step, jump }: WalkthroughProps) {
  const device = (id: string) => snapshot.devices.find(d => d.id === id)!;
  const source = device(record.sourceDeviceId), dest = device(record.destinationDeviceId);
  const origin = snapshot.vlans.find(v => v.id === source.vlanId);
  const destinationPort = dest.interfaces.find(p => p.ipv4 === record.destinationIp);
  const destVlan = snapshot.vlans.find(v => v.id === (dest.vlanId ?? destinationPort?.vlanId));
  const current = steps[step];
  const local = origin !== undefined && !['r1','r2'].includes(dest.id) && origin.id === destVlan?.id;
  const forwarding = local ? `Switches carry the frame within VLAN ${origin?.id}.`
    : ['r1','r2'].includes(dest.id) ? `The target is ${dest.label}’s interface at ${record.destinationIp}.`
    : `The sender uses gateway ${origin?.gateway ?? snapshot.routing?.externalGateway} to reach the destination subnet.`;
  return <article className={ui.panel}><div className={ui.kicker}>PACKET WALKTHROUGH</div>
    <h3>{source.label} → {dest.label}</h3><p><strong>{origin ? shortName(origin.name) + ' · VLAN ' + origin.id : 'External LAN'}</strong> → <strong>{destVlan ? shortName(destVlan.name)+' · VLAN '+destVlan.id : dest.label}</strong></p>
    <HopNotes notes={[
      { concept: 'IP endpoints', detail: `${record.sourceIp} → ${record.destinationIp}.` },
      { concept: 'Forwarding', detail: forwarding },
    ]}/>
    {(['request','reply'] as const).map(leg => {
      const items = steps.map((hop,index) => ({hop,index})).filter(({hop}) => leg === 'reply' ? hop.phase === 'reply' : hop.phase !== 'reply');
      return <section key={leg} className={ui.leg}><h4>{leg === 'request' ? '1. Echo request · ICMP Type 8' : '2. Echo reply · ICMP Type 0'}</h4>
        
        {items.length ? <div className={ui.stops}>{items.map(({hop,index},i) => <div key={index}>{i > 0 && <span aria-hidden="true">→</span>}<button aria-pressed={step === index} onClick={() => jump(index)} data-result={hop.phase === 'blocked' ? 'Block' : undefined}><DeviceSymbol model={device(hop.deviceId).model} size={20}/><strong>{device(hop.deviceId).label}</strong><small>{hop.phase === 'blocked' ? record.blockingDeviceId === 'r2' && !record.enforcementAcl ? 'No private route' : 'ACL drop' : hop.phase === 'reply' ? index === steps.length - 1 ? 'Reply received' : 'Return path' : index === 0 ? 'Sender' : hop.deviceId === dest.id ? 'Destination' : ['r1','r2'].includes(hop.deviceId) ? 'Route & check' : 'Switch frame'}</small></button></div>)}</div> : <p>{device(record.blockingDeviceId ?? 'r1').label} cannot forward the request. No destination echo reply from {dest.label}.</p>}
      </section>;
    })}
    <div className={ui.explain} aria-live="polite"><strong>{current ? 'Step '+(step+1)+' of '+steps.length : 'Before sending'}</strong>{current ? <HopNotes notes={current.notes}/> : <p>Select a hop to inspect its forwarding decision.</p>}</div>

  </article>;
}
