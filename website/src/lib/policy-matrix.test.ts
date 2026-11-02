import { expect, it } from 'vitest';
import matrix from '../../../data/ping-matrix.v3.json';
import policy from '../../../data/policy-matrix.v3.json';

it('ties every policy matrix cell to a measured command in the current submission', () => {
  expect(policy.submissionSha256).toBe(matrix.submissionSha256);
  expect(policy.examples).toHaveLength(23);
  for (const example of policy.examples) {
    const record=matrix.records.find(r => r.id===example.recordId)!;
    expect(record.sourceDeviceId).toBe(example.source);
    expect(record.destinationDeviceId).toBe(example.target);
    expect(record.passed).toBe(true);
    expect(example.verdict==='Block' || example.verdict==='No route').toBe(record.expected==='deny');
  }
});

it('includes permitted client PAT and distinct external-to-private routing failures', () => {
  expect(policy.examples.find(e => e.fromSegment==='students' && e.toSegment==='external')?.verdict).toBe('Allow');
  expect(policy.examples.find(e => e.fromSegment==='external' && e.toSegment==='students')?.verdict).toBe('No route');
  expect(policy.examples.find(e => e.fromSegment==='services' && e.toSegment==='external')?.verdict).toBe('Block');
});
