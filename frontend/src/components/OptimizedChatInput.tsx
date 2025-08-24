import { useState, useRef, useEffect, memo } from 'react';
import { motion } from 'framer-motion';
import { Send, Zap } from 'lucide-react';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';
import { useIsMobile } from '@/hooks/use-mobile';
import { useOptimizedAnimations } from '@/hooks/use-performance';
import { OptimizedHolographicCard } from '@/components/OptimizedHolographicCard';
import { HoloSendIcon, HoloSparklesIcon } from '@/components/HolographicIcons';

interface OptimizedChatInputProps {
  onSendMessage: (message: string) => void;
  placeholder?: string;
  sending?: boolean;
}

// Lightweight input for mobile
const LightweightChatInput: React.FC<OptimizedChatInputProps> = memo(({ 
  onSendMessage, 
  placeholder = "Type a message...",
  sending = false
}) => {
  const [message, setMessage] = useState('');
  const [isFocused, setIsFocused] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const isDisabled = !message.trim() || sending;

  const handleSend = () => {
    if (message.trim() && !sending) {
      onSendMessage(message.trim());
      setMessage('');
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
        textareaRef.current.focus();
      }
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [message]);

  return (
    <div className="border-t border-holo-cyan-500/20 backdrop-blur-md bg-gradient-to-b from-background/60 to-background/80 sticky bottom-0 z-20 relative">
      {/* Simple top border */}
      <div className="absolute top-0 left-0 w-full h-0.5 bg-gradient-to-r from-transparent via-holo-cyan-400/50 to-transparent" />
      
      <div className="max-w-4xl mx-auto p-4 px-3 pb-[calc(env(safe-area-inset-bottom)+0.75rem)]">
        <div className="glass-panel border-holo-cyan-500/30 rounded-xl overflow-hidden transition-all duration-300 hover:border-holo-cyan-500/40">
          <div className="flex items-end gap-3 p-4">
            {/* Message input */}
            <div className="flex-1">
              <Textarea
                ref={textareaRef}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyDown={handleKeyPress}
                onFocus={() => setIsFocused(true)}
                onBlur={() => setIsFocused(false)}
                placeholder={placeholder}
                className="min-h-[24px] max-h-32 resize-none border-none bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0 p-0 font-space placeholder:text-holo-cyan-400/50 text-sm text-holo-cyan-100 placeholder:font-orbitron placeholder:tracking-wider"
                rows={1}
              />
            </div>

            {/* Send button with simple hover effect */}
            <button
              onClick={handleSend}
              disabled={isDisabled}
              className={cn(
                "w-12 h-12 rounded-full relative overflow-hidden",
                "bg-gradient-to-br from-holo-cyan-500 to-holo-blue-500",
                "border-2 border-holo-cyan-400/50 shadow-holo-glow",
                "hover:shadow-holo-blue hover:border-holo-cyan-400/80",
                "disabled:opacity-50 disabled:cursor-not-allowed",
                "transition-all duration-300 flex items-center justify-center",
                "glass-panel backdrop-blur-md",
                !isDisabled && "hover:scale-105 active:scale-95"
              )}
            >
              {sending ? (
                <div className="animate-spin">
                  <Zap className="w-5 h-5 text-white" />
                </div>
              ) : (
                <HoloSendIcon size={20} className="text-white" />
              )}
            </button>
          </div>
        </div>

        {/* Helper text */}
        <p className="text-xs text-holo-cyan-400/60 text-center mt-3 select-none font-orbitron tracking-wide">
          Press <kbd className="px-2 py-1 text-xs bg-holo-cyan-500/20 border border-holo-cyan-400/30 rounded font-orbitron">Enter</kbd> to send
          <span className="mx-1">•</span>
          <kbd className="px-2 py-1 text-xs bg-holo-cyan-500/20 border border-holo-cyan-400/30 rounded font-orbitron">Shift + Enter</kbd> for a new line
        </p>
      </div>
    </div>
  );
});

