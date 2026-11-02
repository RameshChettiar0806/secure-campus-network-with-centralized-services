import type { NetworkSnapshot } from '../models/network';

export function topologyPositions(snapshot: NetworkSnapshot): Record<string, { x: number; y: number }> {
  const positions: Record<string, { x: number; y: number }> = {
    server1: { x: 350, y: 0 }, r2: { x: 710, y: 0 },
    r1: { x: 1070, y: 0 }, sw1: { x: 1070, y: 180 }, server0: { x: 1430, y: 180 },
    sw2: { x: 270, y: 380 }, sw3: { x: 1070, y: 380 }, sw4: { x: 1870, y: 380 },
  };
  for (const [vlan, left] of [[10, 0], [20, 800], [30, 1600]]) {
    const clients = snapshot.devices.filter(d => d.model === 'PC-PT' && d.vlanId === vlan);
    clients.forEach((device, i) => { positions[device.id] = { x: left + i % 4 * 180, y: 570 + Math.floor(i / 4) * 130 }; });
  }
  for (const device of snapshot.devices) positions[device.id] ??= device.position;
  return positions;
}
