# Version 01 — access control policies

These policies belong to the November 2 capture and its [matching router export](../../../evidence/WEBSITE-V3-20261102/configs/R1-CAMPUS-CURRENT.txt). Later management addresses must not be substituted into a Version 01 demonstration.

| Source → destination | Permission / enforcement |
| --- | --- |
| Same client VLAN | Local Layer 2 delivery; routed ACLs do not inspect this exchange |
| Department → own gateway | ICMP Echo permitted |
| Department → SRV-CAMPUS | DHCP, DNS, HTTP and ICMP as explicitly permitted |
| Administration → Faculty / Students | ICMP diagnostics allowed, with reply permissions in the destination VLAN |
| Faculty / Students → another department | Newly initiated cross-department ICMP blocked at the source VLAN ACL |
| Services server → client | New ICMP initiation blocked; required service replies permitted |
| PC8-MGMT → campus IOS devices | SSHv2 allowed from 192.168.10.98; VTY source ACL checks local sessions too |
| Other client → device CLI | SSH denied by management access policy |
| Client VLANs → 203.0.113.10 | HTTP and ICMP Echo only; PAT at R1 |
| External → private campus | R2 has no private route; WAN-IN also restricts traffic arriving at R1 |

## Enforcement model

R1 applies ordered extended ACLs inbound on VLAN subinterfaces: ADMIN-IN, FACULTY-IN, STUDENTS-IN and SERVICES-IN. WAN-IN permits the OSPF neighbor and selected HTTP/ICMP replies. VTY lines use local authentication and a source ACL.

These ACLs are **stateless**. An ICMP echo-reply permission or TCP `established` ACK/RST check does not prove that a matching session exists. A failed external ping to a private address can be a routing failure; it is not automatically proof of WAN ACL enforcement.

VLAN 10 mixes management and Administration in this edition. PortFast and BPDU Guard protect configured edge ports, but this capture must not be credited with Version 02's dedicated VLAN 99, MAC binding or authenticated OSPF.

## Evidence boundary

The ping matrix proves recorded ICMP behavior only. DHCP, DNS, HTTP and SSH need their separate service records. A permitted ping is not permission for arbitrary TCP/UDP applications.

For the isolated management VLAN, core SVI ACLs and Layer 2 hardening, read [Version 02 policies](../version-02/access-controls.md). [Version index](../README.md)
