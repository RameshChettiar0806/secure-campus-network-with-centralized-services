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

All website sections now use `data/network-snapshot.v3.json` and `data/ping-matrix.v3.json`, captured from the current 58-device, 57-link submission. There are 52 endpoint sources and 62 measured destinations per source, for 3,224 ping cases. The OSPF/PAT walkthrough uses `data/ospf-pat-extension.v3.json`; policy matrix cells use `data/policy-matrix.v3.json` and point to actual recorded commands.

Use `.\run.ps1 verify-source` to require the current submission to match the active capture SHA-256. Current sanitized configurations have `-CURRENT.txt` filenames. The v2 data remains historical on disk and is not loaded by the website. See [current website verification](../WEBSITE_V3_ACCEPTANCE.md).
