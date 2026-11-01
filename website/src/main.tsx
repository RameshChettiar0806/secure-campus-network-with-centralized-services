import { StrictMode, Component, lazy, Suspense, type ReactNode } from 'react';
import { createRoot } from 'react-dom/client';
const App = lazy(() => import('./app/App'));
import './styles/global.css';

class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    return this.state.failed ? <main className="fatal"><h1>Network unavailable</h1><p>The network data could not be loaded. Please reload the demonstration.</p><button onClick={() => location.reload()}>Reload viewer</button></main> : this.props.children;
  }
}

createRoot(document.getElementById('root')!).render(<StrictMode><ErrorBoundary><Suspense fallback={<main className="fatal"><h1>Campus Atlas</h1><p>Loading the 50-PC campus network…</p></main>}><App /></Suspense></ErrorBoundary></StrictMode>);
