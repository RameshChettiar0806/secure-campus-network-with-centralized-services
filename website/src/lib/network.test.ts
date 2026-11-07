import { describe, expect, it, vi } from 'vitest';
import { readPreference, writePreference } from './network';

describe('optional browser storage', () => {
  it('survives storage being blocked', () => { vi.stubGlobal('localStorage', { getItem() { throw new Error('blocked'); }, setItem() { throw new Error('blocked'); } }); expect(readPreference('theme', 'dark', (v): v is string => typeof v === 'string')).toBe('dark'); expect(() => writePreference('theme', 'light')).not.toThrow(); vi.unstubAllGlobals(); });
  it('ignores malformed stored JSON', () => { vi.stubGlobal('localStorage', { getItem: () => '{broken' }); expect(readPreference('theme', 'dark', (v): v is string => typeof v === 'string')).toBe('dark'); vi.unstubAllGlobals(); });
});
