import { useState, useEffect, useCallback } from 'react';

interface AnimationConfig {
  /** Whether to reduce/disable animations */
  shouldReduceMotion: boolean;
  /** Multiplier for animation durations (1 = normal, 0 = instant) */
  durationMultiplier: number;
  /** Whether to enable complex effects like particles */
  enableComplexEffects: boolean;
  /** Whether to enable blur effects */
  enableBlur: boolean;
  /** Whether device is low-end */
  isLowEndDevice: boolean;
}

/**
 * Hook to get animation settings based on user preferences and device capabilities
 * Respects prefers-reduced-motion and device performance
 */
export function useAnimationConfig(): AnimationConfig {
  const [config, setConfig] = useState<AnimationConfig>({
    shouldReduceMotion: false,
    durationMultiplier: 1,
    enableComplexEffects: true,
    enableBlur: true,
    isLowEndDevice: false,
  });

  useEffect(() => {
    const checkCapabilities = () => {
      // Check reduced motion preference
      const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      
      // Estimate device capabilities
      const nav = window.navigator as any;
      const deviceMemory = nav.deviceMemory || 8;
      const hardwareConcurrency = nav.hardwareConcurrency || 4;
      
      // Check connection speed
      const connection = (nav.connection || nav.mozConnection || nav.webkitConnection) as any;
      const isSlowConnection = connection?.effectiveType
        ? ['slow-2g', '2g', '3g'].includes(connection.effectiveType)
        : false;
      
      // Determine if low-end device
      const isLowEnd = deviceMemory < 4 || hardwareConcurrency < 4 || isSlowConnection;
      
      setConfig({
        shouldReduceMotion: prefersReducedMotion,
        durationMultiplier: prefersReducedMotion ? 0 : isLowEnd ? 0.5 : 1,
        enableComplexEffects: !prefersReducedMotion && !isLowEnd,
        enableBlur: !isLowEnd,
        isLowEndDevice: isLowEnd,
      });
    };

    checkCapabilities();

    // Listen for changes in motion preference
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    const handleChange = () => checkCapabilities();
    
    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);

  return config;
}

/**
 * Hook to get scaled animation duration
 */
export function useScaledDuration(baseDuration: number): number {
  const { durationMultiplier } = useAnimationConfig();
  return baseDuration * durationMultiplier;
}

/**
 * Returns animation class based on config
 */
export function useAnimationClass(
  baseClass: string,
  reducedClass: string = ''
): string {
  const { shouldReduceMotion } = useAnimationConfig();
  return shouldReduceMotion ? reducedClass : baseClass;
}
