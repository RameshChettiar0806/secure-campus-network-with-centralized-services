# Current website acceptance

Verified on 2 November 2026 (IST). All website sections now reflect the saved extended Packet Tracer network. The simulator file and IOS configurations were unchanged during the 3,224-command ping capture.

- Inventory: 58 devices, 57 links; 50 PCs, four switches, two routers and two servers.
- Ping capture: 52 endpoint sources × 62 destination addresses = 3,224 actual commands; all match policy. One ACL-counter case was rechecked in isolation after initial address discovery; both the original batch and passing recheck are retained.
- Fresh service/addressing/routing/policy checks: 372 passing cases across 16 groups, plus the complete ping group.
- Website: 44 automated checks pass; production build and strict source-identity verification pass.
- Introduction, interactive topology, device/link inspectors, topology guide, addressing, ping lab, access-policy matrix and detailed rules use the current dataset.
- Routed links are shown separately from VLAN trunks. The ping walkthrough explains OSPF forwarding, PAT and reverse PAT, WAN-IN denial, and missing private routes at R2.
- All 23 selectable policy-matrix cells point to measured commands in the current capture.
- Browser verification passed for the main topology, external router inspector, successful PAT replay, WAN ACL denial, private-route failure, policy matrix and routed addressing; no browser errors were observed.
- Preview images: `evidence/WEBSITE-V3-20261102/website-topology-current.png` and `website-topology-branch.png`.

Current datasets: `data/network-snapshot.v3.json`, `data/ping-matrix.v3.json`, `data/policy-matrix.v3.json`, and `data/ospf-pat-extension.v3.json`. Evidence is under `evidence/WEBSITE-V3-20261102/`; current device exports are `configs/*-CURRENT.txt`.

Historical v2 data stays on disk. The failure/recovery walkthrough retains its explicitly dated original evidence. The website replays recorded Packet Tracer traffic; it does not send live packets.

Saved submission SHA-256: `b3b7892fe2d2e80330a2c6b80df6b2cfaf1032d33b3b4ab78f88ca2883b28406`.
