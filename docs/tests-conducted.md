# Tests conducted and results

The October 31, 2026 run verified the expanded network after it was saved and reopened. These results describe that capture. To inspect a case, open **Lab results**, select its ID, then expand the case and its evidence.

## Acceptance checks

| Website ID | Check conducted | Cases passed |
| --- | --- | ---: |
| A01 | All 50 PCs have correct IP, subnet, gateway and DNS settings | 50/50 |
| A02 | All 50 PCs can ping their own gateway | 50/50 |
| A03 | All 50 PCs can ping the centralized server | 50/50 |
| A04 | All 50 PCs resolve portal.campus.test to 192.168.10.130 | 50/50 |
| A05 | All 50 PCs load the campus website using its DNS hostname | 50/50 |
| A06 | Administration diagnostics, same-VLAN forwarding and server gateway checks pass | 5/5 |
| A07 | Student, Faculty and server initiation is denied with ACL counter evidence | 5/5 |
| A08 | PC8-MGMT authenticates by SSHv2 to the router and all four switches | 5/5 |
| A09 | Other Administration PCs cannot access the five network-device VTYs | 5/5 |
| A10 | Student and Faculty clients cannot SSH to router management | 2/2 |
| | **Total** | **272/272** |

See the [recorded acceptance summary](../evidence/SCALE50-20261031/test-summary.json) and [acceptance report](../SCALE_50_ACCEPTANCE.md) for evidence and retry details.

## Complete ICMP matrix (P02)

Each of 51 endpoints sent pings to 50 other endpoints, four switch management addresses and four router addresses. All **2,958** results matched policy. The 1,447 permitted combinations received four replies each. The 1,511 denied combinations received zero replies each. For a denial test, a block is the expected passing result.

[Per-source results and counter interpretation](../PING_ANALYSIS.md) · [Recorded commands](../data/ping-matrix.v2.json)

## Troubleshooting

| Symptom | First check |
| --- | --- |
| Dynamic client shows 0.0.0.0 after reopening | Wait for spanning-tree/trunk convergence, then renew DHCP. Check VLAN membership, pool and relay. Keep PC8-MGMT static. |
| Client can ping its gateway but cannot reach a remote peer | Check both subnet masks, the trunk VLAN list and R1’s inbound ACL. Verify whether the direction is allowed. |
| Server ping succeeds but the portal fails | Query the hostname with `nslookup portal.campus.test`. Try HTTP by IP to isolate name resolution from the web service. |
| Switch answers ping but SSH fails | Confirm the source is PC8-MGMT, use the lab login and check VTY access restrictions. |
| Website shows a different lease from the simulator | Inspect `ipconfig` in the current simulation. The website displays the address recorded with the command. |

[Return to the project contents](../README.md#table-of-contents)
