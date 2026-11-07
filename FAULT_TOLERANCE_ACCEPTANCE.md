# Fault-tolerance acceptance

Verified in Cisco Packet Tracer 9.0.1 on **5 November 2026 (IST)**, including reopening the saved submission on Desktop 1.

The submission has **50 PCs, 58 network devices and 60 links**. Three backup departmental trunks were added; all 57 earlier links were retained. R1 and R2 configurations are unchanged. [Design and demonstration instructions](docs/fault-tolerance.md) describe the ports, costs and remaining failure dependencies.

## Observed results

| Check | Result | Evidence in `evidence/FAULT-TOLERANCE-20261105/` |
| --- | --- | --- |
| Baseline campus connectivity | All 50 PCs reached the central server | `baseline-campus-pings.json` |
| Normal path selection | Gi0/1 is Root FWD; Gi0/2 is Altn BLK for each carried department/management VLAN | `settled-stp.json`, `reopened-state.json` |
| Simultaneous failure | SW1 Gi0/2, Fa0/23 and Fa0/24 shut down together; all three access-switch Gi0/2 ports became Root FWD | `simultaneous-primary-failure.json`, `backup-path-policy-dhcp-stp.json` |
| Failure probe sequences | PC9-ADMIN, PC5 and PC0 each received 30/30 replies across failure: **90/90 total** | `simultaneous-primary-failure.json`, `failure-measurements.json` |
| Campus service over backups | All 50 PCs reached the server and loaded the portal by hostname | `backup-path-campus-pings.json`, `backup-path-http.json`, `backup-path-http-retry.json` |
| External access over backups | All 50 PCs reached the external server and loaded its page by hostname | `backup-path-external-pings.json`, `backup-path-external-http.json`, `backup-path-external-http-retry.json` |
| DHCP and DNS over backups | One DHCP renewal in each department retained valid settings; all three resolved the portal hostname | `backup-path-dhcp-dns-management.json` |
| Isolation over backups | Three expected ICMP denials, with increased matching ACL deny counters; Administration control request succeeded | `backup-path-policy-dhcp-stp.json` |
| SSH over backups | PC8-MGMT authenticated to SW4 using SSHv2; PC9-ADMIN was refused before authentication | `backup-path-ssh-authorized.json`, `backup-path-ssh-denied.json` |
| Restoration | Primary paths resumed. Each 20-probe sequence received 16 replies and lost four; subsequent checks received 4/4 replies in each department | `primary-restoration.json`, `restored-connectivity.json` |
| Reopening and persistence | Correct costs, primary/standby roles and trunk allowlists persisted; running/startup configurations match on all four switches | `reopened-state.json` |
| Reopened services | All 50 PCs reached the campus server, loaded its portal and reached the external server; all 52 endpoint addresses were unique; OSPF adjacency FULL | `reopened-checks.json`, `reopened-external-pings.json` |
| Topology preservation | Exactly the three documented backup cables added; no earlier cable removed | `topology-preservation.json` |

Initial HTTP attempts timed out for 7 campus clients and 3 external clients during backup-path checks. All succeeded on retry. The raw attempts and retries are retained. A client connectivity pass means it received a reply; the separate 90-probe measurement is the basis for the zero-observed-loss failover result. Reopened portal requests passed on the first attempt for all 50 clients.

## Timing interpretation

| Source | First server reply after shutdown | Gap between surrounding successful replies |
| --- | ---: | ---: |
| PC9-ADMIN | 207 ms | 1,035 ms |
| PC5 | 229 ms | 1,057 ms |
| PC0 | 212 ms | 1,037 ms |

These are wall-clock output-event observations with probes approximately one second apart. No fast-forward was used during the measured failure/restoration sequences. The first reply bounds observed service recovery for that probe stream; it is **not an exact STP convergence measurement**, a production latency guarantee or proof of zero interruption. Restoration was observably disruptive, and its exact recovery duration was not measured.

## Saved file and evidence

The reopened file is `Secure_Campus_Network_Submission.pkt`. Its SHA-256 is recorded in [SUBMISSION_SHA256.txt](SUBMISSION_SHA256.txt) and [submission.json](evidence/FAULT-TOLERANCE-20261105/submission.json). Six sanitized `configs/*-CURRENT.txt` exports correspond to the reopened state. The local recovery archive is `evidence/FAULT-TOLERANCE-20261105/campus-before-fault-tolerance.zip`.

Run `python scripts/verify_fault_tolerance.py` from the project directory to check the saved-file identity and the recorded acceptance evidence. This is an offline evidence audit, not a new live simulation test. The manifest lists hashes of public evidence and current configuration exports; recovery archives and credentials are excluded.

The website still presents its **November 2, 58-device/57-link snapshot** and historical 3,224-case matrix. Those cases were not rerun for this extension. Its source-identity guard should reject this newer live submission until the website is deliberately recaptured.

## Scope limits

This implementation protects the tested departmental uplinks. It does not provide redundant campus routing, core/access switch redundancy, server redundancy, a redundant external path, EtherChannel, load balancing or stateful filtering. Normal and backup bandwidth is unmeasured; all backup trunks are nominally 100 Mb/s. The campus router, its core trunk, core switch, central server and each department switch remain single points of failure.

[Return to the project contents](README.md)
