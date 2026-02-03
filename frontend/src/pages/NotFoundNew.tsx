import { useLocation, useNavigate } from "react-router-dom";
import { useEffect, Suspense, lazy } from "react";
import { motion } from "framer-motion";
import { Home, ArrowLeft, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { KuroBackground } from "@/components/kuro";

// Lazy load 3D bot
const KuroBot3D = lazy(() => import("@/components/kuro/KuroBot3D"));

/**
 * NotFound Page - Professional 404
 * Clean, minimal design consistent with Kuro branding
 */
const NotFound = () => {
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    console.error(
      "404 Error: User attempted to access non-existent route:",
      location.pathname
    );
  }, [location.pathname]);

  return (
    <motion.div
      className="min-h-screen bg-background flex items-center justify-center p-4 relative overflow-hidden"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    >
      <KuroBackground variant="hero" />

      <div className="relative z-10 text-center max-w-lg">
        {/* Kuro Bot */}
        <motion.div
          className="flex justify-center mb-8"
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5, delay: 0.1 }}
        >
          <Suspense fallback={
            <div className="w-40 h-40 rounded-full bg-gradient-to-br from-primary to-accent animate-pulse" />
          }>
            <KuroBot3D className="w-40 h-40" />
          </Suspense>
        </motion.div>

        {/* 404 Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.2 }}
          className="glass rounded-2xl p-8 mb-8"
        >
          <div className="mb-6">
            <motion.div 
              className="flex items-center justify-center gap-4 mb-6"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.3 }}
            >
              <span className="text-6xl font-bold text-foreground">4</span>
              <motion.div
                animate={{ rotate: [0, 5, -5, 0] }}
                transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
              >
                <AlertTriangle className="w-12 h-12 text-amber-400" />
              </motion.div>
              <span className="text-6xl font-bold text-foreground">4</span>
            </motion.div>
            
            <h1 className="text-2xl font-bold text-foreground mb-3">
              Page not found
            </h1>
            <p className="text-muted-foreground mb-2">
              The page you're looking for doesn't exist or has been moved.
            </p>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Button
              variant="hero"
              onClick={() => navigate('/')}
              className="gap-2"
            >
              <Home className="w-4 h-4" />
              Back to home
            </Button>
            
            <Button
              variant="ghost"
              onClick={() => navigate(-1)}
              className="gap-2"
            >
              <ArrowLeft className="w-4 h-4" />
              Go back
            </Button>
          </div>
        </motion.div>

        {/* Route Info */}
        <motion.p 
          className="text-xs text-muted-foreground"
          initial={{ opacity: 0 }}
          animate={{ opacity: 0.5 }}
          transition={{ delay: 0.5 }}
        >
          Attempted path: {location.pathname}
        </motion.p>
      </div>
    </motion.div>
  );
};

export default NotFound;
