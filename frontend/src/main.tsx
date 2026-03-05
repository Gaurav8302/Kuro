// Canvas Chat AI - Main entry point
import { createRoot } from 'react-dom/client'
import App from './App.tsx'
import { ClerkProvider } from '@clerk/clerk-react';
// Import main styles (includes Tailwind and design system)
import './index.css'

const publishableKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;

if (!publishableKey) {
  console.error('❌ VITE_CLERK_PUBLISHABLE_KEY is not set!');
}

createRoot(document.getElementById("root")!).render(
  <ClerkProvider 
    publishableKey={publishableKey || 'pk_test_missing'}
    afterSignOutUrl="/"
  signInFallbackRedirectUrl="/chat"
  signUpFallbackRedirectUrl="/chat"
  >
    <App />
  </ClerkProvider>
);
