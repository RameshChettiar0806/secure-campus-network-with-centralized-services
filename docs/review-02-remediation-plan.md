# Review 02 Engineering Remediation & Defense Guide

**Project:** Secure Campus Network with Centralized Services  
**Target:** Engineering Review 02 Assessment & Viva Defense  
**Prepared for:** Ramesh (Technical Lead) and CampusAtlas Team (Devarpan, Aadi, Aditya Vardhan)  
**Date:** November 2026  

> This guide records the original Review 02 proposals. Use the [verified remediation record](audit-remediation.md) for the current port map, implemented controls and simulator limitations.

---

## Executive Summary

The faculty review for Review 01 was a rigorous, industry-grade network design review. The review correctly identified that while the baseline network successfully demonstrates VLAN segmentation, router-on-a-stick, DHCP relay, DNS/HTTP services, and OSPF/PAT routing, it possesses critical single points of failure (SPoFs), relies on stateless ACLs, lacks dedicated management out-of-band segmentation, and has vulnerabilities at Layer 2.

Rather than risking an uncontrolled redesign that breaks the 58-device topology and 3,224-test matrix, this plan implements the review's recommended three-tier engineering framework:
1. **Tier 1 (Category A): Verification & Integrity Assurance** — Resolve hash discrepancies, certify running configurations, and calibrate website labeling.
2. **Tier 2 (Category B): Targeted High-Value Hardening** — Dedicated Management VLAN (VLAN 99), Switch Port Security, DHCP Snooping, Dynamic ARP Inspection (DAI), and port auditing.
3. **Tier 3 (Category C): Architectural Defense & Viva Mastery** — Defend enterprise trade-offs (HSRP, L3 aggregation, stateful inspection) with engineering precision.

---

## 1. Subnet Sizing Correction: FLSM vs. VLSM

> [!IMPORTANT]
> **Key Viva Win:** The Review 01 feedback noted that the network used uniform `/28` subnets. While early iterations (v1) used `/28` FLSM, **the v3 network already upgraded to VLSM**!

During Review 02, present this progression proactively:

| Segment | Early Iteration (v1) | Current Implemented Architecture (v3) | Usable Hosts | Design Justification |
| :--- | :--- | :--- | :---: | :--- |
| **Students (VLAN 30)** | `192.168.10.32/28` (14 hosts) | `192.168.10.0/26` (255.255.255.192) | 62 | High endpoint density (20 active PCs, scalable) |
| **Faculty (VLAN 20)** | `192.168.10.16/28` (14 hosts) | `192.168.10.64/27` (255.255.255.224) | 30 | Medium density (18 active PCs) |
| **Administration (VLAN 10)** | `192.168.10.0/28` (14 hosts) | `192.168.10.96/27` (255.255.255.224) | 30 | Low-to-medium density (12 active PCs) |
| **Services (VLAN 40)** | `192.168.10.48/28` (14 hosts) | `192.168.10.128/28` (255.255.255.240) | 14 | Infrastructure static servers only |
| **Unallocated Reserve** | None (tightly packed) | `192.168.10.144` – `192.168.10.255` | 112 | Unassigned space reserved for future subnets |

**Defense Talking Point:**
> *"In our initial lab prototype, we identified FLSM /28 address exhaustion in the Student network. We redesigned the addressing hierarchy using VLSM, granting Students a /26 block, Faculty/Admin /27 blocks, and preserving 112 host addresses above .144 for future expansion without overlapping subnets."*

---

## 2. Category A: Verification & Integrity Actions

### 2.1 Resolving the Submission `.pkt` Hash Discrepancy
The review highlighted that `Secure_Campus_Network_Submission.pkt` had changed on disk (`9d4076...`) relative to `SUBMISSION_SHA256.txt` (`b3b789...`).
* Packet Tracer recalculates file timestamps and internal UI view states upon saving, altering the SHA-256 hash even if no logical configuration changed.
* **Remediation:** 
  1. Open the `.pkt` in Packet Tracer 9.0.1.
  2. Verify that running-config matches `configs/*-CURRENT.txt`.
  3. Execute `write memory` on all devices.
  4. Save the file cleanly.
  5. Recalculate hash: `Get-FileHash .\Secure_Campus_Network_Submission.pkt -Algorithm SHA256`.
  6. Update `SUBMISSION_SHA256.txt` and timestamp in `PROJECT_OVERVIEW.md`.

