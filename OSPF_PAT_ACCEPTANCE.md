# OSPF / PAT extension acceptance

Verified after reopening in Cisco Packet Tracer 9.0.1 on 2 November 2026 (IST).

The existing submission now has 58 network devices and 57 links. All 55 original campus links were retained; one router, one server and two Ethernet links were added. Campus subnets and switch configurations are retained.

| Check | Result |
| --- | --- |
| Campus gateway / central server ping | 50/50 clients passed each check |
| Campus DNS and HTTP | 50/50 clients passed each check |
| Department policy | 4 allowed and 5 blocked cases matched policy |
| External ICMP and hostname HTTP | 50/50 clients passed each check |
| PAT address sharing | 50 inside-local addresses observed sharing 198.51.100.1 |
| OSPF | FULL adjacency; 203.0.113.0/24 learned dynamically |
| External access restrictions | Other external host and unsolicited inbound ping blocked |
| Failure and restoration | PAT and OSPF dependency demonstrated; both restored |
| Persistence and management | DHCP renewed in all three client VLANs; 5 allowed and 3 blocked SSH checks passed |

The four campus service groups account for 200 client checks; external ping and HTTP add 100 client checks. The 4 permitted/5 denied campus cases and management tests are additional. These checks do not recapture the historical 2,958-case matrix.

Saved submission SHA-256: `b3b7892fe2d2e80330a2c6b80df6b2cfaf1032d33b3b4ab78f88ca2883b28406`. The hash identifies the saved file reopened for these checks; counters and transient flows can evolve while it runs.

Evidence: `evidence/OSPF-PAT-20261102/`. The manifest `data/ospf-pat-extension.json` lists hash-verified public evidence. `campus-before-ospf-pat.zip` in the evidence directory is the local recovery archive.

The [walkthrough](docs/ospf-pat-extension.md) explains the addressing, CLI sequence and failure checks. The website includes an **OSPF & PAT** tab; its other sections retain the original campus capture.

Scope: simulated external network; single-area OSPF, not multi-area or failover; HTTP and ICMP to one external server; stateless ACLs; same-VLAN traffic bypasses routed ACLs. No throughput claim is made.
