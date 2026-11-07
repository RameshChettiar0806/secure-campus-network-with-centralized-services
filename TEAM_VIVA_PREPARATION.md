# Team viva and demonstration assignments

Updated to follow Ramesh's confirmed division and the 14-slide CampusAtlas_Computer_Networks_Updated.pptx on 2 November 2026.

Ramesh owns live ping/packet demonstrations and ACL explanation. Devarpan owns the need, objectives and technology overview. Aadi and Aditya Vardhan share architecture, with Ramesh supporting both. These assignments describe preparation and presentation responsibility, not original implementation contributions.

The slide assignments below refer to the November 2 presentation. The current demonstration follows the verified Iteration 5 checkpoint. [Remediation record](docs/audit-remediation.md), [current presentation](output/presentation/CampusAtlas_Audit_Remediation_Iteration_5.pptx)

## Current checkpoint demonstration

1. Open the saved Packet Tracer checkpoint and verify its SHA-256 against the remediation manifest.
2. From a departmental PC, renew DHCP and open `portal.campus.test`. Compare an allowed Administration diagnostic with a denied Student-to-Administration ping.
3. From PC8-MGMT in VLAN 99, demonstrate authorized SSH. From an ordinary departmental PC, show the denied SSH attempt.
4. Open `external.campus.test` from a departmental PC and inspect the OSPF neighbor and PAT translation on the edge router.
5. Use the failure and restoration procedure documented for the verified checkpoint. Compare service recovery with the time when the expected forwarding roles return.
6. Identify the capture date on Campus Atlas before citing a result. The November 2 replay and the remediation evidence have separate identities.

## Slide ownership

| Slides | Primary speaker | Responsibility |
| --- | --- | --- |
| 1: Title and team | Devarpan | Introduce the team and project |
| 2: Project objective and campus needs | Devarpan | Explain the problem, objectives and a brief technology overview |
| 3: Campus topology | Aadi | Devices, departments, VLANs and physical connections |
| 4: Department subnet sizing | Aadi | VLSM, gateways, usable addresses and static reservations |
| 5: Connectivity and configuration stages | Aadi | VLANs, trunks, R1 subinterfaces and the configuration sequence |
| 6: Student-to-server packet path | Aditya Vardhan, supported by Ramesh | Explain forwarding architecture; Ramesh demonstrates the actual packet flow during the live demo |
| 7: OSPFv2 external subnet | Aditya Vardhan | Explain R1/R2, transit network, adjacency and route learning |
| 8: PAT and external access | Aditya Vardhan | Explain translation, client scope and dependence on the external route; refer ACL details to Ramesh |
| 9: Centralized campus services | Aditya Vardhan | Explain DHCP relay, DNS and HTTP in the architecture |
| 10: Directional ACL policy | Ramesh | Explain permitted/blocked initiation, return packets and counters |
| 11: Restricted SSH management | Ramesh | Explain PC8-MGMT and device VTY source restrictions |
| 12: CampusAtlas companion website | Ramesh | Transition to the live demonstration and captured evidence |
| 13: Baseline verification | Ramesh | Explain test results and distinguish baseline from extension evidence |
| 14: Conclusion | Ramesh | Summarize outcomes, limitations and next steps |

A technology overview is a short spoken addition to slide 2, not an additional slide. Aditya explains routing, translation and service architecture. Ramesh owns the detailed ACL explanation and all live demonstrations.

## Devarpan Ghosh: need, objectives and technology overview

Target: about 2 minutes. Prepare slides 1 and 2, a short speaking sheet and answers to the questions below.

### Exact tasks

1. Introduce CampusAtlas and the four team members without reading registration numbers aloud unless requested.
2. Explain the campus need: separate departments, reduce repeated manual IP setup, share campus services and control network administration.
3. Explain the objectives: connect 50 PCs, create four VLANs/subnets, centralize DHCP/DNS/HTTP, enforce routed access policy and restrict SSH. Mention the simulated external extension using OSPF and PAT.
4. Learn the technology table below. For each technology, explain its purpose in one sentence. Leave configuration details to its assigned speaker.
5. Rehearse the handoff: "Aadi will now explain how we organized the campus devices, VLANs and IP addresses."