### 2.2 CampusAtlas Website Labeling Calibration
The review cautioned against presenting CampusAtlas as a "live monitoring system."
* **Remediation in UI & Docs:**
  * Header badge updated from "Live Network Status" to **"Snapshot V3 — Verified Static Telemetry & Evidence Explorer"**.
  * Add explicit metadata banner: `Capture Baseline: November 2, 2026 | Simulation Engine: Cisco Packet Tracer 9.0.1 | Verified Tests: 3,224/3,224 Passing`.
  * Clarify that animations are **deterministic packet-flow reconstructions** based on recorded CLI trace data, not live websocket packets.

---

## 3. Category B: High-Value Hardening Blueprints

### 3.1 Dedicated Management VLAN (VLAN 99)
Currently, PC8-MGMT (`.98`) and switch SVIs (`.99-.102`) share VLAN 10 with ordinary Administration PCs. A compromised Admin endpoint could attempt ARP spoofing or flood attacks against switch management interfaces.

#### Architecture:
* **VLAN ID:** 99 (`MANAGEMENT`)
* **Subnet:** `192.168.10.144/28` (from unallocated reserve)
* **Subnet Mask:** `255.255.255.240`
* **Default Gateway (R1 Gi0/0.99):** `192.168.10.145`
* **PC8-MGMT Static IP:** `192.168.10.146`
* **SW1-CORE SVI (Vlan 99):** `192.168.10.147`
* **SW2-ACCESS SVI (Vlan 99):** `192.168.10.148`
* **SW3-FACULTY SVI (Vlan 99):** `192.168.10.149`
* **SW4-STUDENTS SVI (Vlan 99):** `192.168.10.150`

#### Configuration Commands:

**1. On R1-CAMPUS:**
```ios
interface GigabitEthernet0/0.99
 description VLAN99_MANAGEMENT
 encapsulation dot1Q 99
 ip address 192.168.10.145 255.255.255.240
 ip access-group MGMT-IN in
 exit

! Restrict MGMT-IN to only permitted SSH and ICMP diagnostics
ip access-list extended MGMT-IN
 permit tcp host 192.168.10.146 192.168.10.144 0.0.0.15 eq 22
 permit tcp host 192.168.10.146 host 192.168.10.97 eq 22
 permit icmp host 192.168.10.146 any
 deny ip any any
```

**2. On SW1-CORE (and propagated to SW2, SW3, SW4):**
```ios
vlan 99
 name MANAGEMENT
 exit

! Update trunk allowed lists on SW1
interface GigabitEthernet0/1
 switchport trunk allowed vlan 10,20,30,40,99
interface GigabitEthernet0/2
 switchport trunk allowed vlan 10,99
interface FastEthernet0/23
 switchport trunk allowed vlan 10,20,99
interface FastEthernet0/24
 switchport trunk allowed vlan 10,30,99
interface FastEthernet0/2
 switchport trunk allowed vlan 10,99
interface FastEthernet0/3
 switchport trunk allowed vlan 10,20,99
interface FastEthernet0/4
 switchport trunk allowed vlan 10,30,99

! Migrate SVI
interface Vlan10
 no ip address
 shutdown
interface Vlan99
 description MANAGEMENT_SVI
 ip address 192.168.10.147 255.255.255.240
 no shutdown
ip default-gateway 192.168.10.145

! VTY Source ACL update
access-list 1 permit host 192.168.10.146
```

**3. On SW2-ACCESS:**
```ios
! Move PC8-MGMT access port (e.g., Fa0/12) to VLAN 99
interface FastEthernet0/12
 description PC8-MGMT_PORT
 switchport mode access
 switchport access vlan 99
 spanning-tree portfast
 spanning-tree bpduguard enable
```

---

### 3.2 Layer 2 Security Hardening

#### A. Switch Port Security
Prevents MAC flooding and unauthorized endpoint attachments.
Applied to all access ports across SW2, SW3, and SW4:

```ios
! Example applied on access range Fa0/1 - Fa0/20 on SW4-STUDENTS
interface range FastEthernet0/1 - 20
 switchport mode access
 switchport port-security
 switchport port-security maximum 2
 switchport port-security mac-address sticky
 switchport port-security violation restrict
 switchport port-security aging time 10
 exit
```
* **Explanation:** `sticky` dynamically learns the device's MAC address and commits it to the running-config. If an unauthorized laptop is plugged in, the violation mode `restrict` drops frames from the unknown MAC, increments the security violation counter, and generates a syslog message without taking down the physical port (or `shutdown` for stricter containment).

#### B. DHCP Snooping
Prevents rogue DHCP servers from handing out invalid default gateways or rogue DNS settings (mitigating DHCP spoofing / Man-in-the-Middle).

