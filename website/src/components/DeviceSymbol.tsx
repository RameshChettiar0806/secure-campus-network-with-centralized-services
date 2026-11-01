export default function DeviceSymbol({ model, size = 24 }: { model: string; size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 32 32" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    {model === '1941' ? <><ellipse cx="16" cy="16" rx="13" ry="11"/><path d="M8 16h16M11 12l-4 4 4 4m10-8 4 4-4 4M16 7v5m0 8v5"/></> : model.includes('2960') ? <><rect x="3" y="8" width="26" height="16" rx="3"/><path d="M7 13h3v5H7zm6 0h3v5h-3zm6 0h3v5h-3zM25 14v3M7 21h16"/></> : model === 'Server-PT' ? <><rect x="7" y="3" width="18" height="26" rx="3"/><path d="M7 12h18M7 21h18M11 8h1m-1 9h1m-1 8h1M17 8h4m-4 9h4m-4 8h4"/></> : <><rect x="3" y="5" width="26" height="18" rx="2"/><path d="M16 23v5m-7 0h14M7 19h18"/></>}
  </svg>;
}
