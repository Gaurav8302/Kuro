import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth, useUser } from '@clerk/clerk-react';
import { AnimatePresence, motion } from 'framer-motion';
import { useExperience } from '../ExperienceContext';
import { DUR, EASE, lineVariants, lineVariantsReduced } from '../motion';
import { storeMemory } from '@/lib/api';
import type { MemoryNode } from '../types';
import { cn } from '@/lib/utils';

/**
 * AWAKENING → ONBOARDING → MEMORY GENESIS
 *
 * One conversation, one component, explicit steps:
 *
 *   connected   CONNECTION ESTABLISHED
 *   unknown     I don't know you yet. Let's change that.
 *   name        What should I call you?             → POST /user/{id}/set-name
 *   building    What are you building?              → POST /store-memory
 *   help        What do you want Kuro to help with? → POST /store-memory
 *   remember    Anything I should remember?         → POST /store-memory (optional)
 *   genesis     Nodes join the Core. I'll remember. → POST /user/{id}/intro-shown
 *   → /chat
 *
 * Every answer is persisted through an existing endpoint. Nothing is faked.
 * The Core gains a memory node for each thing Kuro learns.
 */

type Step = 'connected' | 'unknown' | 'name' | 'building' | 'help' | 'remember' | 'genesis';

interface Answer {
  step: Step;
  label: string;
  value: string;
  /** false when the backend could not persist it — shown honestly */
  saved?: boolean;
}

const QUESTION_STEPS: Step[] = ['name', 'building', 'help', 'remember'];

function short(s: string, n = 34) {
  const t = s.trim().replace(/\s+/g, ' ');
  return t.length > n ? t.slice(0, n - 1).trimEnd() + '…' : t;
}