// Full animated input for desktop
const AnimatedChatInput: React.FC<OptimizedChatInputProps> = memo(({ 
  onSendMessage, 
  placeholder = "Type a message...",
  sending = false
}) => {
  const [message, setMessage] = useState('');
  const [isFocused, setIsFocused] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const { animationDuration } = useOptimizedAnimations();
  const isDisabled = !message.trim() || sending;

  const handleSend = () => {
    if (message.trim() && !sending) {
      onSendMessage(message.trim());
      setMessage('');
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
        textareaRef.current.focus();
      }
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [message]);

  // Initial focus for desktop
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
  }, []);

  return (
    <motion.div
      ref={containerRef}
      className="border-t border-holo-cyan-500/20 backdrop-blur-md bg-gradient-to-b from-background/60 to-background/80 sticky bottom-0 z-20 relative"
      initial={{ y: 50, opacity: 0, scale: 0.9 }}
      animate={{ 
        y: 0, 
        opacity: 1,
        scale: sending ? 0.98 : 1
      }}
      transition={{ 
        duration: animationDuration * 2,
        ease: "easeOut"
      }}
      data-typing={sending ? "true" : "false"}
    >
      {/* Holographic scan line */}
      <div className="absolute top-0 left-0 w-full h-0.5 bg-gradient-to-r from-transparent via-holo-cyan-400 to-transparent" />
      
      {/* Particle drift effect */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <motion.div
          className="absolute inset-0 particle-bg opacity-20"
          animate={{ backgroundPosition: ['0% 0%', '100% 100%'] }}
          transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
        />
      </div>
      
      <div className="max-w-4xl mx-auto p-4">
        <OptimizedHolographicCard
          variant={isFocused ? 'intense' : 'glow'}
          hover={false}
          scanLine={isFocused}
          className={cn(
            "relative transition-all duration-500",
            sending && "opacity-70 scale-98"
          )}
        >
          <div className="flex items-end gap-3 p-4">
          
          {/* Holographic sparkle decoration */}
          {isFocused && (
            <motion.div
              className="absolute -top-3 -right-3 z-10"
              initial={{ scale: 0, rotate: 0, opacity: 0 }}
              animate={{ scale: 1, rotate: 360, opacity: 1 }}
              exit={{ scale: 0, opacity: 0 }}
              transition={{ duration: 0.6, ease: 'backOut' }}
            >
              <div className="w-6 h-6 bg-holo-cyan-400 rounded-full shadow-holo-glow flex items-center justify-center">
                <HoloSparklesIcon size={14} className="text-white" />
              </div>
            </motion.div>
          )}

          {/* Message input */}
          <div className="flex-1">
            <Textarea
              ref={textareaRef}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={handleKeyPress}
              onFocus={() => setIsFocused(true)}
              onBlur={() => setIsFocused(false)}
              placeholder={placeholder}
              className="min-h-[24px] max-h-32 resize-none border-none bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0 p-0 font-space placeholder:text-holo-cyan-400/50 text-sm text-holo-cyan-100 placeholder:font-orbitron placeholder:tracking-wider"
              rows={1}
            />
          </div>

          {/* Send button */}
          <motion.div
            whileHover={{ scale: 1.1, rotate: 5 }}
            whileTap={{ scale: 0.9 }}
            transition={{ duration: animationDuration }}
          >
            <motion.button
              onClick={handleSend}
              disabled={isDisabled}
              className={cn(
                "w-12 h-12 rounded-full relative overflow-hidden",
                "bg-gradient-to-br from-holo-cyan-500 to-holo-blue-500",
                "border-2 border-holo-cyan-400/50 shadow-holo-glow",
                "hover:shadow-holo-blue hover:border-holo-cyan-400/80",
                "disabled:opacity-50 disabled:cursor-not-allowed",
                "transition-all duration-300 flex items-center justify-center",
                "glass-panel backdrop-blur-md"
              )}
              whileHover={!isDisabled ? {
                boxShadow: '0 0 40px rgba(0, 230, 214, 0.6)',
                scale: 1.1
              } : undefined}
            >
              {/* Pulse ring effect */}
              <motion.div
                className="absolute inset-0 rounded-full border-2 border-holo-cyan-400"
                animate={!isDisabled ? {
                  scale: [1, 1.2, 1],
                  opacity: [0.5, 0, 0.5]
                } : {}}
                transition={{ duration: 2, repeat: Infinity }}
              />
              
              {sending ? (
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                >
                  <Zap className="w-5 h-5 text-white" />
                </motion.div>
              ) : (
                <HoloSendIcon size={20} className="text-white" />
              )}
            </motion.button>
          </motion.div>
          </div>
        </OptimizedHolographicCard>

        {/* Helper text */}
        <p className="text-xs text-holo-cyan-400/60 text-center mt-3 select-none font-orbitron tracking-wide">
          Press <kbd className="px-2 py-1 text-xs bg-holo-cyan-500/20 border border-holo-cyan-400/30 rounded font-orbitron">Enter</kbd> to send
          <span className="mx-1">•</span>
          <kbd className="px-2 py-1 text-xs bg-holo-cyan-500/20 border border-holo-cyan-400/30 rounded font-orbitron">Shift + Enter</kbd> for a new line
        </p>
      </div>
    </motion.div>
  );
});

export const OptimizedChatInput: React.FC<OptimizedChatInputProps> = (props) => {
  const isMobile = useIsMobile();
  const { shouldReduceAnimations } = useOptimizedAnimations();

  // Use lightweight input on mobile or when animations should be reduced
  if (isMobile || shouldReduceAnimations) {
    return <LightweightChatInput {...props} />;
  }

  // Use full animated input on desktop
  return <AnimatedChatInput {...props} />;
};

export default OptimizedChatInput;