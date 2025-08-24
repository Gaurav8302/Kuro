import { lazy } from 'react';

// Utility for creating lazy-loaded components with better error handling
export const createLazyComponent = <T extends React.ComponentType<any>>(
  importFn: () => Promise<{ default: T }>,
  fallback?: React.ComponentType
) => {
  const LazyComponent = lazy(importFn);
  
  // Add display name for debugging
  LazyComponent.displayName = `Lazy(${importFn.toString().slice(0, 50)}...)`;
  
  return LazyComponent;
};

// Preload function for critical components
export const preloadComponent = (importFn: () => Promise<any>) => {
  // Only preload on fast connections and capable devices
  if (typeof window !== 'undefined') {
    const connection = (navigator as any).connection;
    const isSlowConnection = connection && ['slow-2g', '2g', '3g'].includes(connection.effectiveType);
    const isLowMemory = (navigator as any).deviceMemory && (navigator as any).deviceMemory < 4;
    
    if (!isSlowConnection && !isLowMemory) {
      // Preload after a short delay to not block initial render
      setTimeout(() => {
        importFn().catch(() => {
          // Silently fail preloading
        });
      }, 1000);
    }
  }
};

// Resource hints for critical assets
export const addResourceHints = () => {
  if (typeof document === 'undefined') return;

  const hints = [
    { rel: 'preload', href: '/kuroai.png', as: 'image' },
    { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
    { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossOrigin: 'anonymous' },
  ];

  hints.forEach(hint => {
    const link = document.createElement('link');
    Object.assign(link, hint);
    document.head.appendChild(link);
  });
};

// Image optimization utility
export const getOptimizedImageSrc = (src: string, width?: number, quality = 75) => {
  // For production, you might want to use a service like Cloudinary or Next.js Image
  // For now, return the original src
  return src;
};

// Intersection Observer for lazy loading
export class LazyLoadManager {
  private observer: IntersectionObserver | null = null;
  private loadedElements = new Set<Element>();

  constructor() {
    if (typeof window !== 'undefined' && 'IntersectionObserver' in window) {
      this.observer = new IntersectionObserver(
        (entries) => {
          entries.forEach(entry => {
            if (entry.isIntersecting && !this.loadedElements.has(entry.target)) {
              this.loadElement(entry.target);
              this.loadedElements.add(entry.target);
              this.observer?.unobserve(entry.target);
            }
          });
        },
        { 
          threshold: 0.1,
          rootMargin: '50px'
        }
      );
    }
  }

  observe(element: Element) {
    if (this.observer && !this.loadedElements.has(element)) {
      this.observer.observe(element);
    }
  }

  private loadElement(element: Element) {
    // Trigger loading for lazy elements
    const lazyImages = element.querySelectorAll('[data-lazy-src]');
    lazyImages.forEach(img => {
      const lazySrc = img.getAttribute('data-lazy-src');
      if (lazySrc) {
        img.setAttribute('src', lazySrc);
        img.removeAttribute('data-lazy-src');
      }
    });

    // Trigger component loading
    const event = new CustomEvent('lazyload', { detail: { element } });
    element.dispatchEvent(event);
  }

  disconnect() {
    if (this.observer) {
      this.observer.disconnect();
      this.observer = null;
    }
    this.loadedElements.clear();
  }
}

// Global lazy load manager instance
export const lazyLoadManager = new LazyLoadManager();