| Technology | One-sentence explanation |
| --- | --- |
| Cisco Packet Tracer | Runs the simulated campus network and lets us inspect packet movement. |
| VLAN | Separates the campus into logical Layer 2 groups for Administration, Faculty, Students and Services. |
| VLSM | Gives different subnets different sizes according to capacity needs. |
| 802.1Q trunk | Carries the required VLANs over a shared link. |
| Router-on-a-stick | Uses R1 subinterfaces to route between VLANs through one physical trunk. |
| DHCP | Automatically supplies client IP settings. |
| DNS | Resolves portal names to server IP addresses. |
| HTTP | Delivers the portal page to the simulated browser. |
| ACL | Permits or denies packets according to the configured policy. |
| SSH | Provides encrypted command-line management, restricted here to PC8-MGMT. |
| OSPF | Allows R1 to learn the route to the simulated external server network from R2. |
| PAT | Lets campus clients share R1's outside address for permitted external traffic. |
| CampusAtlas website | Presents topology, addressing and captured test evidence for explanation. |

### Suggested opening

"Our project, CampusAtlas, models a campus network for 50 PCs across Administration, Faculty and Students. The campus needs departmental separation, consistent client configuration and shared services, with controlled administration. We use separate VLANs and subnets, centralized DHCP, DNS and HTTP, and access-control rules. We also extend connectivity to a simulated external server using OSPF and PAT."

Do not recite every technology as a list during the opening. Group them by purpose: separation/addressing, shared services, controlled access and external connectivity. Know all the definitions for questions.

### Questions to answer independently

- Why does the campus need separate VLANs?
- What does centralizing services achieve?
- How do DHCP, DNS and HTTP differ?
- Why are both OSPF and PAT used?
- What do Packet Tracer and the companion website each do?

## Aadi Jain: physical and logical campus architecture

Target: about 3 minutes. Own slides 3, 4 and 5.

### Exact tasks

1. Draw the topology from memory. Identify 50 PCs, four switches, two routers, two servers, 58 network devices and 57 Ethernet links.
2. Explain SW1 aggregation, SW2 Administration access, SW3 Faculty access and SW4 Student access. State the PC counts: 12 Administration, 18 Faculty and 20 Students.
3. Explain VLAN 10 Administration, VLAN 20 Faculty, VLAN 30 Students and VLAN 40 Services.
4. Explain access ports and trunks. Explain why the Faculty/Student switch uplinks also carry management VLAN 10.
5. Reproduce the address table below. Work through the usable-host calculation for /26 and /27, and explain network, gateway and broadcast addresses.
6. Explain static infrastructure reservations: PC8-MGMT .98, switches .99-.102 and campus server .130.
7. Explain R1 Gi0/0 subinterfaces and 802.1Q tagging. On slide 5, identify the purpose of the gateway and helper lines; let Ramesh explain the attached ACL in detail.
8. Explain the build order: cabling/VLANs, trunks/gateways, services, policy/SSH, verification/save/reopen. Know what each verification command inspects.

| VLAN | Network | Gateway | Broadcast | Usable addresses |
| --- | --- | --- | --- | ---: |
| 30 Students | 192.168.10.0/26 | 192.168.10.1 | 192.168.10.63 | 62 |
| 20 Faculty | 192.168.10.64/27 | 192.168.10.65 | 192.168.10.95 | 30 |
| 10 Administration | 192.168.10.96/27 | 192.168.10.97 | 192.168.10.127 | 30 |
| 40 Services | 192.168.10.128/28 | 192.168.10.129 | 192.168.10.143 | 14 |

### Deliverables and readiness

Produce one annotated topology and address sheet. Explain slides 3-5 without reading them. Answer: Why different masks? Why route between VLANs? Why a trunk? Why keep server and management addresses static? Why are two router interfaces not required for two campus VLANs?

