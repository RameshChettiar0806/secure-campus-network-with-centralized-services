import { expect, it } from 'vitest';
import raw from '../../../data/network-snapshot.v3.json';
import { assertSnapshot } from '../models/network';
import { topologyPositions } from './topology';
assertSnapshot(raw);
const network = raw;

it('places every expanded device without overlapping node cards', () => {
  const positions = topologyPositions(network);
  expect(Object.keys(positions)).toHaveLength(58);
  const values = Object.values(positions);
  for (const [i, a] of values.entries()) for (const b of values.slice(i + 1)) {
    expect(Math.abs(a.x - b.x) >= 150 || Math.abs(a.y - b.y) >= 100).toBe(true);
  }
});
