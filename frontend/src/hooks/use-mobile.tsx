import * as React from "react"

const MOBILE_BREAKPOINT = 768

// Get initial value synchronously to avoid flash of wrong state
const getIsMobile = () => {
  if (typeof window === 'undefined') return false; // SSR fallback
  return window.innerWidth < MOBILE_BREAKPOINT;
};

export function useIsMobile() {
  // Initialize with actual value instead of undefined to prevent flash
  const [isMobile, setIsMobile] = React.useState<boolean>(getIsMobile)

  React.useEffect(() => {
    const mql = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT - 1}px)`)
    const onChange = () => {
      setIsMobile(window.innerWidth < MOBILE_BREAKPOINT)
    }
    mql.addEventListener("change", onChange)
    // Set initial value in case it wasn't set correctly during SSR
    setIsMobile(window.innerWidth < MOBILE_BREAKPOINT)
    return () => mql.removeEventListener("change", onChange)
  }, [])

  return isMobile
}
