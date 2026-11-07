# Campus Atlas website

The [project guide](../README.md) covers the network design, demonstration sequence, course materials and printable walkthroughs.

## Local commands

For a presentation, run `.\run.ps1 build` followed by `.\run.ps1 preview` and open <http://127.0.0.1:4173/>. The generated `dist/` can be served offline with Python 3 and is excluded from Git. For development, use PowerShell in this directory with Node.js 24 and npm. The launcher installs the locked dependencies on first use.

```powershell
.\run.ps1 dev
```

Open the Local URL printed by Vite. Stop the server with Ctrl+C. To run checks and serve the production build, use the following in order.

```powershell
.\run.ps1 test
.\run.ps1 build
.\run.ps1 preview
```

Development normally listens on port 5173 and preview on 4173. Serve the built site over HTTP for browser module loading.

## Where to make changes

| Directory | Responsibility |
| --- | --- |
| `src/app/` | Application shell and theme preference |
| `src/views/` | Campus overview, addressing, topology guide, Ping Lab and access policy |
| `src/components/` | Interactive topology, device symbols and recorded packet scenarios |
| `src/lib/` | Topology layout, routing and ICMP presentation, data validation and unit tests |
| `src/data/` | Generated checkpoint identity |
| `scripts/` | Synchronize the recorded manifests, verify source identity and prepare browser assets |

The sync step validates the retained dual-core capture, checkpoint identity and verification evidence before dev, build or test. It removes obsolete original-explorer browser assets. Historical project captures remain outside the website.

The website serves only the dual-core campus experience previously called Version 02. There is no edition selector or original explorer; older edition hashes open the same campus website. It includes all 60 devices and 64 links, the submission's PC names, and 33 directional scenario types covering 2,652 recorded endpoint ping pairs. Scenario 01 starts with Student → External Server. Playback controls show each request, reply or forwarding stop using the saved test record.

Use `.\run.ps1 verify-source` to match the current local submission against the Version 02 capture. [Version 02 capture manifest](../evidence/AUDIT-REMEDIATION-20261105-182333/release-manifest.json)

Version 02 also provides a **Topology Guide**, a standalone **Ping Lab**, and a separate **Access Policy** tab. The guide explains VLANs, dual-core gateways and the external branch. The Ping Lab accepts captured endpoint IPs and replays the request, reply or stop on the route map. Select a populated cell in the access-policy matrix to open its representative pair in the lab. Protocol permissions are listed separately from the recorded ICMP outcomes.

The **Topology** tab has two views: **View 01 — Simplified view** retains the compact infrastructure layout; **View 02 — Complete topology** includes all 60 devices and 64 links, using the captured Packet Tracer coordinates with uniform spacing expansion. Select any device on the map or in the device selector to read its purpose, forwarding behavior, failure dependencies, addressing, concepts and learning question. The direct-connections table shows both port names, trunk VLAN allowlists or routed subnets, and clickable neighbors. Selecting a hidden workstation automatically opens the complete view. Interface labels, device focus, fit and a complete-map overview support inspection.

Teaching notes are checked against the [saved Iteration 5 configuration exports](../evidence/AUDIT-REMEDIATION-20261105-182333/iteration5-verified-configs/). Coordinates, physical links and endpoint addresses come from the [Version 02 capture](../data/audit-release.json). Connection highlighting does not claim current STP forwarding or live device health; the recorded source remains unchanged.

## Source validation and historical documentation

The [historical version index](../docs/versions/README.md) preserves earlier project captures for reference; only the dual-core edition is served by this website. See the [codebase review](../docs/CODEBASE_REVIEW.md) for the November 7 refinements.

Before generating browser assets, scripts/validate-release.mjs validates Version 02 node and endpoint identity, physical ports, IP addresses, directed-pair coverage, packet counts and verdict totals. scripts/sync-data.mjs also checks the release hash and the checkpoint identity. The test suite includes malformed-capture cases alongside the existing routing and presentation tests.

From the project root, run `python -m unittest discover -s scripts/tests -v` for offline bridge-client and checkpoint-verifier regressions. Run `python scripts/check_docs.py` to check local links in the maintained documentation set. These commands do not require a connected Packet Tracer session.
