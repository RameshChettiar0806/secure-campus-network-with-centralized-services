# Audit remediation

The November 6 verification captured 50 PCs, 60 network devices and 64 physical links after reopening the dual-core Packet Tracer file. The [checkpoint manifest](../evidence/AUDIT-REMEDIATION-20261105-182333/verified-submission.json) records its SHA-256 and the evidence hashes. Run the verifier from the project directory.

```powershell
python scripts/verify_audit_remediation.py
```

| Iteration | Verified outcome | Evidence |
| --- | --- | --- |
| 0 | The re-saved file matched the baseline for all six IOS configurations, inventory, physical links and enabled server services. | [Comparison](../evidence/AUDIT-REMEDIATION-20261105-182333/resaved-baseline-comparison.json) |
| 1 | Distinct device login and enable credentials, local console controls, R2 VTY lockdown, DTP suppression, corrected port descriptions and reduced server services. The router to core link reports 1 Gb/s full duplex. Packet Tracer accepted Type 5 secrets. | [Regression](../evidence/AUDIT-REMEDIATION-20261105-182333/iteration1-regression-summary.json), [link settings](../evidence/AUDIT-REMEDIATION-20261105-182333/iteration1-speed-result.json) |
| 2 | VLAN 99 isolates the management workstation and switch management interfaces. All 50 PCs reached campus services, all 49 departmental PCs reached the external server, and the management PC was denied external ICMP. | [Regression](../evidence/AUDIT-REMEDIATION-20261105-182333/iteration2-regression-summary.json), [backup path](../evidence/AUDIT-REMEDIATION-20261105-182333/iteration2-backup-summary.json) |
| 3 | Bound all 50 PC access ports to the expected MAC addresses, enabled client-VLAN DHCP snooping, carried VLAN 999 as the unused native VLAN and parked unused ports in VLAN 998. An unauthorized MAC produced no ping replies and increased the violation counter. DHCP renewal passed with Option 82 insertion disabled. | [Regression](../evidence/AUDIT-REMEDIATION-20261105-182333/iteration3-regression-summary.json), [MAC violation](../evidence/AUDIT-REMEDIATION-20261105-182333/iteration3-mac-violation.json) |
| 4 | OSPF reached FULL with matching MD5 keys, stayed down with a mismatched key after restarting the link, and recovered with the correct key. The collector received 43 syslog events. After reopening, R1 synchronized with authenticated NTP and the four switches synchronized using the campus server with the existing service ACL restrictions. | [OSPF behavior](../evidence/AUDIT-REMEDIATION-20261105-182333/iteration4-ospf-behavior.json), [reopened monitoring](../evidence/AUDIT-REMEDIATION-20261105-182333/iteration4-monitoring-reopened.json), [regression](../evidence/AUDIT-REMEDIATION-20261105-182333/iteration4-regression-summary.json) |
| 5 | Two 3650 multilayer switches provide HSRP gateways. A 2911 edge router has a separate routed path to each core and retains authenticated OSPF and PAT. With either core powered off, 50 campus and 49 external ICMP checks passed after recovery. Each case also verified DHCP renewals in all three departments, four internal HTTP sessions, three external HTTP sessions, authorized SSH and a policy denial. | [Core outages and restoration](../evidence/AUDIT-REMEDIATION-20261105-182333/iteration5-core-failover.json), [reopened routing](../evidence/AUDIT-REMEDIATION-20261105-182333/iteration5-reopened-routing.json), [regression](../evidence/AUDIT-REMEDIATION-20261105-182333/iteration5-regression-summary.json) |
| 6 · WAN trial | The temporary routed positive control reached the campus test interface. The 2911 rejected the inspection commands with `securityk9` disabled. The interactive console displayed the evaluation license prompt. The trial was rolled back to the verified Iteration 5 file. | [WAN trial](../evidence/AUDIT-REMEDIATION-20261105-182333/iteration6-firewall-behavior.json), [license prompt record](../evidence/AUDIT-REMEDIATION-20261105-182333/iteration6-security-license-interactive.json) |
| 6 · Release refresh | Campus Atlas captured the verified Iteration 5 topology, all 52 endpoint addresses and all 2,652 directed endpoint ping pairs. Every observed verdict matched the policy. The November 2 replay retains its 3,224 cases, which also covered infrastructure targets. | [Release manifest](../evidence/AUDIT-REMEDIATION-20261105-182333/release-manifest.json), [current endpoint addresses](../PROJECT_OVERVIEW.md#341-current-iteration-5-capture) |

## Current topology and forwarding

```text
SRV-EXTERNAL ── R2-EXTERNAL ── R1-CAMPUS (2911 edge and PAT)
                              ╱                       ╲
                   192.168.10.160/30            192.168.10.164/30
                            ╱                           ╲
                     SW1-CORE ═══ intercore trunk ═══ SW5-CORE
                            ╲                           ╱
                     Separate trunks from each core to
           SW2-ACCESS · SW3-FACULTY · SW4-STUDENTS · SW6-SERVICES
               Admin       Faculty      Students         SRV-CAMPUS
```

The intercore trunk carries VLANs 10, 20, 30, 40 and 99. Each departmental or services trunk carries its local VLAN and VLAN 99. Rapid PVST+ prefers SW1 as root. Both cores enforce departmental ACLs and relay DHCP from their physical client SVIs. The edge uses a preferred static route through SW1 and a floating static route through SW5 for each campus subnet. R2 learns no private campus routes. PAT provides the return path through R1.

| Segment | Network | HSRP gateway | SW1 SVI | SW5 SVI | DHCP range |
| --- | --- | --- | --- | --- | --- |
| Administration · VLAN 10 | `192.168.10.96/27` | `.97` | `.98` | `.99` | `.103–.126` |
| Faculty · VLAN 20 | `192.168.10.64/27` | `.65` | `.93` | `.94` | `.66–.92` |
| Students · VLAN 30 | `192.168.10.0/26` | `.1` | `.61` | `.62` | `.2–.60` |
| Services · VLAN 40 | `192.168.10.128/28` | `.129` | `.131` | `.132` | `.133` reserved by the default pool |
| Management · VLAN 99 | `192.168.10.144/28` | `.145` | `.147` | `.151` | Static |

R1 uses `192.168.10.161` and `192.168.10.165` toward the cores, whose routed interfaces use `.162` and `.166`. R1 and R2 retain `198.51.100.1/30` and `198.51.100.2/30` on the OSPF transit. SRV-CAMPUS uses `192.168.10.130` and the external HTTP server uses `203.0.113.10/24` through R2 at `203.0.113.1`.

The first successful three-client probe batches ended 43.64 seconds after the SW1 outage and 29.07 seconds after the SW5 outage. After repowering, the first successful batches ended after 3.28 and 3.49 seconds respectively. The expected HSRP roles were observed repeatedly after 35.59 and 39.89 seconds respectively. These are wall-clock probe observations. The cores use 3-second hellos and a 40-second hold timer in this simulator. Packet Tracer generated `no ip cef` on the two 3650s when the file reopened. Saving that running configuration synchronized startup and running state, and the second reopening verified both.

## Management addressing

| Interface or host | Address |
| --- | --- |
| VLAN 99 | `192.168.10.144/28` |
| HSRP management gateway | `192.168.10.145` |
| PC8-MGMT | `192.168.10.146` |
| SW1 through SW4 | `192.168.10.147–150` |
| SW5-CORE and SW6-SERVICES | `192.168.10.151–152` |

PC8-MGMT can use SSH to the seven managed campus IOS devices and access campus DNS and HTTP. Both departmental uplinks carry VLAN 99. The departmental subnet allocations and DHCP gateway addresses remain in use. R1, SRV-CAMPUS and individual access switches remain single-device dependencies.

The evidence folder holds the sanitized configuration exports, regression results, and private recovery archives. The local credential file and recovery archives are excluded from Git. The November 2 website capture and the November 5 fault tolerance capture retain their original evidence identities.

## Checkpoints and rollback

Each accepted iteration has a dated `iterationN-submission.json` record and an `iterationN-checkpoint-private.zip` in [the evidence directory](../evidence/AUDIT-REMEDIATION-20261105-182333/). The archive member `Secure_Campus_Network_Submission.pkt` is the exact saved simulation for that checkpoint. The archive also holds the matching `LAB_CREDENTIALS_V2.json` when it exists. To abandon an unsaved candidate, reopen the last verified submission. To recover an earlier saved iteration, validate the archived member against its dated record and reopen a separate recovery copy with the corresponding local credentials.

Before accepting a change, check campus and external access, authorized and denied traffic, DHCP renewal, uplink or core failover, and reopening. A failed probe or unsupported simulator feature remains in the dated evidence with its observed result.

## Simulator limitations

- The switch model rejected IP Source Guard. DAI accepted its configuration but the spoofing probe still succeeded, so the configuration was rolled back. The isolated rogue-DHCP trial could not establish a working positive control. [DAI behavior](../evidence/AUDIT-REMEDIATION-20261105-182333/iteration3-dai-behavior.json), [rogue DHCP trial](../evidence/AUDIT-REMEDIATION-20261105-182333/iteration3-rogue-dhcp.json)
- The four simulated switches dropped their NTP keys from running configuration after reopening, including with an eight-character key. R1 retained its key. The switches were configured to use SRV-CAMPUS with UDP/123 scoped by the existing service ACLs. [Persistence test](../evidence/AUDIT-REMEDIATION-20261105-182333/iteration4-ntp-eight-character-reopen.json), [fallback evidence](../evidence/AUDIT-REMEDIATION-20261105-182333/iteration4-ntp-switch-fallback.json)
- The access switch rejected the RADIUS client command. The trial was rolled back and campus SSH continues to use individual device credentials. [AAA behavior](../evidence/AUDIT-REMEDIATION-20261105-182333/iteration4-aaa-behavior.json)
- WAN and departmental filtering remain stateless in the verified file. The prepared WAN test uses a temporary external route and ACL exception to prove the path works before inspection, then removes the exception. With the security package active, the next checks cover outbound HTTP and ICMP, unsolicited inbound blocking and OSPF continuity. Departmental flows routed between campus SVIs stay outside the WAN inspection path. [WAN test script](../scripts/audit_wan.py)
