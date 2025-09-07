import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { useAuth } from "@clerk/clerk-react";
import { Loader2 } from "lucide-react";
import { useEffect, Suspense, lazy } from "react";
import Landing from "./pages/Landing";
import { addResourceHints, preloadComponent } from "@/utils/lazyLoader";

// Lazy load heavy components
const Chat = lazy(() => import("./pages/Chat"));
import SignInPage from "./pages/SignIn";
import SignUpPage from "./pages/SignUp";
import SSOCallback from "./pages/SSOCallback";
import NotFound from "./pages/NotFound";
import ProtectedRoute from "@/components/ProtectedRoute";
import PublicRoute from "@/components/PublicRoute";
import PerformanceMonitor from "@/components/PerformanceMonitor";
import { MobileOptimizations, IOSOptimizations } from "@/components/MobileOptimizations";

const queryClient = new QueryClient();

// Performance optimizations
const LoadingFallback = () => (
  <div className="h-screen flex items-center justify-center bg-background">
    <div className="text-center">
      <Loader2 className="w-8 h-8 animate-spin mx-auto mb-4 text-holo-cyan-400" />
      <p className="text-holo-cyan-400/60 font-orbitron tracking-wide">LOADING INTERFACE...</p>
    </div>
  </div>
);
const App = () => {
  const { isLoaded } = useAuth();

  // Add resource hints and preload critical components
  useEffect(() => {
    addResourceHints();
    
    // Preload Chat component for faster navigation
    preloadComponent(() => import("./pages/Chat"));
  }, []);

  // Auto-warm ping to keep Render backend awake
  useEffect(() => {
    // Only run in production or when API_BASE_URL points to Render
    const apiUrl = import.meta.env.VITE_API_BASE_URL;
    if (!apiUrl || apiUrl.includes('localhost') || import.meta.env.VITE_ENVIRONMENT === 'development') {
      console.log('🔧 Skipping auto-warm ping for local development');
      return;
    }

    console.log('🚀 Starting enhanced auto-warm ping for production backend');
    
    let pingAttempts = 0;
    const maxPingAttempts = 3;
    
    const sendPing = async (reason: string) => {
      try {
        const response = await fetch(`${apiUrl}/ping`, {
          method: 'GET',
          headers: {
            'Cache-Control': 'no-cache',
          },
        });
        
        if (response.ok) {
          console.log(`🔥 ${reason} ping successful (attempt ${pingAttempts + 1})`);
          pingAttempts = 0; // Reset attempts on success
          return true;
        } else {
          throw new Error(`HTTP ${response.status}`);
        }
      } catch (error) {
        pingAttempts++;
        console.warn(`⚠️ ${reason} ping failed (attempt ${pingAttempts}):`, error);
        
        // If all attempts failed, try one more time after a delay
        if (pingAttempts >= maxPingAttempts) {
          console.error('💥 All ping attempts failed - backend may be sleeping');
          pingAttempts = 0; // Reset for next interval
        }
        return false;
      }
    };
    
    // Ping immediately on load
    sendPing('Initial');
    
    // Ping when page becomes visible (user comes back to tab)
    const handleVisibilityChange = () => {
      if (!document.hidden) {
        sendPing('Tab focus');
      }
    };
    
    document.addEventListener('visibilitychange', handleVisibilityChange);
    
    // Ping on mouse movement (user is active)
    let lastActivityPing = Date.now();
    const handleActivity = () => {
      const now = Date.now();
      // Only ping once per minute on activity
      if (now - lastActivityPing > 60000) {
        sendPing('User activity');
        lastActivityPing = now;
      }
    };
    
    document.addEventListener('mousemove', handleActivity);
    document.addEventListener('click', handleActivity);

    // Set up multiple ping intervals for better reliability - AGGRESSIVE MODE
    const primaryInterval = setInterval(() => {
      sendPing('Primary auto-warm');
    }, 1000 * 60 * 2); // 2 minutes (more aggressive)

    // Secondary ping every 3 minutes as backup
    const secondaryInterval = setInterval(() => {
      sendPing('Secondary backup');
    }, 1000 * 60 * 3); // 3 minutes

    // Emergency ping every 90 seconds for first 10 minutes
    const emergencyInterval = setInterval(() => {
      sendPing('Emergency keep-alive');
    }, 1000 * 90); // 90 seconds
    
    // Clear emergency ping after 10 minutes
    setTimeout(() => {
      clearInterval(emergencyInterval);
      console.log('🎯 Emergency ping mode disabled - switching to normal intervals');
    }, 1000 * 60 * 10); // 10 minutes

    // Cleanup intervals on unmount
    return () => {
      console.log('🧹 Cleaning up auto-warm ping intervals');
      clearInterval(primaryInterval);
      clearInterval(secondaryInterval);
      if (emergencyInterval) clearInterval(emergencyInterval);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      document.removeEventListener('mousemove', handleActivity);
      document.removeEventListener('click', handleActivity);
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
        <MobileOptimizations />
        <IOSOptimizations />
        <PerformanceMonitor showInDev={true} />
        <Toaster />
        <Sonner />
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route 
              path="/chat" 
              element={
                <ProtectedRoute>
                  <Suspense fallback={<LoadingFallback />}>
                    <Chat />
                  </Suspense>
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/chat/:sessionId" 
              element={
                <ProtectedRoute>
                  <Suspense fallback={<LoadingFallback />}>
                    <Chat />
                  </Suspense>
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
