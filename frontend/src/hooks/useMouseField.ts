import { useRef, useCallback, useEffect } from 'react';

export interface MouseField {
  x: number;
  y: number;
  smoothedX: number;
  smoothedY: number;
  velX: number;
  velY: number;
  speed: number;
  active: boolean;
}

interface UseMouseFieldOptions {
  lerpFactor?: number;
  velocitySmoothing?: number;
}

export function useMouseField(options: UseMouseFieldOptions = {}) {
  const { lerpFactor = 0.08, velocitySmoothing = 0.12 } = options;

  const fieldRef = useRef<MouseField>({
    x: -9999,
    y: -9999,
    smoothedX: -9999,
    smoothedY: -9999,
    velX: 0,
    velY: 0,
    speed: 0,
    active: false,
  });

  const prevRef = useRef({ x: -9999, y: -9999 });

  const update = useCallback(() => {
    const f = fieldRef.current;

    if (f.active) {
      f.smoothedX += (f.x - f.smoothedX) * lerpFactor;
      f.smoothedY += (f.y - f.smoothedY) * lerpFactor;
    } else {
      f.smoothedX += (-9999 - f.smoothedX) * 0.01;
      f.smoothedY += (-9999 - f.smoothedY) * 0.01;
    }

    const rawVelX = f.smoothedX - prevRef.current.x;
    const rawVelY = f.smoothedY - prevRef.current.y;
    f.velX += (rawVelX - f.velX) * velocitySmoothing;
    f.velY += (rawVelY - f.velY) * velocitySmoothing;
    f.speed += (Math.sqrt(f.velX * f.velX + f.velY * f.velY) - f.speed) * velocitySmoothing;

    prevRef.current.x = f.smoothedX;
    prevRef.current.y = f.smoothedY;
  }, [lerpFactor, velocitySmoothing]);

  useEffect(() => {
    const onMouse = (e: MouseEvent) => {
      fieldRef.current.x = e.clientX;
      fieldRef.current.y = e.clientY;
      fieldRef.current.active = true;
    };
    const onLeave = () => {
      fieldRef.current.active = false;
    };
    window.addEventListener('mousemove', onMouse);
    window.addEventListener('mouseleave', onLeave);
    return () => {
      window.removeEventListener('mousemove', onMouse);
      window.removeEventListener('mouseleave', onLeave);
    };
  }, []);

  return { fieldRef, update };
}
