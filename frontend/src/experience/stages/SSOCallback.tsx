import React from 'react';
import { AuthenticateWithRedirectCallback } from '@clerk/clerk-react';
import { motion } from 'framer-motion';
import { useExperience, useStage } from '../ExperienceContext';
import { lineVariants, lineVariantsReduced } from '../motion';

/**
 * OAuth return. Clerk completes the handshake; the environment shows the Core
 * connecting. No spinner, no separate page.
 */
const SSOCallback: React.FC = () => {
  useStage('connecting', 'connecting');
  const { reducedMotion } = useExperience();
  const lv = reducedMotion ? lineVariantsReduced : lineVariants;
  return (
    <div className="relative h-full w-full">
      <motion.div
        className="absolute inset-x-0 top-[calc(50%+130px)] mx-auto text-center"
        variants={lv}
        initial="hidden"
        animate="show"
      >
        <span className="k-label">Establishing connection</span>
      </motion.div>
      <AuthenticateWithRedirectCallback
        signInFallbackRedirectUrl="/chat"
        signUpFallbackRedirectUrl="/chat"
      />
    </div>
  );
};

export default SSOCallback;
