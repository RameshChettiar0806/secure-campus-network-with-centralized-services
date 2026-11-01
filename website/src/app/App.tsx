import { lazy, Suspense, useEffect, useMemo, useState } from 'react';
import { loadSnapshot } from '../data/snapshot';
import pingIndex from '../data/ping-index.json';
import { isDeviceHighlighted, readPreference, shortName, validateNetwork, vlanColors, writePreference } from '../lib/network';
import DeviceSymbol from '../components/DeviceSymbol';
import TopologyGuide from '../components/TopologyGuide';
import type { PingPair } from '../components/PolicyExplorer';
import Inspector from '../components/Inspector';
import Addressing from '../views/Addressing';
import Policies from '../views/Policies';
import LabResults from '../views/LabResults';
import sourceCheck from '../data/source-check.json';
import styles from './App.module.css';

const tabs = [{ id: 'topology', icon: '⌘', name: 'Topology' }, { id: 'guide', icon: '◇', name: 'Topology guide' }, { id: 'addressing', icon: '▦', name: 'Addressing table' }, { id: 'ping', icon: '↗', name: 'Ping lab' }, { id: 'policy', icon: '⇄', name: 'Access policy' }, { id: 'tests', icon: '✓', name: 'Lab results' }] as const;
const TopologyCanvas = lazy(() => import('../components/TopologyCanvas'));
const PingLab = lazy(() => import('../components/PingLab'));
type Tab = typeof tabs[number]['id'];

