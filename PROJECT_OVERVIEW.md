# Design and Implementation of a Secure Campus Network with Centralized Services

**Companion website:** Campus Atlas — Network Explorer  
**Updated:** 6 November 2026 (IST)  
**Current implementation:** See the [verified audit remediation checkpoint](docs/audit-remediation.md) for the saved Packet Tracer file and current management configuration.  
**Website evidence baseline:** November 2, 2026; 58 devices, 57 links and the v3 datasets.

This project connects 50 campus PCs across Administration, Faculty and Students, provides centralized DHCP, DNS and HTTP services, and controls communication through VLANs and access control lists. An external branch demonstrates how OSPF routing and Port Address Translation (PAT) work together. Three standby departmental trunks provide uplink fault tolerance through Rapid PVST+. Campus Atlas presents the design through an interactive topology, addressing tables, policy explanations and recorded packet demonstrations.

The design and packet walkthroughs document the November 5 fault-tolerance milestone. The current Iteration 5 submission has **50 PCs, 60 network devices and 64 links**, with HSRP gateways on two 3650 multilayer cores and two routed links to the PAT edge. Section 3.4 gives both sets of endpoint addresses. Campus Atlas includes the verified current checkpoint and retains the November 2 topology and its historical ping replay. [Current topology and verification](docs/audit-remediation.md)

## Contents

