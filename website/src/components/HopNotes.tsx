import type { HopNote } from '../lib/ping';
import pane from './PingLab.module.css';

export default function HopNotes({ notes }: { notes: HopNote[] }) {
  return <ul className={pane.hopNotes} aria-label="Packet explanation">
    {notes.map(({ concept, detail }) =>
      <li key={concept}><strong>{concept}</strong> — {detail}</li>
    )}
  </ul>;
}
