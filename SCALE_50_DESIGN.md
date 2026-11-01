# Campus expansion: 50 PCs, 56 devices

Revised: 31 October 2026 (IST)

**Status: implemented in the existing Secure_Campus_Network_Submission.pkt and verified after reopening.** See [SCALE_50_ACCEPTANCE.md](SCALE_50_ACCEPTANCE.md) for actual results and remaining deliverables. This expansion supersedes the 14-device inventory and /28 client subnets in the original implementation guide. Historical v1 evidence describes the earlier network. The current website uses the expanded v2 snapshot and the full PING-20261031 matrix.

## Required inventory

Count 50 client PCs independently of infrastructure so that the minimum is met even if an assessment excludes routers and switches.

| Category | Count | Assignment |
|---|---:|---|
| Administration PCs | 12 | VLAN 10; includes PC8-MGMT |
| Faculty PCs | 18 | VLAN 20 |
| Student PCs | 20 | VLAN 30 |
| Server-PT | 1 | VLAN 40; centralized DHCP, DNS, HTTP |
| Cisco 1941 router | 1 | R1-CAMPUS; four subinterfaces and DHCP relay |
| Cisco 2960-24TT switches | 4 | One aggregation switch and three access switches |
| **Total** | **56** | **50 PCs, 51 endpoints including the server** |

Retain the ten existing PCs and add PC10-PC49. Retain both existing switches, add SW3-FACULTY and SW4-STUDENTS, and move clients to the port assignments below. SW2-ACCESS becomes the Administration access switch. Use stable IDs `pc0`-`pc49`, `r1`, `sw1`-`sw4`, and `server0` in the future website snapshot.

## Addressing and capacity

Use VLSM within `192.168.10.0/24`. The allocation order below is deliberate; these are aligned, non-overlapping networks. This requires renumbering every current VLAN, not just changing its mask.

| VLAN | Department | Network / mask | Gateway | Broadcast | Usable addresses |
|---|---|---|---|---|---:|
| 30 | Students | 192.168.10.0/26; 255.255.255.192 | 192.168.10.1 | 192.168.10.63 | 62 |
| 20 | Faculty | 192.168.10.64/27; 255.255.255.224 | 192.168.10.65 | 192.168.10.95 | 30 |
| 10 | Administration | 192.168.10.96/27; 255.255.255.224 | 192.168.10.97 | 192.168.10.127 | 30 |
| 40 | Services | 192.168.10.128/28; 255.255.255.240 | 192.168.10.129 | 192.168.10.143 | 14 |

The range `192.168.10.144-192.168.10.255` is unallocated. The four active networks consume 144 addresses. Free address space does not by itself provide additional physical switch ports or measured performance.

Static assignments:

| Device | Address | Gateway |
|---|---|---|
| PC8-MGMT | 192.168.10.98/27 | 192.168.10.97 |
| SW1-CORE, VLAN 10 SVI | 192.168.10.99/27 | 192.168.10.97 |
| SW2-ACCESS, VLAN 10 SVI | 192.168.10.100/27 | 192.168.10.97 |
| SW3-FACULTY, VLAN 10 SVI | 192.168.10.101/27 | 192.168.10.97 |
| SW4-STUDENTS, VLAN 10 SVI | 192.168.10.102/27 | 192.168.10.97 |
| SRV-CAMPUS | 192.168.10.130/28 | 192.168.10.129 |

All PCs use DNS `192.168.10.130`. Set the server's DNS address to itself. Retain the local A record `portal.campus.test`, changing its address to `192.168.10.130`.

| DHCP pool | Start | Last | Maximum users | Gateway | Mask |
|---|---|---|---:|---|---|
| ADMIN_POOL | 192.168.10.103 | 192.168.10.126 | 24 | 192.168.10.97 | 255.255.255.224 |
| FACULTY_POOL | 192.168.10.66 | 192.168.10.94 | 29 | 192.168.10.65 | 255.255.255.224 |
| STUDENT_POOL | 192.168.10.2 | 192.168.10.62 | 61 | 192.168.10.1 | 255.255.255.192 |

The initial build needs 49 DHCP leases: 11 Administration, 18 Faculty, and 20 Students. PC8-MGMT is static. DHCP pools provide 114 possible leases across the three VLANs. That is address capacity, not a simultaneous-user performance claim. The Services VLAN stays static. Record observed leases after testing; do not present planned addresses as measured leases.

## Topology and exact port map

```text
                         R1-CAMPUS
                             |
                         SW1-CORE ---- SRV-CAMPUS
                        /    |    \
               SW2-ACCESS SW3-FACULTY SW4-STUDENTS
                12 Admin   18 Faculty   20 Students
```

