import { useAuth } from "@clerk/clerk-react";
import { Navigate } from "react-router-dom";
import { Loader2 } from "lucide-react";

interface PublicRouteProps {
  children: React.ReactNode;
}

const PublicRoute = ({ children }: PublicRouteProps) => {
  const { isLoaded, isSignedIn } = useAuth();

  // Show loading spinner while Clerk is initializing
  if (!isLoaded) {
    return (
      <div className="min-h-screen bg-gradient-hero flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin mx-auto mb-4 text-white" />
          <p className="text-white/80">Loading...</p>
        </div>
      </div>
    );
  }

  // Redirect to chat if user is already authenticated
  if (isSignedIn) {
    return <Navigate to="/chat" replace />;
  }

  // User is not authenticated, render the public content
  return <>{children}</>;
};

export default PublicRoute;
