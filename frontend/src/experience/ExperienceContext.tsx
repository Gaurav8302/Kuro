import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { useUser } from '@clerk/clerk-react';
import { useReducedMotion } from 'framer-motion';
import { useIsMobile } from '@/hooks/use-mobile';
import { useKuroProfile, KuroProfile } from './useKuroProfile';
import type { CoreMode, MemoryNode, Stage } from './types';

export interface PointerState {
  /** -1..1 normalized to viewport, eased by the Core */
  x: number;
  y: number;
  /** ms timestamp of last movement; the Core calms down after inactivity */
  lastMove: number;
  active: boolean;
}

interface ExperienceValue {
  stage: Stage;
  setStage: (s: Stage) => void;

  coreMode: CoreMode;
  setCoreMode: (m: CoreMode) => void;
  /** One-shot: a reply arrived. Core settles back to idle by itself. */
  pulse: () => void;

  memoryNodes: MemoryNode[];
  setMemoryNodes: React.Dispatch<React.SetStateAction<MemoryNode[]>>;

  /** Chat navigation (conversations / memory / projects / settings) */
  navOpen: boolean;
  setNavOpen: (open: boolean) => void;

  pointer: React.MutableRefObject<PointerState>;
  reducedMotion: boolean;
  isMobile: boolean;

  profile: KuroProfile;
}

const ExperienceContext = createContext<ExperienceValue | null>(null);

export const ExperienceProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [stage, setStageState] = useState<Stage>('origin');
  const [coreMode, setCoreModeState] = useState<CoreMode>('idle');
  const [memoryNodes, setMemoryNodes] = useState<MemoryNode[]>([]);
  const [navOpen, setNavOpen] = useState(false);
  const reducedMotion = useReducedMotion() ?? false;
  const isMobile = useIsMobile();
  const { user, isLoaded } = useUser();
  const profile = useKuroProfile(isLoaded ? user?.id : undefined);

  const pointer = useRef<PointerState>({ x: 0, y: 0, lastMove: 0, active: false });
  const pulseTimer = useRef<number | null>(null);

  // Pointer presence — the environment responds to the person, then calms.
  useEffect(() => {
    if (reducedMotion) return;
    const onMove = (e: PointerEvent) => {
      const w = window.innerWidth || 1;
      const h = window.innerHeight || 1;
      pointer.current.x = (e.clientX / w) * 2 - 1;
      pointer.current.y = (e.clientY / h) * 2 - 1;
      pointer.current.lastMove = performance.now();
      pointer.current.active = true;
    };
    const onLeave = () => {
      pointer.current.active = false;
    };
    window.addEventListener('pointermove', onMove, { passive: true });
    window.addEventListener('pointerleave', onLeave);
    window.addEventListener('blur', onLeave);
    return () => {
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerleave', onLeave);
      window.removeEventListener('blur', onLeave);
    };
  }, [reducedMotion]);

  const setStage = useCallback((s: Stage) => {
    setStageState((prev) => (prev === s ? prev : s));
  }, []);

  const setCoreMode = useCallback((m: CoreMode) => {
    if (pulseTimer.current) {
      window.clearTimeout(pulseTimer.current);
      pulseTimer.current = null;
    }
    setCoreModeState((prev) => (prev === m ? prev : m));
  }, []);

  const pulse = useCallback(() => {
    if (pulseTimer.current) window.clearTimeout(pulseTimer.current);
    setCoreModeState('responding');
    pulseTimer.current = window.setTimeout(() => {
      setCoreModeState('idle');
      pulseTimer.current = null;
    }, 1100);
  }, []);

  // Leaving chat closes navigation.
  useEffect(() => {
    if (stage !== 'chat' && navOpen) setNavOpen(false);
  }, [stage, navOpen]);

  const value = useMemo<ExperienceValue>(
    () => ({
      stage,
      setStage,
      coreMode,
      setCoreMode,
      pulse,
      memoryNodes,
      setMemoryNodes,
      navOpen,
      setNavOpen,
      pointer,
      reducedMotion,
      isMobile,
      profile,
    }),
    [stage, setStage, coreMode, setCoreMode, pulse, memoryNodes, navOpen, reducedMotion, isMobile, profile]
  );

  return <ExperienceContext.Provider value={value}>{children}</ExperienceContext.Provider>;
};

export function useExperience(): ExperienceValue {
  const ctx = useContext(ExperienceContext);
  if (!ctx) throw new Error('useExperience must be used within ExperienceProvider');
  return ctx;
}

/**
 * Declare which stage a screen represents. Called once by each stage
 * component; this is the only way the environment changes state.
 */
export function useStage(stage: Stage, mode: CoreMode = 'idle') {
  const { setStage, setCoreMode } = useExperience();
  useEffect(() => {
    setStage(stage);
    setCoreMode(mode);
  }, [stage, mode, setStage, setCoreMode]);
}
