# OSPF and PAT demonstration extension

The campus retains its 50 PCs, four switches, four VLANs, centralized DHCP/DNS/HTTP server, VLSM addresses, trunks and departmental access policy. The extension adds one Cisco 1941 router, one external Server-PT and two Ethernet crossover links. It uses the previously unused R1 GigabitEthernet0/1. No serial modules or campus recabling are required.

## Physical changes

```text
SRV-EXTERNAL ---- R2-EXTERNAL ---- R1-CAMPUS
203.0.113.10      .1 (server LAN)      |
                 .2 (transit)      SW1-CORE ---- SRV-CAMPUS
                                   /  |  \
                              Existing department switches and 50 PCs
```

| Link | Addressing |
| --- | --- |
| R1 Gi0/1 ↔ R2 Gi0/0 | 198.51.100.1/30 ↔ 198.51.100.2/30 |
| R2 Gi0/1 ↔ SRV-EXTERNAL FastEthernet0 | 203.0.113.1/24 ↔ 203.0.113.10/24 |

There are 58 network devices and 57 links after the extension: 50 PCs, two servers, two routers and four switches. Packet Tracer also exposes a power-distribution object; it is excluded from network-device totals. The external address ranges are documentation addresses in a simulation; this is not access to the real Internet.

## What each feature demonstrates

| Feature | Role and demonstration |
| --- | --- |
| VLANs / 802.1Q | Existing Administration, Faculty, Students and Services segments remain intact. |
| DHCP / relay | The existing server allocates client addresses through the original R1 helpers. |
| DNS / HTTP | `portal.campus.test` remains internal. A new A record, `external.campus.test`, resolves to 203.0.113.10. |
| ACLs | Original campus permissions are retained. Each client VLAN additionally permits TCP 80 and ICMP Echo only to 203.0.113.10. |
| OSPFv2 | R1 and R2 form one area-0 adjacency. R2 advertises the external server subnet; R1 learns it as an OSPF route. |
| PAT | The three client subnets share R1's 198.51.100.1 outside interface address. The Services VLAN is excluded. |

OSPF operates only on the routed transit link. R2's server interface is passive, and R1 does not advertise campus client prefixes. Consequently R2 has no route to private client addresses: successful external replies depend on PAT. This deliberate teaching topology combines a simulated external network with a controlled OSPF adjacency; it does not model Internet routing between independent providers.

`WAN-IN` permits OSPF from the R2 transit address and HTTP/ICMP replies from the external server to R1's outside address. It ends with an explicit deny. NAT selection uses the separate `NAT-CLIENTS` standard ACL; this ACL selects translations and does not replace the extended security ACLs.

## Demonstration sequence

1. Show the existing campus topology and four VLANs. Explain that only the two devices above R1 were added.
2. From a departmental PC, show `ipconfig /all`, resolve `portal.campus.test` and load its web page.
3. Demonstrate an allowed Administration diagnostic ping and a denied Student-to-Administration ping. Inspect the original ACL counters.
4. On R1 run `show ip ospf neighbor` and `show ip route ospf`. Identify R2 and the learned 203.0.113.0/24 network.
5. From Student, Faculty and Administration clients resolve and browse `http://external.campus.test`.
6. On R1 run `show ip nat translations` and `show ip nat statistics`. Compare multiple inside-local addresses with the shared inside-global address 198.51.100.1. Port/ICMP identifiers distinguish flows.
7. Explain the controlled failure checks in the acceptance evidence: removing PAT prevents replies because R2 has no private route; making the transit interface passive removes the OSPF-learned external route. Restore both features before finishing.
8. End by opening the internal campus portal again and showing the unchanged departmental restrictions.

These commands inspect the running simulator. All main website sections now use the current 58-device capture and complete 3,224-ping matrix; each source has 62 recorded destinations. The original v2 capture is retained only as historical data on disk.

## Files and recovery

The active file remains `Secure_Campus_Network_Submission.pkt`. Recovery is in `evidence/OSPF-PAT-20261102/campus-before-ospf-pat.zip`. New measurements belong to that evidence directory. The active R1 export is `configs/R1-CAMPUS-OSPF-PAT.txt`; `configs/R1-CAMPUS.txt` is retained for the original hash-verified campus capture. R2's export is `configs/R2-EXTERNAL.txt`.

Implementation and verification results are recorded separately in `OSPF_PAT_ACCEPTANCE.md`; configuration alone does not count as a passing demonstration.
