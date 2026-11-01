import { useEffect, useState } from 'react';
import type { NetworkSnapshot } from '../models/network';
import { assetUrl } from '../lib/network';
import styles from '../app/App.module.css';

export default function EvidenceAsset({ path, snapshot }: { path: string; snapshot: NetworkSnapshot }) {
  const [state, setState] = useState<{ path: string; text: string; error?: boolean } | null>(null);
  const asset = snapshot.evidence.find(e => e.path === path);
  useEffect(() => {
    const abort = new AbortController();
    if (asset && asset.mediaType !== 'image/png') {
      void fetch(assetUrl(path), { signal: abort.signal }).then(response => {
        if (!response.ok || response.headers.get('content-type')?.includes('text/html')) throw new Error('Evidence file unavailable');
        return response.text();
      }).then(text => setState({ path, text })).catch(error => { if (error.name !== 'AbortError') setState({ path, text: 'Evidence could not be loaded. Run npm run sync-data and rebuild the viewer.', error: true }); });
    }
    return () => abort.abort();
  }, [asset, path]);
  if (!asset) return <p role="alert">This evidence reference is not included in the verified manifest.</p>;
  return <div className={styles.asset}>
    <div className={styles.assetHeading}><strong>{path.split('/').at(-1)}</strong><a href={assetUrl(path)} download>Download ↗</a></div>
    {asset.mediaType === 'image/png' ? <>{state?.path === path && state.error ? <p role="alert">Evidence image unavailable.</p> : <img src={assetUrl(path)} loading="lazy" alt={`Recorded Packet Tracer evidence: ${path.split('/').at(-1)}`} onError={() => setState({ path, text: '', error: true })}/>}</> : <pre tabIndex={0} aria-label="Recorded evidence text">{state?.path === path ? state.text : 'Loading recorded evidence…'}</pre>}
  </div>;
}
