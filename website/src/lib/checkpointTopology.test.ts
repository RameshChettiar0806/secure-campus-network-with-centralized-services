import { describe, expect, it } from 'vitest';
import type { Capture } from './checkpoint';
import { connectionFor, deviceLessonFor, topologyFor } from './checkpointTopology';

const files = import.meta.glob<Capture>('../../../data/audit-release.json', { eager: true, import: 'default' });
const capture = Object.values(files)[0];

describe.skipIf(!capture)('Version 02 topology teaching views', () => {
  it('preserves the compact overview and shows every captured device and link in the complete view', () => {
    const simple = topologyFor(capture, 'simplified');
    const complete = topologyFor(capture, 'complete');
    expect(simple.nodes).toHaveLength(11);
    expect(simple.links).toHaveLength(15);
    expect(simple.nodes.some(node => node.name === 'PC8-MGMT')).toBe(true);
    expect(complete.nodes).toHaveLength(60);
    expect(complete.nodes.filter(node => node.model === 'PC-PT')).toHaveLength(50);
    expect(complete.links).toEqual(capture.links);
    expect(complete.links).toHaveLength(64);
    complete.nodes.forEach((node, index) => {
      expect(node.name).toBe(capture.nodes[index].name);
      expect(node.position.x / 1.6).toBeCloseTo(capture.nodes[index].x);
      expect(node.position.y / 1.6).toBeCloseTo(capture.nodes[index].y);
    });
  });

  it('distinguishes endpoint VLANs, exact trunk allowlists and the three routed transit networks', () => {
    const connection = (a: string, b: string) => connectionFor(capture, capture.links.find(link =>
      [link.from, link.to].includes(a) && [link.from, link.to].includes(b))!);
    expect(connection('PC8-MGMT', 'SW2-ACCESS')).toMatchObject({ kind: 'access', title: 'Access · VLAN 99' });
    expect(connection('SW1-CORE', 'SW2-ACCESS').detail).toBe('Allowed VLANs 10, 99 · native VLAN 999');
    expect(connection('SW5-CORE', 'SW6-SERVICES').detail).toBe('Allowed VLANs 40, 99 · native VLAN 999');
    expect(connection('SW1-CORE', 'SW5-CORE').detail).toBe('Allowed VLANs 10, 20, 30, 40, 99 · native VLAN 999');
    expect(connection('R1-CAMPUS', 'SW1-CORE').detail).toContain('192.168.10.160/30');
    expect(connection('R1-CAMPUS', 'SW5-CORE').detail).toContain('192.168.10.164/30');
    expect(connection('R1-CAMPUS', 'R2-EXTERNAL').detail).toContain('198.51.100.0/30');
    expect(connection('R2-EXTERNAL', 'SRV-EXTERNAL').title).toBe('External LAN');
  });

  it('covers every device with a lesson and retains the distinction between a physical SVI and a virtual gateway', () => {
    for (const node of capture.nodes) {
      const lesson = deviceLessonFor(capture, node.name)!;
      expect(Object.values(lesson).join(' ')).not.toMatch(/undefined/);
      expect(lesson.what.length).toBeGreaterThan(20);
      expect(lesson.purpose.length).toBeGreaterThan(20);
      expect(lesson.forwarding.length).toBeGreaterThan(20);
      expect(lesson.failure.length).toBeGreaterThan(20);
      expect(lesson.facts.length).toBeGreaterThan(0);
      expect(lesson.question).toBeTruthy();
      expect(lesson.answer).toBeTruthy();
    }
    const management = deviceLessonFor(capture, 'PC8-MGMT')!;
    expect(management.facts).toContainEqual({ label: 'Default gateway', value: '192.168.10.145' });
    const standby = deviceLessonFor(capture, 'SW5-CORE')!;
    expect(standby.facts).toContainEqual({ label: 'Management SVI · VLAN 99', value: '192.168.10.151' });
    expect(standby.facts.find(fact => fact.label === 'Shared HSRP gateways')?.value).toContain('VLAN 99: 192.168.10.145');
    expect(deviceLessonFor(capture, 'SW2-ACCESS')!.facts).toContainEqual({ label: 'Attached endpoints', value: '12' });
    expect(deviceLessonFor(capture, 'missing')).toBeUndefined();
  });
});
