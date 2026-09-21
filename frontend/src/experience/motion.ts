/**
 * Kuro motion system.
 *
 * Four categories, each with a semantic purpose. Nothing else is animated.
 *
 *   micro       150–250ms   hover, focus, small UI state
 *   interface   300–700ms   panels, menus, Core state changes
 *   experience  700–1400ms  stage → stage (Origin → Identity, Genesis → Chat)
 *   cinematic   > 1400ms    reserved; not used for navigation
 *
 * Every transition must answer "why is this moving?". If it can't, delete it.
 */

export const DUR = {
  micro: 0.18,
  interface: 0.45,
  experience: 0.9,
  cinematic: 1.3,
} as const;

export const EASE = {
  /** Decelerating — things arriving */
  out: [0.22, 1, 0.36, 1] as [number, number, number, number],
  /** Symmetric — things moving between two places */
  inOut: [0.65, 0, 0.35, 1] as [number, number, number, number],
  /** Long tail — Core repositioning */
  settle: [0.16, 1, 0.3, 1] as [number, number, number, number],
};

/** Stage content: emerges slightly forward, recedes slightly back. */
export const stageVariants = {
  initial: { opacity: 0, y: 10, scale: 0.985, filter: 'blur(4px)' },
  enter: {
    opacity: 1,
    y: 0,
    scale: 1,
    filter: 'blur(0px)',
    transition: { duration: DUR.experience, ease: EASE.out, delay: 0.12 },
  },
  exit: {
    opacity: 0,
    y: -8,
    scale: 1.01,
    filter: 'blur(4px)',
    transition: { duration: DUR.experience * 0.6, ease: EASE.inOut },
  },
};

/** Reduced motion: opacity only, short. */
export const stageVariantsReduced = {
  initial: { opacity: 0 },
  enter: { opacity: 1, transition: { duration: 0.2 } },
  exit: { opacity: 0, transition: { duration: 0.12 } },
};

/** Text lines that emerge one after another inside a stage. */
export const lineVariants = {
  hidden: { opacity: 0, y: 8 },
  show: (i = 0) => ({
    opacity: 1,
    y: 0,
    transition: { duration: DUR.interface + 0.15, ease: EASE.out, delay: 0.08 * i },
  }),
  exit: { opacity: 0, y: -6, transition: { duration: DUR.interface * 0.7, ease: EASE.inOut } },
};

export const lineVariantsReduced = {
  hidden: { opacity: 0 },
  show: () => ({ opacity: 1, transition: { duration: 0.2 } }),
  exit: { opacity: 0, transition: { duration: 0.12 } },
};
