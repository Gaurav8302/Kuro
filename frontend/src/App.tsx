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
