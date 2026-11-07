# Centralized services

> Historical scope: this guide describes Version 01 relay and pool settings. Version 02 uses core SVI relays and revised pools; see [current architecture](versions/version-02/network-architecture.md).

- **DHCP** supplies 49 clients with an address, mask, gateway and DNS server. Discover, Offer, Request and Acknowledge use UDP ports 67/68. R1’s `ip helper-address 192.168.10.130` relays departmental broadcasts to the server. Its three client pools exclude static infrastructure. Packet Tracer’s regenerated default `serverPool` is constrained to .131.
- **DNS** maps the A record `portal.campus.test` to `192.168.10.130`. UDP port 53 was verified end to end. The ACL also permits TCP DNS, which was not exercised end to end.
- **HTTP** serves the portal over TCP port 80. Loading the page by hostname exercises both DNS and HTTP. The page content travels unencrypted.

On a client, first run `ipconfig /all` to check its lease, gateway and DNS server. Run `nslookup portal.campus.test` to check the A record, then open the hostname in the simulated browser. The [portal walkthrough](../output/pdf/02-centralized-services.pdf) gives the expected result at each step.

[Return to the project contents](../README.md#table-of-contents)
