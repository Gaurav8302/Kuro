import { AuthenticateWithRedirectCallback } from '@clerk/clerk-react';
import { Loader2 } from 'lucide-react';

const SSOCallback = () => {
  return (
    <div className="min-h-screen bg-gradient-hero flex items-center justify-center">
      <div className="text-center">
        <Loader2 className="w-8 h-8 animate-spin mx-auto mb-4 text-white" />
        <p className="text-white/80">Completing sign-in...</p>
      </div>
      <AuthenticateWithRedirectCallback />
    </div>
  );
};

export default SSOCallback;
