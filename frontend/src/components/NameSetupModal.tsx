import { useState } from 'react';
import { motion } from 'framer-motion';
import { User, Zap } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { HolographicButton } from '@/components/HolographicButton';
import { HolographicCard } from '@/components/HolographicCard';
import { HoloSparklesIcon } from '@/components/HolographicIcons';

interface NameSetupModalProps {
  isOpen: boolean;
  onComplete: (name: string) => void;
  onSkip: () => void;
}

const NameSetupModal = ({ isOpen, onComplete, onSkip }: NameSetupModalProps) => {
  const [name, setName] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    setIsSubmitting(true);
    try {
      await onComplete(name.trim());
    } catch (error) {
      console.error('Error setting name:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSkip = () => {
    onSkip();
  };

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-md flex items-center justify-center z-[10001] p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.8, filter: 'blur(10px)' }}
        animate={{ opacity: 1, scale: 1, filter: 'blur(0px)' }}
        transition={{ duration: 0.5, ease: 'easeOut' }}
        className="w-full max-w-md"
      >
        <HolographicCard variant="intense" className="overflow-hidden">
          <div className="text-center p-8 pb-4 relative">
            {/* Header scan line */}
            <motion.div
              className="absolute top-0 left-0 w-full h-0.5 bg-gradient-to-r from-transparent via-holo-cyan-400 to-transparent"
              animate={{ opacity: [0.3, 0.8, 0.3] }}
              transition={{ duration: 2, repeat: Infinity }}
            />
            
            <div className="flex justify-center mb-4">
              <div className="relative">
                <motion.div
                  className="w-16 h-16 glass-panel border-holo-cyan-400/50 rounded-full flex items-center justify-center shadow-holo-glow"
                  animate={{ 
                    scale: [1, 1.1, 1],
                    rotate: [0, 5, -5, 0]
                  }}
                  transition={{ duration: 3, repeat: Infinity }}
                >
                  <User className="w-8 h-8 text-holo-cyan-400" />
                </motion.div>
                <motion.div
                  className="absolute -top-2 -right-2"
                  animate={{ rotate: 360, scale: [1, 1.2, 1] }}
                  transition={{ duration: 2, repeat: Infinity }}
                >
                  <HoloSparklesIcon size={20} className="text-holo-purple-400" />
                </motion.div>
              </div>
            </div>
            <h2 className="text-2xl font-bold text-holo-cyan-300 mb-3 font-orbitron tracking-wide text-holo-glow">
              NEURAL PROFILE SETUP
            </h2>
            <p className="text-holo-cyan-100/70 text-sm font-space">
              How should the neural interface address you?
            </p>
          </div>
          
          <div className="space-y-6 p-8 pt-0">
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Neural Operator"
                  className="text-center text-lg glass-panel border-holo-cyan-400/30 text-holo-cyan-100 placeholder:text-holo-cyan-400/40 focus:border-holo-cyan-400 focus:shadow-holo-glow font-space"
                  maxLength={50}
                  autoFocus
                />
              </div>

              <div className="flex flex-col gap-3">
                <HolographicButton
                  variant="primary"
                  size="lg"
                  className="w-full font-orbitron tracking-wide"
                  disabled={!name.trim() || isSubmitting}
                  onClick={handleSubmit}
                >
                  {isSubmitting ? (
                    <>
                      <motion.div
                        animate={{ rotate: 360 }}
                        transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                        className="mr-2"
                      >
                        <Zap className="w-4 h-4" />
                      </motion.div>
                      INITIALIZING...
                    </>
                  ) : (
                    <>
                      <HoloSparklesIcon size={16} className="mr-2" />
                      INITIALIZE PROFILE
                    </>
                  )}
                </HolographicButton>
                
                <HolographicButton
                  variant="ghost"
                  size="md"
                  className="w-full font-orbitron tracking-wide"
                  onClick={handleSkip}
                  disabled={isSubmitting}
                >
                  SKIP INITIALIZATION
                </HolographicButton>
              </div>
            </form>
          </div>
        </HolographicCard>
      </motion.div>
    </div>
  );
};

export default NameSetupModal;
