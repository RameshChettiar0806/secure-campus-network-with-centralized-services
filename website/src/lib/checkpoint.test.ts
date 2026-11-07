import { describe, expect, it } from 'vitest';
import { buildScenarios, deviceLabelsFor, flowFor, resolveCheckpointPing, type Capture } from './checkpoint';

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

  it('uses captured physical links and stops blocked requests before their destination', () => {
    const endpoints = new Map(capture.endpoints.map(endpoint => [endpoint.name, endpoint]));
    const key = (a: string, b: string) => [a, b].sort().join(':');
    const links = new Set(capture.links.map(link => key(link.from, link.to)));
    const invalid = capture.ping.rows.filter(row => {
      const flow = flowFor(capture, endpoints.get(row.source)!, endpoints.get(row.target)!, row.expected);
      return flow.path[0] !== row.source || flow.route.at(-1) !== row.target ||
        flow.route.slice(1).some((id, index) => !links.has(key(flow.route[index], id))) ||
        flow.path.at(-1) !== (row.expected === 'allow' ? row.target : row.source === 'SRV-EXTERNAL' ? 'R2-EXTERNAL' : 'SW1-CORE');
    });
    expect(invalid).toEqual([]);
  });

  it('gives every physical device a unique display name', () => {
    const labels = deviceLabelsFor(capture.endpoints);
    expect(capture.nodes.filter(node => !labels.has(node.name))).toEqual([]);
    expect(new Set(labels.values()).size).toBe(capture.nodes.length);
    expect(labels.get('SRV-CAMPUS')).toBe('Campus Services Server');
    expect(labels.get('SW5-CORE')).toBe('Standby Core Switch');
  });

  it('matches the submission PC names at each physical access port', () => {
    const labels = deviceLabelsFor(capture.endpoints);
    const endpointLinks = capture.links.filter(link => link.from.startsWith('PC'));
    expect(endpointLinks).toHaveLength(50);
    for (const link of endpointLinks) {
      const port = Number(link.peer.split('/').at(-1));
      const expected = link.to === 'SW4-STUDENTS' ? `PC${port - 1}`
        : link.to === 'SW3-FACULTY' ? `PC${port + 19}`
        : port === 1 ? 'PC49-MGMT' : `PC${port + 36}`;
      expect(labels.get(link.from)).toBe(expected);
    }
  });

  it('resolves captured commands using the chosen source and rejects unavailable or invalid commands', () => {
    const student = capture.endpoints.find(endpoint => endpoint.name === 'PC0')!;
    const external = capture.endpoints.find(endpoint => endpoint.segment === 'External')!;
    expect(resolveCheckpointPing(capture, student.name, `ping ${external.ip}`).record?.observed).toBe('allow');
    expect(resolveCheckpointPing(capture, external.name, `ping ${student.ip}`).record?.observed).toBe('deny');
    expect(resolveCheckpointPing(capture, student.name, `ping ${student.ip}`).error).toBeTruthy();
    expect(resolveCheckpointPing(capture, student.name, 'ping 1.2.3.4').error).toBeTruthy();
    expect(resolveCheckpointPing(capture, student.name, `ping ${external.ip} -t`).error).toBeTruthy();
  });
});
