# Version 02 — verification and reproduction

The accepted source is **remediation Iteration 5**, saved and reopened on November 6, 2026. The release contains **2,652 / 2,652 directed endpoint pairs** matching policy: 52 × 51, excluding self-pings. These form 33 directional scenario groups. Version 01 has a different target scope, so 2,652 must not be described as reduced coverage of the same matrix.

## Recorded results

| Check | Recorded result |
| --- | --- |
| Inventory | 60 devices, 64 links, 50 PCs, two servers |
| Campus ICMP / DNS / HTTP / own gateway | 50 / 50 for each check |
| External ICMP | 49 / 49 departmental clients |
| Authorized campus SSH | 7 / 7 devices |
| Unauthorized SSH | 2 / 2 denied |
| Management external ICMP | 1 / 1 denied |
| Either core powered off | 50 campus clients, 49 external clients and policy isolation passed after recovery |
| DHCP during each core outage | 3 departmental renewals |
| HTTP during each core outage | 4 internal and 3 external sessions |
| Reopen | File identity, endpoints, configuration and routing verified |

Sources: [regression summary](../../../evidence/AUDIT-REMEDIATION-20261105-182333/iteration5-regression-summary.json), [core failover](../../../evidence/AUDIT-REMEDIATION-20261105-182333/iteration5-core-failover.json), [reopened summary](../../../evidence/AUDIT-REMEDIATION-20261105-182333/iteration5-reopened-summary.json), [release manifest](../../../evidence/AUDIT-REMEDIATION-20261105-182333/release-manifest.json).

## Local commands

From the project directory, run the offline Python checks:

```powershell
python -m unittest discover -s scripts/tests -v
python scripts/verify_audit_remediation.py
python -O scripts/verify_audit_remediation.py
```

The last two commands require the local .pkt, matching private checkpoint ZIP and evidence directory. They read saved material; they do not reconnect to the simulator. Missing private files in a public checkout are an unavailable prerequisite, not proof of a failing network.

Then run:

```powershell
cd website
.\run.ps1 test
.\run.ps1 build
.\run.ps1 verify-source
.\run.ps1 preview
```

Open http://127.0.0.1:4173/#version-02. The viewer can build without the local .pkt using recorded evidence; `verify-source` intentionally requires the file to match.

## November 7 cleanup validation

- Baseline before cleanup: 52 JavaScript tests passed.
- After cleanup: 71 JavaScript tests in eight files and six Python tests passed.
- TypeScript compilation and Vite production build passed using Node 24.22.1.
- Normal and optimized Python verified the same Iteration 5 file and evidence hashes.
- New negative tests reject malformed counts, duplicate endpoint/IP/node/port/pair identities, invalid links, wrong iteration, invalid bridge arrays and evidence-path escapes.

The build validates the release hash, checkpoint identity and projection structure before generating public assets. It validates historical evidence hashes and command-level records separately. This protects consistency, but hashes are not digital signatures and do not independently authenticate the author of evidence.

## Demonstration procedure

1. Show Version 02's inventory and explain the two cores, VLANs and external edge.
2. Replay Student → External Server, then Student → Faculty to compare an allowed flow with a policy stop.
3. Demonstrate Management → client and an unauthorized direction using the captured source/target addresses.
4. Open the recorded outage results and distinguish observed recovery from an availability guarantee.
5. Switch to Version 01 to explain why gateway ownership, management addressing and topology changed.

The November 7 work did not rerun live service or failure injection tests. Animation routes illustrate forwarding; they do not constitute packet captures or live STP telemetry.

[Codebase review](../../CODEBASE_REVIEW.md) · [Version index](../README.md)
