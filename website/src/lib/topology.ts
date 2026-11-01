import type { NetworkSnapshot } from '../models/network';

export function topologyPositions(snapshot: NetworkSnapshot): Record<string, { x: number; y: number }> {
  const positions: Record<string, { x: number; y: number }> = {
    r1: { x: 795, y: 0 }, sw1: { x: 795, y: 155 }, server0: { x: 1100, y: 155 },
    sw2: { x: 205, y: 350 }, sw3: { x: 795, y: 350 }, sw4: { x: 1385, y: 350 },
  };
  for (const [vlan, left] of [[10, 0], [20, 590], [30, 1180]]) {
    const clients = snapshot.devices.filter(d => d.model === 'PC-PT' && d.vlanId === vlan);
    clients.forEach((device, i) => { positions[device.id] = { x: left + i % 4 * 135, y: 525 + Math.floor(i / 4) * 110 }; });
  }
  for (const device of snapshot.devices) positions[device.id] ??= device.position;
  return positions;
}
