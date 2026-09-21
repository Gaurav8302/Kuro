import React from 'react';
import { useLocation, useOutlet } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { ExperienceProvider, useExperience } from './ExperienceContext';
import { KuroEnvironment } from './KuroEnvironment';
import { KuroRail } from './KuroRail';
import { stageVariants, stageVariantsReduced, DUR, EASE } from './motion';

/**
 * KuroExperience — the persistent shell.
 *
 *   KuroExperience
 *   ├── KuroEnvironment   (background + Core: never unmounts)
 *   ├── KuroRail          (orientation)
 *   └── <Outlet/>         (the current stage, cross-faded on route-group change)
 *
 * Routes still change normally; only the presentation is continuous.
 */

function routeGroup(pathname: string): string {
  if (pathname.startsWith('/chat')) return 'chat';
  return pathname;
}

const chatVariants = {
  initial: { opacity: 0, scale: 0.992 },
  enter: { opacity: 1, scale: 1, transition: { duration: DUR.experience, ease: EASE.out, delay: 0.1 } },
  exit: { opacity: 0, transition: { duration: DUR.interface, ease: EASE.inOut } },
};

const Stages: React.FC = () => {
  const location = useLocation();
  const outlet = useOutlet();
  const { reducedMotion } = useExperience();
  const group = routeGroup(location.pathname);
  const variants = reducedMotion ? stageVariantsReduced : group === 'chat' ? chatVariants : stageVariants;

  return (
    <div className="relative z-10 h-[100dvh] w-full">
      <AnimatePresence initial={false}>
        <motion.div
          key={group}
          className="absolute inset-0"
          variants={variants}
          initial="initial"
          animate="enter"
          exit="exit"
        >
          {outlet}
        </motion.div>
      </AnimatePresence>
    </div>
  );
};

export const KuroExperience: React.FC = () => {
  return (
    <ExperienceProvider>
      <KuroEnvironment />
      <KuroRail />
      <Stages />
    </ExperienceProvider>
  );
};

export default KuroExperience;
