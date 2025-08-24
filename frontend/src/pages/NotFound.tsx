import { useLocation, useNavigate } from "react-router-dom";
import { useEffect } from "react";
import { motion } from "framer-motion";
import { Home, ArrowLeft, AlertTriangle, Zap } from "lucide-react";
import { HolographicButton } from "@/components/HolographicButton";
import { HolographicCard } from "@/components/HolographicCard";
import { HolographicBackground } from "@/components/HolographicBackground";
import { HoloSparklesIcon } from "@/components/HolographicIcons";

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
    <div className="min-h-screen bg-background flex items-center justify-center p-4 relative overflow-hidden">
      <HolographicBackground variant="intense" />

      <div className="relative z-10 text-center max-w-lg">
        <HolographicCard variant="intense" className="p-12 mb-8">
          <motion.div
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.8, ease: 'backOut' }}
            className="mb-8"
          >
            <motion.div 
              className="text-8xl font-bold mb-6 font-orbitron"
              animate={{ 
                textShadow: [
                  '0 0 20px #ff1ab1',
                  '0 0 40px #00e6d6',
                  '0 0 20px #8c1aff',
                  '0 0 20px #ff1ab1'
                ]
              }}
              transition={{ duration: 3, repeat: Infinity }}
            >
              <span className="holo-text">4</span>
              <motion.span
                animate={{ rotate: [0, 10, -10, 0], scale: [1, 1.1, 1] }}
                transition={{ duration: 2, repeat: Infinity }}
                className="inline-block mx-2"
              >
                <AlertTriangle className="w-16 h-16 text-holo-magenta-400 inline" />
              </motion.span>
              <span className="holo-text">4</span>
            </motion.div>
            <h1 className="text-4xl font-bold text-holo-cyan-300 mb-4 font-orbitron tracking-wide text-holo-glow">
              NEURAL PATHWAY NOT FOUND
            </h1>
            <p className="text-xl text-holo-cyan-100/80 mb-3 font-space">
              This transmission route has been disconnected from the neural network.
            </p>
            <p className="text-holo-cyan-400/60 font-rajdhani text-lg tracking-wide">
              Even quantum systems experience navigation anomalies.
            </p>
          </motion.div>
        </HolographicCard>

        <motion.div
          initial={{ y: 50, opacity: 0, scale: 0.8 }}
          animate={{ y: 0, opacity: 1, scale: 1 }}
          transition={{ duration: 0.8, delay: 0.4, ease: 'easeOut' }}
          className="flex flex-col sm:flex-row gap-4 justify-center"
        >
          <HolographicButton
            variant="primary"
            size="lg"
            onClick={() => navigate('/')}
            className="group font-orbitron tracking-wide"
          >
            <Home className="w-5 h-5 mr-2" />
            RETURN TO BASE
            <HoloSparklesIcon size={16} className="ml-2" />
          </HolographicButton>
          
          <HolographicButton
            variant="ghost"
            size="lg"
            onClick={() => navigate(-1)}
            className="font-orbitron tracking-wide"
          >
            <ArrowLeft className="w-5 h-5 mr-2" />
            PREVIOUS ROUTE
          </HolographicButton>
        </motion.div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8 }}
          className="mt-12 text-center"
        >
          <p className="text-holo-cyan-400/60 text-sm font-space">
            DISCONNECTED ROUTE: <code className="glass-panel px-3 py-1 rounded text-holo-cyan-300 font-orbitron border border-holo-cyan-400/20">{location.pathname}</code>
          </p>
        </motion.div>
      </div>
    </div>
  );
};

export default NotFound;