Applied on SW1-CORE, SW2, SW3, SW4:
```ios
! Global enable
ip dhcp snooping
ip dhcp snooping vlan 10,20,30,40

! Configure trusted uplink interfaces (where legitimate DHCP offers originate)
! On SW1-CORE:
interface FastEthernet0/1
 description TRACE_TO_SRV-CAMPUS
 ip dhcp snooping trust

interface GigabitEthernet0/1
 description TRUNK_TO_R1
 ip dhcp snooping trust

! On SW2, SW3, SW4:
interface GigabitEthernet0/1
 description UPLINK_TO_SW1
 ip dhcp snooping trust
```
* **Explanation:** Access ports connected to PCs remain **untrusted** by default. If a malicious student runs a rogue DHCP server daemon, DHCP Offer / ACK packets received on untrusted access ports are discarded immediately by the switch.

#### C. Dynamic ARP Inspection (DAI)
Prevents ARP poisoning and MITM attacks by validating ARP packets against the DHCP snooping binding database.

```ios
! On access switches (where supported in PT switch image)
ip arp inspection vlan 10,20,30
interface GigabitEthernet0/1
 ip arp inspection trust
```
* **Explanation:** If a client attempts to claim another host's IP address (e.g. gateway `.1`) via gratuitous ARP, the switch inspects the ARP payload against its snooping database and drops the forged packet.

#### D. Unused Port Lockdown
Confirm each unused port against the physical link export before assigning it to the shutdown parking VLAN. In the November 5 and Iteration 4 single-core topology, SW1 FastEthernet0/1 connects SRV-CAMPUS and FastEthernet0/2–4 are live backup trunks. The range below applies only to the confirmed unused SW1 ports in that topology.
```ios
interface range FastEthernet0/5 - 22
 shutdown
```

---

### 3.3 Device Logging & Time Synchronization (NTP)

Configure centralized event recording on R1 and switches:
```ios
service timestamps log datetime msec
service timestamps debug datetime msec
logging buffered 16384 informational
logging console informational

! Point to campus server for NTP (if NTP service active on Server-PT)
ntp server 192.168.10.130
```

---

## 4. Category C: Architectural Trade-Offs & Viva Defense Playbook

During Review 02, the examiner will challenge architectural choices. The table below arms the team with authoritative, technically sound answers that turn perceived weaknesses into proof of engineering maturity.

### The 5 Core Faculty Questions

#### Q1: "What happens if your main router (R1) fails?"
> **Answer:**  
> *"In our current design, R1-CAMPUS is a single point of failure because it terminates all four VLAN default gateways and executes inter-VLAN routing and DHCP relay. If R1 fails, inter-VLAN routing, relay, and external NAT cease, though intra-VLAN traffic on local access switches continues.*  
> *In an enterprise deployment, this single point of failure is mitigated using **First Hop Redundancy Protocols (FHRP)** such as **HSRP (Hot Standby Router Protocol)** or **VRRP**, deploying a pair of redundant routers sharing a virtual gateway IP, backed by dual uplinks and dynamic routing. For our 50-host academic scope, a single router-on-a-stick topology was chosen to clearly demonstrate 802.1Q subinterface encapsulation, directional ACLs, and NAT boundaries without unnecessary protocol overhead."*

#### Q2: "Can your Student VLAN ACL prevent two Students from communicating with each other?"
> **Answer:**  
> *"No, router ACLs cannot filter same-VLAN communication. Because PC0 and PC1 reside in the same broadcast domain (`192.168.10.0/26`), their traffic is switched directly at Layer 2 across SW4 via MAC table lookups and does not traverse the default gateway on R1.*  
> *In Review 01, we demonstrated this via test case N18. To enforce endpoint isolation within the same VLAN in production, we would deploy **Private VLANs (PVLANs)** with isolated secondary VLANs, switchport **Protected Ports**, or 802.1X endpoint micro-segmentation."*

#### Q3: "Why did you use stateless ACLs instead of a firewall?"
> **Answer:**  
> *"Extended Cisco IOS ACLs evaluate packets statelessly on an ordered rule-by-rule basis looking at 5-tuple headers (source/dest IP, protocol, source/dest port). Because they do not maintain a dynamic connection state table, we engineered explicit symmetric return rules (such as matching TCP `established` flags on ACK/RST, and permitted ICMP Echo Replies).*  
> *A stateful firewall (or Cisco Zone-Based Policy Firewall - ZFW) would track state tables and automatically permit ephemeral return sessions. We utilized extended stateless ACLs deliberately to master granular directional traffic control, wildcard mask mathematics, and rule ordering at the network layer."*

