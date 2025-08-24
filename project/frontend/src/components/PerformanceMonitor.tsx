import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Activity, Zap, AlertTriangle } from 'lucide-react';
import { useOptimizedAnimations } from '@/hooks/use-performance';

interface PerformanceMetrics {
  fps: number;
  memoryUsage: number;
  loadTime: number;
  isOptimal: boolean;
}

export const PerformanceMonitor = ({ showInDev = true }: { showInDev?: boolean }) => {
  const [metrics, setMetrics] = useState<PerformanceMetrics>({
    fps: 60,
    memoryUsage: 0,
    loadTime: 0,
    isOptimal: true
  });
  const [showMonitor, setShowMonitor] = useState(false);
  const { shouldReduceAnimations } = useOptimizedAnimations();
  const isDev = import.meta.env.DEV;

  useEffect(() => {
    if (!showInDev || !isDev) return;

    let frameCount = 0;
    let lastTime = performance.now();
    let animationId: number;

    const measureFPS = () => {
      frameCount++;
      const currentTime = performance.now();
      
      if (currentTime >= lastTime + 1000) {
        const fps = Math.round((frameCount * 1000) / (currentTime - lastTime));
        frameCount = 0;
        lastTime = currentTime;
        
        // Get memory usage if available
        const memory = (performance as any).memory;
        const memoryUsage = memory ? Math.round(memory.usedJSHeapSize / 1048576) : 0;
        
        // Get load time
        const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
        const loadTime = navigation ? Math.round(navigation.loadEventEnd - navigation.fetchStart) : 0;
        
        const isOptimal = fps >= 50 && memoryUsage < 100;
        
        setMetrics({ fps, memoryUsage, loadTime, isOptimal });
      }
      
      animationId = requestAnimationFrame(measureFPS);
    };

    measureFPS();

    // Show monitor on triple-click
    const handleTripleClick = () => {
      setShowMonitor(prev => !prev);
    };

    let clickCount = 0;
    const handleClick = () => {
      clickCount++;
      setTimeout(() => { clickCount = 0; }, 500);
      if (clickCount === 3) {
        handleTripleClick();
      }
    };

    document.addEventListener('click', handleClick);

    return () => {
      cancelAnimationFrame(animationId);
      document.removeEventListener('click', handleClick);
    };
  }, [showInDev, isDev]);

  if (!isDev || !showInDev) return null;

  return (
    <AnimatePresence>
      {showMonitor && (
        <motion.div
          initial={{ opacity: 0, scale: 0.8, x: 20 }}
          animate={{ opacity: 1, scale: 1, x: 0 }}
          exit={{ opacity: 0, scale: 0.8, x: 20 }}
          className="fixed top-4 left-4 z-[9999] glass-panel border-holo-cyan-400/30 rounded-lg p-3 text-xs font-orbitron"
        >
          <div className="flex items-center gap-2 mb-2">
            <Activity className="w-4 h-4 text-holo-cyan-400" />
            <span className="text-holo-cyan-300 font-semibold">PERFORMANCE</span>
            <button 
              onClick={() => setShowMonitor(false)}
              className="ml-auto text-holo-cyan-400/60 hover:text-holo-cyan-400"
            >
              ×
            </button>
          </div>
          
          <div className="space-y-1 text-holo-cyan-100">
            <div className="flex justify-between">
              <span>FPS:</span>
              <span className={metrics.fps >= 50 ? 'text-holo-green-400' : 'text-holo-magenta-400'}>
                {metrics.fps}
              </span>
            </div>
            <div className="flex justify-between">
              <span>Memory:</span>
              <span className={metrics.memoryUsage < 100 ? 'text-holo-green-400' : 'text-holo-magenta-400'}>
                {metrics.memoryUsage}MB
              </span>
            </div>
            <div className="flex justify-between">
              <span>Load:</span>
              <span className={metrics.loadTime < 2000 ? 'text-holo-green-400' : 'text-holo-magenta-400'}>
                {metrics.loadTime}ms
              </span>
            </div>
            <div className="flex justify-between">
              <span>Mode:</span>
              <span className={shouldReduceAnimations ? 'text-holo-blue-400' : 'text-holo-cyan-400'}>
                {shouldReduceAnimations ? 'LITE' : 'FULL'}
              </span>
            </div>
          </div>
          
          {!metrics.isOptimal && (
            <div className="mt-2 pt-2 border-t border-holo-cyan-400/20">
              <div className="flex items-center gap-1 text-holo-magenta-400">
                <AlertTriangle className="w-3 h-3" />
                <span>Performance degraded</span>
              </div>
            </div>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default PerformanceMonitor;