export default function App() {
  const snapshot = useMemo(() => { const s = loadSnapshot(); const errors = validateNetwork(s); if (errors.length) throw new Error(errors.join('\n')); return s; }, []);
  const [tab, setTab] = useState<Tab>('topology');
  const [pingPair, setPingPair] = useState<PingPair>({source:'pc0',target:'server0'});
  const [selected, setSelected] = useState('r1');
  const [linkId, setLinkId] = useState<string | null>(null);
  const [vlan, setVlan] = useState<number | null>(null);
  const [query, setQuery] = useState('');
  const [expanded, setExpanded] = useState(false);
  const [testId, setTestId] = useState('A01');
  const [theme, setTheme] = useState<'dark' | 'light'>(() => readPreference('campus-theme', 'dark', (v): v is 'dark' | 'light' => v === 'dark' || v === 'light'));
  useEffect(() => { document.documentElement.dataset.theme = theme; writePreference('campus-theme', theme); }, [theme]);
  const select = (id: string) => { setSelected(id); setLinkId(null); };
  const openTest = (id: string) => { setTestId(id); setTab('tests'); };
  const pcCount = snapshot.devices.filter(d => d.model === 'PC-PT').length;
  const switchCount = snapshot.devices.filter(d => d.id.startsWith('sw')).length;
  const endpointCount = snapshot.devices.filter(d => ['PC-PT', 'Server-PT'].includes(d.model)).length;
  const trunkCount = snapshot.links.filter(l => l.mode === 'trunk').length;
  const devices = snapshot.devices.filter(d => `${d.label} ${d.role} ${d.model}`.toLowerCase().includes(query.toLowerCase()));

  return <div className={styles.app}>
    <a href="#main-content" className={styles.skipLink}>Skip to main content</a>
    <header className={styles.header}><div className={styles.brand}><span className={styles.brandMark}>⌘</span><div><strong>campus<span>atlas</span></strong><small>NETWORK EXPLORER</small></div></div><div className={styles.headerActions}><button className={styles.themeButton} onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')} aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}>{theme === 'dark' ? '☼' : '☾'}</button></div></header>
    <div className={styles.intro}><div><h1>{snapshot.projectTitle}</h1><p>{pcCount} PCs across three departments. Explore the network and replay {pingIndex.cases.toLocaleString('en-IN')} verified ping combinations.</p></div><div className={styles.capture}><span className={styles.sectionLabel}>CENTRALIZED CAMPUS SERVICES</span><strong>{snapshot.services.dns.records[0].name}</strong><small>{snapshot.services.ipv4} · DHCP / DNS / HTTP</small></div></div>
    <div className={styles.stats}><div><span>DEVICES</span><strong>{snapshot.devices.length}<small>1 router · {switchCount} switches · {endpointCount} endpoints</small></strong></div><div><span>PHYSICAL LINKS</span><strong>{snapshot.links.length}<small>{trunkCount} trunks · {snapshot.links.length - trunkCount} access links</small></strong></div><div><span>NETWORK SEGMENTS</span><strong>{snapshot.vlans.length}<small>VLSM · /26, /27 and /28</small></strong></div><button onClick={() => openTest('A05')} aria-label="View campus portal verification"><span>CENTRALIZED SERVICES ↗</span><strong>3<small className={styles.statusUp}>DHCP · DNS · HTTP</small></strong></button></div>
    <nav className={styles.tabs} aria-label="Viewer sections">{tabs.map(item => <button key={item.id} aria-current={tab === item.id ? 'page' : undefined} className={tab === item.id ? styles.activeTab : ''} onClick={() => setTab(item.id)}><span>{item.icon}</span>{item.name}{item.id === 'tests' && <small>{snapshot.recordedTests.length}</small>}</button>)}</nav>
    <main id="main-content" tabIndex={-1}>
      {tab === 'topology' ? <>
        <div className={styles.topologyToolbar}><div><strong>Physical topology</strong><span>Choose a department to focus its devices and connections</span></div><div className={styles.filters} aria-label="VLAN highlights"><button aria-pressed={vlan === null} onClick={() => setVlan(null)}>All VLANs</button>{snapshot.vlans.map(v => <button key={v.id} aria-pressed={vlan === v.id} onClick={() => setVlan(vlan === v.id ? null : v.id)}><i style={{ background: vlanColors[v.id] }}/>{shortName(v.name)}<small>{v.id}</small></button>)}<button aria-pressed={expanded} onClick={() => setExpanded(v => !v)}>{expanded ? 'Show panels' : 'Expand topology'}</button></div></div>
        <div className={`${styles.workspace} ${expanded ? styles.workspaceWide : ''}`}>
          <aside className={styles.inventory} aria-label="Keyboard accessible device inventory"><div className={styles.inventoryHeading}><span className={styles.sectionLabel}>DEVICE INVENTORY</span><span>{snapshot.devices.length}</span></div><label className={styles.search}><span>⌕</span><input aria-label="Find a device" placeholder="Find a device…" value={query} onChange={e => setQuery(e.target.value)}/>{query && <button aria-label="Clear device search" onClick={() => setQuery('')}>×</button>}</label><div className={styles.deviceList}>{devices.sort((a, b) => { const order = (id: string) => id === 'r1' ? 0 : id.startsWith('sw') ? 1 : id === 'server0' ? 2 : 3; return order(a.id) - order(b.id); }).map(d => <button key={d.id} aria-pressed={selected === d.id && !linkId} className={`${selected === d.id && !linkId ? styles.deviceActive : ''} ${!isDeviceHighlighted(d, vlan) ? styles.inventoryDimmed : ''}`} onClick={() => select(d.id)}><DeviceSymbol model={d.model} size={22}/><span><strong>{d.label}</strong><small>{d.model}</small></span><span className={styles.deviceVlan} style={{ color: vlanColors[d.vlanId ?? 0] }}>{d.vlanId ?? '↗'}</span></button>)}{!devices.length && <p className={styles.help}>No devices match “{query}”.</p>}</div>
          <details className={styles.linkList}><summary>Physical links · {snapshot.links.length}</summary>{snapshot.links.map(l => <button key={l.id} onClick={() => setLinkId(l.id)} aria-pressed={linkId === l.id}>{l.sourceDeviceId} ↔ {l.targetDeviceId}<small>{l.mode} · VLAN {l.vlanIds.join('/')}</small></button>)}</details></aside>
          <Suspense fallback={<div className={styles.canvas}><p className={styles.help}>Loading topology…</p></div>}><TopologyCanvas snapshot={snapshot} vlan={vlan} selected={selected} select={select} selectLink={setLinkId} theme={theme}/></Suspense>
          <Inspector key={linkId ?? selected} snapshot={snapshot} selected={selected} linkId={linkId} select={select}/>
        </div>
        <div className={styles.services}><span className={styles.sectionLabel}>CENTRALIZED SERVICES</span><div><span>DHCP</span><code>3 client pools</code></div><div><span>DNS</span><code>{snapshot.services.dns.records[0].name}</code></div><div><span>HTTP</span><code>{snapshot.services.ipv4}:80</code></div><div><span>SSHv2</span><code>PC8-MGMT only</code></div></div>
      </> : tab === 'guide' ? <TopologyGuide snapshot={snapshot} inspect={(id, segment) => { select(id); setVlan(segment); setExpanded(false); setQuery(''); setTab('topology'); }}/> : tab === 'addressing' ? <Addressing snapshot={snapshot}/> : tab === 'ping' ? <Suspense fallback={<p className={styles.help}>Loading recorded pings…</p>}><PingLab snapshot={snapshot} theme={theme} initial={pingPair}/></Suspense> : tab === 'policy' ? <Policies snapshot={snapshot} openTest={openTest} openPing={pair => { setPingPair(pair); setTab('ping'); }}/> : <LabResults snapshot={snapshot} selectedTest={testId} selectTest={setTestId}/>}
    </main>
    <footer className={styles.footer}><span><span className={styles.tinyDot}/> {sourceCheck.matchesRecordedSubmission ? 'Recorded lab · Submission hash verified' : 'Recorded lab · Current submission hash differs or file is unavailable'}</span><span>VLAN segmentation · Router-on-a-stick · Centralized services</span></footer>
  </div>;
}
