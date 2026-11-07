# Version 01 — verification and limits

The [November 2 acceptance report](../../../WEBSITE_V3_ACCEPTANCE.md) records **3,224 / 3,224** ping cases matching policy across 52 endpoint sources and 62 destination addresses per source. Targets include infrastructure interfaces as well as endpoints.

## Evidence chain

1. [Snapshot](../../../data/network-snapshot.v3.json) identifies the topology, leases, submission hash and evidence files.
2. [Ping matrix](../../../data/ping-matrix.v3.json) records source/target addresses, expected outcomes, command output and enforcement observations.
3. [Capture directory](../../../evidence/WEBSITE-V3-20261102/) supplies the commands, routing evidence and sanitized configuration exports.
4. [Sync script](../../../website/scripts/sync-data.mjs) checks identities, hashes, duplicate pairs, coverage, packet counts and agreement with captured command data before publishing assets.

A denied command with an ACL attribution must include the corresponding deny-counter observation. The external private-route case instead requires R2 routing evidence. Some counters are scoped to a capture batch, not an individual command.

## Reproduce the viewer checks

From the project directory:

```powershell
cd website
.\run.ps1 test
.\run.ps1 build
.\run.ps1 preview
```

Open http://127.0.0.1:4173/#version-01. Startup can use historical evidence without the original local .pkt. The current-file verifier selects Version 02 when that release exists, so its success does not mean the newer .pkt equals Version 01.

## Limits

- Version 01's 57-link replay does not incorporate the later three backup links or the dual-core redesign.
- This is recorded evidence, not live health, telemetry, throughput or packet-capture monitoring.
- DHCP leases can change after a new simulator run.
- ICMP outcomes cannot establish application permissions or a stateful security boundary.
- The single router, core, server and departmental access switches are dependencies in this topology.

The later [backup-link acceptance](../../../FAULT_TOLERANCE_ACCEPTANCE.md) and [Version 02 verification](../version-02/verification.md) have separate file identities and test scopes. [Version index](../README.md)
