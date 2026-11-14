import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '@clerk/clerk-react';
import { useExperience, useStage } from './ExperienceContext';

/**
 * Route gates. While something is being established the environment shows the
 * Core in `connecting` — there is no separate loading screen.
 */

export const Connecting: React.FC = () => {
  useStage('connecting', 'connecting');
  return null;
};

/** Clerk remains the authority. Unauthenticated → Identity. */
export const RequireAuth: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isLoaded, isSignedIn } = useAuth();
  if (!isLoaded) return <Connecting />;
  // No `state` object here: a fresh object each render would make <Navigate>
  // re-run while AnimatePresence keeps the exiting route mounted.
  if (!isSignedIn) return <Navigate to="/enter" replace />;
  return <>{children}</>;
};

/**
 * First-time people go through the Awakening once. Kuro remembers this via the
 * existing `intro-shown` profile flag, set at the end of Memory Genesis.
 */
export const RequireAwakened: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { profile } = useExperience();
  if (profile.status === 'idle' || profile.status === 'loading') return <Connecting />;
  // If profile failed to load, don't block - let them through to chat
  // The chat will handle showing onboarding if needed
  if (profile.status === 'error') return <>{children}</>;
  if (!profile.introShown) return <Navigate to="/awaken" replace />;
  return <>{children}</>;
};

/** Already signed in → the identity stage is not needed. */
export const RedirectIfSignedIn: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isLoaded, isSignedIn } = useAuth();
  if (!isLoaded) return <Connecting />;
  if (isSignedIn) return <Navigate to="/chat" replace />;
  return <>{children}</>;
};
