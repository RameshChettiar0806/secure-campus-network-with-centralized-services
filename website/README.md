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

Development normally listens on port 5173 and preview on 4173. Serve the built site over HTTP so the browser can fetch evidence and per-source ping records.

## Where to make changes

| Directory | Responsibility |
| --- | --- |
| `src/app/` | Application shell, navigation, cross-view selection and shared layout styles |
| `src/views/` | Addressing table, detailed policy and lab results screens |
| `src/components/` | Interactive topology, segment guide, ping console, walkthrough, policy matrix and evidence viewer |
| `src/lib/` | Topology layout, routing and ICMP presentation, data validation and unit tests |
| `src/data/` and `src/models/` | Typed snapshot loading and generated data indexes |
| `scripts/` | Synchronize the recorded manifests, verify source identity and prepare browser assets |

The sync step validates the v3 snapshot, ping matrix and allowlisted evidence before dev, build or test. Source changes cancel obsolete fetches. Each source file carries the recorded submission identity and 62 commands. The website checks both before replay and offers retry for load failures.

The November 2 replay uses `data/network-snapshot.v3.json` and `data/ping-matrix.v3.json` from the 58-device, 57-link capture. There are 52 endpoint sources and 62 measured destinations per source, for 3,224 ping cases. The OSPF/PAT walkthrough uses `data/ospf-pat-extension.v3.json`. Policy matrix cells use `data/policy-matrix.v3.json` and point to recorded commands. Configuration downloads for this replay use the matching, hash-verified November 2 exports.

**Version 01** opens the original explorer at `#version-01`. **Version 02** opens by default when the remediation capture is present and can be linked directly at `#version-02`. It shows the verified dual-core topology, descriptive device names, endpoint addresses, and 33 directional scenario types covering 2,652 recorded endpoint ping pairs. Scenario 01 starts with Student → External Server. The visual replay follows an illustrated echo request and its reply or forwarding stop. Use the playback controls or select an individual hop. The measured reply count comes from the saved test record.

Use `.\run.ps1 verify-source` to match the current local submission against the Version 02 capture. [Version 02 capture manifest](../evidence/AUDIT-REMEDIATION-20261105-182333/release-manifest.json), [November 2 website verification](../WEBSITE_V3_ACCEPTANCE.md)

Version 02 also provides a **Topology Guide**, a standalone **Ping Lab**, and a separate **Access Policy** tab. The guide explains VLANs, dual-core gateways and the external branch. The Ping Lab accepts captured endpoint IPs and replays the request, reply or stop on the route map. Select a populated cell in the access-policy matrix to open its representative pair in the lab. Protocol permissions are listed separately from the recorded ICMP outcomes.

The **Topology** tab has two views: **View 01 — Simplified view** retains the compact infrastructure layout; **View 02 — Complete topology** includes all 60 devices and 64 links, using the captured Packet Tracer coordinates with uniform spacing expansion. Select any device on the map or in the device selector to read its purpose, forwarding behavior, failure dependencies, addressing, concepts and learning question. The direct-connections table shows both port names, trunk VLAN allowlists or routed subnets, and clickable neighbors. Selecting a hidden workstation automatically opens the complete view. Interface labels, device focus, fit and a complete-map overview support inspection.

Teaching notes are checked against the [saved Iteration 5 configuration exports](../evidence/AUDIT-REMEDIATION-20261105-182333/iteration5-verified-configs/). Coordinates, physical links and endpoint addresses come from the [Version 02 capture](../data/audit-release.json). Connection highlighting does not claim current STP forwarding or live device health; the recorded source remains unchanged.
