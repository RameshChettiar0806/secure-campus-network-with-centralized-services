import { describe, expect, it } from 'vitest';
import { buildScenarios, deviceLabelsFor, flowFor, type Capture } from './checkpoint';

const files = import.meta.glob<Capture>('../../../data/audit-release.json', { eager: true, import: 'default' });
const capture = Object.values(files)[0];

describe.skipIf(!capture)('Version 02 scenario coverage', () => {
  it('assigns every recorded directed pair to one of the 33 scenarios', () => {
    const scenarios = buildScenarios(capture);
    expect(scenarios).toHaveLength(33);
    expect(scenarios[0]).toMatchObject({ number: 1, name: 'Student → External Server' });
    expect(scenarios[0].rows).toHaveLength(20);
    const pairs = scenarios.flatMap(scenario => scenario.rows.map(row => [row.source, row.target].join(':')));
    expect(pairs).toHaveLength(2652);
    expect(new Set(pairs).size).toBe(2652);
    expect(scenarios.find(scenario => scenario.from === 'External' && scenario.to === 30)?.rows.every(row => row.received === 0)).toBe(true);
  });

  it('keeps the access switch in both legs of a routed management-to-administration path', () => {
    const source = capture.endpoints.find(endpoint => endpoint.segment === 99)!;
    const target = capture.endpoints.find(endpoint => endpoint.segment === 10)!;
    const { path } = flowFor(capture, source, target, 'allow');
    expect(path).toEqual([source.name, 'SW2-ACCESS', 'SW1-CORE', 'SW2-ACCESS', target.name]);
  });

  it('gives every physical device a unique display name', () => {
    const labels = deviceLabelsFor(capture.endpoints);
    expect(capture.nodes.filter(node => !labels.has(node.name))).toEqual([]);
    expect(new Set(labels.values()).size).toBe(capture.nodes.length);
    expect(labels.get('SRV-CAMPUS')).toBe('Campus Services Server');
    expect(labels.get('SW5-CORE')).toBe('Standby Core Switch');
  });
});
