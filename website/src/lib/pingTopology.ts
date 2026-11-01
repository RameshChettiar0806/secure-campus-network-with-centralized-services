import type { DeviceId, NetworkSnapshot } from '../models/network';
import { physicalPath, type PingStep } from './ping';

// Keep the physical path between the endpoints visible even when R1 drops the request.
// A routed exchange can also visit an uplink and return over that same cable.
export function pingTopology(network: NetworkSnapshot, source: DeviceId, dest: DeviceId, steps: PingStep[]): NetworkSnapshot {
  const backbone = physicalPath(network, source, dest);
  const ids = new Set([...backbone, ...steps.map(hop => hop.deviceId)]);
  const links = network.links.filter(l => ids.has(l.sourceDeviceId) && ids.has(l.targetDeviceId));
  const positions = new Map(backbone.map((id, i) => [id, { x: i * 174, y: 0 }]));
  const queue = [...backbone];
  for (const id of queue) {
    const pos = positions.get(id)!;
    for (const l of links) {
      const next = l.sourceDeviceId === id ? l.targetDeviceId : l.targetDeviceId === id ? l.sourceDeviceId : undefined;
      if (!next || positions.has(next)) continue;
      positions.set(next, { x: pos.x, y: pos.y - 128 });
      queue.push(next);
    }
  }
  return { ...network, links, devices: network.devices.filter(d => ids.has(d.id)).map(d => ({ ...d, position: positions.get(d.id)! })) };
}
