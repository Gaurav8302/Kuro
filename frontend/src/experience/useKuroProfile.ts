import { useCallback, useEffect, useRef, useState } from 'react';
import {
  checkUserHasName,
  getIntroShown,
  getUserName,
  setIntroShown,
  setUserName,
} from '@/lib/api';

/**
 * What Kuro already knows about the signed-in person.
 *
 * Backed entirely by the existing profile endpoints:
 *   GET  /user/{id}/has-name
 *   GET  /user/{id}/name
 *   GET  /user/{id}/intro-shown
 *   POST /user/{id}/set-name
 *   POST /user/{id}/intro-shown
 *
 * `introShown` is the first-time / returning discriminator: Kuro marks it at
 * the end of Memory Genesis, so a person who has been through the awakening
 * once never sees it again.
 */
export interface KuroProfile {
  status: 'idle' | 'loading' | 'ready' | 'error';
  userId: string | null;
  name: string | null;
  hasName: boolean;
  introShown: boolean;
  /** Persist a name via the existing endpoint and update local state. */
  saveName: (name: string) => Promise<void>;
  /** Mark onboarding complete via the existing endpoint and update local state. */
  completeAwakening: () => Promise<void>;
  refresh: () => Promise<void>;
}

export function useKuroProfile(userId: string | null | undefined): KuroProfile {
  const [status, setStatus] = useState<KuroProfile['status']>('idle');
  const [name, setName] = useState<string | null>(null);
  const [hasName, setHasName] = useState(false);
  const [introShown, setIntroShownState] = useState(false);
  const loadedFor = useRef<string | null>(null);

  const load = useCallback(async (id: string) => {
    setStatus('loading');
    try {
      const [hasNameRes, introRes] = await Promise.all([
        checkUserHasName(id),
        getIntroShown(id),
      ]);
      setHasName(hasNameRes.has_name);
      setIntroShownState(introRes.intro_shown);
      if (hasNameRes.has_name) {
        try {
          const n = await getUserName(id);
          setName(n.name);
        } catch {
          setName(null);
        }
      } else {
        setName(null);
      }
      setStatus('ready');
    } catch (e) {
      console.error('[kuro] profile load failed', e);
      // Fall back to a local flag so a backend hiccup doesn't trap a returning
      // user in onboarding, or force a new one through it twice.
      const local = localStorage.getItem(`kuro_intro_shown_${id}`) === '1';
      setIntroShownState(local);
      setStatus('error');
    }
  }, []);

  useEffect(() => {
    if (!userId) {
      loadedFor.current = null;
      setStatus('idle');
      setName(null);
      setHasName(false);
      setIntroShownState(false);
      return;
    }
    if (loadedFor.current === userId) return;
    loadedFor.current = userId;
    load(userId);
  }, [userId, load]);

  const saveName = useCallback(
    async (n: string) => {
      const trimmed = n.trim();
      if (!userId || !trimmed) return;
      setName(trimmed);
      setHasName(true);
      try {
        await setUserName(userId, trimmed);
      } catch (e) {
        console.error('[kuro] set-name failed', e);
      }
    },
    [userId]
  );

  const completeAwakening = useCallback(async () => {
    if (!userId) return;
    setIntroShownState(true);
    try {
      localStorage.setItem(`kuro_intro_shown_${userId}`, '1');
    } catch {
      /* ignore */
    }
    try {
      await setIntroShown(userId);
    } catch (e) {
      console.error('[kuro] intro-shown failed', e);
    }
  }, [userId]);

  const refresh = useCallback(async () => {
    if (userId) await load(userId);
  }, [userId, load]);

  return {
    status,
    userId: userId ?? null,
    name,
    hasName,
    introShown,
    saveName,
    completeAwakening,
    refresh,
  };
}
