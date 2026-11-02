# Expanded campus acceptance

Historical campus baseline. The current submission has the additional branch described in [OSPF/PAT acceptance](OSPF_PAT_ACCEPTANCE.md); the results and hash below belong to the October 31 capture.

Verified: 2026-10-31T21:50:13+05:30 (IST). Existing file edited in place: **Secure_Campus_Network_Submission.pkt**.

The file was saved, closed, and reopened in Cisco Packet Tracer 9.0.1. All checks below ran against the reopened file. Its SHA-256 remained unchanged during the final acceptance run: `E8A0AA8E0B7411073D4B29CAE6A284C439A97F088AEBECB9D42D3546D26D9905`.

## Inventory and addressing

- 50 PCs: 12 Administration, 18 Faculty, 20 Students.
- One Cisco 1941 router, four Cisco 2960-24TT switches, and one Server-PT: **56 network devices and 55 links**.
- Packet Tracer also exposes a physical-workspace Power Distribution Device. It is not counted as a network device or endpoint.
- 49 DHCP clients, static PC8-MGMT at 192.168.10.98, and static server at 192.168.10.130: 51 unique endpoint addresses.
- Students 192.168.10.0/26; Faculty 192.168.10.64/27; Administration 192.168.10.96/27; Services 192.168.10.128/28.
- Switch management addresses 192.168.10.99-102, all in VLAN 10. Router management address 192.168.10.97.

## Actual results

| Check group | Passed |
|---|---:|
| ipconfig | 50/50 |
| gatewayPing | 50/50 |
| serverPing | 50/50 |
| dns | 50/50 |
| http | 50/50 |
| policyAllowed | 5/5 |
| policyDenied | 5/5 |
| sshAllowed | 5/5 |
| sshDeniedAdmin | 5/5 |
| sshDeniedDepartments | 2/2 |
| **Total** | **272/272** |

Every PC was checked for correct IP/gateway/DNS settings, gateway ping, server ping, hostname DNS resolution, and actual HTTP content from `http://portal.campus.test`. Policy checks cover permitted Administration diagnostics and same-VLAN traffic, prohibited departmental initiation, and prohibited server initiation. Denials include ACL counter observations. Authorized SSH authenticated to all five IOS devices; unauthorized Administration and departmental sources were denied.

This is the original 272-case expanded acceptance set. A subsequent PING-20261031 run completed all 2,958 directed ICMP combinations successfully; see [PING_ANALYSIS.md](PING_ANALYSIS.md). Initial simultaneous service requests had timeouts; final per-client outcomes include recorded retries where needed. These are functional tests, not throughput or load benchmarks.

## Reopen behavior and limitations

Dynamic addresses may initially display 0.0.0.0 after opening. Allow trunk/STP convergence and DHCP recovery, approximately 60 seconds in this run; renew DHCP if a client remains unconfigured. PC8-MGMT stays static. Lease order can change.

Packet Tracer regenerates a default `serverPool`. It was explicitly constrained to the single Services address 192.168.10.131/28, gateway 192.168.10.129, DNS 192.168.10.130, and verified after reopening. The three departmental pools are separate.

Faculty and Student switch trunks use 100 Mb/s FastEthernet ports on the aggregation switch. The router and Administration trunks use Gigabit ports. The network retains a single router and central services server. Routed ACLs do not isolate endpoints in the same VLAN and are not a stateful firewall.

## Artifacts and cleanup

- [Current file](Secure_Campus_Network_Submission.pkt) and [SHA-256](SUBMISSION_SHA256.txt).
- [Revised design](SCALE_50_DESIGN.md), [simulator topology image](evidence/SCALE50-20261031/topology.png), [test summary](evidence/SCALE50-20261031/test-summary.json), and [leases](evidence/SCALE50-20261031/leases.json).
- Sanitized router/switch configurations are in `configs/`.
- [Cleanup manifest](evidence/SCALE50-20261031/cleanup.json) lists the removed older campus copies. Their original bytes are retained in `evidence/SCALE50-20261031/campus-before-expansion.zip` for recovery. This ZIP contains lab credentials embedded in the old simulations; keep it local.
- Separate lab experiment .pkt files were preserved.
- Historical N4/W0 and PING-20261030 records describe the earlier 14-device network. The companion website now uses the expanded v2 snapshot and PING-20261031 matrix. Updating the report and presentation remains pending.
