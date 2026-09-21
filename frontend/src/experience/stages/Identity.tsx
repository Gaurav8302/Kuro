import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSignIn, useSignUp } from '@clerk/clerk-react';
import { AnimatePresence, motion } from 'framer-motion';
import { useExperience, useStage } from '../ExperienceContext';
import { DUR, EASE, lineVariants, lineVariantsReduced } from '../motion';
import { cn } from '@/lib/utils';

/**
 * IDENTITY — authentication inside the Kuro environment.
 *
 * Clerk remains responsible for authentication (useSignIn / useSignUp, OAuth
 * redirect, email verification). Kuro only owns the presentation: no card, no
 * borders, one question and a small number of answers.
 */

type Intent = 'signin' | 'signup';
type Method = 'choose' | 'email' | 'verify';

const GoogleMark = () => (
  <svg className="h-3.5 w-3.5 opacity-80" viewBox="0 0 24 24" aria-hidden="true">
    <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
    <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
    <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
    <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
  </svg>
);

function clerkMessage(err: unknown, fallback: string): string {
  const e = err as { errors?: Array<{ longMessage?: string; message?: string }>; message?: string };
  return e?.errors?.[0]?.longMessage || e?.errors?.[0]?.message || e?.message || fallback;
}

const Identity: React.FC = () => {
  const navigate = useNavigate();
  const { signIn, setActive: setActiveIn, isLoaded: inLoaded } = useSignIn();
  const { signUp, setActive: setActiveUp, isLoaded: upLoaded } = useSignUp();
  const { reducedMotion, setCoreMode, isMobile } = useExperience();
  useStage('identity', 'idle');

  const [intent, setIntent] = useState<Intent>('signin');
  const [method, setMethod] = useState<Method>('choose');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [firstName, setFirstName] = useState('');
  const [code, setCode] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isLoaded = inLoaded && upLoaded;
  const lv = reducedMotion ? lineVariantsReduced : lineVariants;

  useEffect(() => {
    setCoreMode(busy ? 'connecting' : method === 'choose' ? 'idle' : 'attention');
  }, [busy, method, setCoreMode]);

  const finish = useCallback(() => {
    navigate('/chat', { replace: true });
  }, [navigate]);

  const withGoogle = useCallback(async () => {
    if (!isLoaded) return;
    setBusy(true);
    setError(null);
    try {
      const strategy = 'oauth_google' as const;
      const opts = {
        strategy,
        redirectUrl: `${window.location.origin}/sso-callback`,
        redirectUrlComplete: `${window.location.origin}/chat`,
      };
      if (intent === 'signup' && signUp) await signUp.authenticateWithRedirect(opts);
      else if (signIn) await signIn.authenticateWithRedirect(opts);
    } catch (err) {
      setError(clerkMessage(err, 'Google sign-in did not complete.'));
      setBusy(false);
    }
  }, [isLoaded, intent, signIn, signUp]);

  const submitEmail = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!isLoaded || busy) return;
      setBusy(true);
      setError(null);
      try {
        if (intent === 'signin') {
          if (!signIn) throw new Error('Sign-in unavailable');
          const res = await signIn.create({ identifier: email.trim(), password });
          if (res.status === 'complete' && res.createdSessionId) {
            await setActiveIn({ session: res.createdSessionId });
            finish();
          } else {
            throw new Error('Sign-in needs another step that is not supported here.');
          }
        } else {
          if (!signUp) throw new Error('Sign-up unavailable');
          let res;
          try {
            res = await signUp.create({
              emailAddress: email.trim(),
              password,
              ...(firstName.trim() ? { firstName: firstName.trim() } : {}),
            });
          } catch (createErr) {
            // Some Clerk instances reject name fields; retry without.
            const msg = clerkMessage(createErr, '').toLowerCase();
            if (firstName.trim() && (msg.includes('first_name') || msg.includes('parameter'))) {
              res = await signUp.create({ emailAddress: email.trim(), password });
            } else {
              throw createErr;
            }
          }
          if (res.status === 'complete' && res.createdSessionId) {
            await setActiveUp({ session: res.createdSessionId });
            finish();
          } else {
            await signUp.prepareEmailAddressVerification({ strategy: 'email_code' });
            setMethod('verify');
          }
        }
      } catch (err) {
        setError(clerkMessage(err, intent === 'signin' ? 'Those details were not recognised.' : 'The account could not be created.'));
      } finally {
        setBusy(false);
      }
    },
    [isLoaded, busy, intent, signIn, signUp, email, password, firstName, setActiveIn, setActiveUp, finish]
  );

  const submitCode = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!isLoaded || !signUp || busy) return;
      setBusy(true);
      setError(null);
      try {
        const res = await signUp.attemptEmailAddressVerification({ code: code.trim() });
        if (res.status === 'complete' && res.createdSessionId) {
          await setActiveUp({ session: res.createdSessionId });
          finish();
        } else {
          throw new Error('That code was not accepted.');
        }
      } catch (err) {
        setError(clerkMessage(err, 'That code was not accepted.'));
      } finally {
        setBusy(false);
      }
    },
    [isLoaded, signUp, busy, code, setActiveUp, finish]
  );

  const toggleIntent = () => {
    setIntent((i) => (i === 'signin' ? 'signup' : 'signin'));
    setError(null);
    if (method === 'verify') setMethod('email');
  };

  const back = () => {
    if (method === 'choose') navigate('/');
    else {
      setMethod('choose');
      setError(null);
    }
  };

  const coreY = 0.3;
  const topOffset = `calc(${coreY * 100}vh + ${(isMobile ? 132 * 0.74 : 132) / 2 + 40}px)`;

  return (
    <div className="relative h-full w-full">
      {/* Return — top right */}
      <div className="absolute right-7 top-0 flex h-[60px] items-center">
        <button type="button" onClick={back} className="k-quiet">
          {method === 'choose' ? 'Return' : 'Back'}
        </button>
      </div>

      <div
        className="absolute left-1/2 w-[min(92vw,420px)] -translate-x-1/2"
        style={{ top: topOffset }}
      >
        <AnimatePresence mode="wait" initial={false}>
          {method === 'choose' && (
            <motion.div key="choose" className="flex flex-col items-center" variants={lv} initial="hidden" animate="show" exit="exit">
              <motion.h1 className="k-display text-center text-[clamp(1.5rem,3.4vw,2.25rem)]" variants={lv} custom={0}>
                {intent === 'signin' ? 'Identify yourself' : 'Make yourself known'}
              </motion.h1>

              <motion.div className="mt-12 flex flex-col items-center gap-4" variants={lv} custom={1}>
                <button type="button" onClick={withGoogle} disabled={!isLoaded || busy} className="k-action inline-flex items-center gap-3">
                  <GoogleMark />
                  Continue with Google
                </button>
                <button
                  type="button"
                  onClick={() => setMethod('email')}
                  disabled={!isLoaded || busy}
                  className="k-action"
                >
                  Continue with email
                </button>
              </motion.div>

              <motion.button
                type="button"
                onClick={toggleIntent}
                className="k-quiet mt-14"
                variants={lv}
                custom={2}
              >
                {intent === 'signin' ? 'New here? Create an identity' : 'Already known? Sign in'}
              </motion.button>
            </motion.div>
          )}

          {method === 'email' && (
            <motion.form key="email" onSubmit={submitEmail} className="flex flex-col" variants={lv} initial="hidden" animate="show" exit="exit">
              <motion.h1 className="k-display text-center text-[clamp(1.375rem,3vw,2rem)]" variants={lv} custom={0}>
                {intent === 'signin' ? 'Welcome back' : 'Begin'}
              </motion.h1>

              <motion.div className="mt-10 flex flex-col gap-5" variants={lv} custom={1}>
                {intent === 'signup' && (
                  <input
                    className="k-field text-base"
                    type="text"
                    autoComplete="given-name"
                    placeholder="Your name (optional)"
                    value={firstName}
                    onChange={(e) => setFirstName(e.target.value)}
                    maxLength={50}
                  />
                )}
                <input
                  className="k-field text-base"
                  type="email"
                  autoComplete="email"
                  placeholder="Email"
                  required
                  autoFocus
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
                <input
                  className="k-field text-base"
                  type="password"
                  autoComplete={intent === 'signin' ? 'current-password' : 'new-password'}
                  placeholder={intent === 'signin' ? 'Password' : 'Password (8+ characters)'}
                  required
                  minLength={intent === 'signup' ? 8 : undefined}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </motion.div>

              {/* Clerk bot-protection mounts here when required */}
              <div id="clerk-captcha" className="mt-4 empty:hidden" />

              <motion.div className="mt-9 flex items-center justify-between" variants={lv} custom={2}>
                <button type="button" onClick={toggleIntent} className="k-quiet">
                  {intent === 'signin' ? 'Create an identity' : 'Sign in instead'}
                </button>
                <button type="submit" disabled={busy || !isLoaded} className="k-action">
                  {busy ? 'Connecting' : intent === 'signin' ? 'Enter' : 'Continue'}
                </button>
              </motion.div>
            </motion.form>
          )}

          {method === 'verify' && (
            <motion.form key="verify" onSubmit={submitCode} className="flex flex-col" variants={lv} initial="hidden" animate="show" exit="exit">
              <motion.h1 className="k-display text-center text-[clamp(1.375rem,3vw,2rem)]" variants={lv} custom={0}>
                Confirm it&apos;s you
              </motion.h1>
              <motion.p className="k-label mt-4 text-center !normal-case !tracking-[0.03em]" variants={lv} custom={1}>
                A code was sent to {email}
              </motion.p>
              <motion.input
                className="k-field mt-10 text-center font-mono text-xl tracking-[0.5em]"
                type="text"
                inputMode="numeric"
                autoComplete="one-time-code"
                placeholder="······"
                required
                autoFocus
                value={code}
                onChange={(e) => setCode(e.target.value)}
                variants={lv}
                custom={2}
              />
              <motion.div className="mt-9 flex items-center justify-end" variants={lv} custom={3}>
                <button type="submit" disabled={busy || !code.trim()} className="k-action">
                  {busy ? 'Connecting' : 'Confirm'}
                </button>
              </motion.div>
            </motion.form>
          )}
        </AnimatePresence>

        <AnimatePresence>
          {error && (
            <motion.p
              key="error"
              role="alert"
              className={cn('k-label mt-8 text-center !normal-case !tracking-[0.03em] !text-destructive')}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: DUR.interface, ease: EASE.out }}
            >
              {error}
            </motion.p>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default Identity;
