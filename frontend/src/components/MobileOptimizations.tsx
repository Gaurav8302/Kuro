import { useEffect } from 'react';
import { useIsMobile } from '@/hooks/use-mobile';

// Mobile-specific optimizations component
export const MobileOptimizations = () => {
  const isMobile = useIsMobile();

  useEffect(() => {
    if (!isMobile) return;

    // Optimize viewport for mobile
    const viewport = document.querySelector('meta[name="viewport"]');
    if (viewport) {
      viewport.setAttribute('content', 
        'width=device-width, initial-scale=1.0, viewport-fit=cover, interactive-widget=resizes-content, user-scalable=no'
      );
    }

    // Prevent zoom on input focus
    const inputs = document.querySelectorAll('input, textarea, select');
    inputs.forEach(input => {
      input.addEventListener('focus', () => {
        if (viewport) {
          viewport.setAttribute('content', 
            'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no'
          );
        }
      });
      
      input.addEventListener('blur', () => {
        if (viewport) {
          viewport.setAttribute('content', 
            'width=device-width, initial-scale=1.0, viewport-fit=cover, interactive-widget=resizes-content'
          );
        }
      });
    });

    // Optimize touch events
    document.body.style.touchAction = 'manipulation';
    
    // Reduce motion on mobile by default
    document.documentElement.style.setProperty('--animation-duration', '0.2s');
    
    // Optimize scrolling
    document.body.style.overscrollBehavior = 'none';
    
    // Prevent pull-to-refresh
    document.body.style.overscrollBehaviorY = 'contain';

    return () => {
      // Cleanup
      document.body.style.touchAction = '';
      document.body.style.overscrollBehavior = '';
      document.body.style.overscrollBehaviorY = '';
    };
  }, [isMobile]);

  return null; // This component only applies side effects
};

// iOS Safari specific optimizations
export const IOSOptimizations = () => {
  useEffect(() => {
    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
    if (!isIOS) return;

    // Fix iOS Safari viewport issues
    const setViewportHeight = () => {
      const vh = window.innerHeight * 0.01;
      document.documentElement.style.setProperty('--vh', `${vh}px`);
    };

    setViewportHeight();
    window.addEventListener('resize', setViewportHeight);
    window.addEventListener('orientationchange', setViewportHeight);

    // Prevent iOS Safari bounce
    document.body.style.position = 'fixed';
    document.body.style.width = '100%';
    document.body.style.height = '100%';
    document.body.style.overflow = 'hidden';

    // Create scrollable container
    const scrollContainer = document.createElement('div');
    scrollContainer.style.position = 'absolute';
    scrollContainer.style.top = '0';
    scrollContainer.style.left = '0';
    scrollContainer.style.width = '100%';
    scrollContainer.style.height = '100%';
    scrollContainer.style.overflow = 'auto';
    scrollContainer.style.webkitOverflowScrolling = 'touch';

    // Move all body children to scroll container
    while (document.body.firstChild) {
      scrollContainer.appendChild(document.body.firstChild);
    }
    document.body.appendChild(scrollContainer);

    return () => {
      window.removeEventListener('resize', setViewportHeight);
      window.removeEventListener('orientationchange', setViewportHeight);
      
      // Restore original body styles
      document.body.style.position = '';
      document.body.style.width = '';
      document.body.style.height = '';
      document.body.style.overflow = '';
      
      // Move children back to body
      while (scrollContainer.firstChild) {
        document.body.appendChild(scrollContainer.firstChild);
      }
      scrollContainer.remove();
    };
  }, []);

  return null;
};

export default MobileOptimizations;