Read: [topology](docs/topology.md), [addressing](docs/addressing-table.md), and [campus design and port map](SCALE_50_DESIGN.md). The campus design predates the two-device external extension; use the updated deck's 58-device total.

Handoff: "Aditya will explain how packets move through this design, how the external branch connects and how clients use the shared services."

## Aditya Vardhan: forwarding, external branch and service architecture

Target: about 3-4 minutes. Own slides 6, 7, 8 and 9. Ramesh supports packet-flow explanations and performs the live tests.

### Exact tasks

1. Explain PC0 to server: PC0, SW4, SW1, R1, SW1 again in VLAN 40, then SRV-CAMPUS. Explain why a remote destination uses the default gateway.
2. Explain ARP for the next-hop MAC, VLAN tagging on trunks and routing between subinterfaces. Contrast this path with same-VLAN local switching.
3. Explain that campus subnets are directly connected on R1. OSPF serves the external branch rather than enabling the existing campus inter-VLAN routing.
4. Explain the transit network: R1 198.51.100.1/30 and R2 198.51.100.2/30. Explain the external LAN: 203.0.113.0/24, R2 .1 and external server .10.
5. Explain one OSPF area-0 adjacency and R1's learned external route. Explain the passive server interface and the absence of a redundant path.
6. Explain PAT: multiple inside-local client addresses share 198.51.100.1, distinguished by ports or ICMP identifiers. Services VLAN is excluded.
7. Explain why R2's lack of private campus routes makes PAT necessary for external replies in this design. Distinguish routing from translation.
8. Explain the centralized server at 192.168.10.130: three DHCP pools, R1 relay, 49 DHCP PCs plus static PC8-MGMT, the two DNS records and HTTP delivery.
9. Know service ports: DHCP UDP 67/68, verified DNS UDP 53 and HTTP TCP 80. TCP DNS is permitted but was not verified end to end.
10. On slide 8, explain the external access scope briefly and let Ramesh handle the ACL rules. Describe its test figures as recorded extension results.

### Deliverables and readiness

Produce one internal/external packet-path sheet and one short DHCP-to-DNS-to-HTTP sequence. Explain slides 6-9 without reading them. Answer: Why does the internal portal work without OSPF? Why do we need both OSPF and PAT externally? Why does DHCP need a relay? Does DNS deliver the page? What would fail if the centralized server stopped?

Read: [topology](docs/topology.md), [centralized services](docs/centralized-services.md), [OSPF/PAT guide](docs/ospf-pat-extension.md) and [extension acceptance](OSPF_PAT_ACCEPTANCE.md).

Handoff: "Ramesh will now show how the ACLs control these paths and demonstrate the allowed and blocked traffic."

## Ramesh: packet demonstration, ACLs and overall technical lead

Target: about 5 minutes plus questions. Own slides 10-14 and the live Packet Tracer/website demonstrations. Support both architecture speakers and know the entire project.

### Exact explanation tasks

- Explain slide 10's matrix from the sender rows. Distinguish new echo requests from allowed echo replies.
- Explain ordered ACL matching, wildcard masks, inbound subinterface placement and the final deny.
- Explain why these ACLs are stateless and why same-VLAN traffic bypasses R1's routed ACLs.
- Explain slide 11's SSH restriction: PC8-MGMT is 192.168.10.98; router and switch VTY restrictions also cover local VLAN 10 management attempts.
- Support Aadi on subnetting/trunks and Aditya on forwarding, OSPF/PAT and service dependencies when questions require more detail.
- Explain the companion website, the evidence dates and realistic limitations. Lead the closing.

### Exact live demo sequence

