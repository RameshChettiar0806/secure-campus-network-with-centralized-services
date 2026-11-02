# Access policy

The [OSPF/PAT extension](ospf-pat-extension.md) retains these campus rules and adds only client TCP/80 and ICMP Echo access to 203.0.113.10. The WAN ingress ACL permits OSPF and selected replies and denies other traffic.

| Initiator and destination | Decision and reason |
| --- | --- |
| Two endpoints in the same client VLAN | Local switching. Traffic stays within the broadcast domain and bypasses R1’s routed ACLs. |
| Client → own gateway or services server | ICMP echo permitted. The client can also use [the centralized services](centralized-services.md). |
| Administration → Faculty or Students | Routed diagnostic ping permitted. The destination department permits the echo reply. |
| Faculty or Students → another client department | R1 blocks the newly initiated echo request on the source VLAN. |
| Server → client | R1 blocks a newly initiated ping. Services ACL rules permit required replies to clients. |
| PC8-MGMT → router or switch CLI | SSHv2 on TCP 22 is authorized for 192.168.10.98. A VTY source ACL also restricts local VLAN 10 sessions, which can reach a switch without traversing R1. |

The router’s extended ACLs evaluate rules in order. They distinguish protocols, source and destination ranges, ports, and ICMP types. ICMP Echo Request is type 8 and Echo Reply is type 0. Explicit return rules make Administration-initiated diagnostics possible while a Student-initiated request to the same Administration PC is blocked. These ACLs are stateless. A TCP ACK/RST check or an ICMP reply rule does not track sessions.

Management uses VLAN 10. PC8-MGMT is static at .98, R1’s management gateway is .97, and the SW1–SW4 switch virtual interfaces (SVIs) are .99–.102. Each switch uses .97 for management traffic bound outside its subnet.

[Compare a permitted and a blocked exchange (PDF)](../output/pdf/03-access-policy.pdf)

[Return to the project contents](../README.md#table-of-contents)
