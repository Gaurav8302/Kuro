import { useEffect, useState, useCallback } from 'react';

interface PerformanceMetrics {
  fps: number;
  loadTime: number;
  memoryUsage?: number;
}

export const usePerformance = () => {
  const [metrics, setMetrics] = useState<PerformanceMetrics>({
    fps: 0,
    loadTime: 0
  });

  const [isLowPerformance, setIsLowPerformance] = useState(false);

  // FPS monitoring
  useEffect(() => {
    let frameCount = 0;
    let lastTime = performance.now();
    let animationId: number;

    const measureFPS = () => {
      frameCount++;
      const currentTime = performance.now();
      
      if (currentTime >= lastTime + 1000) {
        const fps = Math.round((frameCount * 1000) / (currentTime - lastTime));
        setMetrics(prev => ({ ...prev, fps }));
        
        // Detect low performance
        setIsLowPerformance(fps < 30);
        
        frameCount = 0;
        lastTime = currentTime;
      }
      
      animationId = requestAnimationFrame(measureFPS);
    };

    animationId = requestAnimationFrame(measureFPS);

    return () => {
      if (animationId) {
        cancelAnimationFrame(animationId);
      }
    };
  }, []);

  // Load time measurement
  useEffect(() => {
    const loadTime = performance.now();
    setMetrics(prev => ({ ...prev, loadTime }));

    // Memory usage (if available)
    if ('memory' in performance) {
      const memory = (performance as any).memory;
      setMetrics(prev => ({ 
        ...prev, 
        memoryUsage: memory.usedJSHeapSize / 1024 / 1024 
      }));
    }
  }, []);

  const getPerformanceLevel = useCallback(() => {
    if (metrics.fps >= 50) return 'high';
    if (metrics.fps >= 30) return 'medium';
    return 'low';
  }, [metrics.fps]);

  return {
    metrics,
    isLowPerformance,
    performanceLevel: getPerformanceLevel()
  };
};

export default usePerformance;