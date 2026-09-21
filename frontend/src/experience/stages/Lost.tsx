import React from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useExperience, useStage } from '../ExperienceContext';
import { lineVariants, lineVariantsReduced } from '../motion';

/** 404 — still inside Kuro. */
const Lost: React.FC = () => {
  useStage('lost', 'idle');
  const { reducedMotion } = useExperience();
  const lv = reducedMotion ? lineVariantsReduced : lineVariants;
  return (
    <div className="relative h-full w-full">
      <motion.div
        className="absolute inset-x-0 top-[calc(42%+120px)] mx-auto flex w-[min(92vw,520px)] flex-col items-center gap-8 text-center"
        variants={lv}
        initial="hidden"
        animate="show"
      >
        <motion.p className="k-voice text-[clamp(1.25rem,2.6vw,1.75rem)]" variants={lv} custom={0}>
          This place is not part of Kuro.
        </motion.p>
        <motion.div variants={lv} custom={1}>
          <Link to="/" className="k-action">
            Return to origin
          </Link>
        </motion.div>
      </motion.div>
    </div>
  );
};

export default Lost;
