import { useState } from 'react';
import DeviceSymbol from '../components/DeviceSymbol';
import type { Capture, EndpointPair } from '../lib/checkpoint';
import styles from './Remediation.module.css';

const descriptions: Record<number, string> = {
  10: 'Administration workstations can initiate diagnostic pings toward Faculty and Students, reach campus services and browse the external demonstration server.',
  20: 'Faculty workstations communicate locally and reach campus DNS, HTTP and the external server. The campus ACL restricts new requests toward other departments.',
  30: 'Student workstations share one local VLAN and can reach the campus server and external HTTP demonstration. New requests toward Administration and Faculty meet an ACL boundary at the active core.',
  40: 'The Campus Services Server provides DHCP, DNS and the campus portal. Client DHCP requests from other VLANs reach it through the relay configuration on both cores.',
  99: 'The Management Workstation uses a separate VLAN for administration and diagnostics. It can establish SSH to the seven campus IOS devices and use internal services.',
};

export default function CheckpointGuide({ capture, labels, onPing, onTopology }: {
  capture: Capture; labels: ReadonlyMap<string, string>; onPing: (pair: EndpointPair) => void; onTopology: () => void;
}) {
  const [segment, setSegment] = useState(30);
  const network = capture.networks.find(network => network.vlan === segment)!;
  const members = capture.endpoints.filter(endpoint => endpoint.segment === segment);
  const example = members[0];
  const cable = capture.links.find(link => link.from === example.name || link.to === example.name)!;
  const accessId = cable.from === example.name ? cable.to : cable.from;
  const devices = [example.name, accessId].map(id => capture.nodes.find(device => device.name === id)!);
  return <section aria-labelledby="topology-guide-title">
    <div className={styles.sectionIntro}>
      <p className={styles.eyebrow}>Topology guide</p>
      <h2 id="topology-guide-title">How the campus connects</h2>
      <p>Start with a VLAN, follow an endpoint to its access switch, and see how the core gateways handle traffic to other networks.</p>
    </div>
    <div className={styles.guideChoices} role="group" aria-label="Choose a campus VLAN">
      {capture.networks.map(vlan => <button key={vlan.vlan} type="button" className={styles.secondary}
        aria-pressed={vlan.vlan === segment} onClick={() => setSegment(vlan.vlan)}>{vlan.name} · VLAN {vlan.vlan}</button>)}
    </div>
    <article className={styles.guidePanel}>
      <div className={styles.panelHeading}><h3>{network.name}</h3><span>{members.length} captured {members.length === 1 ? 'endpoint' : 'endpoints'}</span></div>
      <p>{descriptions[segment]}</p>
      <ol className={styles.guidePath} aria-label="Endpoint attachment">
        {devices.map(device => <li key={device.name}>
          <DeviceSymbol model={device.model} size={30}/><span><strong>{labels.get(device.name)}</strong><small>{device.model}</small></span>
        </li>)}
      </ol>
      <dl className={styles.guideFacts}>
        <div><dt>Local subnet</dt><dd><code>{network.subnet}</code></dd></div>
        <div><dt>Virtual default gateway</dt><dd><code>{network.gateway}</code></dd></div>
        <div><dt>Example address</dt><dd><code>{example.ip}</code></dd></div>
      </dl>
      <div className={styles.actions}>
        <button type="button" className={styles.primary} onClick={() => onPing({ source: example.name, target: segment === 40 ? 'PC0' : 'SRV-CAMPUS' })}>
          {segment === 40 ? 'Inspect server → Student in Ping Lab' : 'Replay access to the campus server'}
        </button>
        <button type="button" className={styles.secondary} onClick={onTopology}>Open full topology</button>
      </div>
    </article>
    <div className={styles.guideCards}>
      <article>
        <h3>Local switching</h3>
        <p>Endpoints in the same VLAN exchange frames through their access switch. The switch uses its MAC table to choose the outgoing port.</p>
      </article>
      <article>
        <h3>Trunks and segmentation</h3>
        <p>Every access switch has a trunk to each core. Each departmental or services trunk carries its local VLAN and management VLAN 99. The intercore trunk carries all five campus VLANs.</p>
      </article>
      <article>
        <h3>Shared gateways</h3>
        <p>The two 3650 core switches use HSRP to provide each VLAN’s virtual gateway. The active core routes between VLANs and checks the ingress ACL for the source VLAN.</p>
      </article>
      <article>
        <h3>Primary and backup paths</h3>
        <p>Rapid PVST+ selects a forwarding path and holds alternatives ready. If either core fails, the surviving core can provide the gateways and carry campus traffic.</p>
      </article>
      <article>
        <h3>Centralized services</h3>
        <p>The Campus Services Server at <code>192.168.10.130</code> supplies addresses through DHCP relay, resolves <code>portal.campus.test</code>, and delivers the portal over HTTP.</p>
      </article>
      <article>
        <h3>Management access</h3>
        <p>The Management Workstation at <code>192.168.10.146</code> uses VLAN 99. VTY source restrictions limit SSH to this workstation. Its external access is blocked by campus policy.</p>
      </article>
    </div>
    <article className={styles.guidePanel}>
      <h3>The external branch</h3>
      <p>The Campus Edge Router connects to both cores and to the External Router over <code>198.51.100.0/30</code>. Authenticated OSPF supplies the route to the External Server network. PAT translates departmental client traffic to <code>198.51.100.1</code>, allowing replies to return through the edge.</p>
      <p>The External Router has no private campus routes. A new request from the External Server to a private campus endpoint stops at that router.</p>
      <div className={styles.actions}>
        <button type="button" className={styles.primary} onClick={() => onPing({ source: 'PC0', target: 'SRV-EXTERNAL' })}>Replay Student → External</button>
        <button type="button" className={styles.secondary} onClick={() => onPing({ source: 'SRV-EXTERNAL', target: 'PC0' })}>Inspect the reverse direction</button>
      </div>
    </article>
  </section>;
}
