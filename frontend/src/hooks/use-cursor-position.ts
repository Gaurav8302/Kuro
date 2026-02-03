import { useState, useEffect, useRef } from 'react';

interface CursorPosition {
  x: number;
  y: number;
  isActive: boolean;
}

/**
 * Hook to track cursor position with performance optimizations
 * Uses requestAnimationFrame for smooth updates
 */
export function useCursorPosition(): CursorPosition {
  const [position, setPosition] = useState<CursorPosition>({
    x: 0,
    y: 0,
    isActive: false,
  });
  
  const rafRef = useRef<number>();
  const positionRef = useRef({ x: 0, y: 0 });

  useEffect(() => {
    let isActive = false;
    let timeout: NodeJS.Timeout;

    const updatePosition = () => {
      setPosition({
        x: positionRef.current.x,
        y: positionRef.current.y,
        isActive,
      });
    };

    const handleMouseMove = (e: MouseEvent) => {
      positionRef.current = { x: e.clientX, y: e.clientY };
      isActive = true;
      
      // Clear existing timeout
      clearTimeout(timeout);
      
      // Set inactive after 3 seconds of no movement
      timeout = setTimeout(() => {
        isActive = false;
        updatePosition();
      }, 3000);

      // Throttle updates using RAF
      if (!rafRef.current) {
        rafRef.current = requestAnimationFrame(() => {
          updatePosition();
          rafRef.current = undefined;
        });
      }
    };

    const handleMouseLeave = () => {
      isActive = false;
      updatePosition();
    };

    window.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseleave', handleMouseLeave);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseleave', handleMouseLeave);
      clearTimeout(timeout);
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current);
      }
    };
  }, []);

  return position;
}

/**
 * Hook to check if cursor is near an element
 */
export function useCursorProximity(
  ref: React.RefObject<HTMLElement>,
  threshold: number = 100
): { isNear: boolean; distance: number } {
  const cursor = useCursorPosition();
  const [proximity, setProximity] = useState({ isNear: false, distance: Infinity });

  useEffect(() => {
    if (!ref.current || !cursor.isActive) {
      setProximity({ isNear: false, distance: Infinity });
      return;
    }

    const rect = ref.current.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;

    const dx = cursor.x - centerX;
    const dy = cursor.y - centerY;
    const distance = Math.sqrt(dx * dx + dy * dy);

    setProximity({
      isNear: distance < threshold,
      distance,
    });
  }, [cursor, ref, threshold]);

  return proximity;
}