- [Objectives and problem statement](#1-objectives-and-problem-statement)
- [System components and topology](#2-system-components-and-topology)
- [Addressing tables and centralized services](#3-addressing-and-centralized-services)
- [Networking technologies used](#4-networking-technologies-used)
- [ACL design and access policy](#5-acl-design-and-access-policy)
- [Routing and packet workflows](#6-routing-and-packet-workflows)
- [OSPF and PAT configuration](#7-ospf-and-pat-configuration-strategy)
- [Website stack and architecture](#8-website-tech-stack-and-architecture)
- [Information covered in Campus Atlas](#9-information-covered-in-campus-atlas)
- [Evidence and verification status](#10-evidence-and-verification-status)
- [Limitations and future work](#11-design-limits-and-future-work)
- [Additional work and deliverables](#12-additional-work-and-deliverables)
- [Versions and iterations](#13-versions-and-iterations)
- [Current technical skills used](#14-current-technical-skills-used)
- [Demonstration and source references](#15-demonstration-and-source-references)

## 1. Objectives and Problem Statement

### 1.1 Problem and Intended Users

Administration, Faculty and Students need shared campus services while departmental access and network administration follow different permissions. Configuring every client manually creates maintenance work and inconsistent settings. A single departmental uplink also interrupts that department when its cable or port fails.

The intended network users are the three campus departments and the authorized management operator. The report and companion website also support faculty review, student learning, project demonstrations and viva preparation.

### 1.2 Objectives

The main objective is to design and demonstrate a campus network in which departments share essential services while routed access and device administration follow explicit permissions.

The project has seven practical goals:

1. **Organize the campus:** Place Administration, Faculty, Students and Services in separate VLANs and IP subnets.
2. **Simplify client configuration:** Automatically supply 49 PCs with addresses, subnet masks, gateways and DNS settings using centralized DHCP and relay. Keep the management workstation static.
3. **Provide shared services:** Let all departments resolve campus hostnames and access the internal web portal.
4. **Control access:** Permit required services and Administration diagnostics, block prohibited departmental initiation, and restrict SSH administration to PC8-MGMT.
5. **Demonstrate external connectivity:** Dynamically learn an external server network through single-area OSPF and let client VLANs share one outside address through PAT.
6. **Maintain departmental connectivity after an uplink failure:** Add a preferred primary path and a standby trunk per department, with Rapid PVST+ preventing loops and selecting the usable path.
7. **Explain and verify the design:** Use Campus Atlas to connect configuration, packet paths, expected permissions and captured test evidence.

The November 5 milestone demonstrated campus services, isolation, routing, translation, uplink failure and restoration, and saved-file persistence. The later [remediation record](docs/audit-remediation.md) identifies the current verified checkpoint and its separately dated simulator tests.

## 2. System Components and Topology

### 2.1 Inventory

| Component | Quantity | Purpose |
| --- | ---: | --- |
| Administration PCs | 12 | VLAN 10; includes the authorized management workstation |
| Faculty PCs | 18 | VLAN 20 |
| Student PCs | 20 | VLAN 30 |
| Cisco 2960-24TT switches | 4 | One aggregation switch and three departmental access switches |
| Cisco 1941 routers | 2 | Campus inter-VLAN routing and the simulated external branch |
| Server-PT devices | 2 | Internal DHCP/DNS/HTTP server and external HTTP demonstration server |
| **Total network devices** | **58** | **50 PCs, four switches, two routers and two servers** |

The current network has **60 physical links**: 51 campus endpoint access links, seven VLAN trunks (one router/core trunk, three primary departmental trunks and three standby departmental trunks), and two routed Ethernet links. The external server connection belongs to the routed-link category. Packet Tracer's power-distribution object is excluded from network-device totals. The website's November 2 topology has the earlier 57 links.

### 2.2 Overall Layout

```text
                  SRV-EXTERNAL
                  203.0.113.10/24
                         |
                  R2 Gi0/1: 203.0.113.1/24
                   R2-EXTERNAL
                  R2 Gi0/0: 198.51.100.2/30
                         |
                Routed Ethernet / OSPF area 0
                         |
                  R1 Gi0/1: 198.51.100.1/30
                    R1-CAMPUS
                  R1 Gi0/0: 802.1Q trunk
                         |
                     SW1-CORE -------- SRV-CAMPUS
                   //    ||    \\        192.168.10.130/28
                  //     ||     \\       Access VLAN 40
          SW2-ACCESS  SW3-FACULTY  SW4-STUDENTS
             |            |            |
         12 Admin      18 Faculty    20 Students
          VLAN 10       VLAN 20      VLAN 30

  Each double line represents a primary and a standby trunk.
  Normally only the primary forwards for each carried department VLAN.
```

The campus has an extended star/tree access layout with parallel departmental uplinks. Rapid PVST+ keeps one departmental path forwarding and the other alternate/blocking, creating a loop-free active tree. SW1 aggregates departmental traffic, while R1 supplies all four campus gateways. The 2960 switches perform Layer 2 forwarding; their management IP addresses do not make them the inter-VLAN routers.

### 2.3 Device Responsibilities

| Device | Responsibility |
| --- | --- |
| **R1-CAMPUS** | Four VLAN subinterfaces, DHCP relay, inbound security ACLs, campus SSH management, OSPF adjacency and client PAT |
| **SW1-CORE** | Aggregates the departmental switches; connects the campus server and the trunk to R1; Rapid PVST+ root bridge |
| **SW2-ACCESS** | Connects Administration PCs, including PC8-MGMT |
| **SW3-FACULTY** | Connects Faculty PCs; carries VLAN 10 management traffic on its uplink |
| **SW4-STUDENTS** | Connects Student PCs; carries VLAN 10 management traffic on its uplink |
| **SRV-CAMPUS** | Central DHCP pools, DNS records and internal portal over HTTP |
| **R2-EXTERNAL** | Forms an OSPF adjacency with R1 and advertises the external server LAN |
| **SRV-EXTERNAL** | Serves the external demonstration page at 203.0.113.10 |

### 2.4 Important Physical Connections

| Connection | Mode / VLANs | Significance |
| --- | --- | --- |
| R1 Gi0/0 ↔ SW1 Gi0/1 | Trunk: 10, 20, 30, 40 | Shared physical link for all campus routed VLANs |
| SW1 Gi0/2 ↔ SW2 Gi0/1 | Trunk: 10 | Administration and switch management |
| SW1 Fa0/23 ↔ SW3 Gi0/1 | Trunk: 10, 20 | Faculty plus management |
| SW1 Fa0/24 ↔ SW4 Gi0/1 | Trunk: 10, 30 | Students plus management |
| SW1 Fa0/2 ↔ SW2 Gi0/2 | Standby trunk: 10 | Administration backup uplink |
| SW1 Fa0/3 ↔ SW3 Gi0/2 | Standby trunk: 10, 20 | Faculty backup uplink |
| SW1 Fa0/4 ↔ SW4 Gi0/2 | Standby trunk: 10, 30 | Student backup uplink |
| SW1 Fa0/1 ↔ SRV-CAMPUS Fa0 | Access: 40 | Centralized services attachment |
| R1 Gi0/1 ↔ R2 Gi0/0 | Routed Ethernet | OSPF transit and PAT boundary |
| R2 Gi0/1 ↔ SRV-EXTERNAL Fa0 | Routed Ethernet | External server LAN |

SW2 uses Fa0/1–Fa0/12 for Administration, SW3 uses Fa0/1–Fa0/18 for Faculty, and SW4 uses Fa0/1–Fa0/20 for Students. PC numbering follows retained project identities rather than department order: PC0 is a Student, PC5 is Faculty, and PC8-MGMT is Administration.

The primary Faculty and Student uplinks use SW1's **100 Mb/s FastEthernet** ports. The router and primary Administration trunks use Gigabit interfaces. All three standby trunks negotiate at 100 Mb/s because their SW1 ends use FastEthernet. These are interface characteristics; throughput has not been benchmarked. The reopened core status records the router-facing Gi0/1 negotiating at 100 Mb/s despite its Gigabit-capable interface type.

### 2.5 Redundant Uplink Design

All four switches use `spanning-tree mode rapid-pvst`. SW1 has configured bridge priority 4096 for VLANs 1, 10, 20, 30 and 40. On each departmental switch, Gi0/1 is normally `Root FWD` and Gi0/2 is `Altn BLK` for each carried user/management VLAN.

The primary path cost is 4 for Administration and 19 for Faculty/Students. The backup Gi0/2 has per-VLAN costs 200 for VLAN 10, 201 for Faculty VLAN 20, 202 for Student VLAN 30, and 203 for the native instance where configured. Distinct values also avoid a Packet Tracer configuration serialization problem observed when several VLANs shared one explicit cost. Final reopened exports confirm persistence. Backup trunks use point-to-point negotiation without PortFast or BPDU Guard; endpoint ports retain their edge settings.

Both trunks terminate on the same pair of switches. This protects the tested uplinks and ports, while core and access switch failures remain dependencies. See [fault-tolerance design](docs/fault-tolerance.md).

## 3. Addressing and Centralized Services

### 3.1 VLAN and VLSM Plan

The campus divides `192.168.10.0/24` using Variable Length Subnet Masking (VLSM). Students receive the largest subnet, while Services receives a smaller static-address segment.

| VLAN | Segment | Subnet | Mask | Gateway | Broadcast | Usable addresses |
| --- | --- | --- | --- | --- | --- | ---: |
| 10 | Administration | 192.168.10.96/27 | 255.255.255.224 | 192.168.10.97 | 192.168.10.127 | 30 |
| 20 | Faculty | 192.168.10.64/27 | 255.255.255.224 | 192.168.10.65 | 192.168.10.95 | 30 |
| 30 | Students | 192.168.10.0/26 | 255.255.255.192 | 192.168.10.1 | 192.168.10.63 | 62 |
| 40 | Services | 192.168.10.128/28 | 255.255.255.240 | 192.168.10.129 | 192.168.10.143 | 14 |

The range `192.168.10.144–192.168.10.255` remains unallocated. Subnet capacity includes infrastructure addresses and is separate from the number of connected PCs.

### 3.2 DHCP and Static Assignments

| DHCP pool | Allocation range | Capacity | Present dynamic clients |
| --- | --- | ---: | ---: |
| ADMIN_POOL | 192.168.10.103–192.168.10.126 | 24 | 11 |
| FACULTY_POOL | 192.168.10.66–192.168.10.94 | 29 | 18 |
| STUDENT_POOL | 192.168.10.2–192.168.10.62 | 61 | 20 |

All departmental pools provide DNS server `192.168.10.130` and the appropriate VLAN gateway. The 114 possible pool leases represent address capacity. The implemented network has **49 DHCP clients and one static client**.

| Static device / interface | Address |
| --- | --- |
| PC8-MGMT | 192.168.10.98/27 |
| SW1-CORE VLAN 10 SVI | 192.168.10.99/27 |
| SW2-ACCESS VLAN 10 SVI | 192.168.10.100/27 |
| SW3-FACULTY VLAN 10 SVI | 192.168.10.101/27 |
| SW4-STUDENTS VLAN 10 SVI | 192.168.10.102/27 |
| SRV-CAMPUS | 192.168.10.130/28 |
| R1 Gi0/1 / R2 Gi0/0 | 198.51.100.1/30 / 198.51.100.2/30 |
| R2 Gi0/1 / SRV-EXTERNAL | 203.0.113.1/24 / 203.0.113.10/24 |

Switches use `192.168.10.97` as their management default gateway. SRV-CAMPUS uses `192.168.10.129`; SRV-EXTERNAL uses `203.0.113.1`. A constrained, unused Packet Tracer default `serverPool` exists at `.131`; the three departmental pools supply the clients.

### 3.3 Services

| Service | Location | Role |
| --- | --- | --- |
| DHCP | SRV-CAMPUS | Supplies IP address, mask, gateway and DNS; R1 relays requests across VLAN boundaries |
| DNS | SRV-CAMPUS | Resolves `portal.campus.test` → `192.168.10.130` and `external.campus.test` → `203.0.113.10` |
| Internal HTTP | SRV-CAMPUS, TCP 80 | Delivers the shared campus portal |
| External HTTP | SRV-EXTERNAL, TCP 80 | Demonstrates DNS, OSPF forwarding, PAT and permitted replies |
| SSHv2 | R1 and SW1–SW4, TCP 22 | Encrypted device administration from PC8-MGMT |

The external subnets use documentation address ranges within the simulation. They represent a controlled external network rather than real Internet access.

### 3.4 Complete Endpoint Addressing Table

#### 3.4.1 Current Iteration 5 Capture

These addresses were observed on **06 November 2026 at 22:49:16 IST** in the reopened Iteration 5 simulation. The DHCP entries describe that capture. The current subnet and HSRP details are in the [remediation record](docs/audit-remediation.md#current-topology-and-forwarding). [Capture manifest](evidence/AUDIT-REMEDIATION-20261105-182333/release-manifest.json)

| Endpoint | Department / segment | VLAN | Observed IPv4 / prefix | Assignment | Gateway |
| --- | --- | --- | --- | --- | --- |
| PC0 | Students | 30 | 192.168.10.35/26 | DHCP | 192.168.10.1 |
| PC1 | Students | 30 | 192.168.10.36/26 | DHCP | 192.168.10.1 |
| PC2 | Students | 30 | 192.168.10.28/26 | DHCP | 192.168.10.1 |
| PC3 | Students | 30 | 192.168.10.6/26 | DHCP | 192.168.10.1 |
| PC4 | Students | 30 | 192.168.10.34/26 | DHCP | 192.168.10.1 |
| PC5 | Faculty | 20 | 192.168.10.70/27 | DHCP | 192.168.10.65 |
| PC6 | Faculty | 20 | 192.168.10.75/27 | DHCP | 192.168.10.65 |
| PC7 | Faculty | 20 | 192.168.10.73/27 | DHCP | 192.168.10.65 |
| PC8-MGMT | Management | 99 | 192.168.10.146/28 | Static | 192.168.10.145 |
| PC9-ADMIN | Administration | 10 | 192.168.10.107/27 | DHCP | 192.168.10.97 |
| PC10 | Students | 30 | 192.168.10.16/26 | DHCP | 192.168.10.1 |
| PC11 | Students | 30 | 192.168.10.30/26 | DHCP | 192.168.10.1 |
| PC12 | Students | 30 | 192.168.10.2/26 | DHCP | 192.168.10.1 |
| PC13 | Students | 30 | 192.168.10.24/26 | DHCP | 192.168.10.1 |
| PC14 | Students | 30 | 192.168.10.9/26 | DHCP | 192.168.10.1 |
| PC15 | Students | 30 | 192.168.10.27/26 | DHCP | 192.168.10.1 |
| PC16 | Students | 30 | 192.168.10.20/26 | DHCP | 192.168.10.1 |
| PC17 | Students | 30 | 192.168.10.18/26 | DHCP | 192.168.10.1 |
| PC18 | Students | 30 | 192.168.10.3/26 | DHCP | 192.168.10.1 |
| PC19 | Students | 30 | 192.168.10.7/26 | DHCP | 192.168.10.1 |
| PC20 | Students | 30 | 192.168.10.40/26 | DHCP | 192.168.10.1 |
| PC21 | Students | 30 | 192.168.10.14/26 | DHCP | 192.168.10.1 |
| PC22 | Students | 30 | 192.168.10.26/26 | DHCP | 192.168.10.1 |
| PC23 | Students | 30 | 192.168.10.10/26 | DHCP | 192.168.10.1 |
| PC24 | Students | 30 | 192.168.10.31/26 | DHCP | 192.168.10.1 |
| PC25 | Faculty | 20 | 192.168.10.90/27 | DHCP | 192.168.10.65 |
| PC26 | Faculty | 20 | 192.168.10.80/27 | DHCP | 192.168.10.65 |
| PC27 | Faculty | 20 | 192.168.10.72/27 | DHCP | 192.168.10.65 |
| PC28 | Faculty | 20 | 192.168.10.85/27 | DHCP | 192.168.10.65 |
| PC29 | Faculty | 20 | 192.168.10.86/27 | DHCP | 192.168.10.65 |
| PC30 | Faculty | 20 | 192.168.10.84/27 | DHCP | 192.168.10.65 |
| PC31 | Faculty | 20 | 192.168.10.68/27 | DHCP | 192.168.10.65 |
| PC32 | Faculty | 20 | 192.168.10.66/27 | DHCP | 192.168.10.65 |
| PC33 | Faculty | 20 | 192.168.10.78/27 | DHCP | 192.168.10.65 |
| PC34 | Faculty | 20 | 192.168.10.92/27 | DHCP | 192.168.10.65 |
| PC35 | Faculty | 20 | 192.168.10.69/27 | DHCP | 192.168.10.65 |
| PC36 | Faculty | 20 | 192.168.10.74/27 | DHCP | 192.168.10.65 |
| PC37 | Faculty | 20 | 192.168.10.67/27 | DHCP | 192.168.10.65 |
| PC38 | Faculty | 20 | 192.168.10.81/27 | DHCP | 192.168.10.65 |
| PC39 | Faculty | 20 | 192.168.10.71/27 | DHCP | 192.168.10.65 |
| PC40 | Administration | 10 | 192.168.10.122/27 | DHCP | 192.168.10.97 |
| PC41 | Administration | 10 | 192.168.10.113/27 | DHCP | 192.168.10.97 |
| PC42 | Administration | 10 | 192.168.10.108/27 | DHCP | 192.168.10.97 |
| PC43 | Administration | 10 | 192.168.10.103/27 | DHCP | 192.168.10.97 |
| PC44 | Administration | 10 | 192.168.10.112/27 | DHCP | 192.168.10.97 |
| PC45 | Administration | 10 | 192.168.10.121/27 | DHCP | 192.168.10.97 |
| PC46 | Administration | 10 | 192.168.10.111/27 | DHCP | 192.168.10.97 |
| PC47 | Administration | 10 | 192.168.10.115/27 | DHCP | 192.168.10.97 |
| PC48 | Administration | 10 | 192.168.10.116/27 | DHCP | 192.168.10.97 |
| PC49 | Administration | 10 | 192.168.10.119/27 | DHCP | 192.168.10.97 |
| SRV-CAMPUS | Services | 40 | 192.168.10.130/28 | Static | 192.168.10.129 |
| SRV-EXTERNAL | External | External LAN | 203.0.113.10/24 | Static | 203.0.113.1 |

#### 3.4.2 November 5 Reopened Capture

The table below uses **November 5, 2026 (IST) reopened lease observations** from [reopened checks](evidence/FAULT-TOLERANCE-20261105/reopened-checks.json). It includes all 50 PCs and both servers. DHCP addresses can change after renewal or reopening and may differ from the website's November 2 leases. Prefixes correspond to the recorded masks; VLAN gateways come from the configuration and subnet tables above. All departmental PCs use DNS `192.168.10.130`.

| Endpoint | Department / segment | VLAN | Observed IPv4 / prefix | Assignment | Gateway |
| --- | --- | --- | --- | --- | --- |
| PC0 | Students | 30 | 192.168.10.4/26 | DHCP | 192.168.10.1 |
| PC1 | Students | 30 | 192.168.10.15/26 | DHCP | 192.168.10.1 |
| PC2 | Students | 30 | 192.168.10.6/26 | DHCP | 192.168.10.1 |
| PC3 | Students | 30 | 192.168.10.8/26 | DHCP | 192.168.10.1 |
| PC4 | Students | 30 | 192.168.10.14/26 | DHCP | 192.168.10.1 |
| PC5 | Faculty | 20 | 192.168.10.73/27 | DHCP | 192.168.10.65 |
| PC6 | Faculty | 20 | 192.168.10.70/27 | DHCP | 192.168.10.65 |
| PC7 | Faculty | 20 | 192.168.10.77/27 | DHCP | 192.168.10.65 |
| PC8-MGMT | Administration | 10 | 192.168.10.98/27 | Static | 192.168.10.97 |
| PC9-ADMIN | Administration | 10 | 192.168.10.105/27 | DHCP | 192.168.10.97 |
| PC10 | Students | 30 | 192.168.10.10/26 | DHCP | 192.168.10.1 |
| PC11 | Students | 30 | 192.168.10.19/26 | DHCP | 192.168.10.1 |
| PC12 | Students | 30 | 192.168.10.7/26 | DHCP | 192.168.10.1 |
| PC13 | Students | 30 | 192.168.10.3/26 | DHCP | 192.168.10.1 |
| PC14 | Students | 30 | 192.168.10.2/26 | DHCP | 192.168.10.1 |
| PC15 | Students | 30 | 192.168.10.20/26 | DHCP | 192.168.10.1 |
| PC16 | Students | 30 | 192.168.10.16/26 | DHCP | 192.168.10.1 |
| PC17 | Students | 30 | 192.168.10.17/26 | DHCP | 192.168.10.1 |
| PC18 | Students | 30 | 192.168.10.13/26 | DHCP | 192.168.10.1 |
| PC19 | Students | 30 | 192.168.10.11/26 | DHCP | 192.168.10.1 |
| PC20 | Students | 30 | 192.168.10.12/26 | DHCP | 192.168.10.1 |
| PC21 | Students | 30 | 192.168.10.18/26 | DHCP | 192.168.10.1 |
| PC22 | Students | 30 | 192.168.10.22/26 | DHCP | 192.168.10.1 |
| PC23 | Students | 30 | 192.168.10.9/26 | DHCP | 192.168.10.1 |
| PC24 | Students | 30 | 192.168.10.21/26 | DHCP | 192.168.10.1 |
| PC25 | Faculty | 20 | 192.168.10.79/27 | DHCP | 192.168.10.65 |
| PC26 | Faculty | 20 | 192.168.10.68/27 | DHCP | 192.168.10.65 |
| PC27 | Faculty | 20 | 192.168.10.67/27 | DHCP | 192.168.10.65 |
| PC28 | Faculty | 20 | 192.168.10.83/27 | DHCP | 192.168.10.65 |
| PC29 | Faculty | 20 | 192.168.10.82/27 | DHCP | 192.168.10.65 |
| PC30 | Faculty | 20 | 192.168.10.78/27 | DHCP | 192.168.10.65 |
| PC31 | Faculty | 20 | 192.168.10.86/27 | DHCP | 192.168.10.65 |
| PC32 | Faculty | 20 | 192.168.10.76/27 | DHCP | 192.168.10.65 |
| PC33 | Faculty | 20 | 192.168.10.80/27 | DHCP | 192.168.10.65 |
| PC34 | Faculty | 20 | 192.168.10.85/27 | DHCP | 192.168.10.65 |
| PC35 | Faculty | 20 | 192.168.10.87/27 | DHCP | 192.168.10.65 |
| PC36 | Faculty | 20 | 192.168.10.84/27 | DHCP | 192.168.10.65 |
| PC37 | Faculty | 20 | 192.168.10.81/27 | DHCP | 192.168.10.65 |
| PC38 | Faculty | 20 | 192.168.10.69/27 | DHCP | 192.168.10.65 |
| PC39 | Faculty | 20 | 192.168.10.66/27 | DHCP | 192.168.10.65 |
| PC40 | Administration | 10 | 192.168.10.115/27 | DHCP | 192.168.10.97 |
| PC41 | Administration | 10 | 192.168.10.103/27 | DHCP | 192.168.10.97 |
| PC42 | Administration | 10 | 192.168.10.108/27 | DHCP | 192.168.10.97 |
| PC43 | Administration | 10 | 192.168.10.114/27 | DHCP | 192.168.10.97 |
| PC44 | Administration | 10 | 192.168.10.112/27 | DHCP | 192.168.10.97 |
| PC45 | Administration | 10 | 192.168.10.113/27 | DHCP | 192.168.10.97 |
| PC46 | Administration | 10 | 192.168.10.104/27 | DHCP | 192.168.10.97 |
| PC47 | Administration | 10 | 192.168.10.116/27 | DHCP | 192.168.10.97 |
| PC48 | Administration | 10 | 192.168.10.106/27 | DHCP | 192.168.10.97 |
| PC49 | Administration | 10 | 192.168.10.110/27 | DHCP | 192.168.10.97 |
| SRV-CAMPUS | Services | 40 | 192.168.10.130/28 | Static | 192.168.10.129 |
| SRV-EXTERNAL | External server LAN | N/A | 203.0.113.10/24 | Static | 203.0.113.1 |

### 3.5 External Network Addressing

| Segment | Network / mask | Interfaces | Broadcast | Assignment |
| --- | --- | --- | --- | --- |
| R1–R2 OSPF transit | 198.51.100.0/30; 255.255.255.252 | R1 Gi0/1: .1; R2 Gi0/0: .2 | 198.51.100.3 | Static; R1 .1 is the shared PAT outside address |
| External server LAN | 203.0.113.0/24; 255.255.255.0 | R2 Gi0/1: .1; SRV-EXTERNAL: .10 | 203.0.113.255 | Static; server gateway 203.0.113.1 |

## 4. Networking Technologies Used

| Concept | How the project uses it |
| --- | --- |
| **Ethernet switching and MAC learning** | Switches learn source MAC addresses and forward frames within the relevant VLAN. |
| **ARP and default gateways** | Hosts resolve a local destination's MAC address or the gateway's MAC address before sending Ethernet frames. ARP stays within its broadcast domain. |
| **VLAN segmentation** | Four VLANs separate department and service broadcast domains. |
| **802.1Q trunking** | Shared uplinks carry the explicitly allowed VLANs using VLAN tagging. |
| **IPv4 subnetting and VLSM** | `/26`, `/27` and `/28` campus networks allocate different address capacities without overlap. |
| **Router-on-a-stick** | R1 Gi0/0.10, .20, .30 and .40 route between VLANs over one physical trunk. |
| **DHCP relay** | `ip helper-address 192.168.10.130` on the three client subinterfaces forwards DHCP requests to the central server. |
| **DNS and HTTP** | Hostname-based browsing combines name resolution with routed application access. |
| **Extended ACLs** | R1 filters packets by source, destination, protocol, TCP/UDP service and ICMP type. |
| **Standard ACLs** | ACL 1 restricts VTY source addresses; NAT-CLIENTS selects private addresses eligible for translation. |
| **SSHv2** | Authorized management sessions use encrypted remote access and local authentication. |
| **OSPFv2, area 0** | R1 and R2 exchange routing information on the transit network; R1 learns `203.0.113.0/24`. |
| **PAT / NAT overload** | Multiple client addresses share R1's `198.51.100.1`, distinguished by transport ports or ICMP identifiers. |
| **Rapid PVST+, PortFast and BPDU Guard** | The four switches use Rapid PVST+ for primary/standby departmental paths. PortFast accelerates endpoint startup and BPDU Guard protects configured endpoint ports; backup trunks do not use these edge features. |
| **Port and trunk hardening** | Unused switch ports are shut down, and trunks carry only required VLANs. |
| **ICMP and evidence-based troubleshooting** | Ping results, route tables, translation entries and ACL counters explain reachability and intended denials. |

OSPF is the routing control plane: it establishes where the external subnet is reachable. ACLs and PAT act on forwarded traffic. These features have separate responsibilities, even though one external request depends on all three.

## 5. ACL Design and Access Policy

### 5.1 Enforcement Locations

| ACL | Applied at | Main purpose |
| --- | --- | --- |
| ADMIN-IN | R1 Gi0/0.10, inbound | Administration services, own gateway, diagnostic Echo Requests to Faculty/Students, authorized SSH to R1 and scoped external access |
| FACULTY-IN | R1 Gi0/0.20, inbound | Faculty services, own gateway, Echo Replies to Administration and scoped external access |
| STUDENTS-IN | R1 Gi0/0.30, inbound | Student services, own gateway, Echo Replies to Administration and scoped external access |
| SERVICES-IN | R1 Gi0/0.40, inbound | Required server responses to clients, DHCP relay responses and server/gateway ICMP |
| WAN-IN | R1 Gi0/1, inbound | OSPF from R2 and selected external HTTP/ICMP replies |
| Standard ACL 1 | VTY lines on R1 and SW1–SW4 | Authorizes only source `192.168.10.98` for remote terminal access |
| NAT-CLIENTS | Referenced by R1's NAT overload rule | Selects the three client subnets for PAT |

An inbound VLAN ACL checks a packet as it enters R1 from that VLAN. A reply enters through a different interface and must satisfy that interface's ACL. The five extended filtering ACLs end with `deny ip any any`.

### 5.2 Effective Permissions

| Traffic | Decision | Explanation |
| --- | --- | --- |
| Two PCs in the same VLAN | Locally switched | R1's routed ACLs are bypassed. |
| Any client → its own gateway | ICMP Echo permitted | Confirms local gateway reachability. |
| Any client → SRV-CAMPUS | DHCP, DNS, HTTP and ICMP as configured | Shared services remain available across departments. |
| Administration → Faculty or Students | ICMP Echo permitted | Supports departmental diagnostics; does not grant unrestricted application access. |
| Faculty/Students → Administration | New routed requests blocked | Echo Replies to permitted Administration diagnostics are explicitly allowed. |
| Faculty ↔ Students | New routed requests blocked | No departmental initiation permission is provided. |
| SRV-CAMPUS → clients | New ping initiation blocked | Required DHCP/DNS/HTTP responses and ICMP Echo Replies are permitted. |
| Client VLANs → 203.0.113.10 | TCP 80 and ICMP Echo permitted | External access is limited to the demonstration host and services. |
| Client → other external addresses/services | Blocked by client ACL | An OSPF route alone does not grant permission. |
| External server → R1 outside address | Selected replies permitted | Unsolicited Echo Requests are denied by WAN-IN. |
| PC8-MGMT → campus device SSH | Permitted | The source matches the VTY source ACL. |
| Other PCs → campus device SSH | Denied | Includes unauthorized Administration PCs on the same VLAN. |

### 5.3 Important ACL Mechanics

- **Rule order matters:** Processing uses the first matching entry. Specific permits precede the final deny.
- **DHCP needs startup exceptions:** A client without a lease can use UDP source port 68 and a broadcast destination on port 67. The ACLs permit these requests as well as relevant renewal traffic.
- **Return traffic needs explicit rules:** SERVICES-IN permits DNS responses, HTTP responses with the TCP `established` check, DHCP responses and ICMP Echo Replies. Faculty and Student ACLs permit Echo Replies toward Administration.
- **These ACLs are stateless:** TCP `established` checks ACK/RST flags; it does not maintain a connection table. An Echo Reply permit likewise does not prove a matching prior Echo Request. PAT maintains translation mappings separately.
- **Same-VLAN access needs device-level controls:** PC8-MGMT can reach switch management SVIs through Layer 2 switching. The VTY ACL remains necessary even though R1 has VLAN ACLs.
- **NAT selection is separate from filtering:** NAT-CLIENTS determines eligibility for translation. It does not grant service access or replace ADMIN-IN, FACULTY-IN, STUDENTS-IN or WAN-IN. VLAN 40 is excluded from PAT.

Representative rules from the current exports illustrate the policy:

```ios
! Students may reach the campus HTTP service.
permit tcp 192.168.10.0 0.0.0.63 host 192.168.10.130 eq www

! Students may reply to Administration diagnostic pings.
permit icmp 192.168.10.0 0.0.0.63 192.168.10.96 0.0.0.31 echo-reply

! Selected WAN replies are addressed to R1's translated outside address.
permit tcp host 203.0.113.10 eq www host 198.51.100.1 established
permit icmp host 203.0.113.10 host 198.51.100.1 echo-reply
```

These are excerpts from different ACLs, not a standalone configuration to apply.

## 6. Routing and Packet Workflows

Campus VLAN routes are directly connected to R1; they do not require OSPF. R1 uses the longest matching destination prefix, applies the relevant interface policy, and forwards toward the destination subnet. Same-VLAN traffic is switched locally. Only the external server LAN depends on the OSPF-learned route, and only eligible external client traffic uses PAT.

### 6.1 A New PC Obtains Its Settings

**Example path:** Student PC → SW4 → SW1 → R1 → SW1 → SRV-CAMPUS.

1. The PC broadcasts DHCP Discover in VLAN 30 using UDP ports 68 → 67.
2. SW4 and SW1 carry the request in VLAN 30; the client ACL permits the DHCP startup traffic.
3. R1's DHCP helper relays the request to `192.168.10.130`. The relay gateway information identifies the Student subnet to the DHCP server.
4. The server selects STUDENT_POOL and returns an Offer through R1.
5. Request and Acknowledge complete the lease exchange. The PC receives its address, `/26` mask, gateway `.1` and DNS server `.130`.

Faculty and Administration follow the same process through their own subinterfaces and pools. DHCP broadcasts do not simply cross VLAN boundaries; relay makes the centralized service possible.

### 6.2 Two Students Communicate Locally

**Example path:** PC0 → SW4 → PC1.

The sender identifies the destination as local using its subnet mask, resolves the destination MAC through ARP, and sends frames directly through SW4. The packets do not visit R1. Consequently, inter-VLAN ACLs do not isolate Student PCs from one another.

### 6.3 A Student Opens the Campus Portal

**Example path:** PC0 → SW4 → SW1 → R1 → SW1 → SRV-CAMPUS.

1. The PC asks DNS server `192.168.10.130` for `portal.campus.test`.
2. Because the DNS server is outside the Student subnet, the PC resolves its gateway's MAC and sends the frame to R1 through VLAN 30.
3. STUDENTS-IN permits DNS. R1 routes the packet back down the same physical trunk in VLAN 40, and SW1 delivers it to the server.
4. SERVICES-IN permits the DNS response, which returns the address `192.168.10.130`.
5. The PC establishes a TCP connection to server port 80 and sends an HTTP request along the same routed path.
6. STUDENTS-IN permits the request, while SERVICES-IN permits the required TCP response traffic. The browser displays the portal.

R1 replaces Ethernet headers when routing between VLANs. The internal source and destination IP addresses remain unchanged; internal portal traffic does not use outside PAT.

### 6.4 Administration Performs an Allowed Diagnostic

**Example path:** PC8-MGMT → SW2 → SW1 → R1 → SW1 → SW3 → Faculty PC.

ADMIN-IN permits the ICMP Echo Request to the Faculty subnet. The destination sends an Echo Reply back through VLAN 20, where FACULTY-IN explicitly permits replies to Administration. Both directions succeed because both ingress ACLs permit their respective packet types.

### 6.5 A Student Attempts Prohibited Administration Access

**Example path:** Student PC → SW4 → SW1 → R1 **[dropped]**.

The Student PC sends an Echo Request toward an Administration address through its gateway. STUDENTS-IN has no matching permit for that request, so the final deny drops it before forwarding to VLAN 10. The expected test outcome is no Echo Reply. The packet does not reach the destination department.

### 6.6 A Client Reaches the External Server Through PAT

**Example path:** Client → departmental switch → SW1 → R1 → R2 → SRV-EXTERNAL.

1. Campus DNS resolves `external.campus.test` to `203.0.113.10`.
2. The client sends an HTTP request or ICMP Echo Request toward its default gateway.
3. Its inbound departmental ACL permits the specific external destination and protocol.
4. R1 uses the OSPF-learned route to `203.0.113.0/24`, with next hop `198.51.100.2`.
5. PAT changes the private source address to `198.51.100.1`, tracking the TCP port or ICMP identifier needed to distinguish clients.
6. R2 forwards the packet over its directly connected external LAN.
7. The external server replies to `198.51.100.1`. R2 reaches this address over the directly connected transit network.
8. WAN-IN permits the selected HTTP response or Echo Reply addressed to R1's outside address. Reverse translation restores the original client destination, and R1 forwards the reply into that client's VLAN.

R1 does **not** advertise the private campus prefixes to R2. Therefore, R2 has no route back to private clients, and successful replies depend on PAT. The two features solve different problems: OSPF supplies the outward route; PAT supplies a reachable return address and mapping.

### 6.7 Unsolicited External Traffic Fails

An external Echo Request addressed to R1's `198.51.100.1` reaches WAN-IN and is denied: the allowed ICMP entry matches Echo Replies, not new Echo Requests. An external packet addressed directly to a private campus client encounters a different problem at R2: there is no private-campus route. Campus Atlas explains both ACL denial and missing-route failure.

### 6.8 The Authorized Workstation Manages Devices

PC8-MGMT uses SSHv2 to R1 `.97` and switch SVIs `.99–.102`. Switch-bound sessions remain inside VLAN 10 and can pass through the switching infrastructure without routing at R1. Each target's VTY ACL accepts only source `.98`, so another Administration PC cannot gain the same remote terminal access merely by sharing the VLAN.

### 6.9 A Department Uses Its Backup Uplink

**Example after the Faculty primary fails:** Faculty PC → SW3 Gi0/2 → SW1 Fa0/3 → R1 → SW1 → SRV-CAMPUS.

1. Under normal conditions SW3 Gi0/1 forwards and Gi0/2 is alternate/blocking for the carried VLANs.
2. When the primary uplink fails, Rapid PVST+ makes Gi0/2 the forwarding root port, retaining VLAN 20 user traffic and VLAN 10 management connectivity.
3. Packets still use the same IP gateways, DHCP relay, DNS, ACLs and PAT configuration. This is a Layer 2 path change; OSPF does not choose between the departmental trunks.
4. When the primary returns, its lower cost makes it preferred again and the standby returns to alternate/blocking.

The November 5 test disabled all three primary departmental uplinks together. Each department's 30-probe failure sequence received 30 replies, for 90/90 total. Restoration was disruptive: each 20-probe sequence received 16 replies and lost four. Later checks recovered. The measurements describe those probe streams, not guaranteed interruption-free recovery or exact protocol convergence times.

## 7. OSPF and PAT Configuration Strategy

R1 and R2 use OSPF process 1 in area 0, with router IDs `1.1.1.1` and `2.2.2.2`. Interfaces are passive by default; only the transit-facing interfaces form an adjacency. R2 advertises `203.0.113.0/24` while keeping its server-facing interface passive. The capture records a FULL adjacency and an OSPF-learned external route on R1.

On R1, Gi0/0.10, .20 and .30 are NAT inside interfaces. Gi0/1 is NAT outside. The overload rule is:

```ios
ip nat inside source list NAT-CLIENTS interface GigabitEthernet0/1 overload
```

NAT-CLIENTS selects `192.168.10.0/26`, `192.168.10.64/27` and `192.168.10.96/27`. The services subinterface is excluded. WAN-IN separately permits OSPF from `198.51.100.2` and the selected external replies.

Recorded controlled tests demonstrate the dependencies: disabling PAT prevented external replies, and making the OSPF transit passive withdrew the external route. Restoring each feature recovered access. The campus server remained reachable during the OSPF outage because campus connected routes do not depend on that adjacency.

## 8. Website Tech Stack and Architecture

### 8.1 Campus Atlas Companion Website

Campus Atlas is a browser-based explanation and evidence viewer. It loads recorded network data and replays captured commands; it does not originate live packets or configure Packet Tracer.

| Layer | Technology | Responsibility |
| --- | --- | --- |
| User interface | React 19.3.1 and React DOM 19.3.1 | Views, interactive controls, inspectors, selection and replay state |
| Language | TypeScript 7.0.2 | Typed network models, data handling and application logic |
| Build / development | Vite 8.3.5 with the React plugin | Development server and production asset build |
| Topology visualization | React Flow through `@xyflow/react` 12.12.0 | Interactive device/link graph and packet-path presentation |
| Styling | CSS Modules and global CSS | Component styles, shared layout, responsive behavior and light/dark themes |
| Runtime / packages | Node.js 24 and npm | Build, synchronization and maintenance commands; npm lockfile fixes dependencies |
| Tests | Vitest 5.0.5 and Node-based source-identity tests | Network, topology, ping, policy and source-consistency checks |
| Data | Versioned JSON and sanitized configuration exports | Topology, services, policies, command results and evidence references |
| Evidence preparation | JavaScript synchronization scripts and Python project utilities | Capture preparation, validation and staging browser-readable assets |

Versions above come from this project's package manifest; they describe the repository's declared stack.

There is no required application backend or database in the viewer. Browser fetches load static evidence and per-source ping JSON over HTTP. React state coordinates selections across views; browser storage retains the theme preference. The production output can be served by a static HTTP server, including Python locally.

### 8.2 Data and Evidence Pipeline

```text
Packet Tracer network and recorded commands
                 |
       Project capture/export utilities
                 |
  data/*.v3.json + evidence/ + sanitized configs/
                 |
    website/scripts/sync-data.mjs
                 |
  Validated assets + per-source ping files + source identity
                 |
      React / TypeScript / React Flow viewer
```

The active datasets are:

- `network-snapshot.v3.json`: devices, links, interfaces, VLANs, DHCP pools, services, policies and test groups.
- `ping-matrix.v3.json`: the complete recorded ICMP matrix with command output, expected outcomes and evidence references.
- `policy-matrix.v3.json`: selectable policy examples tied to measured commands.
- `ospf-pat-extension.v3.json`: extension configuration context, observations and failure/recovery evidence.

The synchronization script checks dataset identities, address coverage, command evidence, asset hashes and credential sanitization. It prepares allowlisted public assets and 52 source-specific ping files. The browser loads a source's 62 commands when needed and validates the source identity before replay. Large interactive components are loaded lazily.

### 8.3 The Websites Inside Packet Tracer

The simulation also contains two simple HTTP pages. These serve a different role from Campus Atlas:

| Page | Stack and hosting | Information covered |
| --- | --- | --- |
| Internal campus portal | Static HTML served by Server-PT at `http://portal.campus.test` | Identifies the shared campus service, its three user groups, current server address `.130`, VLAN 40, and the DHCP/DNS/HTTP/routing/ACL demonstration |
| External demonstration page | Static HTML served by Server-PT at `http://external.campus.test` | Explains that access uses an OSPF-learned route and PAT; shows server `203.0.113.10` and shared outside address `198.51.100.1` |

The portal is a service-reachability demonstration. Campus Atlas contains the detailed project teaching material and interactive network exploration. Both simulated pages use unencrypted HTTP on TCP port 80.

## 9. Information Covered in Campus Atlas

| Website section | Information and interactions |
| --- | --- |
| **Introduction** | Project objective, inventory, shared-service design, technology explanations and the sequence of opening the campus portal |
| **Topology** | All 58 devices and 57 links; department highlighting, device search, interactive graph, device/interface details, link details and separate presentation of trunks versus routed links |
| **Topology guide** | Department-by-department explanations, example clients, subnets, access switches, shared trunks, router-on-a-stick and the external branch |
| **Addressing table** | VLAN networks, masks, gateways, broadcasts, DHCP ranges and capacities; static infrastructure and captured leases; OSPF transit and external LAN addresses; device/IP search |
| **Ping lab** | Source/destination selection, router interface targets, recorded command output, packet counts, request/reply animation and step-by-step forwarding explanations |
| **Access policy** | A selectable permission matrix, 23 measured policy examples, permit/deny rule details, protocols, services, enforcement locations and links to tests or ping replay |
| **Lab results** | Recorded test groups, expected and observed outcomes, individual cases, timestamps, evidence files and status filtering |
| **OSPF & PAT** | Retained campus layout, learned route, hostname browsing, translation sharing, scoped access, controlled failure and recovery |

Ping lab presets cover internal services, same-VLAN switching, Administration diagnostics, prohibited Student access, external PAT, unsolicited WAN traffic and external-to-private routing failure. It displays real captured command results while using the topology to explain one representative Echo exchange. The animation is an explanatory reconstruction rather than a new live simulation trace.

The website therefore covers three connected questions: **how the network is built, why a packet is permitted or blocked, and what recorded evidence supports that explanation.**

## 10. Evidence and Verification Status

### 10.1 November 2 Recorded Results

The v3 capture records **3,224 ping commands**, all matching the intended policy. This is **52 endpoint sources × 62 destination addresses per source**. Each source targets the other 51 endpoints, four switch management addresses and seven router interface addresses.

A passing policy test can be an intentional denial. The matrix is not a claim that all 3,224 destinations accepted traffic. Allowed commands recorded four replies; expected denials recorded zero replies.

| Recorded check | Result |
| --- | --- |
| Client addressing, own gateway, campus server ping, internal DNS and portal HTTP | 50/50 in each of five groups |
| Permitted Administration/local diagnostics | 4/4 |
| Prohibited departmental/server initiation | 5/5 |
| Authorized campus SSH | 5/5 |
| Unauthorized Administration SSH example | 1/1 |
| Student/Faculty SSH rejection | 2/2 |
| OSPF adjacency and learned route | 1/1 |
| External ICMP and hostname HTTP | 50/50 in each group |
| PAT sharing across 50 client addresses | 1/1 |
| Other external target / unsolicited WAN restrictions | 2/2 |
| DHCP renewal and saved extension settings | 1/1 |
| **Service, addressing, routing and policy checks** | **372/372 across 16 groups** |
| Complete ping matrix, additional to those groups | 3,224/3,224 policy matches |

The Lab results view represents the ping matrix as P03 with 52 source-level records. Those summaries correspond to 3,224 commands. The website acceptance report also records 44 passing automated checks, a successful production build and browser verification on 2 November 2026. These are existing recorded results, not tests rerun while preparing this document.

Some ACL-counter observations cover a capture batch and may include other commands. They should not be interpreted as isolated counters for one animated packet. The evidence retains an isolated recheck for a case affected by initial discovery.

### 10.2 November 5 Fault-Tolerance Results

The [fault-tolerance acceptance report](FAULT_TOLERANCE_ACCEPTANCE.md) records tests against the extended network, including the saved submission reopened on November 5. These checks supplement the historical v3 results; the 3,224-command matrix was not rerun for this extension.

| Check | Recorded result |
| --- | --- |
| Topology preservation | All 57 original links retained; exactly three backup departmental trunks added |
| Normal spanning-tree roles | Departmental Gi0/1 Root FWD; Gi0/2 Altn BLK for carried user/management VLANs |
| Simultaneous failure of all three primary departmental uplinks | All three backup Gi0/2 ports became Root FWD |
| Failure probe sequences | 30/30 replies per department; 90/90 total |
| Campus services through backups | All 50 PCs reached SRV-CAMPUS and loaded its portal by hostname, including successful retries |
| External services through backups | All 50 PCs reached SRV-EXTERNAL and loaded its page by hostname, including successful retries |
| DHCP and DNS through backups | One renewal and portal lookup in each department retained valid settings |
| Access controls through backups | Three expected ICMP denials with matching ACL counter increases; allowed Administration control succeeded |
| SSH through backups | PC8-MGMT authenticated to SW4; PC9-ADMIN was refused before authentication |
| Primary restoration probes | Each department received 16/20 replies and lost four; subsequent checks received 4/4 replies |
| Reopened configuration persistence | Correct costs, trunk allowlists and primary/standby roles; running/startup configurations matched on all four switches |
| Reopened service checks | All 50 PCs reached both servers and loaded the campus portal; 52 unique endpoint addresses; OSPF adjacency FULL |

Initial backup-path HTTP attempts timed out for seven campus clients and three external clients; all succeeded on retry. Reopened campus portal requests succeeded on the first attempt for all 50 clients. A general ping connectivity pass requires a received reply and can include initial packet loss; it does not mean every four-packet command received four replies. The separate 90-probe failure measurement supports the zero-observed-loss result for that sequence only.

First server replies after primary shutdown were observed at 207 ms for PC9-ADMIN, 229 ms for PC5, and 212 ms for PC0. Probes were approximately one second apart; the surrounding successful-reply gaps were 1,035–1,057 ms. These wall-clock output observations do not establish exact Rapid PVST+ convergence time. No fast-forward was used during the measured failure/restoration sequences, and exact restoration recovery duration was not measured.

### 10.3 November 5 Saved-File Identity and Documentation Audit

For the current file, use the [remediation checkpoint](docs/audit-remediation.md). The hashes and verification below belong to the November 5 milestone.

The November 5 saved file was 132,688 bytes. Its [dated submission manifest](evidence/FAULT-TOLERANCE-20261105/submission.json) records the hash. The root [SUBMISSION_SHA256.txt](SUBMISSION_SHA256.txt) tracks the current verified checkpoint.

```text
November 5 fault-tolerance submission SHA-256:
298045a4c7dba128eb84f7e37c992529955e6268cd83671ccf613e6394debdd7

Historical November 2 website / v3 capture SHA-256:
b3b7892fe2d2e80330a2c6b80df6b2cfaf1032d33b3b4ab78f88ca2883b28406
```

The earlier November 3 overview recorded an intermediate mismatch (`9d4076…` compared with the website capture). The November 5 evidence subsequently verified the fault-tolerance submission under its own file identity. The November 2 replay preserves the original matrix and capture identity.

The offline audit for the November 5 snapshot used the following command against the matching saved file.

```powershell
python scripts/verify_fault_tolerance.py
```

It verified the saved-file identity, 58-device/60-link inventory, original-link preservation, three exact added cables, recorded failover/restoration outcomes, service checks, configuration persistence and 37 hashed artifacts. The evidence and six dated sanitized exports are listed in the [fault-tolerance manifest](evidence/FAULT-TOLERANCE-20261105/manifest.json).

Older project guides reference the 56-device campus and its 2,958-case v2 matrix. The website and v3 matrix describe the later November 2 network with 57 links; current fault-tolerance evidence describes 60 links. The root `campus_index.html` template still displays the earlier `.50` server address; the captured served portal in [November 5 reopened checks](evidence/FAULT-TOLERANCE-20261105/reopened-checks.json) displays the current `.130` address.

## 11. Design Limits and Future Work

### 11.1 Design Limits at the November 5 Milestone

- **Availability:** Standby departmental trunks protect the tested uplinks/ports. R1, its core trunk, SW1, SRV-CAMPUS, each departmental switch and the external branch remain single points of failure. R2 provides the external branch rather than redundant campus routing.
- **Isolation:** Routed ACLs separate departments at R1. Hosts sharing a VLAN can communicate locally without those ACL checks.
- **Filtering:** The ACLs are stateless. The project demonstrates explicit service and reply rules rather than a stateful firewall.
- **External scope:** Only the demonstration server's HTTP and ICMP access is enabled for client VLANs. The Services VLAN is excluded from client PAT.
- **Routing scope:** OSPF uses one area and one transit adjacency. The topology does not demonstrate multi-area routing or alternate-path convergence.
- **Application security:** HTTP content is unencrypted. SSH provides encrypted device administration for the five campus IOS devices; R2 is not included in that authorized management set.
- **Verification scope:** UDP DNS was verified end to end; TCP DNS is permitted by ACL but was not exercised end to end. Functional results and the dated failure probe observations do not establish production throughput, load capacity, availability percentages or convergence guarantees.
- **Replay scope:** The companion website uses recorded addresses and commands. DHCP leases in a running simulator can change after reopening or renewal.
- **Management placement:** PC8-MGMT and switch management SVIs share Administration VLAN 10. A VTY source restriction does not provide a separate management broadcast domain.
- **Redundancy scope:** Standby trunks do not add normal forwarding capacity. EtherChannel, load balancing, redundant routers/core switches and server failover are outside the implemented design.

### 11.2 November 5 Improvement Proposals

The [Review 02 proposal](docs/review-02-remediation-plan.md) records the original suggestions. The [November 6 remediation record](docs/audit-remediation.md) tracks implementation, simulator limitations and outstanding work, including the completed VLAN 99 migration, switch port security and client-VLAN DHCP snooping.

| Proposed improvement | Purpose | Work needed before claiming completion |
| --- | --- | --- |
| Dedicated management VLAN 99 | Separate device management from ordinary Administration hosts | Migrate addressing, trunk allowlists, management SVIs and source restrictions; retest authorized and denied management |
| Port security, DHCP snooping and DAI | Strengthen endpoint attachment and Layer 2 protections | Confirm simulator support, plan trusted ports/bindings, and test legitimate and hostile behavior |
| Redundant gateways, core devices and services | Reduce remaining central failure dependencies | Redesign paths and addressing as needed; measure failure and restoration with service/policy checks |
| Stateful filtering and HTTPS | Improve session enforcement and application confidentiality | Select supported platforms and certificate handling; verify application and return traffic |
| Website recapture for the 60-link topology | Align the viewer with the November 5 submission | Produce a new dated capture and identity; rerun affected coverage and update explanations without overwriting historical results |

## 12. Additional Work and Deliverables

The project extends beyond configuring the network. Supporting work makes the design explainable, testable and recoverable.

| Work completed / available artifact | Contribution | Evidence or location |
| --- | --- | --- |
| Campus Atlas companion website | Interactive topology, addressing search, policy explorer, ping replay, explanations and recorded lab results | [Website source and maintenance guide](website/README.md); [v3 acceptance](WEBSITE_V3_ACCEPTANCE.md) |
| Internal and external simulated HTTP pages | Show actual hostname-based service delivery through the campus and OSPF/PAT paths | [November 5 served portal](evidence/FAULT-TOLERANCE-20261105/reopened-checks.json); [external page capture](evidence/WEBSITE-V3-20261102/external-http.json) |
| Packet Tracer access and capture utilities | Local bridge/API clients and repeatable command/evidence collection | [Bridge](scripts/pt_bridge.py), [client](scripts/pt_client.py), [project API](scripts/project_api.py) |
| Expansion, routing and evidence scripts | Implemented staged expansion and supported later capture/verification workflows | [Scale verifier](scripts/scale50_verify.py), [OSPF/PAT extension](scripts/extend_ospf_pat.py), [v3 capture](scripts/capture_website_v3.py) |
| Automated viewer checks | Validate topology, subnet logic, policy examples, ping explanations and source identity | [Website tests](website/src/lib/), [source-identity tests](website/scripts/source-identity.test.mjs), [package scripts](website/package.json) |
| Evidence synchronization and integrity | Validate versioned inputs, references, sanitized assets and recorded-file identity before staging viewer assets | [Data synchronization](website/scripts/sync-data.mjs); [fault-tolerance audit](scripts/verify_fault_tolerance.py) |
| Sanitized configuration exports | Preserve exact interface, routing, filtering and switch settings for review | [Configuration directory](configs/); six current exports matched by the November 5 manifest |
| Recovery and historical archives | Preserve earlier work and allow restoration before expansion or fault-tolerance experiments | Local `archive/earlier-campus-work.zip` and dated recovery ZIPs; archive members are cited in Section 13 |
| Printable campus labs | Separate walkthroughs for topology/addressing, centralized services and access policy | [Lab 1](output/pdf/01-topology-and-addressing.pdf), [Lab 2](output/pdf/02-centralized-services.pdf), [Lab 3](output/pdf/03-access-policy.pdf) |
| Presentation variants | Available project slides, updated deck and faculty walkthrough | [Updated presentation](output/presentation/CampusAtlas_Computer_Networks_Updated.pptx), [faculty walkthrough](output/presentation/CampusAtlas_Faculty_Walkthrough.pptx) |
| Team viva and demonstration preparation | Slide ownership, technical explanation tasks and a shared rehearsal sequence | [Team viva preparation](TEAM_VIVA_PREPARATION.md) |

Slide assignments describe presentation responsibility; they do not establish who originally implemented each feature. The available decks and printed labs may reflect earlier milestones and should be checked against the 60-link design before reuse. This documentation update does not revise those artifacts. Earlier simulations and recovery archives can contain lab credentials and remain local, as documented in the project README.

## 13. Versions and Iterations

Dates below are in IST where the source supplies a date/time. The project evolved through network, website and evidence milestones. **v1, v2 and v3 identify existing datasets/captures**; the November 5 fault-tolerance extension has a named evidence run and is not assigned an invented v4 label. A scope document or blueprint records intent, while acceptance evidence records implementation.

### 13.1 Chronological Development Record

| Date / milestone | Motivation and principal changes | Results and supporting source |
| --- | --- | --- |
| **11 October 2026 — original VLAN/ACL prototype** | Build departmental separation with one 1941 router, one 2960 switch, ten PCs and one server. Four equal `/28` subnets; router-hosted DHCP; server `.50`; browsing by IP. No OSPF, PAT or external branch. | User-shared CLI/tests documented VLANs, trunks, leases, server HTTP and intended denials. Cabling, a mistaken extra PC, convergence and unsupported ACL `log` syntax were addressed. [Master summary](../Lab/Packet%20Tracer/Secure_Campus_Network_Master_Summary.md) and [troubleshooting summary](../Lab/Packet%20Tracer/Secure_Campus_Network_Troubleshooting_Master_Summary.md) explicitly limit their independent verification claims. |
| **29 October — formalized centralized-services scope** | Select the current formal title. Plan centralized DHCP/DNS/HTTP, relay, explicit request/reply policies, SSH management and an interactive viewer. | [Scope](../Project/PROJECT_SCOPE.md) and [implementation roadmap](../Project/IMPLEMENTATION_GUIDE_AND_ROADMAP.md) record agreed requirements and a ten-PC/two-switch baseline; their planning language is historical. |
| **30 October — centralized services, N4 acceptance and W0/v1 foundation** | Implement the 14-device/13-link network: ten PCs, two switches, one router and one server. Retain four `/28` subnets; move DHCP to SRV-CAMPUS with relay, add DNS/hostname portal, reserve a static management PC and constrain SSH. Create typed/versioned evidence for the viewer. | Archived `N4_ACCEPTANCE.md` records 19 passing acceptance rows including reopened-file controls; `W0_SNAPSHOT.md` records 835 domain/file checks plus schema/runtime validation. These are distinct check types, not one aggregate test count. |
| **30 October — full endpoint ping replay evidence** | Extend beyond selected acceptance examples with endpoint-originated command coverage and allowed/denied results for the viewer. | Archived `evidence/PING-20261030/ANALYSIS.md` records **176/176 policy matches**: 73 permitted and 103 denied. Eleven endpoint sources × 16 destination addresses; this later capture has its own saved-file identity. |
| **31 October — 50-PC expansion / v2** | Expand to 12 Administration, 18 Faculty and 20 Student PCs using four switches. Replace equal client `/28`s with VLSM; relocate server, gateways and management addresses. Central services and ACL/SSH behavior retained. | **56 devices, 55 links**, 49 DHCP clients plus one static PC. [Scale acceptance](SCALE_50_ACCEPTANCE.md) records **272/272 checks** after reopening; [v2 ping analysis](PING_ANALYSIS.md) records **2,958/2,958 policy matches**. [Design](SCALE_50_DESIGN.md) explains the migration. |
| **2 November — OSPF/PAT external branch** | Add R2, SRV-EXTERNAL and two routed links while retaining the 55 campus links. Teach dynamic route learning, shared outside addressing and scoped external access. | **58 devices, 57 links**. [Extension acceptance](OSPF_PAT_ACCEPTANCE.md) and [walkthrough](docs/ospf-pat-extension.md) record FULL adjacency, learned external route, translation and controlled OSPF/PAT failure/recovery. |
| **2 November — integrated website / v3 evidence** | Recapture the extended topology across website views; expand ping targets to include external endpoints and router interfaces. Add technology introduction and correct policy-matrix alignment. | [Website acceptance](WEBSITE_V3_ACCEPTANCE.md) records **3,224/3,224 policy matches**, **372/372 other checks**, 44 automated checks, production build and browser verification. Local Git commits also record the introduction, alignment fix and integrated OSPF/PAT update. |
| **2–3 November — presentation, viva and consolidated overview** | Prepare project explanations, slide variants and team demonstration ownership; assemble an overview against the November 2 design. | [Updated slides](output/presentation/CampusAtlas_Computer_Networks_Updated.pptx), [team preparation](TEAM_VIVA_PREPARATION.md), and this overview's earlier November 3 baseline. The earlier overview disclosed an intermediate saved-file mismatch; Section 10 now records the verified newer file. |
| **5 November — redundant uplinks and current project record** | Retain all devices and 57 earlier cables; add three backup departmental trunks. Use Rapid PVST+, root selection and explicit standby costs. Correct persistence of per-VLAN cost settings and validate reopening. Expand this record with full history, latest addressing and technical skills. | **58 devices, 60 links**. [Fault-tolerance acceptance](FAULT_TOLERANCE_ACCEPTANCE.md) records 90/90 failure probes, restoration loss, service/policy/SSH checks and persistence. Offline integrity audit passed for the current saved file and 37 hashed artifacts. Website remains on its dated v3 capture. |
| **6 November — audit remediation and dual-core migration** | Re-establish the saved-file baseline, harden device and service settings, isolate VLAN 99, test Layer 2 protections and add monitoring and routing authentication. Move the original gateway addresses to HSRP on two multilayer cores. | **60 devices, 64 links**. The [remediation record](docs/audit-remediation.md) gives the current verified checkpoint, both core outage tests and simulator limitations. |

The early N4/W0 and ping documents are members of local `archive/earlier-campus-work.zip`, not loose files at their former paths. They were inspected directly inside the archive without extracting recovery simulations or credentials. Member paths above identify their exact locations; archive contents were not republished.

### 13.2 Addressing and Service Evolution

| Segment / feature | October prototype and centralized-services v1 | Expanded v2, external v3 and November 5 network |
| --- | --- | --- |
| Administration VLAN 10 | 192.168.10.0/28; gateway .1 | 192.168.10.96/27; gateway .97 |
| Faculty VLAN 20 | 192.168.10.16/28; gateway .17 | 192.168.10.64/27; gateway .65 |
| Students VLAN 30 | 192.168.10.32/28; gateway .33 | 192.168.10.0/26; gateway .1 |
| Services VLAN 40 | 192.168.10.48/28; gateway .49; server .50 | 192.168.10.128/28; gateway .129; server .130 |
| Subnetting method | Equal-size `/28` allocation (FLSM) | Different `/26`, `/27`, `/28` allocations (VLSM) |
| DHCP ownership | October 11: router pools; October 30: centralized server with relay | Central server with three departmental pools and relay; 49 dynamic PCs |
| Name-based service access | October 11: IP-based HTTP, DNS not required; October 30: DNS and hostname portal | Internal and external hostname access; external hostname added with OSPF/PAT |
| Management workstation | v1 static PC8-MGMT at .2 | Static PC8-MGMT at .98; switch SVIs .99–.102 |
| External connectivity | None in the isolated campus | R2 and external server added November 2; campus clients use OSPF/PAT |
| Departmental uplinks | Single paths in earlier baselines | Primary plus standby per department from November 5 |

VLSM was introduced with the October 31 expansion, before the OSPF/PAT addition. The later extension retained campus addressing. Host capacity, DHCP pool capacity, physical port capacity and measured performance are separate quantities.

### 13.3 Ping Coverage by Capture

| Capture | Endpoint sources | Destinations per source | Commands | What the result means |
| --- | ---: | ---: | ---: | --- |
| PING-20261030, earlier network | 11 | 16 | 176 | 73 allowed and 103 denied combinations matched policy |
| PING-20261031 / v2 | 51 | 58 | 2,958 | 1,447 allowed and 1,511 denied combinations matched policy |
| WEBSITE-V3-20261102 / v3 | 52 | 62 | 3,224 | Every recorded allowed/denied combination matched policy |
| FAULT-TOLERANCE-20261105 | Targeted service, policy and failure checks | Not a complete directed matrix | No replacement matrix claimed | Validates the new backup-path behavior and reopened state |

Sources exclude infrastructure-originated ping diagnostics and self-pings. v1 targets the other ten endpoints, two switch management IPs and four gateway IPs. v2 targets the other 50 endpoints, four switch management IPs and four gateway IPs. v3 targets the other 51 endpoints, four switch management IPs and seven router interface IPs. Expected denial is a successful policy test, not successful reachability.

## 14. Current Technical Skills Used

These skills are supported by project artifacts and describe work demonstrated by the project. They do not assign individual authorship or imply professional certification. Future proposals such as DAI are excluded from the implemented skill claims.

| Skill | Concrete use in this project | Supporting artifact |
| --- | --- | --- |
| Network requirements and architecture | Translate departmental access and shared-service needs into roles, VLANs and a hierarchical campus | [Scope](../Project/PROJECT_SCOPE.md), [topology guide](docs/topology.md) |
| Cisco Packet Tracer and IOS configuration | Configure interfaces, trunks, subinterfaces, services and saved/startup state. Inspect a reopened simulation. | [Current checkpoint exports](evidence/AUDIT-REMEDIATION-20261105-182333/verified-submission.json), [November 5 acceptance](FAULT_TOLERANCE_ACCEPTANCE.md) |
| IPv4 subnetting and VLSM | Migrate equal `/28`s to capacity-based `/26`, `/27`, `/28` segments; reserve static and DHCP ranges | [Scale design](SCALE_50_DESIGN.md), Section 3 tables |
| VLANs, Ethernet and router-on-a-stick | Separate broadcast domains, carry VLANs on trunks and route using R1 subinterfaces | [Topology](docs/topology.md), [R1 export](configs/R1-CAMPUS-CURRENT.txt) |
| Centralized service configuration | Supply DHCP pools through relay; configure DNS and internal/external HTTP demonstrations | [Centralized services](docs/centralized-services.md), [reopened evidence](evidence/FAULT-TOLERANCE-20261105/reopened-checks.json) |
| ACL design and packet-path reasoning | Account for ingress interfaces, protocols, request/reply directions and intentional denials | [Access policy](docs/access-policy.md), [R1 export](configs/R1-CAMPUS-CURRENT.txt) |
| Secure device administration | Limit SSHv2 to the static management workstation and verify rejected sources | [Scale acceptance](SCALE_50_ACCEPTANCE.md), [backup-path SSH evidence](evidence/FAULT-TOLERANCE-20261105/backup-path-ssh-authorized.json) |
| Dynamic routing and address translation | Establish OSPF area 0, learn the external prefix, configure PAT and explain the return path | [OSPF/PAT walkthrough](docs/ospf-pat-extension.md), [extension evidence](OSPF_PAT_ACCEPTANCE.md) |
| Layer 2 redundancy and fault analysis | Select a root bridge, control primary/standby costs, inject failures and measure recovery observations | [Fault-tolerance design](docs/fault-tolerance.md), [failure measurements](evidence/FAULT-TOLERANCE-20261105/failure-measurements.json) |
| Management segmentation and Layer 2 hardening | Migrate authorized management to VLAN 99, bind expected endpoint MACs and validate DHCP renewal with snooping | [Remediation record](docs/audit-remediation.md), [MAC violation test](evidence/AUDIT-REMEDIATION-20261105-182333/iteration3-mac-violation.json) |
| Routing authentication and monitoring | Restart OSPF with matching and mismatched keys, collect syslog events and check NTP persistence | [OSPF evidence](evidence/AUDIT-REMEDIATION-20261105-182333/iteration4-ospf-behavior.json), [monitoring persistence](evidence/AUDIT-REMEDIATION-20261105-182333/iteration4-monitoring-reopened.json) |
| First-hop and core redundancy | Migrate gateways to HSRP SVIs, build independent routed edge paths and validate DHCP, PAT and policy with either core powered off | [Dual-core failure tests](evidence/AUDIT-REMEDIATION-20261105-182333/iteration5-core-failover.json), [reopened routing](evidence/AUDIT-REMEDIATION-20261105-182333/iteration5-reopened-routing.json) |
| Troubleshooting and protocol analysis | Use ARP behavior, interface state, DHCP leases, routing tables, ACL counters and NAT translations to explain results | [Tests conducted](docs/tests-conducted.md), [ping analysis](PING_ANALYSIS.md), Section 6 workflows |
| Python automation | Collect simulator output, support expansion/capture, normalize records and audit saved evidence | [Scripts](scripts/), [offline verifier](scripts/verify_fault_tolerance.py) |
| React, TypeScript and React Flow | Build coordinated topology, inspector, addressing, policy and ping-replay views using typed network data | [Website application](website/src/app/App.tsx), [models](website/src/models/network.ts), [components](website/src/components/) |
| HTML/CSS and responsive interface design | Create served portal content and style the companion viewer with CSS Modules, global styles and themes | [Captured portal](evidence/FAULT-TOLERANCE-20261105/reopened-checks.json), [website styles](website/src/styles/global.css) |
| JavaScript tooling and automated verification | Synchronize static evidence, build through Vite/TypeScript, and validate logic with Vitest and Node checks | [Package manifest](website/package.json), [sync script](website/scripts/sync-data.mjs) |
| Data modeling and evidence integrity | Maintain versioned JSON captures, distinguish observed leases, validate references and compare SHA-256 identities | [v3 snapshot](data/network-snapshot.v3.json), [fault-tolerance manifest](evidence/FAULT-TOLERANCE-20261105/manifest.json) |
| Git and configuration history | Track viewer/document changes and preserve earlier datasets and exports for comparison | Local Git history, [configuration directory](configs/), Section 13 chronology |
| Technical writing and presentation | Connect objectives, topology, addressing, policy, tests, limitations and demonstration tasks | This record, [printable labs](output/pdf/), [viva preparation](TEAM_VIVA_PREPARATION.md) |

## 15. Demonstration and Source References

A useful presentation sequence is: introduce the objective, show the four campus VLANs and external branch, explain the VLSM plan, open the campus portal, compare an allowed Administration ping with a denied Student ping, inspect the OSPF route and PAT translations, then use Lab results to show the evidence.

For a live simulator demonstration, inspect rather than assume the current state:

```text
Client: ipconfig /all
Client: nslookup portal.campus.test
Client browser: http://portal.campus.test
Client browser: http://external.campus.test
R1: show ip ospf neighbor
R1: show ip route ospf
R1: show ip nat translations
R1: show ip nat statistics
R1: show access-lists
Switch: show interfaces trunk
Switch: show vlan brief
Switch: show spanning-tree vlan 10
```

To build and present Campus Atlas locally, run these commands from the project's `website` directory:

```powershell
.\run.ps1 build
.\run.ps1 preview
```

Open `http://127.0.0.1:4173/`. This is the companion website on the host computer; simulated campus hostnames are opened inside Packet Tracer clients.

| Source | Use |
| --- | --- |
| [Latest fault-tolerance acceptance](FAULT_TOLERANCE_ACCEPTANCE.md) and [design](docs/fault-tolerance.md) | November 5 implementation, primary/standby paths, failure and restoration observations |
| [Latest reopened checks](evidence/FAULT-TOLERANCE-20261105/reopened-checks.json), [submission identity](evidence/FAULT-TOLERANCE-20261105/submission.json) and [manifest](evidence/FAULT-TOLERANCE-20261105/manifest.json) | Current endpoint observations, 60-link topology and verified saved-file/evidence identities |
| [Website network snapshot](data/network-snapshot.v3.json) | November 2 inventory, interfaces, addressing, services and recorded test groups; 57 links |
| [Website ping matrix](data/ping-matrix.v3.json) | November 2 complete measured ICMP coverage and command results |
| [Website policy examples](data/policy-matrix.v3.json) | Measured examples behind the November 2 website matrix |
| [Website OSPF/PAT walkthrough data](data/ospf-pat-extension.v3.json) | Routing, translation and dated failure/recovery observations |
| [R1 configuration](configs/R1-CAMPUS-CURRENT.txt) and [R2 configuration](configs/R2-EXTERNAL-CURRENT.txt) | Exact routing, interface, NAT and filtering configuration |
| [Configuration directory](configs/) | Current sanitized switch exports and historical configuration files |
| [Website acceptance report](WEBSITE_V3_ACCEPTANCE.md) | November 2 website and capture verification |
| [Extension acceptance report](OSPF_PAT_ACCEPTANCE.md) | Extension tests and controlled recovery evidence; some website-scope prose predates v3 integration |
| [Website package manifest](website/package.json) | Declared libraries, versions and build/test scripts |
| [Website application](website/src/app/App.tsx) and [maintenance guide](website/README.md) | Navigation, viewer structure and data workflow |
| [Captured internal portal](evidence/WEBSITE-V3-20261102/http-all.json) and [external page](evidence/WEBSITE-V3-20261102/external-http.json) | Actual served HTML recorded from clients |
| [Original prototype summary](../Lab/Packet%20Tracer/Secure_Campus_Network_Master_Summary.md), [formal scope](../Project/PROJECT_SCOPE.md), [scale acceptance](SCALE_50_ACCEPTANCE.md) and [historical ping analysis](PING_ANALYSIS.md) | Development context and stage-specific results |
| Local `archive/earlier-campus-work.zip` members `N4_ACCEPTANCE.md`, `W0_SNAPSHOT.md`, `evidence/PING-20261030/ANALYSIS.md` | Earlier centralized-services implementation, snapshot validation and 176-command capture; read as archive members |
