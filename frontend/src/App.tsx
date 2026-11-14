import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useEffect, Suspense, lazy } from "react";
import { addResourceHints, preloadComponent } from "@/utils/lazyLoader";
import { MobileOptimizations } from "@/components/MobileOptimizations";

// The persistent Kuro environment (background + Core + rail) and its stages.
import KuroExperience from "@/experience/KuroExperience";
import Origin from "@/experience/stages/Origin";
import Identity from "@/experience/stages/Identity";
import SSOCallback from "@/experience/stages/SSOCallback";
import Awakening from "@/experience/stages/Awakening";
import Lost from "@/experience/stages/Lost";
import { RequireAuth, RequireAwakened, RedirectIfSignedIn, Connecting } from "@/experience/gates";

// Chat is the heaviest stage; load it on demand. While it loads the Core
// shows `connecting` — there is no separate loading screen.
const Chat = lazy(() => import("./pages/Chat"));

const queryClient = new QueryClient();

const ChatStage = () => (
  <RequireAuth>
    <RequireAwakened>
      <Suspense fallback={<Connecting />}>
        <Chat />
      </Suspense>
    </RequireAwakened>
  </RequireAuth>
);

const App = () => {
  // Resource hints + preload the chat stage so entering feels immediate.
  useEffect(() => {
    addResourceHints();
    preloadComponent(() => import("./pages/Chat"));
  }, []);

  // Keep the Render-hosted backend warm (unchanged behaviour).
  useEffect(() => {
    const apiUrl = import.meta.env.VITE_API_BASE_URL;
    if (!apiUrl || apiUrl.includes('localhost') || import.meta.env.VITE_ENVIRONMENT === 'development') {
      return;
    }

    let pingAttempts = 0;
    const maxPingAttempts = 3;

    const sendPing = async (reason: string) => {
      try {
        const response = await fetch(`${apiUrl}/ping`, { method: 'GET', headers: { 'Cache-Control': 'no-cache' } });
        if (response.ok) {
          pingAttempts = 0;
          return true;
        }
        throw new Error(`HTTP ${response.status}`);
      } catch (error) {
        pingAttempts++;
        console.warn(`[kuro] ${reason} ping failed (attempt ${pingAttempts}):`, error);
        if (pingAttempts >= maxPingAttempts) pingAttempts = 0;
        return false;
      }
    };

    sendPing('Initial');

    const handleVisibilityChange = () => {
      if (!document.hidden) sendPing('Tab focus');
    };
    document.addEventListener('visibilitychange', handleVisibilityChange);

    let lastActivityPing = Date.now();
    const handleActivity = () => {
      const now = Date.now();
      if (now - lastActivityPing > 60000) {
        sendPing('User activity');
        lastActivityPing = now;
      }
    };
    document.addEventListener('mousemove', handleActivity, { passive: true });
    document.addEventListener('click', handleActivity);

    const primaryInterval = setInterval(() => sendPing('Primary auto-warm'), 1000 * 60 * 2);
    const secondaryInterval = setInterval(() => sendPing('Secondary backup'), 1000 * 60 * 3);
    const emergencyInterval = setInterval(() => sendPing('Emergency keep-alive'), 1000 * 90);
    const emergencyStop = setTimeout(() => clearInterval(emergencyInterval), 1000 * 60 * 10);

    return () => {
      clearInterval(primaryInterval);
      clearInterval(secondaryInterval);
      clearInterval(emergencyInterval);
      clearTimeout(emergencyStop);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      document.removeEventListener('mousemove', handleActivity);
      document.removeEventListener('click', handleActivity);
    };
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <MobileOptimizations />
        <Toaster />
        <Sonner />
        <BrowserRouter>
          <Routes>
            <Route element={<KuroExperience />}>
              <Route path="/" element={<Origin />} />

              <Route
                path="/enter"
                element={
                  <RedirectIfSignedIn>
                    <Identity />
                  </RedirectIfSignedIn>
                }
              />
              {/* Legacy auth URLs converge on the Identity stage */}
              <Route path="/sign-in" element={<Navigate to="/enter" replace />} />
              <Route path="/sign-up" element={<Navigate to="/enter" replace />} />
              <Route path="/auth/signin" element={<Navigate to="/enter" replace />} />
              <Route path="/auth/signup" element={<Navigate to="/enter" replace />} />
              <Route path="/sso-callback" element={<SSOCallback />} />

              <Route
                path="/awaken"
                element={
                  <RequireAuth>
                    <Awakening />
                  </RequireAuth>
                }
              />

              <Route path="/chat" element={<ChatStage />} />
              <Route path="/chat/:sessionId" element={<ChatStage />} />

              <Route path="*" element={<Lost />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </TooltipProvider>
    </QueryClientProvider>
  );
};

export default App;
