export function getDebugDnd(): boolean {
  try {
    if (typeof window !== 'undefined') {
      const ls = window.localStorage.getItem('debug.dnd');
      if (ls === '1') return true;
      const qs = new URLSearchParams(window.location.search);
      if (qs.get('debugDnd') === '1') return true;
    }
    // Vite env var fallback
    // @ts-ignore
    const envFlag = import.meta?.env?.VITE_DEBUG_DND;
    return envFlag === '1' || envFlag === 'true';
  } catch {
    return false;
  }
}

export function setDebugDnd(on: boolean) {
  try {
    if (typeof window !== 'undefined') {
      window.localStorage.setItem('debug.dnd', on ? '1' : '0');
    }
  } catch {}
}