#### Q4: "What happens if the centralized server (SRV-CAMPUS) fails?"
> **Answer:**  
> *"SRV-CAMPUS consolidates DHCP, DNS, and HTTP on a single endpoint, creating a shared failure domain. However, the failure impact has distinct time phases:*  
> *1. **HTTP failure is immediate** — the campus portal becomes unreachable.*  
> *2. **DNS failure is buffered** — clients with active DNS cache entries continue resolving hostnames until TTL expires.*  
> *3. **DHCP failure is deferred** — existing clients retain their assigned leases until the renewal timer (`T1 = 0.5 * Lease`) expires. Only new clients and lease renewals fail immediately.*  
> *In production, these services are decoupled across dedicated, redundant virtual machines with secondary DNS servers, split DHCP scopes, and high-availability HTTP clusters."*

#### Q5: "Is CampusAtlas a live monitoring dashboard or a static viewer?"
> **Answer:**  
> *"CampusAtlas is a post-execution evidence and verification explorer, not an active SNMP/telemetry network monitoring system. It parses a verified, versioned snapshot (`v3`) of the network state, device configurations, and 3,224 captured test outputs.*  
> *This decouples verification from simulation run-time variations, providing deterministic, repeatable proof of security policies and packet forwarding paths. Real-time telemetry via SNMPv3, NetFlow, or telemetry agents is scoped as a future extension."*

---

### Additional Examiner Challenge Questions

#### Q6: "Why did you use PAT (NAT Overload) instead of Dynamic NAT?"
> **Answer:**  
> *"Dynamic NAT maps private addresses to a 1:1 pool of public IPs. With 50 campus endpoints, Dynamic NAT would require 50 public IPv4 addresses, which is wasteful and unrealistic under IPv4 address exhaustion. PAT (NAT Overload) translates all 50 campus endpoints to a single external interface address (`198.51.100.1`) by multiplexing unique Layer 4 source port numbers (and ICMP query IDs), achieving high address conservation."*

#### Q7: "Why is SW1-CORE a bigger failure domain than SW2, SW3, or SW4?"
> **Answer:**  
> *"SW1 aggregates the entire campus switching fabric: the trunk to R1, the server link, and the downlinks to SW2, SW3, and SW4. A failure of SW4 only affects Students; a failure of SW1 partitions all departments from each other, from the central server, and from the router. In enterprise design, this is resolved via a dual-switch distribution layer utilizing **Multi-chassis EtherChannel (MEC)** or Cisco StackWise with redundant routed uplinks."*

#### Q8: "How do your switch configurations prevent switching loops and rogue switches?"
> **Answer:**  
> *"We utilize **Per-VLAN Spanning Tree Plus (PVST+)**. All edge access ports connecting to PCs have **PortFast** and **BPDU Guard** enabled. PortFast transitions ports immediately to forwarding, avoiding 30-second listening/learning delays, while BPDU Guard immediately error-disables any edge port that receives a BPDU frame, preventing unauthorized rogue switches from disrupting the STP topology."*

---

## 5. Summary Presentation Checklist for Review 02

- [x] **Acknowledge Review 01 Feedback Upfront**: Show maturity by opening with: *"Following Review 01, we conducted an engineering vulnerability review focusing on single points of failure, Layer 2 hardening, and out-of-band management separation."*
- [x] **Clarify the VLSM Upgrade**: Highlight that the campus utilizes VLSM (`/26`, `/27`, `/28`), leaving unallocated space for growth.
- [x] **Demonstrate Layer 2 Hardening**: Show Port Security sticky MAC tables and DHCP snooping trust configuration on switches.
- [x] **Explain Management Isolation**: Present the dedicated Management VLAN 99 blueprint that decouples PC8-MGMT from user data traffic.
- [x] **Execute Live Demo Smoothly**:
  1. `ipconfig /all` on Student PC.
  2. Ping gateway (`192.168.10.1`) -> Success.
  3. Ping portal (`192.168.10.130`) & resolve DNS -> Success.
  4. Ping Admin from Student (`192.168.10.98`) -> Dropped by ACL (show deny counter on R1 `show access-lists STUDENTS-IN`).
  5. Show OSPF neighbor (`show ip ospf neighbor`) and NAT translation table (`show ip nat translations`).
- [x] **Present CampusAtlas Accurately**: Position it as a companion verification platform and evidence auditor.
