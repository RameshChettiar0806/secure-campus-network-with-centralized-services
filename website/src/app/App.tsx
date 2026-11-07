import { lazy, Suspense, useEffect, useState } from 'react';
import { readPreference, writePreference } from '../lib/network';
import sourceCheck from '../data/source-check.json';
import type { CheckpointSource } from '../views/Remediation';

const Remediation = lazy(() => import('../views/Remediation'));
const source = (sourceCheck as { remediation: CheckpointSource }).remediation;

export default function App() {
  const [theme, setTheme] = useState<'dark' | 'light'>(() => readPreference('campus-theme', 'dark', (v): v is 'dark' | 'light' => v === 'dark' || v === 'light'));
  useEffect(() => { document.documentElement.dataset.theme = theme; writePreference('campus-theme', theme); }, [theme]);
  const toggleTheme = () => setTheme(previous => previous === 'dark' ? 'light' : 'dark');

  return <Suspense fallback={<main className="fatal"><h1>Campus Atlas</h1><p>Loading the campus network…</p></main>}>
    <Remediation theme={theme} source={source} toggleTheme={toggleTheme}/>
  </Suspense>;
}
