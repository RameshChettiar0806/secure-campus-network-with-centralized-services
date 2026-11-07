export function readPreference<T>(key: string, fallback: T, validate: (v: unknown) => v is T): T {
  try {
    const raw: unknown = JSON.parse(localStorage.getItem(key) ?? 'null');
    return validate(raw) ? raw : fallback;
  } catch { return fallback; }
}

export function writePreference(key: string, value: unknown) {
  try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* Preferences are optional. */ }
}
