import { describe, expect, it } from 'vitest';
import { checkSourceIdentity } from './source-identity.mjs';

const recorded = 'a'.repeat(64);
const changed = 'b'.repeat(64);
describe('recorded viewer startup and current-file audit', () => {
  it('starts the viewer with recorded data when a later .pkt differs', () => {
    expect(checkSourceIdentity(recorded, recorded, changed)).toEqual({ recordedSubmissionSha256: recorded, currentSubmissionSha256: changed, matchesRecordedSubmission: false });
  });
  it('starts a standalone viewer when the local .pkt is absent', () => {
    expect(checkSourceIdentity(recorded, recorded, null).matchesRecordedSubmission).toBe(false);
  });
  it('still rejects disagreement between the snapshot and its ping evidence', () => {
    expect(() => checkSourceIdentity(recorded, changed, changed)).toThrow('different submissions');
  });
  it('keeps strict source verification available', () => {
    expect(() => checkSourceIdentity(recorded, recorded, changed, true)).toThrow('Revalidate');
    expect(() => checkSourceIdentity(recorded, recorded, null, true)).toThrow('Revalidate');
    expect(checkSourceIdentity(recorded, recorded, recorded, true).matchesRecordedSubmission).toBe(true);
  });
});
