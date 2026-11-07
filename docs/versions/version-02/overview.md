# Version 02 — scope and iterations

Version 02 is the dual-core Campus Atlas explorer at `#version-02`. It presents the **November 6, 2026 release of verified remediation Iteration 5**: 60 devices, 64 links, 50 PCs and two servers. There are 49 departmental workstations and one dedicated management workstation.

The objective extends Version 01 with management separation, Layer 2 hardening and continuity during a single core-switch outage. The companion viewer retains the original edition for comparison and provides a complete topology, device explanations, directional scenarios, Ping Lab and access-policy view.

## Engineering iteration record

| Iteration | Outcome |
| --- | --- |
| 0 | Re-saved baseline compared with inventory, configurations, services and reopened behavior |
| 1 | Device credentials and console controls, DTP suppression, port descriptions and service reduction |
| 2 | PC8-MGMT and management interfaces moved to VLAN 99 |
| 3 | Expected-MAC port security, DHCP snooping, native VLAN 999 and unused-port VLAN 998 |
| 4 | OSPF MD5 authentication, syslog and NTP verification; simulator limitations recorded |
| 5 | Two 3650 multilayer cores, HSRP gateways, dual access uplinks, services switch and 2911 edge |
| 6 trial | Stateful WAN inspection trial rolled back; not an accepted firewall feature |
| Release refresh | Published Iteration 5 and all 2,652 directed endpoint pairs, grouped into 33 scenario types |

The [audit remediation record](../../audit-remediation.md) links the evidence for every step. The [release manifest](../../../evidence/AUDIT-REMEDIATION-20261105-182333/release-manifest.json) identifies the November 6 capture; the [checkpoint manifest](../../../evidence/AUDIT-REMEDIATION-20261105-182333/verified-submission.json) binds it to the reopened .pkt.

## November 7 code refinement iteration

The cleanup extracted and strengthened release validation, made the checkpoint verifier safe under Python optimization, and cleaned up the bridge client with scoped output paths and response handling. It added regression tests and these versioned guides. See [codebase review](../../CODEBASE_REVIEW.md) for findings, changes and validation.

The cleanup leaves the recorded network data and saved simulator checkpoint intact. A fresh capture is necessary to claim changed live network behavior.

[Architecture](network-architecture.md) · [Access controls](access-controls.md) · [Verification](verification.md) · [Version index](../README.md)
