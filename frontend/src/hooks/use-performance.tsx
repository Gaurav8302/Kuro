import { useState, useEffect } from 'react';

interface PerformanceMetrics {
  isLowEndDevice: boolean;
  prefersReducedMotion: boolean;
  connectionSpeed: 'slow' | 'fast' | 'unknown';
  deviceMemory: number;
  hardwareConcurrency: number;
}

export const usePerformance = (): PerformanceMetrics => {
  const [metrics, setMetrics] = useState<PerformanceMetrics>({
    isLowEndDevice: false,
    prefersReducedMotion: false,
    connectionSpeed: 'unknown',
    deviceMemory: 4,
    hardwareConcurrency: 4
  });

  useEffect(() => {
    const checkPerformance = () => {
      // Check for reduced motion preference
      const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      
      // Estimate device capabilities
      const navigator = window.navigator as any;
      const deviceMemory = navigator.deviceMemory || 4;
      const hardwareConcurrency = navigator.hardwareConcurrency || 4;
      
      // Connection speed estimation
      const connection = (navigator.connection || navigator.mozConnection || navigator.webkitConnection) as any;
      let connectionSpeed: 'slow' | 'fast' | 'unknown' = 'unknown';
      
      if (connection) {
        const effectiveType = connection.effectiveType;
        connectionSpeed = ['slow-2g', '2g', '3g'].includes(effectiveType) ? 'slow' : 'fast';
      }
      
      // Determine if device is low-end based on multiple factors
      const isLowEndDevice = 
        deviceMemory < 4 || 
        hardwareConcurrency < 4 || 
        connectionSpeed === 'slow' ||
        prefersReducedMotion;

      setMetrics({
        isLowEndDevice,
        prefersReducedMotion,
        connectionSpeed,
        deviceMemory,
        hardwareConcurrency
      });
    };

    checkPerformance();

    // Listen for changes in motion preference
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    const handleChange = () => checkPerformance();
    
    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);

  return metrics;
};

export const useOptimizedAnimations = () => {
  const { isLowEndDevice, prefersReducedMotion, connectionSpeed } = usePerformance();
  const shouldReduceAnimations = isLowEndDevice || prefersReducedMotion;
  const isSlowConnection = connectionSpeed === 'slow';

  return {
    shouldReduceAnimations,
    // Faster animation durations for smoother feel
    animationDuration: shouldReduceAnimations ? 0.1 : 0.25,
    // Reduced particle count for better performance
    particleCount: shouldReduceAnimations ? 5 : 20,
    enableComplexAnimations: !shouldReduceAnimations && !isSlowConnection,
    enableParticles: !shouldReduceAnimations && !isSlowConnection,
    // New: transition config for framer-motion
    springConfig: shouldReduceAnimations 
      ? { type: 'tween', duration: 0.1 } 
      : { type: 'spring', stiffness: 400, damping: 30 },
    // New: whether to use CSS transitions instead of JS animations
    preferCSSTransitions: shouldReduceAnimations
  };
};