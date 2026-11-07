import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { validateRelease } from './validate-release.mjs';

const read = path => JSON.parse(readFileSync(new URL(path, import.meta.url), 'utf8'));
const release = read('../../data/audit-release.json');
const checkpoint = read('../../evidence/AUDIT-REMEDIATION-20261105-182333/verified-submission.json');
const manifest = read('../../evidence/AUDIT-REMEDIATION-20261105-182333/release-manifest.json');

describe('checkpoint projection validation', () => {
  it('accepts the recorded dual-core capture', () => {
    expect(() => validateRelease(release, checkpoint, manifest)).not.toThrow();
  });
  it.each([
    ['duplicate endpoint', data => { data.endpoints.push(data.endpoints[0]); }],
    ['duplicate address', data => { data.endpoints[1].ip = data.endpoints[0].ip; }],
    ['invalid address', data => { data.endpoints[0].ip = '999.1.2.3'; }],
    ['unknown segment', data => { data.endpoints[0].segment = 999; }],
    ['duplicate node', data => { data.nodes[1] = data.nodes[0]; }],
    ['unknown link', data => { data.links[0].to = 'missing'; }],
    ['reused port', data => { data.links[1] = data.links[0]; }],
    ['duplicate pair', data => { data.ping.rows[1] = data.ping.rows[0]; }],
    ['unknown source', data => { data.ping.rows[0].source = 'missing'; }],
    ['missing pair', data => { data.ping.rows.pop(); }],
    ['negative count', data => { data.ping.rows[0].received = -1; }],
    ['excess replies', data => { data.ping.rows[0].received = 5; }],
    ['fractional replies', data => { data.ping.rows[0].received = 1.5; }],
    ['incomplete command', data => { data.ping.rows[0].sent = 0; }],
    ['contradictory verdict', data => {
      const row = data.ping.rows[0];
      row.observed = row.received > 0 ? 'deny' : 'allow';
    }],
    ['unrecognized verdict', data => { data.ping.rows[0].expected = 'pass'; }],
    ['incorrect match count', data => { data.ping.matched--; }],
  ])('rejects %s', (_name, mutate) => {
    const candidate = structuredClone(release);
    mutate(candidate);
    expect(() => validateRelease(candidate, checkpoint, manifest)).toThrow('Invalid remediation release');
  });
  it('rejects a manifest for another iteration', () => {
    expect(() => validateRelease(release, checkpoint, { ...manifest, iteration: 99 })).toThrow('identity');
  });
});
