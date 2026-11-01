# Design and Implementation of a Secure Campus Network with Centralized Services

Fifty PCs share a campus portal while Administration, Faculty and Students occupy separate VLANs. Cisco Packet Tracer runs the network. The companion website lets a presenter inspect the topology, replay captured ping results and explain each forwarding decision.

## Table of contents

| Guide | What you’ll find |
| --- | --- |
| [Run the project](#run-the-project) | Start the website and open the Packet Tracer simulation. |
| [Topology and forwarding](docs/topology.md) | Device roles, physical links, VLAN trunks and router-on-a-stick forwarding. |
| [Addressing table](docs/addressing-table.md) | Subnets, gateways, DHCP ranges and the captured IP address of each numbered interface. |
| [Centralized services](docs/centralized-services.md) | DHCP relay, DNS resolution and HTTP delivery. |
| [Access policy](docs/access-policy.md) | Departmental ICMP permissions, return traffic and SSH management. |
| [Ping analysis](PING_ANALYSIS.md) | Recorded outcomes for each source and interpretation of ACL counters. |
| [Tests conducted](docs/tests-conducted.md) | A01–A10 acceptance results, P02 ping coverage, evidence and troubleshooting. |
| [Lab walkthroughs](docs/lab-walkthroughs.md) | Website demo sequence, three printable campus labs and related course exercises. |
| [Project layout](#project-layout-and-maintenance) | Project files, evidence, build and test commands. |

## Run the project

**Present the website.** From the project directory in PowerShell, build and serve the website locally. Development, test and build commands need Node 24 and npm. The helper restores missing packages using the lockfile and the local npm cache, downloading any missing packages.

```powershell
cd .\website
.\run.ps1 build
.\run.ps1 preview
```

Open <http://127.0.0.1:4173/> and stop the server with Ctrl+C. To edit the website, run `.\run.ps1 dev` from the same folder and open the Local URL (normally port 5173). Once built, preview can also serve the production build using Python 3 if JavaScript dependencies are unavailable.

**Live simulator (local files).** Packet Tracer files, lab credentials and private recovery archives are excluded from this repository. If you have the local `Secure_Campus_Network_Submission.pkt`, open it in **Packet Tracer 9.0.1**. Allow about a minute for trunks and DHCP after reopening. From a client’s **Desktop → Web Browser**, open `http://portal.campus.test`. This hostname belongs to the simulated campus. The localhost address above opens the companion website on your computer. The companion website can replay the recorded evidence without the simulation file.

**Evidence boundary.** The website uses the October 31, 2026 capture. The current submission has a different SHA-256 from the recorded file. The documented results describe the captured network. Use `.\run.ps1 verify-source` inside `website` to compare the current file with that capture.

## Project layout and maintenance

| Location | Purpose |
| --- | --- |
| Local `Secure_Campus_Network_Submission.pkt` and [configs](configs/) | Active simulation (local only) and versioned sanitized IOS configuration exports. Lab credentials stay in the local credential file. |
| [data](data/) | Versioned network snapshot, ping matrix, addressing and evidence references. The website consumes v2. |
| [evidence](evidence/) | Current capture, leases, images and acceptance records. Simulation recovery ZIPs remain local. |
| Local `archive/earlier-campus-work.zip` | Earlier captures, retired scripts, design drafts and QA screenshots in their original relative paths. Contains private lab material and is excluded from Git. Extract into a separate folder to inspect. |
| [scripts](scripts/) | Packet Tracer bridge, build, capture and validation utilities. Live capture requires a connected simulator. |
| [website](website/) | Local React/TypeScript viewer, Vite build, React Flow topology and Vitest suite. |
| [output/pdf](output/pdf/) | Printable campus walkthroughs. |

From `website`, run `.\run.ps1 test` for the checks or `.\run.ps1 build` followed by `.\run.ps1 preview` for the production build. The sync step checks snapshot identity, coverage, command output and evidence hashes. It stages allowlisted assets under `public/` and generates one ping file per source. Edit source data or components rather than generated assets. See the [website maintenance guide](website/README.md).
