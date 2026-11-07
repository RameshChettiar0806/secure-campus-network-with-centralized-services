# Codebase analysis and refinement — 7 November 2026

This review covers the Campus Atlas application, its evidence synchronization boundary, the local bridge client, the checkpoint verifier and the documentation used to explain the network. The workspace also contains course material, temporary exports and another bridge repository; those are outside this project's cleanup.

Existing uncommitted configuration, evidence and documentation work was preserved. No simulator configuration, capture JSON, credential file or historical acceptance result was rewritten, and no live network mutation was performed.

## Architecture and responsibilities

| Area | Responsibility | Maintenance guidance |
| --- | --- | --- |
| website/src/app | Edition selection, shared preferences and application shell | Keep capture selection explicit |
| website/src/views and components | Topology, policy, scenarios and ping presentation | Explain recorded behavior without implying live health |
| website/src/lib | Routing illustrations, naming, validation and scenario grouping | Keep logic independent of presentation where practical |
| website/scripts | Source identity, release validation and public asset generation | Validate inputs before replacing generated assets |
| data | Versioned capture projections and ping matrices | Regenerate through the capture workflow; preserve provenance |
| scripts | Python bridge, capture, remediation and verification tools | Separate read-only verification from live mutation |
| evidence | Dated commands, measurements, manifests and sanitized exports | Treat accepted capture content as immutable |
| docs and root Markdown | Design, policy, teaching and acceptance | State the capture/version each claim describes |

The runtime pipeline is Packet Tracer → local Python/Qt bridge → dated evidence and JSON projection → synchronization/validation → static browser viewer. A running bridge is required only for live capture or configuration work, not for website presentation.

## Findings and changes

| ID | Finding before cleanup | Refinement | Validation |
| --- | --- | --- | --- |
| C01 | Version 02's inline synchronization checks covered identity and aggregate pairs but accepted inconsistent packet counts, duplicate endpoint names and invalid inventory references if a producer supplied matching metadata | Extracted validate-release.mjs; checks node/endpoint uniqueness, IPv4 addresses, physical port references, pair coverage, supported segments, packet counts/verdicts and manifest iteration | 19 additional Vitest cases, including the real capture and malformed candidates |
| C02 | verify_audit_remediation.py used assert for integrity checks; Python -O removes these checks | Replaced assertions with explicit ValueError checks, readable errors and path validation inside verify() | Optimized subprocess rejects a failed checkpoint; normal and optimized verification of the real file pass |
| C03 | pt_client.py compressed parsing, networking and CLI logic; response lifetime was unmanaged and malformed array shapes could drop data or raise incidental errors | Structured functions, context-managed HTTP response, strict dense Qt-array validation and argparse entry point | Nested arrays, malformed arrays and mocked response closure tests |
| C04 | The bridge CLI could write an evidence result outside evidence/ through its output argument | Resolve and check the destination before making the tool call; create nested evidence directories as needed | Relative traversal, absolute escape and directory-root rejection tests |
| D01 | The main README mixed historical router-on-a-stick guides with the current dual-core release | Consolidated current project README and paired version-01/version-02 guides; added scope notices to older topical guides | Local Markdown target/fragment checks |
| D02 | Website edition numbers, JSON v3 filenames and audit iterations could be mistaken for the same version sequence | Explicit naming map and iteration tables | Cross-check against release and checkpoint manifests |

The validator preserves the producer's definition of observed allow: at least one reply from a completed four-packet probe. It checks received is an integer between zero and four; it does not change partial replies into a new policy verdict. A policy mismatch can be represented honestly when the recorded match totals agree. Integrity validation and network acceptance are separate concerns.

## Validation performed

| Check | Result |
| --- | --- |
| Baseline website suite | 52 tests passed before changes |
| Final website suite | 71 tests passed in eight files |
| Python offline unit tests | Six tests passed |
| TypeScript and production build | Passed with the selected Node 24.22.1 runtime |
| Current checkpoint verifier | Iteration 5, 60 devices, 64 links and recorded hashes verified |
| Optimized Python verifier | Same successful result; failure checks remain active |
| Strict website source verification | Current local .pkt matches Version 02 |

Commands and prerequisites are in [Version 02 verification](versions/version-02/verification.md). The live failure, DHCP, DNS, HTTP and SSH results are historical evidence from November 6; this cleanup revalidated the saved artifacts rather than rerunning those experiments.

## Remaining engineering boundaries

- Historical and live mutation scripts retain their original workflows; this is a targeted cleanup, not a wholesale rewrite of every experiment. Some other capture scripts still use assertions. Do not run live capture/mutation workflows with Python optimization until those checks are similarly hardened.
- The bridge depends on the adjacent cisco-pt-mcp checkout and its Python dependencies; this dependency is not needed by the offline viewer.
- Snapshot hashes protect against accidental disagreement. An actor able to rewrite both a capture and its manifests could create a different consistent set; the project has no signed evidence chain.
- Generated public assets, build output and private simulator recovery files are not source code. Removing historical captures would break replay, so they were retained.
- Existing stateless filtering, unsupported security experiments, single-device dependencies and unmeasured performance are described in [Version 02 architecture](versions/version-02/network-architecture.md) and [access controls](versions/version-02/access-controls.md).

[Versioned documentation index](versions/README.md) · [Project README](../README.md)