| Endpoint A | Endpoint B | Mode / VLANs |
|---|---|---|
| R1 Gi0/0 | SW1 Gi0/1 | 802.1Q trunk; 10,20,30,40 |
| SW1 Gi0/2 | SW2 Gi0/1 | Trunk; 10 |
| SW1 Fa0/23 | SW3 Gi0/1 | Trunk; 10,20 |
| SW1 Fa0/24 | SW4 Gi0/1 | Trunk; 10,30 |
| SW1 Fa0/1 | SRV-CAMPUS FastEthernet0 | Access; 40 |
| SW2 Fa0/1 | PC8-MGMT FastEthernet0 | Access; 10 |
| SW2 Fa0/2 | PC9-ADMIN FastEthernet0 | Access; 10 |
| SW2 Fa0/3-Fa0/12 | PC40-PC49, in numerical order | Access; 10 |
| SW3 Fa0/1-Fa0/3 | PC5-PC7, in numerical order | Access; 20 |
| SW3 Fa0/4-Fa0/18 | PC25-PC39, in numerical order | Access; 20 |
| SW4 Fa0/1-Fa0/5 | PC0-PC4, in numerical order | Access; 30 |
| SW4 Fa0/6-Fa0/20 | PC10-PC24, in numerical order | Access; 30 |

Use straight-through cables for endpoint/router-to-switch links and crossover cables between switches. There are 55 links: 51 endpoint links and four infrastructure links. No switch port is assigned twice. Unused access-switch FastEthernet ports: 12 on SW2, six on SW3, four on SW4. Shut unused ports after commissioning.

The 2960-24TT has only two Gigabit uplink ports. With one used for R1, SW1 uses two FastEthernet ports for additional trunks. Consequently, Faculty and Student uplinks negotiate at **100 Mb/s**; the Administration and router uplinks are nominally 1 Gb/s. This is adequate for the planned lab demonstration, but performance remains unmeasured. A core switch with more Gigabit ports is a later upgrade if all-Gigabit uplinks become a requirement.

Hardware reference: [Cisco Catalyst 2960 Series at a glance](https://www.cisco.com/c/dam/en_us/solutions/small-business/products/routers-switches/catalyst-2960-series-switches/C45-484155-03_2960_AAG_v1b.pdf).

## Migration sequence

1. Per the user's in-place editing instruction, archive the original campus files in one recovery ZIP, then edit the existing `Secure_Campus_Network_Submission.pkt`. No additional active build/submission .pkt copies are needed.
2. Add two switches and 40 PCs, rename and cable according to this document, and check the total is 56 devices and 55 links.
3. Create the four VLANs on SW1 and required VLANs on the access switches. Configure trunks, client access ports, PortFast on client/server ports only, switch management SVIs, and switch default gateways. Keep all four management SVIs in VLAN 10.
4. Renumber R1's four gateway subinterfaces. Change all three helpers to `192.168.10.130`. Replace the old ACL network addresses, wildcard masks, directed broadcast addresses, relay gateway addresses, and server host addresses together. Old subnets overlap the new allocation; do not leave partial addressing active.
5. Change the server's address, mask, gateway, DNS A record, and all three DHCP pools. Remove obsolete pool definitions. Update PC8-MGMT's static settings and renew DHCP on the remaining 49 PCs.
6. Keep the existing access-policy intent: all departments reach DNS/HTTP and can ping the server and their own gateway; Administration may initiate departmental ping diagnostics; Faculty and Students cannot initiate routed access to each other or Administration. Permit necessary DHCP/DNS/HTTP/ICMP replies in the Services ACL. Permit SSH from PC8-MGMT (`192.168.10.98`) only, using a VTY source ACL on the router and all four switches. Same-VLAN traffic still bypasses routed ACLs.
7. Verify, save running configurations to startup configurations, save the existing `Secure_Campus_Network_Submission.pkt` in place, close and reopen it, then repeat essential checks before declaring it verified.
8. Export new sanitized configurations, actual client leases, topology, acceptance evidence, file hash, and a new versioned website snapshot. Update report and slides to 50 PCs, 56 total devices, VLSM, and measured results. Historical 176/176 tests apply to the earlier network.

ACL wildcard masks: Students `0.0.0.63`, Faculty and Administration `0.0.0.31`, Services `0.0.0.15`. The authorized SSH source remains a single host, not the entire Administration subnet. Do not relax policy to `permit ip any any` to make the expanded network pass tests.

## Acceptance criteria

- Count exactly 50 unique PC devices: 12 Administration, 18 Faculty, 20 Students; plus the server, router, and four switches.
- Observe 49 unique DHCP leases in the correct VLAN/pool with correct mask, gateway, and DNS; verify PC8-MGMT's static settings separately.
- From every PC, test its gateway, DNS resolution of `portal.campus.test`, and an actual HTTP request to that hostname.
- Verify same-VLAN communication and Administration-to-department ICMP across the relevant switches. Test prohibited Student/Faculty initiation against known-live targets and inspect ACL counters and packet traces.
- Test authorized SSH to all five IOS devices from PC8-MGMT and denied SSH from another Administration PC and restricted departmental clients.
- Verify all trunks, four switch management SVIs, startup configurations, and persistence after reopening the new submission.
- For a complete directed endpoint ping matrix, use 51 endpoints (50 PCs and the server), exclude self-pairs, and add four switch management and four router gateway destinations per source: `51 * (50 + 4 + 4) = 2,958` cases. Assess each against the policy, including expected denials and same-VLAN paths. Use ARP warm-up/retries so initial discovery loss is not misclassified.
- Actual expanded-network acceptance is recorded in SCALE_50_ACCEPTANCE.md. The companion website now integrates its new v2 snapshot and full matrix; historical v1 evidence remains unchanged.