1. Open the saved submission and allow roughly one minute for convergence. Inspect live addresses with `ipconfig /all`; do not assume historical DHCP leases still apply.
2. Demonstrate PC0 to its Student gateway 192.168.10.1 and internal server 192.168.10.130.
3. Use Packet Tracer Simulation mode to step through one Student-to-server ICMP exchange. Include ARP if the next-hop MAC has not been learned; identify the VLAN 30 outward path, R1 routing and VLAN 40 server path.
4. Obtain PC0's current address. From PC8-MGMT, ping that address: expect permitted diagnostic traffic. Explain the Student echo-reply permission.
5. From PC0, ping PC8-MGMT at 192.168.10.98: expect a blocked new request. Inspect `show access-lists` before/after and correlate the matching deny counter. A timeout alone does not establish why a packet failed.
6. Show a same-VLAN client exchange if needed to explain why it stays within the switch and bypasses routed ACLs.
7. Run `nslookup portal.campus.test`, then open `http://portal.campus.test` in the simulated browser.
8. On R1, show `show ip ospf neighbor` and `show ip route ospf`. Identify the adjacency and 203.0.113.0/24 route that Aditya described.
9. Generate fresh permitted external traffic from more than one client, using `http://external.campus.test` and/or ping 203.0.113.10. Immediately show `show ip nat translations` and `show ip nat statistics`; translation entries can expire.
10. If time permits or asked, demonstrate authorized SSH from PC8-MGMT and the denial from another Administration PC using local lab credentials.
11. Use the companion website to inspect topology, allowed/blocked evidence and the OSPF/PAT tab. State when a result is replayed evidence rather than the current live exchange.

For a short slot, prioritize the server packet path, the allowed/blocked pair with ACL evidence and one external transaction with OSPF/PAT output. Keep the remaining demonstrations ready for questions. Use rehearsed recorded evidence for failure/restoration explanations unless a live failure demonstration is requested and restoration has been practised.

### Results and limitations to state accurately

- Slide 13: the 31 October campus baseline has 272/272 acceptance cases and 2,958/2,958 directed ping combinations matching policy. Expected denials count as correct policy outcomes.
- Slide 8: the 2 November extension has separate checks. The historical full ping matrix was not rerun for that extension.
- External connectivity is to a simulated server, not the real Internet.
- There is no redundant external path, R1 or campus services server. Student and Faculty core uplinks operate at 100 Mb/s. Throughput and failover were not measured.
- HTTP is unencrypted; ACLs are stateless. Stateful filtering, same-VLAN isolation and redundancy are future improvements.

### Deliverable and readiness

Prepare one ordered demo checklist with each source, destination, expected result and explanation. Run the demo twice and practise one recovery scenario. Explain both successful traffic and intentional denials without changing policy to force connectivity.

Read: [access policy](docs/access-policy.md), [tests](docs/tests-conducted.md), [extension guide](docs/ospf-pat-extension.md), [extension acceptance](OSPF_PAT_ACCEPTANCE.md) and [active R1 configuration](configs/R1-CAMPUS-OSPF-PAT.txt).

## Shared minimum and rehearsal

Every member must know the project objective, the four VLANs, the major device roles, how DHCP/DNS/HTTP differ and why a Student can access the portal but cannot initiate departmental diagnostic traffic to Administration. Everyone should locate their topics on the topology.

1. Ramesh explains the entire network once; each teammate gives a 30-second summary.
2. Devarpan rehearses slides 1-2 and purpose-level technology definitions with Ramesh.
3. Aadi and Aditya teach their architecture sections to each other. Ramesh checks subnetting, forwarding and the external dependencies.
4. Run the slide sequence and demonstration in one uninterrupted rehearsal, using the handoffs above.
5. Repeat without prompting. Each member answers five questions about their section and one follow-up asking why.

Each person creates a one-page speaking/preparation sheet. During questions, the assigned member answers first; Ramesh adds details when needed. Preparation ownership does not remove the need for everyone to understand the project at a basic level.

## Team assignment message

"Our presentation split is now: Devarpan covers the introduction, campus need, objectives and purpose of the technologies on slides 1-2. Aadi covers campus topology, VLANs, subnetting and the configuration stages on slides 3-5. Aditya Vardhan covers packet-flow architecture, OSPF, PAT and centralized services on slides 6-9. I will help both with architecture and handle ACLs, SSH restrictions, ping/packet demonstrations, the website, results and conclusion on slides 10-14. Each person should prepare a one-page sheet, explain their own slides without reading them and answer five questions. We will rehearse the full sequence together."
