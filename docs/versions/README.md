# Versioned project documentation

Reviewed on **7 November 2026**. These names match the website's **Version 01** and **Version 02** selectors. They are documentation editions of existing captures, not new Packet Tracer releases.

| Topic | Version 01: original explorer | Version 02: dual-core campus |
| --- | --- | --- |
| Scope and iteration history | [Overview](version-01/overview.md) | [Overview](version-02/overview.md) |
| Topology, addressing and protocols | [Network architecture](version-01/network-architecture.md) | [Network architecture](version-02/network-architecture.md) |
| Access policies and security boundaries | [Access controls](version-01/access-controls.md) | [Access controls](version-02/access-controls.md) |
| Evidence, reproduction and limitations | [Verification](version-01/verification.md) | [Verification](version-02/verification.md) |

Read [the codebase review](../CODEBASE_REVIEW.md) for the November 7 code cleanup and its validation. Read [the final project README](../../README.md) for the consolidated project description.

## Version naming

- **Version 01** uses the November 2 website capture: 58 devices, 57 links and 3,224 recorded ping commands. Its data files use schema/capture suffix `v3`; that suffix is not the website edition.
- **Intermediate milestone, November 5:** three backup departmental uplinks, 58 devices and 60 links. [Fault-tolerance record](../fault-tolerance.md)
- **Version 02** uses the November 6 release of remediation **Iteration 5**: 60 devices, 64 links and 2,652 endpoint-to-endpoint ping pairs.
- Remediation **iterations 0–6** describe engineering steps inside the audit. Iteration 6's WAN inspection trial was rolled back. Its later website refresh publishes Iteration 5.
- The **November 7 cleanup** changes source validation, developer tooling and documentation. It does not establish a new simulator checkpoint.

For network facts, prefer the matching capture, its manifests and sanitized exports. Historical guides, screenshots and PDFs remain evidence of their own capture dates.
