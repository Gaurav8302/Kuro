import { Variants, type Transition } from 'framer-motion';

/**
 * Kuro Animation System
 * Purpose-driven motion design inspired by GitHub, Vercel, Linear
 * 
 * Principles:
 * - Every animation has a purpose
 * - Motion hierarchy: Cursor → Micro, Page → Medium, Section → Slow
 * - Calm, not flashy
 */

// ============================================
// TRANSITION CONFIGS
// ============================================

// Easing curves as tuples for proper typing
type EasingCurve = [number, number, number, number];
const easeDefault: EasingCurve = [0.4, 0, 0.2, 1];

export const transitions = {
  instant: { duration: 0.05 } satisfies Transition,
  fast: { duration: 0.15, ease: easeDefault } satisfies Transition,
  normal: { duration: 0.25, ease: easeDefault } satisfies Transition,
  slow: { duration: 0.4, ease: easeDefault } satisfies Transition,
  slower: { duration: 0.6, ease: easeDefault } satisfies Transition,
  spring: { type: 'spring' as const, damping: 25, stiffness: 200 },
  springBouncy: { type: 'spring' as const, damping: 15, stiffness: 300 },
  springSmooth: { type: 'spring' as const, damping: 30, stiffness: 150 },
};

// ============================================
// PAGE TRANSITIONS
// ============================================

export const pageVariants: Variants = {
  initial: {
    opacity: 0,
    y: 20,
  },
  enter: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.4,
      ease: [0.4, 0, 0.2, 1],
      staggerChildren: 0.1,
    },
  },
  exit: {
    opacity: 0,
    y: -10,
    transition: {
      duration: 0.2,
      ease: [0.4, 0, 1, 1],
    },
  },
};

// ============================================
// FADE ANIMATIONS
// ============================================

export const fadeInVariants: Variants = {
  hidden: { opacity: 0 },
  visible: { 
    opacity: 1,
    transition: transitions.normal,
  },
};

export const fadeInUpVariants: Variants = {
  hidden: { 
    opacity: 0, 
    y: 20,
  },
  visible: { 
    opacity: 1, 
    y: 0,
    transition: transitions.normal,
  },
};

export const fadeInDownVariants: Variants = {
  hidden: { 
    opacity: 0, 
    y: -20,
  },
  visible: { 
    opacity: 1, 
    y: 0,
    transition: transitions.normal,
  },
};

// ============================================
// SCALE ANIMATIONS
// ============================================

export const scaleInVariants: Variants = {
  hidden: { 
    opacity: 0, 
    scale: 0.95,
  },
  visible: { 
    opacity: 1, 
    scale: 1,
    transition: transitions.normal,
  },
};

// ============================================
// STAGGER ANIMATIONS
// ============================================

export const staggerContainerVariants: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.08,
      delayChildren: 0.1,
    },
  },
};

export const staggerItemVariants: Variants = {
  hidden: { 
    opacity: 0, 
    y: 16,
  },
  visible: { 
    opacity: 1, 
    y: 0,
    transition: transitions.normal,
  },
};

// ============================================
// HOVER & INTERACTION STATES
// ============================================

export const hoverScale = {
  scale: 1.02,
  transition: transitions.fast,
};

export const hoverGlow = {
  boxShadow: '0 0 20px -5px rgba(59, 130, 246, 0.5)',
  transition: transitions.fast,
};

export const tapScale = {
  scale: 0.98,
  transition: transitions.instant,
};

export const buttonHoverVariants = {
  rest: { scale: 1 },
  hover: { scale: 1.02 },
  tap: { scale: 0.98 },
};

// ============================================
// MESSAGE ANIMATIONS
// ============================================

export const messageVariants: Variants = {
  hidden: { 
    opacity: 0, 
    y: 10,
    scale: 0.98,
  },
  visible: { 
    opacity: 1, 
    y: 0,
    scale: 1,
    transition: {
      duration: 0.2,
      ease: [0, 0, 0.2, 1],
    },
  },
  exit: {
    opacity: 0,
    y: -5,
    transition: {
      duration: 0.15,
    },
  },
};

// ============================================
// TYPING INDICATOR
// ============================================

export const typingDotVariants: Variants = {
  initial: { y: 0 },
  animate: {
    y: [-2, 2, -2],
    transition: {
      duration: 0.6,
      repeat: Infinity,
      ease: 'easeInOut',
    },
  },
};

// ============================================
// SIDEBAR ANIMATIONS
// ============================================

export const sidebarVariants: Variants = {
  closed: {
    x: '-100%',
    opacity: 0,
    transition: transitions.normal,
  },
  open: {
    x: 0,
    opacity: 1,
    transition: transitions.spring,
  },
};

// ============================================
// MODAL / OVERLAY ANIMATIONS
// ============================================

export const overlayVariants: Variants = {
  hidden: { opacity: 0 },
  visible: { 
    opacity: 1,
    transition: transitions.fast,
  },
  exit: {
    opacity: 0,
    transition: transitions.fast,
  },
};

export const modalVariants: Variants = {
  hidden: { 
    opacity: 0, 
    scale: 0.95,
    y: 10,
  },
  visible: { 
    opacity: 1, 
    scale: 1,
    y: 0,
    transition: transitions.spring,
  },
  exit: {
    opacity: 0,
    scale: 0.95,
    y: 10,
    transition: transitions.fast,
  },
};

// ============================================
// UTILITY FUNCTIONS
// ============================================

/**
 * Creates a delayed variant for staggered child animations
 */
export const createDelayedVariant = (delay: number): Variants => ({
  hidden: { opacity: 0, y: 16 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      ...transitions.normal,
      delay,
    },
  },
});

/**
 * Creates custom spring transition
 */
export const createSpring = (damping = 25, stiffness = 200) => ({
  type: 'spring' as const,
  damping,
  stiffness,
});