const Awakening: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useUser();
  const { getToken } = useAuth();
  const { setStage, setCoreMode, setMemoryNodes, memoryNodes, reducedMotion, profile, isMobile } = useExperience();

  const [step, setStep] = useState<Step>('connected');
  const [value, setValue] = useState('');
  const [answers, setAnswers] = useState<Answer[]>([]);
  const [busy, setBusy] = useState(false);
  const timers = useRef<number[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);
  const userId = user?.id;

  const later = useCallback((fn: () => void, ms: number) => {
    const t = window.setTimeout(fn, reducedMotion ? Math.min(ms, 350) : ms);
    timers.current.push(t);
  }, [reducedMotion]);

  useEffect(() => () => timers.current.forEach((t) => window.clearTimeout(t)), []);

  // Stage / Core wiring — explicit per step.
  useEffect(() => {
    if (step === 'connected' || step === 'unknown') {
      setStage('awakening');
      setCoreMode(step === 'connected' ? 'connecting' : 'attention');
    } else if (step === 'genesis') {
      setStage('genesis');
      setCoreMode('genesis');
    } else {
      setStage('onboarding');
      setCoreMode(busy ? 'thinking' : 'attention');
    }
  }, [step, busy, setStage, setCoreMode]);

  // Start with an empty lattice; nodes arrive as Kuro learns.
  useEffect(() => {
    setMemoryNodes([]);
  }, [setMemoryNodes]);

  // Sequenced intro.
  useEffect(() => {
    if (step === 'connected') later(() => setStep('unknown'), 1500);
    if (step === 'unknown') {
      later(() => {
        if (profile.hasName && profile.name) {
          setMemoryNodes([{ id: 'name', kind: 'name', label: profile.name }]);
          setAnswers([{ step: 'name', label: 'Called', value: profile.name }]);
          setStep('building');
        } else {
          setStep('name');
        }
      }, 2300);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step]);

  // Focus the field when a question appears.
  useEffect(() => {
    if (QUESTION_STEPS.includes(step)) {
      const t = window.setTimeout(() => inputRef.current?.focus(), reducedMotion ? 50 : 520);
      timers.current.push(t);
    }
  }, [step, reducedMotion]);

  // Genesis → chat.
  useEffect(() => {
    if (step !== 'genesis') return;
    later(async () => {
      await profile.completeAwakening();
      navigate('/chat', { replace: true });
    }, 3400);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step]);

  const nameKnown = useMemo(
    () => answers.find((a) => a.step === 'name')?.value || profile.name || user?.firstName || '',
    [answers, profile.name, user?.firstName]
  );

  const next = (from: Step): Step => {
    const i = QUESTION_STEPS.indexOf(from);
    return i >= 0 && i < QUESTION_STEPS.length - 1 ? QUESTION_STEPS[i + 1] : 'genesis';
  };

  const addNode = useCallback(
    (node: MemoryNode) => setMemoryNodes((prev) => (prev.some((n) => n.id === node.id) ? prev : [...prev, node])),
    [setMemoryNodes]
  );

  const persist = useCallback(
    async (s: Step, v: string) => {
      if (!userId) return;
      const token = (await getToken().catch(() => null)) || undefined;
      if (s === 'name') {
        await profile.saveName(v);
        return;
      }
      const text =
        s === 'building'
          ? `${nameKnown || 'The user'} is currently building: ${v}`
          : s === 'help'
            ? `${nameKnown || 'The user'} wants Kuro to help with: ${v}`
            : `${nameKnown || 'The user'} asked Kuro to remember: ${v}`;
      const category = s === 'building' ? 'project' : s === 'help' ? 'goal' : 'personal';
      await storeMemory(userId, text, { category, source: 'onboarding', importance: 0.9, kind: s }, token);
    },
    [userId, getToken, profile, nameKnown]
  );

  const submit = useCallback(
    async (e?: React.FormEvent) => {
      e?.preventDefault();
      const v = value.trim();
      if (!v || busy) return;
      setBusy(true);
      const labelMap: Record<string, string> = { name: 'Called', building: 'Building', help: 'Help with', remember: 'Remember' };
      let saved = true;
      try {
        await persist(step, v);
      } catch (err) {
        // Persistence failure should not trap the person; Kuro continues, but
        // it does NOT pretend to have remembered: no node, and the answer is
        // marked as not kept so it can be re-stated in chat.
        console.error('[kuro] onboarding persist failed', err);
        saved = false;
      }
      if (saved) addNode({ id: step, kind: step, label: step === 'name' ? v : short(v) });
      setAnswers((prev) => [...prev.filter((a) => a.step !== step), { step, label: labelMap[step], value: v, saved }]);
      setValue('');
      setBusy(false);
      setStep(next(step));
    },
    [value, busy, step, persist, addNode]
  );

  const skip = useCallback(() => {
    if (busy) return;
    setValue('');
    setStep(next(step));
  }, [busy, step]);

  const lv = reducedMotion ? lineVariantsReduced : lineVariants;
  const coreSize = (step === 'connected' || step === 'unknown' ? 200 : step === 'genesis' ? 220 : 112) * (isMobile ? 0.74 : 1);
  const coreY = step === 'connected' || step === 'unknown' || step === 'genesis' ? 0.5 : 0.26;

  const question: Record<Step, React.ReactNode> = {
    connected: null,
    unknown: null,
    name: 'What should I call you?',
    building: (
      <>
        {nameKnown && <span className="block text-muted-foreground">Nice to meet you, {nameKnown}.</span>}
        What are you building?
      </>
    ),
    help: 'What do you want Kuro to help you with?',
    remember: 'Anything I should remember?',
    genesis: null,
  };

  const placeholder: Partial<Record<Step, string>> = {
    name: 'Your name',
    building: 'A product, a thesis, a habit…',
    help: 'Thinking, writing, code, decisions…',
    remember: 'A preference, a constraint, a fact',
  };

  return (
    <div className="relative h-full w-full">
      {/* ---- Awakening lines ---- */}
      <AnimatePresence mode="wait">
        {step === 'connected' && (
          <motion.div
            key="connected"
            className="absolute inset-x-0 mx-auto text-center"
            style={{ top: `calc(${coreY * 100}% + ${coreSize / 2 + 44}px)` }}
            variants={lv}
            initial="hidden"
            animate="show"
            exit="exit"
          >
            <span className="k-label !text-foreground/80">Connection established</span>
          </motion.div>
        )}
        {step === 'unknown' && (
          <motion.div
            key="unknown"
            className="absolute inset-x-0 mx-auto w-[min(92vw,560px)] text-center"
            style={{ top: `calc(${coreY * 100}% + ${coreSize / 2 + 40}px)` }}
            variants={lv}
            initial="hidden"
            animate="show"
            exit="exit"
          >
            <motion.p className="k-voice text-[clamp(1.5rem,3.4vw,2.25rem)]" variants={lv} custom={0}>
              I don&apos;t know you yet.
            </motion.p>
            <motion.p className="k-voice mt-2 text-[clamp(1.5rem,3.4vw,2.25rem)] text-muted-foreground" variants={lv} custom={3}>
              Let&apos;s change that.
            </motion.p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ---- Conversation ---- */}
      {QUESTION_STEPS.includes(step) && (
        <div
          className="absolute left-1/2 w-[min(92vw,600px)] -translate-x-1/2"
          style={{ top: `calc(${coreY * 100}% + ${coreSize / 2 + 40}px)` }}
        >
          {/* What Kuro already knows — stays visible, quietly */}
          <div className="mb-6 flex min-h-[16px] flex-wrap justify-center gap-x-5 gap-y-1">
            <AnimatePresence>
              {answers.map((a) => (
                <motion.span
                  key={a.step}
                  className="k-label !text-muted-foreground/70"
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: DUR.interface, ease: EASE.out }}
                >
                  {a.label} · <span className="!normal-case !tracking-normal text-foreground/70">{short(a.value, 28)}</span>
                  {a.saved === false && <span className="!text-muted-foreground/45"> · not kept</span>}
                </motion.span>
              ))}
            </AnimatePresence>
          </div>

          <AnimatePresence mode="wait" initial={false}>
            <motion.form
              key={step}
              onSubmit={submit}
              className="flex flex-col items-center text-center"
              variants={lv}
              initial="hidden"
              animate="show"
              exit="exit"
            >
              <motion.h1 className="k-voice text-[clamp(1.5rem,3.4vw,2.25rem)]" variants={lv} custom={0}>
                {question[step]}
              </motion.h1>

              <motion.div className="mt-9 w-[min(88vw,440px)]" variants={lv} custom={1}>
                <input
                  ref={inputRef}
                  className="k-field text-center text-lg"
                  type="text"
                  value={value}
                  onChange={(e) => setValue(e.target.value)}
                  placeholder={placeholder[step]}
                  maxLength={step === 'name' ? 50 : 240}
                  autoComplete={step === 'name' ? 'given-name' : 'off'}
                  disabled={busy}
                  aria-label={typeof question[step] === 'string' ? (question[step] as string) : 'Answer'}
                />
              </motion.div>

              <motion.div className="mt-7 flex items-center gap-8" variants={lv} custom={2}>
                {step !== 'name' && (
                  <button type="button" onClick={skip} className="k-quiet" disabled={busy}>
                    Skip
                  </button>
                )}
                <button type="submit" className={cn('k-action', !value.trim() && 'opacity-40')} disabled={busy || !value.trim()}>
                  {busy ? 'Remembering' : 'Continue'}
                </button>
              </motion.div>
            </motion.form>
          </AnimatePresence>
        </div>
      )}

      {/* ---- Memory Genesis ---- */}
      <AnimatePresence>
        {step === 'genesis' && (
          <motion.div key="genesis" className="absolute inset-0" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: DUR.interface }}>
            {/* Node labels around the Core — what was learned, not how it's stored */}
            {memoryNodes.slice(0, 6).map((n, i, arr) => {
              const a = -Math.PI / 2 + (i / Math.max(arr.length, 1)) * Math.PI * 2;
              const r = coreSize / 2 + (isMobile ? 46 : 72);
              const x = Math.cos(a) * r;
              const y = Math.sin(a) * r * 0.78;
              return (
                <motion.div
                  key={n.id}
                  className="absolute left-1/2 top-1/2 w-[160px] text-center"
                  style={{ marginLeft: x, marginTop: y }}
                  initial={{ opacity: 0, scale: 0.94, x: '-50%', y: '-50%' }}
                  animate={{ opacity: 1, scale: 1, x: '-50%', y: '-50%' }}
                  transition={{ delay: 0.25 + i * 0.16, duration: DUR.interface + 0.2, ease: EASE.out }}
                >
                  <div className="k-label !text-muted-foreground/70">{n.kind === 'name' ? 'You' : n.kind}</div>
                  <div className="mt-1 text-[13px] font-light leading-snug text-foreground/85">{n.label}</div>
                </motion.div>
              );
            })}

            <motion.div
              className="absolute inset-x-0 mx-auto text-center"
              style={{ top: `calc(50% + ${coreSize / 2 + (isMobile ? 96 : 118)}px)` }}
              variants={lv}
              initial="hidden"
              animate="show"
              custom={memoryNodes.length + 4}
            >
              <p className="k-voice text-[clamp(1.375rem,3vw,2rem)]">
                {answers.some((a) => a.saved === false)
                  ? memoryNodes.length > 0
                    ? 'I\u2019ll remember what I could.'
                    : 'I couldn\u2019t keep that yet.'
                  : 'I\u2019ll remember.'}
              </p>
              <p className="k-label mt-4">
                {answers.some((a) => a.saved === false) && memoryNodes.length === 0
                  ? 'Tell me again in conversation'
                  : 'Initialising Kuro for you'}
              </p>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default Awakening;
