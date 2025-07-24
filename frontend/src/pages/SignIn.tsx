import { SignIn } from '@clerk/clerk-react';

export default function SignInPage() {
  console.log("CLERK KEY:", import.meta.env.VITE_CLERK_PUBLISHABLE_KEY);
  return (
    <div className="flex items-center justify-center min-h-screen">
      <SignIn />
    </div>
  );
}