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
    <div className={cn(
      "max-w-4xl mx-auto px-4 py-4 flex items-start gap-3",
      isUser ? "flex-row-reverse" : "flex-row"
    )}>
      {/* Avatar */}
      <Avatar className="w-8 h-8 border border-holo-cyan-400/30 flex-shrink-0">
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

      {/* Message bubble */}
      <div className={cn(
        "flex flex-col gap-1 max-w-[85%]",
        isUser ? "items-end" : "items-start"
      )}>
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
        <div className={cn(
          "flex items-center gap-2",
          isUser ? "flex-row-reverse" : "flex-row"
        )}>
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
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: animationDuration, ease: [0.25, 0.1, 0.25, 1] }}
      className={cn(
        "max-w-4xl mx-auto px-4 py-4 flex items-start gap-3",
        isUser ? "flex-row-reverse" : "flex-row"
      )}
    >
      {/* Avatar */}
      <div className="flex-shrink-0">
        <div className="transform-gpu hover:scale-110 transition-transform duration-200">
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
            )}n          </Avatar>
        </div>
      </div>

      {/* Message Bubble */}
      <div className={cn(
        "flex flex-col gap-1 max-w-[70%]",
        isUser ? "items-end" : "items-start"
      )}>
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

              {/* Holographic decorative elements - simplified CSS animations */}
              {isUser && (
                <div 
                  className="absolute -bottom-1 -right-1 w-3 h-3 bg-holo-cyan-400 rounded-full shadow-holo-glow animate-pulse"
                />
              )}
              {!isUser && (
                <div 
                  className="absolute -bottom-1 -left-1 w-3 h-3 bg-holo-purple-400 rounded-full shadow-holo-purple animate-pulse"
                  style={{ animationDelay: '0.5s' }}
                />
              )}
            </motion.div>
          </OptimizedHolographicCard>
          
          {/* Copy button */}
          <div className="flex mt-1 justify-end">
            <button
              type="button"
              onClick={handleCopyFull}
              className={cn(
                "inline-flex items-center gap-1 rounded-md border text-[10px] px-2 py-1 shadow-sm backdrop-blur-sm font-orbitron",
                "transform-gpu transition-all duration-150 hover:scale-105 active:scale-95",
                isUser
                  ? "border-holo-cyan-400/30 bg-holo-cyan-500/10 hover:bg-holo-cyan-500/20 text-holo-cyan-300 hover:shadow-holo-glow"
                  : "border-holo-purple-400/30 bg-holo-purple-500/10 hover:bg-holo-purple-500/20 text-holo-purple-300 hover:shadow-holo-purple hover:text-holo-purple-200"
              )}
            >
              {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
              {copied ? 'Copied' : 'Copy'}
            </button>
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

AnimatedChatBubble.displayName = 'AnimatedChatBubble';

export const OptimizedChatBubble: React.FC<OptimizedChatBubbleProps> = memo((props) => {
  const isMobile = useIsMobile();
  const { shouldReduceAnimations } = useOptimizedAnimations();

  // Use lightweight bubble on mobile or when animations should be reduced
  if (isMobile || shouldReduceAnimations) {
    return <LightweightChatBubble {...props} />;
  }

  // Use full animated bubble on desktop
  return <AnimatedChatBubble {...props} />;
});

OptimizedChatBubble.displayName = 'OptimizedChatBubble';

export default OptimizedChatBubble;