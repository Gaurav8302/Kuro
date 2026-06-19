import { useRef, useEffect, useCallback } from 'react';

type FrameCallback = (time: number, delta: number) => void;

export function useAnimationEngine(callback: FrameCallback, active = true) {
  const cbRef = useRef(callback);
  cbRef.current = callback;

  const rafRef = useRef(0);
  const lastTimeRef = useRef(0);

  const loop = useCallback((time: number) => {
    const delta = lastTimeRef.current ? Math.min(time - lastTimeRef.current, 33) : 16;
    lastTimeRef.current = time;
    cbRef.current(time, delta);
    rafRef.current = requestAnimationFrame(loop);
  }, []);

  useEffect(() => {
    if (!active) return;
    rafRef.current = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(rafRef.current);
  }, [active, loop]);
}
