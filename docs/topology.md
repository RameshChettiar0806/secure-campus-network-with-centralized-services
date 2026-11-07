# Topology and packet forwarding

> Historical scope: this guide describes the single-core network and November 5 backup-uplink milestone. For the current dual-core design, use [Version 02 architecture](versions/version-02/network-architecture.md).

This diagram shows the retained campus. The [OSPF/PAT extension](ospf-pat-extension.md) adds R2-EXTERNAL and SRV-EXTERNAL through R1 Gi0/1. The November 5 [fault-tolerance extension](fault-tolerance.md) adds a parallel backup uplink for each access switch, for **58 network devices and 60 links** overall.

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

Four Cisco 2960-24TT switches connect 51 campus endpoints over 51 access links. Four original infrastructure trunks and three backup trunks bring the campus total to 58 links; the external branch adds two. An access port associates ordinary endpoint frames with one VLAN. A switch uses the destination MAC address to forward a frame within that VLAN. SW1 aggregates the access switches and connects the server directly. The diagram shows primary paths; the table includes backups.

| Link from SW1 | Peer | VLANs carried |
| --- | --- | --- |
| Gi0/1 | R1 Gi0/0 | 10, 20, 30, 40 |
| Gi0/2 | SW2 Gi0/1 | 10 |
| Fa0/23 | SW3 Gi0/1 | 10, 20 |
| Fa0/24 | SW4 Gi0/1 | 10, 30 |
| Fa0/2 (backup) | SW2 Gi0/2 | 10 |
| Fa0/3 (backup) | SW3 Gi0/2 | 10, 20 |
| Fa0/4 (backup) | SW4 Gi0/2 | 10, 30 |

R1 provides **router-on-a-stick** forwarding. A PC compares the destination with its own subnet. For a remote destination, it uses ARP to resolve its default gateway’s MAC address and sends the IP packet in a frame addressed to the gateway. R1 checks the ingress ACL, selects the destination network, and emits a new frame on the corresponding VLAN subinterface. In a PC0-to-server request, SW1 first carries VLAN 30 up to R1, then VLAN 40 back toward the server. For two Student PCs, SW4 can deliver the frame locally. See the [exact client port map](../SCALE_50_DESIGN.md).

The Faculty and Student primary core uplinks and all backup uplinks run at 100 Mb/s. Rapid PVST+ keeps each backup blocked during normal operation and promotes it after a primary departmental uplink failure. [Failure/recovery checks](../FAULT_TOLERANCE_ACCEPTANCE.md) exercise this behavior separately from the historical ping matrix. R1, its core trunk, SW1, each departmental switch and SRV-CAMPUS remain single points of failure; throughput remains unmeasured.

[Return to the project contents](../README.md#table-of-contents)
