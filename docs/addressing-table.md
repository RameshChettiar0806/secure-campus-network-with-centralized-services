# Addressing table

The campus assignments below are retained. The [external extension](ospf-pat-extension.md) adds 198.51.100.0/30 for the OSPF/PAT transit and 203.0.113.0/24 for the test server.

The campus uses variable-length subnet masks (VLSM) within `192.168.10.0/24`. Each VLAN has a gateway on R1. The 49 dynamic clients use departmental pools. PC8-MGMT and the services server have static addresses.

## VLAN plan

| VLAN | Segment | Network | Subnet mask | Gateway | Broadcast | Usable hosts | DHCP range |
| --- | --- | --- | --- | --- | --- | ---: | --- |
| 30 | Students | 192.168.10.0/26 | 255.255.255.192 | 192.168.10.1 | 192.168.10.63 | 62 | 192.168.10.2 – 192.168.10.62 |
| 20 | Faculty | 192.168.10.64/27 | 255.255.255.224 | 192.168.10.65 | 192.168.10.95 | 30 | 192.168.10.66 – 192.168.10.94 |
| 10 | Administration | 192.168.10.96/27 | 255.255.255.224 | 192.168.10.97 | 192.168.10.127 | 30 | 192.168.10.103 – 192.168.10.126 |
| 40 | Services | 192.168.10.128/28 | 255.255.255.240 | 192.168.10.129 | 192.168.10.143 | 14 | Static |
 
## Device and interface addresses

These addresses come from the [October 31 snapshot](../data/network-snapshot.v2.json). A DHCP client can receive a different address after reopening the simulation. Use `ipconfig` on that client before a live test. On the website, open **Addressing table** and search by device label or IP.

