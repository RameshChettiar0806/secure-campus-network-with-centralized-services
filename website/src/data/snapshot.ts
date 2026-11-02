import raw from '../../../data/network-snapshot.v3.json';
import { assertSnapshot, type NetworkSnapshot } from '../models/network';

export function loadSnapshot(): NetworkSnapshot {
  assertSnapshot(raw);
  return raw;
}
