import { isIPv4 } from 'node:net';

/** Validate the public checkpoint projection before generating browser assets. */
export function validateRelease(release, checkpoint, manifest) {
  const fail = message => { throw new Error(`Invalid remediation release: ${message}`); };
  if (!Array.isArray(release.nodes) || !Array.isArray(release.links) ||
      !Array.isArray(release.endpoints) || !Array.isArray(release.ping?.rows)) {
    fail('missing inventory or ping rows');
  }
  if (release.iteration !== checkpoint.iteration || release.iteration !== manifest.iteration ||
      release.submissionSha256 !== checkpoint.sha256 ||
      release.submissionSha256 !== manifest.submissionSha256 ||
      release.nodes.length !== checkpoint.networkDevices || release.links.length !== checkpoint.links) {
    fail('checkpoint identity or inventory counts differ');
  }
  const names = new Set();
  for (const node of release.nodes) {
    if (typeof node.name !== 'string' || !node.name || names.has(node.name) ||
        !Number.isFinite(node.x) || !Number.isFinite(node.y)) fail('invalid or duplicate node');
    names.add(node.name);
  }
  const ports = new Set();
  for (const link of release.links) {
    if (!names.has(link.from) || !names.has(link.to) || link.from === link.to) fail('unknown or self-linked node');
    for (const [node, port] of [[link.from, link.port], [link.to, link.peer]]) {
      const key = JSON.stringify([node, port]);
      if (typeof port !== 'string' || !port || ports.has(key)) fail('invalid or reused physical port');
      ports.add(key);
    }
  }
  const endpoints = new Set();
  const addresses = new Set();
  for (const endpoint of release.endpoints) {
    if (!names.has(endpoint.name) || endpoints.has(endpoint.name) ||
        typeof endpoint.ip !== 'string' || !isIPv4(endpoint.ip) || endpoint.ip === '0.0.0.0' ||
        addresses.has(endpoint.ip) || ![10, 20, 30, 40, 99, 'External'].includes(endpoint.segment)) {
      fail('invalid or duplicate endpoint');
    }
    endpoints.add(endpoint.name);
    addresses.add(endpoint.ip);
  }
  const expectedCases = endpoints.size * (endpoints.size - 1);
  if (endpoints.size !== checkpoint.endpoints || endpoints.size < 2 ||
      release.ping.rows.length !== expectedCases || release.ping.total !== expectedCases ||
      manifest.endpointCases !== expectedCases) fail('incomplete endpoint coverage');
  const pairs = new Set();
  let matched = 0;
  for (const row of release.ping.rows) {
    const pair = JSON.stringify([row.source, row.target]);
    if (!endpoints.has(row.source) || !endpoints.has(row.target) ||
        row.source === row.target || pairs.has(pair)) fail('invalid or duplicate ping pair');
    pairs.add(pair);
    if (!['allow', 'deny'].includes(row.expected) || !['allow', 'deny'].includes(row.observed) ||
        row.sent !== 4 || !Number.isInteger(row.received) || row.received < 0 || row.received > row.sent ||
        row.observed !== (row.received > 0 ? 'allow' : 'deny')) fail('invalid ping outcome or packet counts');
    if (row.expected === row.observed) matched++;
  }
  if (release.ping.matched !== matched || manifest.policyMatches !== matched) fail('policy match count differs');
}
