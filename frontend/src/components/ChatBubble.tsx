import { motion } from 'framer-motion';
import { Message } from '@/types';
import { cn } from '@/lib/utils';
import { Bot, User, Copy, Check, Zap } from 'lucide-react';
import { Avatar, AvatarImage, AvatarFallback } from '@/components/ui/avatar';
import { useIsMobile } from '@/hooks/use-mobile';
import { SystemMessage } from '@/components/SystemMessage';
import { MarkdownMessage } from '@/components/MarkdownMessage';
import { HolographicCard } from '@/components/HolographicCard';
import { HoloSparklesIcon } from '@/components/HolographicIcons';

interface ChatBubbleProps {
  message: Message;
  userAvatar?: string;
  onRetry?: () => void;
}

const TypingIndicator = () => (
  <div className="flex space-x-2 items-center p-4">
    <div className="w-3 h-3 bg-holo-cyan-400 rounded-full animate-typing-dots shadow-holo-glow"></div>
    <div className="w-3 h-3 bg-holo-blue-400 rounded-full animate-typing-dots shadow-holo-blue" style={{ animationDelay: '0.2s' }}></div>
    <div className="w-3 h-3 bg-holo-purple-400 rounded-full animate-typing-dots shadow-holo-purple" style={{ animationDelay: '0.4s' }}></div>
    <span className="text-xs text-holo-cyan-400 font-orbitron ml-2">PROCESSING...</span>
  </div>
);

import { useState } from 'react';

export const ChatBubble = ({ message, userAvatar, onRetry }: ChatBubbleProps) => {
  const isUser = message.role === 'user';
  const isMobile = useIsMobile();
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

  // Handle system messages (rate limits, errors, etc.)
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
      transition={{ duration: 0.5, ease: 'easeOut' }}
      className={cn(
        "max-w-4xl mx-auto px-4 py-4",
        isMobile ? "flex flex-col gap-2" : "flex items-start gap-3",
        !isMobile && (isUser ? "flex-row-reverse" : "flex-row")
      )}
    >
      {/* Avatar - Mobile: Top, Desktop: Side */}
      <div className={cn(
        "flex items-center gap-2",
        isMobile ? (isUser ? "justify-end" : "justify-start") : "flex-shrink-0",
        !isMobile && (isUser ? "animate-fade-in-up" : "animate-slide-in-holo")
      )}>
        <motion.div
          whileHover={{ scale: 1.1, rotate: 5 }}
          transition={{ duration: 0.2 }}
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
        
        {/* Name label for mobile */}
        {isMobile && (
          <span className="text-sm font-medium text-holo-cyan-400 font-rajdhani">
            {isUser ? 'You' : 'Kuro'}
          </span>
        )}
      </div>

      {/* Message Bubble */}
      <div className={cn(
        "flex flex-col gap-1",
        isMobile ? "w-full" : "max-w-[70%]",
        !isMobile && (isUser ? "items-end" : "items-start")
      )}>
        <div className="w-full">
          <HolographicCard
            variant={isUser ? 'glow' : 'default'}
            hover={true}
            scanLine={!isUser}
            className={cn(
              "group w-full",
              isMobile ? "max-w-[85%]" : "w-full",
              isMobile ? (isUser ? "ml-auto mr-0" : "mr-auto ml-0") : ""
            )}
          >
            <motion.div
              className={cn(
                "px-4 py-3 relative",
                isUser 
                  ? "bg-gradient-to-br from-holo-blue-500/20 to-holo-cyan-500/20 text-holo-cyan-100 border-holo-cyan-400/30" 
                  : "bg-gradient-to-br from-holo-purple-500/10 to-holo-magenta-500/10 text-foreground border-holo-purple-400/20"
              )}
              whileHover={{ scale: 1.01 }}
              transition={{ duration: 0.2 }}
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
          </HolographicCard>
          
            {/* Copy button BELOW bubble aligned right (ChatGPT style) */}
            <div className={cn(
              "flex mt-1",
              isUser ? "justify-end" : "justify-end"
            )}>
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
                aria-label={isUser ? "Copy your message" : "Copy full response"}
              >
                {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                {copied ? 'Copied' : 'Copy'}
              </motion.button>
            </div>
        </div>
        
        {/* Timestamp */}
        <span className={cn(
          "text-xs text-holo-cyan-400/60 px-1 font-orbitron",
          isMobile && (isUser ? "text-right" : "text-left")
        )}>
          {new Date(message.timestamp).toLocaleTimeString([], { 
            hour: '2-digit', 
            minute: '2-digit' 
          })}
        </span>
      </div>
    </motion.div>
  );
};