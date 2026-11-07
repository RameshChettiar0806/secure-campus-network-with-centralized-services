import { mkdir, readFile, writeFile, rm } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { dirname, resolve, relative, isAbsolute } from 'node:path';
import { fileURLToPath } from 'node:url';
import { checkSourceIdentity } from './source-identity.mjs';
import { validateRelease } from './validate-release.mjs';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const publicRoot = resolve(root, 'website/public');
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
let currentHash = null;
try { currentHash = hash(await readFile(resolve(root, 'Secure_Campus_Network_Submission.pkt'))); }
catch (error) { if (error.code !== 'ENOENT') throw error; }
const requireCurrent = process.argv.includes('--require-current-submission');
const releasePath = 'data/audit-release.json';
const remediationPath = 'evidence/AUDIT-REMEDIATION-20261105-182333';
const releaseBytes = await readFile(resolve(root, releasePath));
const release = JSON.parse(releaseBytes);
const manifest = JSON.parse(await readFile(resolve(root, remediationPath, 'release-manifest.json'), 'utf8'));
const checkpoint = JSON.parse(await readFile(resolve(root, remediationPath, 'verified-submission.json'), 'utf8'));
if (manifest.sha256[releasePath] !== hash(releaseBytes)) {
  throw new Error('The remediation release does not match the verified checkpoint');
}
validateRelease(release, checkpoint, manifest);
const readCheckpointEvidence = async name => {
  const path = `${remediationPath}/iteration${checkpoint.iteration}-${name}.json`;
  const bytes = await readFile(resolve(root, path));
  if (checkpoint.evidence[path] !== hash(bytes)) throw new Error(`Evidence hash mismatch: ${path}`);
  return JSON.parse(bytes);
};
const [regression, failover] = await Promise.all([
  readCheckpointEvidence('regression-summary'),
  readCheckpointEvidence('core-failover'),
]);
const checks = [
  ['Campus reachability', regression.campus],
  ['External reachability', regression.external],
  ['Campus portal (HTTP)', regression.http],
  ['DNS resolution', regression.dns],
  ['Gateway reachability', regression.gateways],
  ['Authorized SSH', regression.ssh],
  ['Unauthorized SSH blocked', regression.sshDenied],
].map(([name, { passed, total }]) => ({ name, passed, total }));
const outages = Object.entries(failover).map(([core, run]) => ({
  core,
  campusClients: run.campusClients,
  externalClients: run.externalClients,
  dhcpRenewals: run.dhcpRenewals,
  isolationPassed: run.isolationPassed,
  firstRepliesSeconds: run.failureRecovery.firstSuccessfulProbeBatchSeconds,
}));
const remediationSourceCheck = {
  ...checkSourceIdentity(release.submissionSha256, manifest.submissionSha256, currentHash, requireCurrent),
  verification: { checks, outages },
};
// Remove obsolete Version 01 browser assets after validating the retained capture.
await mkdir(publicRoot, { recursive: true });
for (const name of ['evidence', 'configs', 'downloads', 'data/pings']) {
  const target = resolve(publicRoot, name);
  const rel = relative(publicRoot, target);
  if (rel.startsWith('..') || isAbsolute(rel) || !rel) throw new Error('Unsafe generated asset directory');
  await rm(target, { recursive: true, force: true });
}
await mkdir(resolve(root, 'website/src/data'), { recursive: true });
await writeFile(resolve(root, 'website/src/data/source-check.json'), JSON.stringify({ checkedAt: new Date().toISOString(), remediation: remediationSourceCheck }, null, 2) + '\n');
console.log(`Prepared ${release.nodes.length} devices, ${release.links.length} links and ${release.ping.total} verified endpoint pings.`);
console.log(remediationSourceCheck.matchesRecordedSubmission
  ? 'The release matches the local Packet Tracer file.'
  : 'The release is a recorded checkpoint. Its local Packet Tracer file is absent or differs.');
