# Fault tolerance: redundant departmental uplinks

> Milestone scope: this is the November 5 single-core backup-uplink experiment. It precedes the [Version 02 dual-core design](versions/version-02/network-architecture.md).

The November 5, 2026 extension adds three backup cables to the existing submission. It retains all 58 network devices and all 57 earlier links, bringing the total to **60 links**. Each department can reach the core after its primary switch uplink fails.

| Department | Primary core port → access port | Backup core port → access port | Allowed VLANs |
| --- | --- | --- | --- |
| Administration | SW1 Gi0/2 → SW2 Gi0/1 | SW1 Fa0/2 → SW2 Gi0/2 | 10 |
| Faculty | SW1 Fa0/23 → SW3 Gi0/1 | SW1 Fa0/3 → SW3 Gi0/2 | 10,20 |
| Students | SW1 Fa0/24 → SW4 Gi0/1 | SW1 Fa0/4 → SW4 Gi0/2 | 10,30 |

Both links in a department terminate on the same two switches. This protects against one uplink or port failure; it does not protect against either switch failing. All three backup links negotiate at 100 Mb/s because they use FastEthernet ports on SW1. Administration therefore has less uplink capacity while using its backup.

## Automatic path selection

All four switches use `spanning-tree mode rapid-pvst`. SW1 has priority 4096 for VLANs 1,10,20,30,40. It is the root bridge. The departmental Gi0/1 is normally `Root FWD`; Gi0/2 is `Altn BLK` for each carried user/management VLAN. Blocking one path prevents a Layer 2 loop.

On each access switch, Gi0/2 has cost 200 for VLAN 10. Faculty VLAN 20 uses 201, and Student VLAN 30 uses 202. The native instance uses 203. Primary costs remain 4 for Administration and 19 for Faculty/Students, so the original links are preferred. Backup trunks use point-to-point negotiation, with PortFast and BPDU Guard disabled. Client access ports retain their existing edge settings.

Packet Tracer 9.0.1 produced a combined, malformed running-config line when several VLANs shared an explicitly configured cost. Distinct per-VLAN costs produce individual valid configuration lines and allow reopening to verify persistence. An early capture in `after-build.json` predates this correction; use the final and reopened captures for the accepted state.

## Failure demonstration

Keep a recovery archive and restore links after every experiment. From SW1 privileged EXEC:

```text
configure terminal
interface GigabitEthernet0/2
 shutdown
interface FastEthernet0/23
 shutdown
interface FastEthernet0/24
 shutdown
end
```

Do not save this temporary failed state. On each department switch, use `show spanning-tree vlan 10` and its data VLAN (20 or 30 where applicable). Gi0/2 should become `Root FWD`. Verify a client can resolve `portal.campus.test` and open its HTTP page; then check a prohibited departmental request against a known-live endpoint and inspect R1 ACL counters.

Restore the three SW1 interfaces with `no shutdown`. Gi0/1 should return to `Root FWD` and Gi0/2 to `Altn BLK`. Save only after restoration and validation. [Acceptance results](../FAULT_TOLERANCE_ACCEPTANCE.md) link the captured evidence.

The captured failover sequences received 30/30 replies from each department. Restoring all three primaries was disruptive: each 20-probe restoration sequence received 16 replies and lost four. Subsequent departmental checks received 4/4 replies, and the reopened file passed all 50 client service checks. Do not promise uninterrupted restoration or quote the first post-failure reply as an exact convergence time.

## Scalability, Resilience, and Design Tradeoffs

| Requirement | Design choice | Evidence | Remaining limitation |
| --- | --- | --- | --- |
| Connect more campus users | Departmental access switches and VLSM; expanded from 10 to 50 PCs | Earlier scale acceptance and 50-client checks after this extension | Address space, physical ports and bandwidth are separate capacity limits; throughput is unmeasured |
| Maintain service after an uplink failure | A standby trunk per department with Rapid PVST+ | All three primary uplinks disabled simultaneously; services remain reachable through Gi0/2 | Both paths share the same core and access switch |
| Control recovery behavior | Prefer original paths with explicit standby costs | STP roles and costs persisted after reopening; packet probes captured failure and restoration | Restoration lost four packets in each 20-probe sequence |
| Preserve isolation during failure | Keep existing VLAN allowlists, routed ACLs and VTY restrictions | Allowed control, three expected denials with ACL counters, authorized SSH and refused unauthorized SSH over backups | Same-VLAN traffic bypasses routed ACLs; ACLs are stateless |
| Keep clients manageable | Central DHCP, DNS and HTTP with relay | DHCP renewals and DNS queries from each department, plus 50-client HTTP checks | Central server and router remain shared failure dependencies |
| Make results reviewable | Recovery archive, sanitized exports, raw evidence and saved-file hash | Acceptance report, topology preservation check and evidence verifier | Website retains its November 2 capture until separately recaptured |

The design trades three cables and six ports for continued connectivity after any tested primary departmental uplink failure. The simultaneous three-uplink test exercises every backup at once. A standby link provides fault tolerance rather than additional normal-operation bandwidth; there is no EtherChannel or load balancing here.

The router, router-to-core trunk, core switch, central DHCP/DNS/HTTP server, each departmental switch, external router and external path remain single points of failure. Centralization reduces configuration work but concentrates dependencies. Router ACLs remain stateless, and same-VLAN communication still bypasses routed ACLs. Packet Tracer functional results do not establish production throughput, availability percentages or hardware convergence guarantees.

Protocol reference: [Cisco Catalyst 2960 spanning-tree configuration guide](https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst2960/software/release/15-2_2_e/configuration/guide/b_1522e_2960_2960c_2960s_2960sf_2960p_cg/m_1522e_layer2_stp_2960_2960s_cg.html).

[Return to project contents](../README.md)
