// Performance optimization utilities for Kuro AI

// Debounce utility for expensive operations
export const debounce = <T extends (...args: any[]) => any>(
  func: T,
  wait: number
): ((...args: Parameters<T>) => void) => {
  let timeout: NodeJS.Timeout;
  return (...args: Parameters<T>) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
};

// Throttle utility for scroll/resize events
export const throttle = <T extends (...args: any[]) => any>(
  func: T,
  limit: number
): ((...args: Parameters<T>) => void) => {
  let inThrottle: boolean;
  return (...args: Parameters<T>) => {
    if (!inThrottle) {
      func(...args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
};

// Memory management utilities
export const cleanupUnusedResources = () => {
  // Force garbage collection if available (Chrome DevTools)
  if ('gc' in window && typeof (window as any).gc === 'function') {
    (window as any).gc();
  }
  
  // Clear unused image cache
  const images = document.querySelectorAll('img[data-cleanup="true"]');
  images.forEach(img => {
    if (img.getAttribute('data-last-used')) {
      const lastUsed = parseInt(img.getAttribute('data-last-used') || '0');
      if (Date.now() - lastUsed > 300000) { // 5 minutes
        img.remove();
      }
    }
  });
};

// Optimize images for different screen sizes
export const getResponsiveImageSrc = (
  baseSrc: string, 
  screenWidth: number,
  devicePixelRatio: number = 1
) => {
  const targetWidth = Math.ceil(screenWidth * devicePixelRatio);
  
  // For production, integrate with image optimization service
  // For now, return original with size hints
  if (baseSrc.includes('placeholder.svg') || baseSrc.includes('kuroai.png')) {
    return baseSrc; // Keep original for logos/icons
  }
  
  return baseSrc;
};

// Preload critical resources
export const preloadCriticalResources = () => {
  const criticalResources = [
    { href: '/kuroai.png', as: 'image' },
    { href: 'https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;600;700;800;900&display=swap', as: 'style' }
  ];

  criticalResources.forEach(resource => {
    const link = document.createElement('link');
    link.rel = 'preload';
    link.href = resource.href;
    link.as = resource.as;
    if (resource.as === 'style') {
      link.onload = () => {
        link.rel = 'stylesheet';
      };
    }
    document.head.appendChild(link);
  });
};

// Monitor and report performance metrics
export const reportPerformanceMetrics = () => {
  if (typeof window === 'undefined') return;

  // Core Web Vitals
  const observer = new PerformanceObserver((list) => {
    list.getEntries().forEach((entry) => {
      if (entry.entryType === 'largest-contentful-paint') {
        console.log('LCP:', entry.startTime);
      }
      if (entry.entryType === 'first-input') {
        console.log('FID:', (entry as any).processingStart - entry.startTime);
      }
      if (entry.entryType === 'layout-shift') {
        console.log('CLS:', (entry as any).value);
      }
    });
  });

  try {
    observer.observe({ entryTypes: ['largest-contentful-paint', 'first-input', 'layout-shift'] });
  } catch (e) {
    // Fallback for browsers that don't support all metrics
    console.log('Performance monitoring not fully supported');
  }

  // Memory usage monitoring
  if ('memory' in performance) {
    const memory = (performance as any).memory;
    console.log('Memory usage:', {
      used: Math.round(memory.usedJSHeapSize / 1048576) + 'MB',
      total: Math.round(memory.totalJSHeapSize / 1048576) + 'MB',
      limit: Math.round(memory.jsHeapSizeLimit / 1048576) + 'MB'
    });
  }
};

// Optimize scroll performance
export const optimizeScrollPerformance = () => {
  // Use passive listeners for better scroll performance
  const passiveSupported = (() => {
    let passive = false;
    try {
      const options = {
        get passive() {
          passive = true;
          return false;
        }
      };
      window.addEventListener('test', () => {}, options);
      window.removeEventListener('test', () => {}, options);
    } catch (err) {
      passive = false;
    }
    return passive;
  })();

  return passiveSupported ? { passive: true } : false;
};

// Bundle size analyzer helper
export const analyzeBundleSize = () => {
  if (import.meta.env.DEV) {
    console.log('Bundle analysis available in production build with npm run build:analyze');
  }
};

// Critical CSS extraction
export const extractCriticalCSS = () => {
  const criticalSelectors = [
    '.bg-background',
    '.text-foreground',
    '.font-orbitron',
    '.font-space',
    '.glass-panel',
    '.holo-text',
    '.text-holo-glow'
  ];

  const criticalCSS = criticalSelectors.map(selector => {
    const elements = document.querySelectorAll(selector);
    if (elements.length > 0) {
      return `${selector} { /* critical styles */ }`;
    }
    return '';
  }).filter(Boolean).join('\n');

  return criticalCSS;
};