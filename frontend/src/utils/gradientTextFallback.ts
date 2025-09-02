/**
 * Utility to handle gradient text fallback on mobile devices
 * Detects if webkit background-clip is working properly and applies fallback if needed
 */

export const checkAndApplyGradientFallback = () => {
  // Only run on mobile devices
  if (window.innerWidth <= 640) {
    const gradientElements = document.querySelectorAll('.hero-gradient-word');
    
    gradientElements.forEach((element) => {
      // Check if the element is visible and has the proper gradient
      const computedStyle = window.getComputedStyle(element);
      const hasBackgroundClip = computedStyle.getPropertyValue('-webkit-background-clip') === 'text';
      
      // If background-clip isn't working or element appears empty, apply fallback
      if (!hasBackgroundClip || element.textContent && element.scrollHeight === 0) {
        (element as HTMLElement).style.background = 'none';
        (element as HTMLElement).style.webkitBackgroundClip = 'unset';
        (element as HTMLElement).style.backgroundClip = 'unset';
        (element as HTMLElement).style.webkitTextFillColor = '#00e6d6';
        (element as HTMLElement).style.color = '#00e6d6';
        (element as HTMLElement).style.textShadow = '0 0 14px rgba(0,230,214,0.35)';
      }
    });
  }
};

export const initGradientFallback = () => {
  // Run on load
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', checkAndApplyGradientFallback);
  } else {
    checkAndApplyGradientFallback();
  }
  
  // Run on resize to handle orientation changes
  window.addEventListener('resize', () => {
    setTimeout(checkAndApplyGradientFallback, 100);
  });
};
