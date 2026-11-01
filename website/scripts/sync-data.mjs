import { copyFile, mkdir, readFile, realpath, writeFile, rm } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { dirname, resolve, relative, isAbsolute } from 'node:path';
import { fileURLToPath } from 'node:url';
import { checkSourceIdentity } from './source-identity.mjs';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const publicRoot = resolve(root, 'website/public');
const snapshotPath = resolve(root, 'data/network-snapshot.v2.json');
const matrixPath = resolve(root, 'data/ping-matrix.v2.json');
const snapshot = JSON.parse(await readFile(snapshotPath, 'utf8'));
const matrix = JSON.parse(await readFile(matrixPath, 'utf8'));
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
let currentHash = null;
try { currentHash = hash(await readFile(resolve(root, snapshot.submissionFile))); }
catch (error) { if (error.code !== 'ENOENT') throw error; }
const recordedHash = snapshot.submissionSha256;
const sourceCheck = checkSourceIdentity(recordedHash, matrix.submissionSha256, currentHash, process.argv.includes('--require-current-submission'));
if (!sourceCheck.matchesRecordedSubmission) console.warn('Source notice: the local .pkt is missing or changed since verification. Starting the website with the recorded snapshot and ping results; the current .pkt has not been revalidated.');
const endpoints = snapshot.devices.filter(d => ['PC-PT', 'Server-PT'].includes(d.model));
const perSource = snapshot.devices.length - 1 + snapshot.vlans.length - 1;
const expectedCount = endpoints.length * perSource;
if (matrix.schemaVersion !== 2 || matrix.cases !== expectedCount || matrix.passed !== expectedCount || matrix.records.length !== expectedCount || matrix.mismatches.length || !matrix.submissionUnchanged || !matrix.iosConfigurationsUnchanged) throw new Error('Expanded ICMP capture is incomplete');
const addresses = Object.values(matrix.addressContext);
if (addresses.length !== endpoints.length || new Set(addresses).size !== addresses.length) throw new Error('Invalid matrix address context');
for (const d of endpoints) {
  const p = d.interfaces.find(p => p.observedLease || p.ipv4);
  if (matrix.addressContext[d.id] !== (p.observedLease?.ipv4 ?? p.ipv4)) throw new Error(`Snapshot/matrix address mismatch: ${d.id}`);
}
const assets = new Map();
for (const asset of [...snapshot.evidence, ...matrix.evidence]) {
  if (!/^(evidence\/[\w./-]+\.(json|png)|configs\/[\w-]+\.txt)$/.test(asset.path) || asset.path.includes('..')) throw new Error(`Unsafe evidence path: ${asset.path}`);
  if (assets.has(asset.path)) {
    if (assets.get(asset.path).sha256 !== asset.sha256) throw new Error('Conflicting evidence hashes');
    continue;
  }
  const source = await realpath(resolve(root, asset.path));
  const rel = relative(root, source);
  if (rel.startsWith('..') || isAbsolute(rel)) throw new Error('Evidence escapes the project');
  const bytes = await readFile(source);
  if (hash(bytes) !== asset.sha256.toLowerCase()) throw new Error(`Evidence hash mismatch: ${asset.path}`);
  const text = asset.path.endsWith('.png') ? '' : bytes.toString('utf8');
  if (/CampusDemo@|\$1\$|(?:enable|username .+) secret \d|password 7 /i.test(text)) throw new Error(`Unsanitized credential in ${asset.path}`);
  assets.set(asset.path, { source, sha256: asset.sha256, data: asset.path.endsWith('.json') ? JSON.parse(text) : null });
}
const pairs = new Set();
const sources = {};
for (const record of matrix.records) {
  const evidence = assets.get(record.evidenceRef)?.data;
  const actual = evidence?.records?.find(r => r.id === record.id);
  if (!actual || evidence.submissionSha256 !== recordedHash || !record.passed || !actual.passed) throw new Error('Missing verified ping command');
  for (const key of ['id','testId','sourceDeviceId','sourceIp','destinationDeviceId','destinationIp','expected','sent','received','output','counterScope']) {
    if (record[key] !== actual[key]) throw new Error(`Ping evidence differs: ${record.id} ${key}`);
  }
  if (JSON.stringify(record.counterDelta) !== JSON.stringify(actual.counterDelta)) throw new Error('Ping ACL evidence differs');
  if (record.sent !== 4 || record.received !== (record.expected === 'allow' ? 4 : 0) || !record.output.includes(`ping ${record.destinationIp}`) || !record.output.includes(`Sent = ${record.sent}, Received = ${record.received}`)) throw new Error('Invalid ping packet counts/output');
  if (record.expected === 'deny' && !Object.entries(record.counterDelta).some(([rule, count]) => rule.includes(' deny ') && count >= 4)) throw new Error('Denied ping lacks a matching ACL counter observation');
  if (record.sourceIp !== matrix.addressContext[record.sourceDeviceId]) throw new Error('Invalid source context');
  const target = snapshot.devices.find(d => d.id === record.destinationDeviceId);
  const targetAddresses = target?.interfaces.flatMap(p => [p.ipv4, p.observedLease?.ipv4].filter(Boolean));
  if (!targetAddresses?.includes(record.destinationIp) || record.sourceDeviceId === record.destinationDeviceId) throw new Error('Invalid destination context');
  const key = `${record.sourceDeviceId}:${record.destinationIp}`;
  if (pairs.has(key)) throw new Error('Duplicate ping pair');
  pairs.add(key);
  (sources[record.sourceDeviceId] ??= []).push(record);
}
for (const source of endpoints) {
  const rows = sources[source.id] ?? [];
  const targets = snapshot.devices.filter(d => d.id !== source.id);
  if (rows.length !== perSource || targets.some(d => !rows.some(r => r.destinationDeviceId === d.id)) || snapshot.vlans.some(v => !rows.some(r => r.destinationDeviceId === 'r1' && r.destinationIp === v.gateway))) throw new Error(`Incomplete coverage: ${source.id}`);
}
// Replace only generated, allowlisted website assets after validating sources.
await mkdir(publicRoot, { recursive: true });
for (const name of ['evidence', 'configs', 'downloads', 'data/pings']) {
  const target = resolve(publicRoot, name);
  const rel = relative(publicRoot, target);
  if (rel.startsWith('..') || isAbsolute(rel) || !rel) throw new Error('Unsafe generated asset directory');
  await rm(target, { recursive: true, force: true });
}
for (const [path, asset] of assets) {
  const target = resolve(publicRoot, path);
  await mkdir(dirname(target), { recursive: true });
  await copyFile(asset.source, target);
}
const index = { schemaVersion: 2, runId: matrix.runId, submissionSha256: recordedHash, capturedAt: matrix.completedAt, cases: matrix.cases, passed: matrix.passed, perSource, sources: {} };
for (const [id, records] of Object.entries(sources)) {
  const path = `data/pings/${id}.json`;
  const target = resolve(publicRoot, path);
  await mkdir(dirname(target), { recursive: true });
  await writeFile(target, JSON.stringify({ schemaVersion: 2, sourceDeviceId: id, submissionSha256: recordedHash, addressContext: matrix.addressContext, records }));
  index.sources[id] = path;
}
await writeFile(resolve(root, 'website/src/data/ping-index.json'), JSON.stringify(index, null, 2) + '\n');
await writeFile(resolve(root, 'website/src/data/source-check.json'), JSON.stringify({ checkedAt: new Date().toISOString(), ...sourceCheck }, null, 2) + '\n');
console.log(`Prepared ${snapshot.devices.length} devices, ${snapshot.links.length} links, ${matrix.cases} verified pings in ${endpoints.length} source files, and ${assets.size} hash-verified evidence assets.`);
