# Version 01 — scope and iterations

Version 01 is the original Campus Atlas explorer at `#version-01`. Its frozen November 2, 2026 capture demonstrates a segmented campus with centralized DHCP, DNS and HTTP plus a small OSPF/PAT external branch.

The objective is to let 50 PCs use shared services while Administration, Faculty and Students have separate broadcast domains and directional routed permissions. An evidence viewer explains the topology, addressing and packet outcomes without requiring a running simulator.

## Iteration record

| Stage | Result | Source |
| --- | --- | --- |
| Campus baseline and scale-up | 50 PCs, departmental VLSM, centralized services and router-on-a-stick | [Scale design](../../../SCALE_50_DESIGN.md), [acceptance](../../../SCALE_50_ACCEPTANCE.md) |
| External branch | R2 and an external HTTP server; OSPF area 0 and PAT on R1 | [Extension acceptance](../../../OSPF_PAT_ACCEPTANCE.md) |
| Version 01 capture | 58 devices, 57 links, 52 endpoint sources and 62 destinations per source | [Website acceptance](../../../WEBSITE_V3_ACCEPTANCE.md) |
| Later backup-uplink milestone | Three extra links and Rapid PVST+ failover; separate from the frozen website snapshot | [Fault-tolerance acceptance](../../../FAULT_TOLERANCE_ACCEPTANCE.md) |

The 58 devices comprise 50 PCs, two servers, four 2960 access/core switches and two routers. PC8-MGMT belongs to the original Administration VLAN and uses a static address; 49 PCs obtain DHCP leases.

## Software and evidence

The viewer is a static React/TypeScript application built with Vite, using React Flow for topology diagrams and Vitest for tests. Python scripts communicate with the local Packet Tracer bridge to collect evidence. JSON records and sanitized IOS exports provide reproducible inputs. The browser replays captured commands; it does not send ICMP probes.

Primary inputs are [network-snapshot.v3.json](../../../data/network-snapshot.v3.json), [ping-matrix.v3.json](../../../data/ping-matrix.v3.json), [policy-matrix.v3.json](../../../data/policy-matrix.v3.json) and [ospf-pat-extension.v3.json](../../../data/ospf-pat-extension.v3.json).

Continue with [architecture](network-architecture.md), [access controls](access-controls.md) and [verification](verification.md). [Version index](../README.md)
