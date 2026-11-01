# Website and lab walkthroughs

## Website demonstration

| Section | What to demonstrate |
| --- | --- |
| Topology | Filter to Students, find PC0, inspect its port, then select its uplink. Use **Fit all** for the 56-device overview. |
| Topology guide | Select a VLAN to explain a client, its access switch, subnet and gateway. **Locate** opens that device in the topology. |
| Addressing table | Search a label or IP address. Compare a DHCP lease with PC8-MGMT’s reserved static address and the switches’ management interfaces. |
| Ping lab | Choose **Server access** and run the recorded ping. The console shows command output and loss. **Follow the packet** shows each switch, router decision and reply. Pause or step through repeated visits to SW1. |
| Access policy | Read the ICMP matrix from the sender’s row to the destination column. Select Students → Administration, replay it, then reverse the direction. Open the detailed rules for service-specific enforcement and test links. |
| Lab results | Select a check group, inspect an individual case, and open its evidence. Compare DNS resolution (A04) with an actual HTTP response (A05). |

### Follow the packet

The route view illustrates one exchange using the recorded topology. Its hops include Layer 2 switches. The CLI counters describe all four requests in that command. **Server access** shows PC0 → SW4 → SW1 → R1 → SW1 → SRV-CAMPUS and the return path. **Blocked access** stops at R1 with zero replies. A timeout alone cannot identify the cause. Compare the sender, VLAN, rule and counter observations. Capture-batch counter deltas can include other pings.

## Printable campus labs

Open these sheets from **Lab results → Printable lab walkthroughs** in the website or use the links below. Each sheet names the device, the command or UI action, the expected observation and a troubleshooting check. Use current client leases when running the steps in Packet Tracer.

1. [Trace a campus connection (PDF)](../output/pdf/01-topology-and-addressing.pdf) — follow PC0 from its access port through the 802.1Q trunks to its VLAN gateway.
2. [Open the campus portal (PDF)](../output/pdf/02-centralized-services.pdf) — verify a lease, ping the server, resolve its hostname and request the page.
3. [Test a policy in both directions (PDF)](../output/pdf/03-access-policy.pdf) — compare blocked and permitted ICMP, inspect ACL counters and attempt SSH from two Administration PCs.

## Course exercises

The [course lab manual](<../../Lab/CN Lab Manual (2025-26).pdf>) covers the following experiments. The campus reuses the LAN, IP and secure-management concepts. The WAN, NAT and dynamic-routing exercises use their own topologies.

| Manual exercise | Technical focus and verification |
| --- | --- |
| 1–2 | Packet Tracer, cables, networking commands, peer-to-peer links, LANs and physical topologies. Inspect link state and use `ipconfig` and `ping` to test neighbors. |
| 3–4 | Router console access, interface addressing and WAN subnetting. Check interface state with `show ip interface brief` and verify address boundaries. |
| 5 | Static routes name remote prefixes and a next hop. A default route matches remaining destinations. Inspect `show ip route` and test the return path. |
| 6A/6B | Static NAT maps an inside local address to a fixed inside global address. Dynamic NAT allocates a translation from a pool. Generate inside-to-outside traffic and inspect `show ip nat translations`. [Static NAT](<../../Lab/Packet Tracer/Exp 6A.pdf>) · [Dynamic NAT](<../../Lab/Packet Tracer/Exp 6B.pdf>) |
| 7 | RIPv1 and RIPv2 use hop count. RIPv2 carries subnet masks. Compare learned routes in the routing table. |
| 8A/8B | Single-area and multi-area OSPF form neighbor adjacencies and calculate routes from link costs. Verify neighbors and inter-area routes. [Single-area steps](<../../Lab/Packet Tracer/Exp_8A_Single_Area_OSPF.md>) · [Multi-area steps](<../../Lab/Packet Tracer/Exp_8B_Multi_Area_OSPF.md>) |
| 9A/9B | PPP and HDLC provide serial link encapsulation. Match both ends and inspect the line protocol and encapsulation in `show interfaces`. |
| 10–11 | BGP exchanges prefixes between peers using autonomous-system information. EIGRP forms neighbor relationships and selects routes using a composite metric. Inspect peer status and installed routes in each exercise. |
| 12 | Compare Telnet and SSH remote CLI access. The campus uses SSHv2 with local authentication, 2048-bit RSA configuration and an authorized source host. |

The companion [Packet Tracer setup handout](<../../Lab/CISCO PACKET TRACER REGISTRATION AND DOWNLOAD PROCEDURE.pdf>) covers course registration and installation. Course-file links expect the surrounding subject workspace.

[Return to the project contents](../README.md#table-of-contents)
