import { lazy, Suspense } from 'react';
import { Loader2 } from 'lucide-react';
import { motion } from 'framer-motion';

// Lazy load heavy components
export const LazyHolographicBackground = lazy(() => import('@/components/HolographicBackground'));
export const LazyHolographicParticles = lazy(() => import('@/components/HolographicParticles'));

// Loading fallback component
const ComponentLoader = ({ name }: { name: string }) => (
  <div className="flex items-center justify-center p-4">
    <motion.div
      animate={{ rotate: 360 }}
      transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
      className="mr-2"
    >
      <Loader2 className="w-4 h-4 text-holo-cyan-400" />
    </motion.div>
    <span className="text-xs text-holo-cyan-400/60 font-orbitron">Loading {name}...</span>
  </div>
);

// Wrapper components with suspense
export const SuspendedHolographicBackground = (props: any) => (
  <Suspense fallback={<div className="fixed inset-0 bg-gradient-to-br from-background via-holo-cyan-900/10 to-holo-purple-900/10" />}>
    <LazyHolographicBackground {...props} />
  </Suspense>
);

export const SuspendedHolographicParticles = (props: any) => (
  <Suspense fallback={<ComponentLoader name="particles" />}>
    <LazyHolographicParticles {...props} />
  </Suspense>
);

// Intersection Observer hook for lazy loading
export const useIntersectionObserver = (
  ref: React.RefObject<Element>,
  options: IntersectionObserverInit = {}
) => {
  const [isIntersecting, setIsIntersecting] = useState(false);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;

    const observer = new IntersectionObserver(
      ([entry]) => setIsIntersecting(entry.isIntersecting),
      { threshold: 0.1, ...options }
    );

    observer.observe(element);
    return () => observer.disconnect();
  }, [ref, options]);

  return isIntersecting;
};