import { motion } from 'framer-motion';
import { Message } from '@/types';
import { cn } from '@/lib/utils';
import { User, Copy, Check } from 'lucide-react';
import { Avatar, AvatarImage, AvatarFallback } from '@/components/ui/avatar';
import { useIsMobile } from '@/hooks/use-mobile';
import { useOptimizedAnimations } from '@/hooks/use-performance';
import { SystemMessage } from '@/components/SystemMessage';
import { MarkdownMessage } from '@/components/MarkdownMessage';
import { OptimizedHolographicCard } from '@/components/OptimizedHolographicCard';
import { HoloSparklesIcon } from '@/components/HolographicIcons';
import { useState, memo } from 'react';

interface OptimizedChatBubbleProps {
  message: Message;
  userAvatar?: string;
  onRetry?: () => void;
}

// Lightweight bubble for mobile
const LightweightChatBubble: React.FC<OptimizedChatBubbleProps> = memo(({ 
  message, 
  userAvatar, 
  onRetry 
}) => {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);

  const handleCopyFull = async () => {
    if (!message.message) return;
    try {
      await navigator.clipboard.writeText(message.message);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch (e) {
      try {
        const ta = document.createElement('textarea');
        ta.value = message.message;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
      } catch {/* noop */}
    }
  };

  // Handle system messages
  if (message.role === 'system') {
    return (
      <SystemMessage
        message={message.message}
        messageType={message.messageType || 'normal'}
        timestamp={message.timestamp || new Date().toISOString()}
        onRetry={onRetry}
      />
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-4 flex flex-col gap-2">
      {/* Avatar and name */}
      <div className={cn("flex items-center gap-2", isUser ? "justify-end" : "justify-start")}>
        <Avatar className="w-8 h-8 border border-holo-cyan-400/30">
          {isUser ? (
            <>
              <AvatarImage src={userAvatar} alt="User" />
              <AvatarFallback className="bg-gradient-to-br from-holo-blue-500 to-holo-cyan-500 text-white text-xs">
                <User className="w-3 h-3" />
              </AvatarFallback>
            </>
          ) : (
            <>
              <AvatarImage src="/kuroai.png" alt="Kuro AI" />
              <AvatarFallback className="bg-gradient-to-br from-holo-purple-500 to-holo-magenta-500 text-white text-xs">
                <HoloSparklesIcon size={12} />
              </AvatarFallback>
            </>
          )}
        </Avatar>
        <span className="text-xs font-medium text-holo-cyan-400 font-rajdhani">
          {isUser ? 'You' : 'Kuro'}
        </span>
      </div>

      {/* Message bubble */}
      <div className={cn("w-full", isUser ? "flex justify-end" : "flex justify-start")}>
        <div className={cn("max-w-[85%] w-full")}>
          <div
            className={cn(
              "px-4 py-3 rounded-xl transition-all duration-300 hover:scale-[1.01]",
              isUser 
                ? "bg-gradient-to-br from-holo-blue-500/20 to-holo-cyan-500/20 text-holo-cyan-100 border border-holo-cyan-400/30 glass-panel" 
                : "bg-gradient-to-br from-holo-purple-500/10 to-holo-magenta-500/10 text-foreground border border-holo-purple-400/20 glass-panel"
            )}
          >
            {isUser ? (
              <p className="text-sm leading-relaxed whitespace-pre-wrap text-holo-cyan-100 font-space">
                {message.message}
              </p>
            ) : (
              <MarkdownMessage content={message.message} />
            )}
          </div>
          
          {/* Copy button and timestamp */}
          <div className="flex justify-between items-center mt-1">
            <span className="text-xs text-holo-cyan-400/60 px-1 font-orbitron">
              {new Date(message.timestamp).toLocaleTimeString([], { 
                hour: '2-digit', 
                minute: '2-digit' 
              })}
            </span>
            
            <button
              type="button"
              onClick={handleCopyFull}
              className={cn(
                "inline-flex items-center gap-1 rounded-md border text-[10px] px-2 py-1 transition-all duration-300 shadow-sm backdrop-blur-sm font-orbitron hover:scale-105 active:scale-95",
                isUser
                  ? "border-holo-cyan-400/30 bg-holo-cyan-500/10 hover:bg-holo-cyan-500/20 text-holo-cyan-300"
                  : "border-holo-purple-400/30 bg-holo-purple-500/10 hover:bg-holo-purple-500/20 text-holo-purple-300"
              )}
            >
              {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
              {copied ? 'Copied' : 'Copy'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
});

// Full animated bubble for desktop
const AnimatedChatBubble: React.FC<OptimizedChatBubbleProps> = memo(({ 
  message, 
  userAvatar, 
  onRetry 
}) => {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);
  const { animationDuration } = useOptimizedAnimations();

  const handleCopyFull = async () => {
    if (!message.message) return;
    try {
      await navigator.clipboard.writeText(message.message);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch (e) {
      try {
        const ta = document.createElement('textarea');
        ta.value = message.message;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
      } catch {/* noop */}
    }
  };

  // Handle system messages
  if (message.role === 'system') {
    return (
      <SystemMessage
        message={message.message}
        messageType={message.messageType || 'normal'}
        timestamp={message.timestamp || new Date().toISOString()}
        onRetry={onRetry}
      />
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 30, scale: 0.8, filter: 'blur(10px)' }}
      animate={{ opacity: 1, y: 0, scale: 1, filter: 'blur(0px)' }}
      transition={{ duration: animationDuration, ease: 'easeOut' }}
      className="max-w-4xl mx-auto px-4 py-4 flex items-start gap-3"
    >
      {/* Avatar */}
      <div className="flex-shrink-0">
        <motion.div
          whileHover={{ scale: 1.1, rotate: 5 }}
          transition={{ duration: animationDuration }}
        >
          <Avatar className="w-10 h-10 border-2 border-holo-cyan-400/50 shadow-holo-glow">
            {isUser ? (
              <>
                <AvatarImage src={userAvatar} alt="User" />
                <AvatarFallback className="bg-gradient-to-br from-holo-blue-500 to-holo-cyan-500 text-white">
                  <User className="w-4 h-4" />
                </AvatarFallback>
              </>
            ) : (
              <>
                <AvatarImage src="/kuroai.png" alt="Kuro AI" />
                <AvatarFallback className="bg-gradient-to-br from-holo-purple-500 to-holo-magenta-500 text-white">
                  <HoloSparklesIcon size={16} />
                </AvatarFallback>
              </>
            )}
          </Avatar>
        </motion.div>
      </div>

      {/* Message Bubble */}
      <div className="flex flex-col gap-1 max-w-[70%]">
        <div className="w-full">
          <OptimizedHolographicCard
            variant={isUser ? 'glow' : 'default'}
            hover={true}
            scanLine={!isUser}
            className="group w-full"
          >
            <motion.div
              className={cn(
                "px-4 py-3 relative",
                isUser 
                  ? "bg-gradient-to-br from-holo-blue-500/20 to-holo-cyan-500/20 text-holo-cyan-100 border-holo-cyan-400/30" 
                  : "bg-gradient-to-br from-holo-purple-500/10 to-holo-magenta-500/10 text-foreground border-holo-purple-400/20"
              )}
              whileHover={{ scale: 1.01 }}
              transition={{ duration: animationDuration }}
            >
              {isUser ? (
                <p className="text-sm leading-relaxed whitespace-pre-wrap text-holo-cyan-100 font-space">
                  {message.message}
                </p>
              ) : (
                <MarkdownMessage content={message.message} />
              )}

              {/* Holographic decorative elements */}
              {isUser && (
                <motion.div 
                  className="absolute -bottom-1 -right-1 w-3 h-3 bg-holo-cyan-400 rounded-full shadow-holo-glow"
                  animate={{ scale: [1, 1.2, 1], opacity: [0.6, 1, 0.6] }}
                  transition={{ duration: 2, repeat: Infinity }}
                />
              )}
              {!isUser && (
                <motion.div 
                  className="absolute -bottom-1 -left-1 w-3 h-3 bg-holo-purple-400 rounded-full shadow-holo-purple"
                  animate={{ scale: [1, 1.2, 1], opacity: [0.6, 1, 0.6] }}
                  transition={{ duration: 2, repeat: Infinity, delay: 0.5 }}
                />
              )}
            </motion.div>
          </OptimizedHolographicCard>
          
          {/* Copy button */}
          <div className="flex mt-1 justify-end">
            <motion.button
              type="button"
              onClick={handleCopyFull}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className={cn(
                "inline-flex items-center gap-1 rounded-md border text-[10px] px-2 py-1 transition-all duration-300 shadow-sm backdrop-blur-sm font-orbitron",
                isUser
                  ? "border-holo-cyan-400/30 bg-holo-cyan-500/10 hover:bg-holo-cyan-500/20 text-holo-cyan-300 hover:shadow-holo-glow"
                  : "border-holo-purple-400/30 bg-holo-purple-500/10 hover:bg-holo-purple-500/20 text-holo-purple-300 hover:shadow-holo-purple hover:text-holo-purple-200"
              )}
            >
              {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
              {copied ? 'Copied' : 'Copy'}
            </motion.button>
          </div>
        </div>
        
        {/* Timestamp */}
        <span className="text-xs text-holo-cyan-400/60 px-1 font-orbitron">
          {new Date(message.timestamp).toLocaleTimeString([], { 
            hour: '2-digit', 
            minute: '2-digit' 
          })}
        </span>
      </div>
    </motion.div>
  );
});

export const OptimizedChatBubble: React.FC<OptimizedChatBubbleProps> = (props) => {
  const isMobile = useIsMobile();
  const { shouldReduceAnimations } = useOptimizedAnimations();

  // Use lightweight bubble on mobile or when animations should be reduced
  if (isMobile || shouldReduceAnimations) {
    return <LightweightChatBubble {...props} />;
  }

  // Use full animated bubble on desktop
  return <AnimatedChatBubble {...props} />;
};

export default OptimizedChatBubble;