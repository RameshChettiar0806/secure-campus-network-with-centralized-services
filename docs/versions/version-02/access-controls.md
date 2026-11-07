# Version 02 — access control policies

Authoritative inputs: [SW1 core ACLs](../../../evidence/AUDIT-REMEDIATION-20261105-182333/iteration5-verified-configs/SW1-CORE.txt), [SW5 core ACLs](../../../evidence/AUDIT-REMEDIATION-20261105-182333/iteration5-verified-configs/SW5-CORE.txt), [R1 edge policy](../../../evidence/AUDIT-REMEDIATION-20261105-182333/iteration5-verified-configs/R1-CAMPUS.txt) and [R2 configuration](../../../evidence/AUDIT-REMEDIATION-20261105-182333/iteration5-verified-configs/R2-EXTERNAL.txt).

## Directional permissions

| Initiator → destination | Allowed traffic / decision |
| --- | --- |
| Same departmental VLAN | Local Layer 2 communication; does not cross an SVI ACL |
| Department → own virtual gateway | ICMP Echo |
| Department → campus server | DHCP, DNS, HTTP and ICMP under explicit ACL entries |
| Administration → Faculty / Students | ICMP Echo; corresponding replies allowed |
| Faculty / Students → another department | New ICMP initiation denied |
| Department → Management VLAN | Unsolicited access denied; explicit replies to management diagnostics permitted |
| PC8-MGMT → departmental clients | ICMP diagnostics and corresponding replies |
| PC8-MGMT → campus server | DNS, HTTP and ICMP |
| PC8-MGMT → seven campus IOS devices | SSH from 192.168.10.146; local VTY authentication and source ACL |
| Ordinary client → campus CLI | Denied; two unauthorized SSH cases recorded |
| 49 departmental clients → external server | HTTP TCP/80 and ICMP Echo to 203.0.113.10; PAT enabled |
| Management → external server | Denied; excluded from NAT-CLIENTS |
| Campus server → clients / external server | New endpoint ping initiation denied; explicitly allowed service/control responses remain |
| External server → private campus | No private route on R2; cannot attribute this ping failure to a stateful firewall |

## Enforcement points

Both cores apply ADMIN-IN, FACULTY-IN, STUDENTS-IN, SERVICES-IN and MGMT-IN inbound on the respective SVIs. Required HSRP peer messages are explicitly permitted. The service ACL accommodates DHCP replies to the physical relay addresses as well as the virtual gateway addresses.

R1's WAN-IN allows OSPF from 198.51.100.2, TCP responses from external server port 80 with the ACK/RST check, and ICMP echo replies from that server. Other ingress traffic is denied. NAT-CLIENTS covers VLANs 10, 20 and 30 only.

VTY ACLs permit PC8-MGMT (192.168.10.146) and deny other sources. This matters for devices on the same management VLAN, whose traffic does not cross a routed ACL. VLAN 99 is dedicated **in-band management**, not a separate out-of-band network. R2 management is locked down separately.

## Layer 2 and device controls

- PC access ports are bound to expected MAC addresses with port-security controls. An unauthorized-MAC probe failed and increased the violation counter.
- DHCP snooping is enabled for client VLANs with infrastructure trust configured; Option 82 insertion is disabled to preserve observed DHCP behavior.
- Trunks have explicit VLAN allowlists and DTP suppression. Unused ports are shut down in VLAN 998; native VLAN 999 is unused.
- PortFast/BPDU Guard protect configured endpoint access ports.
- Campus devices use local credentials, SSH-only VTY access and console/session controls. Sanitized exports omit credentials; they are references, not complete deployable configurations.

## Verified limits and residual policy

All routed filters remain **stateless**. TCP `established` and ICMP reply rules do not provide session inspection. PAT alone is not a stateful security policy.

DAI was rolled back after the spoofing probe succeeded. IP Source Guard and the attempted switch RADIUS command were unsupported. The rogue-DHCP trial lacked a working positive control, so configured snooping must not be reported as proof that this attack was defeated. RADIUS-related UDP ACL entries remain in exports, but do not establish a working centralized AAA service.

OSPF MD5 and Type 5 secret support reflect this educational simulator. Switch NTP keys did not persist after reopen; R1 retained authenticated NTP. The WAN inspection trial was rolled back with securityk9 disabled. HTTP remains unencrypted. Consult [the audit limitations](../../audit-remediation.md#simulator-limitations) before presenting a security claim.

[Verification](verification.md) · [Version index](../README.md)