| Device | Interface | VLAN | IPv4 / prefix | Assignment | Default gateway |
| --- | --- | --- | --- | --- | --- |
| R1-CAMPUS | GigabitEthernet0/0.10 | 10 | 192.168.10.97/27 | Static | — |
| R1-CAMPUS | GigabitEthernet0/0.20 | 20 | 192.168.10.65/27 | Static | — |
| R1-CAMPUS | GigabitEthernet0/0.30 | 30 | 192.168.10.1/26 | Static | — |
| R1-CAMPUS | GigabitEthernet0/0.40 | 40 | 192.168.10.129/28 | Static | — |
| SW1-CORE | Vlan10 | 10 | 192.168.10.99/27 | Static | 192.168.10.97 |
| SW2-ACCESS | Vlan10 | 10 | 192.168.10.100/27 | Static | 192.168.10.97 |
| SW3-FACULTY | Vlan10 | 10 | 192.168.10.101/27 | Static | 192.168.10.97 |
| SW4-STUDENTS | Vlan10 | 10 | 192.168.10.102/27 | Static | 192.168.10.97 |
| SRV-CAMPUS | FastEthernet0 | 40 | 192.168.10.130/28 | Static | 192.168.10.129 |
| PC0 | FastEthernet0 | 30 | 192.168.10.19/26 | DHCP | 192.168.10.1 |
| PC1 | FastEthernet0 | 30 | 192.168.10.20/26 | DHCP | 192.168.10.1 |
| PC2 | FastEthernet0 | 30 | 192.168.10.21/26 | DHCP | 192.168.10.1 |
| PC3 | FastEthernet0 | 30 | 192.168.10.4/26 | DHCP | 192.168.10.1 |
| PC4 | FastEthernet0 | 30 | 192.168.10.25/26 | DHCP | 192.168.10.1 |
| PC5 | FastEthernet0 | 20 | 192.168.10.78/27 | DHCP | 192.168.10.65 |
| PC6 | FastEthernet0 | 20 | 192.168.10.81/27 | DHCP | 192.168.10.65 |
| PC7 | FastEthernet0 | 20 | 192.168.10.77/27 | DHCP | 192.168.10.65 |
| PC8-MGMT | FastEthernet0 | 10 | 192.168.10.98/27 | Static | 192.168.10.97 |
| PC9-ADMIN | FastEthernet0 | 10 | 192.168.10.108/27 | DHCP | 192.168.10.97 |
| PC10 | FastEthernet0 | 30 | 192.168.10.18/26 | DHCP | 192.168.10.1 |
| PC11 | FastEthernet0 | 30 | 192.168.10.11/26 | DHCP | 192.168.10.1 |
| PC12 | FastEthernet0 | 30 | 192.168.10.17/26 | DHCP | 192.168.10.1 |
| PC13 | FastEthernet0 | 30 | 192.168.10.16/26 | DHCP | 192.168.10.1 |
| PC14 | FastEthernet0 | 30 | 192.168.10.10/26 | DHCP | 192.168.10.1 |
| PC15 | FastEthernet0 | 30 | 192.168.10.3/26 | DHCP | 192.168.10.1 |
| PC16 | FastEthernet0 | 30 | 192.168.10.7/26 | DHCP | 192.168.10.1 |
| PC17 | FastEthernet0 | 30 | 192.168.10.22/26 | DHCP | 192.168.10.1 |
| PC18 | FastEthernet0 | 30 | 192.168.10.2/26 | DHCP | 192.168.10.1 |
| PC19 | FastEthernet0 | 30 | 192.168.10.15/26 | DHCP | 192.168.10.1 |
| PC20 | FastEthernet0 | 30 | 192.168.10.23/26 | DHCP | 192.168.10.1 |
| PC21 | FastEthernet0 | 30 | 192.168.10.24/26 | DHCP | 192.168.10.1 |
| PC22 | FastEthernet0 | 30 | 192.168.10.8/26 | DHCP | 192.168.10.1 |
| PC23 | FastEthernet0 | 30 | 192.168.10.9/26 | DHCP | 192.168.10.1 |
| PC24 | FastEthernet0 | 30 | 192.168.10.5/26 | DHCP | 192.168.10.1 |
| PC25 | FastEthernet0 | 20 | 192.168.10.70/27 | DHCP | 192.168.10.65 |
| PC26 | FastEthernet0 | 20 | 192.168.10.66/27 | DHCP | 192.168.10.65 |
| PC27 | FastEthernet0 | 20 | 192.168.10.69/27 | DHCP | 192.168.10.65 |
| PC28 | FastEthernet0 | 20 | 192.168.10.79/27 | DHCP | 192.168.10.65 |
| PC29 | FastEthernet0 | 20 | 192.168.10.83/27 | DHCP | 192.168.10.65 |
| PC30 | FastEthernet0 | 20 | 192.168.10.67/27 | DHCP | 192.168.10.65 |
| PC31 | FastEthernet0 | 20 | 192.168.10.73/27 | DHCP | 192.168.10.65 |
| PC32 | FastEthernet0 | 20 | 192.168.10.80/27 | DHCP | 192.168.10.65 |
| PC33 | FastEthernet0 | 20 | 192.168.10.71/27 | DHCP | 192.168.10.65 |
| PC34 | FastEthernet0 | 20 | 192.168.10.72/27 | DHCP | 192.168.10.65 |
| PC35 | FastEthernet0 | 20 | 192.168.10.68/27 | DHCP | 192.168.10.65 |
| PC36 | FastEthernet0 | 20 | 192.168.10.76/27 | DHCP | 192.168.10.65 |
| PC37 | FastEthernet0 | 20 | 192.168.10.75/27 | DHCP | 192.168.10.65 |
| PC38 | FastEthernet0 | 20 | 192.168.10.74/27 | DHCP | 192.168.10.65 |
| PC39 | FastEthernet0 | 20 | 192.168.10.82/27 | DHCP | 192.168.10.65 |
| PC40 | FastEthernet0 | 10 | 192.168.10.113/27 | DHCP | 192.168.10.97 |
| PC41 | FastEthernet0 | 10 | 192.168.10.111/27 | DHCP | 192.168.10.97 |
| PC42 | FastEthernet0 | 10 | 192.168.10.109/27 | DHCP | 192.168.10.97 |
| PC43 | FastEthernet0 | 10 | 192.168.10.112/27 | DHCP | 192.168.10.97 |
| PC44 | FastEthernet0 | 10 | 192.168.10.114/27 | DHCP | 192.168.10.97 |
| PC45 | FastEthernet0 | 10 | 192.168.10.107/27 | DHCP | 192.168.10.97 |
| PC46 | FastEthernet0 | 10 | 192.168.10.105/27 | DHCP | 192.168.10.97 |
| PC47 | FastEthernet0 | 10 | 192.168.10.110/27 | DHCP | 192.168.10.97 |
| PC48 | FastEthernet0 | 10 | 192.168.10.106/27 | DHCP | 192.168.10.97 |
| PC49 | FastEthernet0 | 10 | 192.168.10.103/27 | DHCP | 192.168.10.97 |

[Return to the project contents](../README.md#table-of-contents)
