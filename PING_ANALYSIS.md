# Expanded campus ping analysis

Run: PING-20261031. **2,958/2,958 source/address combinations matched the implemented policy.** Actual Packet Tracer commands returned four replies for each of 1,447 allowed pairs and zero replies for each of 1,511 denied pairs.

There are 51 endpoint sources (50 PCs and the server). Each source targets the other 50 endpoints, four switch management addresses, and all four router gateways: `51 × (50 + 4 + 4) = 2,958`. Self-pings are excluded.

The saved submission and IOS configurations remained unchanged. The active [v2 matrix](data/ping-matrix.v2.json), [capture metadata](evidence/PING-20261031/run.json), and [website snapshot](data/network-snapshot.v2.json) share submission SHA-256 `e8a0aa8e0b7411073d4b29cae6a284c439a97f088aebecb9d42d3546d26d9905`.

## Results by source

| Source | Recorded address | Allowed | Denied | Matched |
|---|---|---:|---:|---:|
| PC8-MGMT | 192.168.10.98 | 57 | 1 | 58/58 |
| PC9-ADMIN | 192.168.10.108 | 57 | 1 | 58/58 |
| PC40 | 192.168.10.113 | 57 | 1 | 58/58 |
| PC41 | 192.168.10.111 | 57 | 1 | 58/58 |
| PC42 | 192.168.10.109 | 57 | 1 | 58/58 |
| PC43 | 192.168.10.112 | 57 | 1 | 58/58 |
| PC44 | 192.168.10.114 | 57 | 1 | 58/58 |
| PC45 | 192.168.10.107 | 57 | 1 | 58/58 |
| PC46 | 192.168.10.105 | 57 | 1 | 58/58 |
| PC47 | 192.168.10.110 | 57 | 1 | 58/58 |
| PC48 | 192.168.10.106 | 57 | 1 | 58/58 |
| PC49 | 192.168.10.103 | 57 | 1 | 58/58 |
| PC5 | 192.168.10.78 | 19 | 39 | 58/58 |
| PC6 | 192.168.10.81 | 19 | 39 | 58/58 |
| PC7 | 192.168.10.77 | 19 | 39 | 58/58 |
| PC25 | 192.168.10.70 | 19 | 39 | 58/58 |
| PC26 | 192.168.10.66 | 19 | 39 | 58/58 |
| PC27 | 192.168.10.69 | 19 | 39 | 58/58 |
| PC28 | 192.168.10.79 | 19 | 39 | 58/58 |
| PC29 | 192.168.10.83 | 19 | 39 | 58/58 |
| PC30 | 192.168.10.67 | 19 | 39 | 58/58 |
| PC31 | 192.168.10.73 | 19 | 39 | 58/58 |
| PC32 | 192.168.10.80 | 19 | 39 | 58/58 |
| PC33 | 192.168.10.71 | 19 | 39 | 58/58 |
| PC34 | 192.168.10.72 | 19 | 39 | 58/58 |
| PC35 | 192.168.10.68 | 19 | 39 | 58/58 |
| PC36 | 192.168.10.76 | 19 | 39 | 58/58 |
| PC37 | 192.168.10.75 | 19 | 39 | 58/58 |
| PC38 | 192.168.10.74 | 19 | 39 | 58/58 |
| PC39 | 192.168.10.82 | 19 | 39 | 58/58 |
| PC0 | 192.168.10.19 | 21 | 37 | 58/58 |
| PC1 | 192.168.10.20 | 21 | 37 | 58/58 |
| PC2 | 192.168.10.21 | 21 | 37 | 58/58 |
| PC3 | 192.168.10.4 | 21 | 37 | 58/58 |
| PC4 | 192.168.10.25 | 21 | 37 | 58/58 |
| PC10 | 192.168.10.18 | 21 | 37 | 58/58 |
| PC11 | 192.168.10.11 | 21 | 37 | 58/58 |
| PC12 | 192.168.10.17 | 21 | 37 | 58/58 |
| PC13 | 192.168.10.16 | 21 | 37 | 58/58 |
| PC14 | 192.168.10.10 | 21 | 37 | 58/58 |
| PC15 | 192.168.10.3 | 21 | 37 | 58/58 |
| PC16 | 192.168.10.7 | 21 | 37 | 58/58 |
| PC17 | 192.168.10.22 | 21 | 37 | 58/58 |
| PC18 | 192.168.10.2 | 21 | 37 | 58/58 |
| PC19 | 192.168.10.15 | 21 | 37 | 58/58 |
| PC20 | 192.168.10.23 | 21 | 37 | 58/58 |
| PC21 | 192.168.10.24 | 21 | 37 | 58/58 |
| PC22 | 192.168.10.8 | 21 | 37 | 58/58 |
| PC23 | 192.168.10.9 | 21 | 37 | 58/58 |
| PC24 | 192.168.10.5 | 21 | 37 | 58/58 |
| SRV-CAMPUS | 192.168.10.130 | 1 | 57 | 58/58 |

## Evidence and interpretation

Every record links to its actual command output in one of 58 capture batches. ACL counter changes are shared batch observations and are labelled accordingly in the Ping lab. A server-to-router denial initially had only three ACL matches because its first packet timed out; [an isolated recheck](evidence/PING-20261031/retry-PING2-2805.json) confirmed four sent, zero replies and four deny matches. The initial attempt remains in batch-55.json.

Packet Tracer's built-in realtime fast-forward was used to complete command processing efficiently. This is functional verification, not a latency or throughput benchmark. The interactive movement illustrates the physical routing and ACL decision; the browser does not execute new packets.

Administration clients reach switch management addresses within VLAN 10 without R1. Routed service access visits SW1 before and after R1. Student/Faculty interdepartmental initiation stops at R1, and local same-VLAN traffic remains switched.

The [local history archive](archive/earlier-campus-work.zip) contains the earlier 176-command report at `evidence/PING-20261030/ANALYSIS.md` and both v1 datasets. The active website uses v2.
