import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { useAuth } from "@clerk/clerk-react";
import { Loader2 } from "lucide-react";
import { useEffect } from "react";
import Landing from "./pages/Landing";
import Chat from "./pages/Chat";
import SignInPage from "./pages/SignIn";
import SignUpPage from "./pages/SignUp";
import SSOCallback from "./pages/SSOCallback";
import NotFound from "./pages/NotFound";
import ProtectedRoute from "@/components/ProtectedRoute";
import PublicRoute from "@/components/PublicRoute";

const queryClient = new QueryClient();

const App = () => {
  const { isLoaded } = useAuth();

  // Auto-warm ping to keep Render backend awake
  useEffect(() => {
    // Only run in production or when API_BASE_URL points to Render
    const apiUrl = import.meta.env.VITE_API_BASE_URL;
    if (!apiUrl || apiUrl.includes('localhost') || import.meta.env.VITE_ENVIRONMENT === 'development') {
      console.log('🔧 Skipping auto-warm ping for local development');
      return;
    }

    console.log('🚀 Starting auto-warm ping for production backend');
    
    // Ping immediately on load
    fetch(`${apiUrl}/ping`)
      .then(() => console.log('✅ Initial ping sent to backend'))
      .catch(() => console.warn('⚠️ Initial ping failed'));

    // Set up interval to ping every 4.5 minutes
    const interval = setInterval(() => {
      fetch(`${apiUrl}/ping`)
        .then(() => console.log('🔥 Auto-warm ping sent to keep backend awake'))
        .catch(() => console.warn('⚠️ Auto-warm ping failed – backend might be sleeping'));
    }, 1000 * 60 * 4.5); // 270,000ms = 4.5 minutes

    // Cleanup interval on unmount
    return () => {
      console.log('🧹 Cleaning up auto-warm ping interval');
      clearInterval(interval);
    };
  }, []);

  // Show loading screen while Clerk initializes
  if (!isLoaded) {
    return (
      <div className="h-screen flex items-center justify-center bg-gradient-hero">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin mx-auto mb-4 text-white" />
          <p className="text-white/80">Loading Kuro AI...</p>
        </div>
      </div>
    );
  }

  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <Toaster />
        <Sonner />
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route 
              path="/chat" 
              element={
                <ProtectedRoute>
                  <Chat />
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/chat/:sessionId" 
              element={
                <ProtectedRoute>
                  <Chat />
                </ProtectedRoute>
              } 
            />
            <Route path="/auth/signin" element={
              <PublicRoute>
                <SignInPage />
              </PublicRoute>
            } />
            <Route path="/auth/signup" element={
              <PublicRoute>
                <SignUpPage />
              </PublicRoute>
            } />
            <Route path="/sso-callback" element={<SSOCallback />} />
            {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
            <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      </TooltipProvider>
    </QueryClientProvider>
  );
};

export default App;
