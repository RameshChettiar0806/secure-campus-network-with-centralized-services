/** Recorded data must agree internally; a later .pkt save is a separate audit. */
export function checkSourceIdentity(recordedHash, matrixHash, currentHash, strict = false) {
  if (!/^[a-f0-9]{64}$/.test(recordedHash) || recordedHash !== matrixHash) {
    throw new Error('The network snapshot and ping matrix refer to different submissions');
  }
  const matchesRecordedSubmission = currentHash === recordedHash;
  if (strict && !matchesRecordedSubmission) {
    throw new Error('Current .pkt is missing or differs from the recorded submission. Revalidate it before claiming current-file verification.');
  }
  return { recordedSubmissionSha256: recordedHash, currentSubmissionSha256: currentHash, matchesRecordedSubmission };
}
