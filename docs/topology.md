# Topology and packet forwarding

```text
                     R1-CAMPUS (Cisco 1941)
                           |
                      802.1Q trunk
                           |
  SRV-CAMPUS ----------- SW1-CORE
  access VLAN 40        /    |    \
                  SW2-ACCESS SW3-FACULTY SW4-STUDENTS
                    12 PCs      18 PCs       20 PCs
```

Four Cisco 2960-24TT switches connect 51 endpoints over 51 access links. Four infrastructure trunks bring the total to 55 links. An access port associates ordinary endpoint frames with one VLAN. A switch uses the destination MAC address to forward a frame within that VLAN. SW1 aggregates the access switches and connects the server directly.

| Link from SW1 | Peer | VLANs carried |
| --- | --- | --- |
| Gi0/1 | R1 Gi0/0 | 10, 20, 30, 40 |
| Gi0/2 | SW2 Gi0/1 | 10 |
| Fa0/23 | SW3 Gi0/1 | 10, 20 |
| Fa0/24 | SW4 Gi0/1 | 10, 30 |

R1 provides **router-on-a-stick** forwarding. A PC compares the destination with its own subnet. For a remote destination, it uses ARP to resolve its default gateway’s MAC address and sends the IP packet in a frame addressed to the gateway. R1 checks the ingress ACL, selects the destination network, and emits a new frame on the corresponding VLAN subinterface. In a PC0-to-server request, SW1 first carries VLAN 30 up to R1, then VLAN 40 back toward the server. For two Student PCs, SW4 can deliver the frame locally. See the [exact client port map](../SCALE_50_DESIGN.md).

The Faculty and Student core uplinks run at 100 Mb/s. R1 and SRV-CAMPUS are each a single point of failure. The recorded checks measure functional connectivity and policy, not throughput or failover.

[Return to the project contents](../README.md#table-of-contents)
