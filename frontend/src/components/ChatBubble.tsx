import { motion } from 'framer-motion';
import { Message } from '@/types';
import { cn } from '@/lib/utils';
import { Bot, User, Copy, Check } from 'lucide-react';
import { Avatar, AvatarImage, AvatarFallback } from '@/components/ui/avatar';
import { useIsMobile } from '@/hooks/use-mobile';
import { SystemMessage } from '@/components/SystemMessage';
import { MarkdownMessage } from '@/components/MarkdownMessage';

interface ChatBubbleProps {
  message: Message;
  userAvatar?: string;
  onRetry?: () => void;
}

const TypingIndicator = () => (
  <div className="flex space-x-1 items-center p-3">
    <div className="w-2 h-2 bg-primary rounded-full animate-typing"></div>
    <div className="w-2 h-2 bg-primary rounded-full animate-typing" style={{ animationDelay: '0.2s' }}></div>
    <div className="w-2 h-2 bg-primary rounded-full animate-typing" style={{ animationDelay: '0.4s' }}></div>
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
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={cn(
        "max-w-4xl mx-auto px-4 py-3",
        isMobile ? "flex flex-col gap-2" : "flex items-start gap-3",
        !isMobile && (isUser ? "flex-row-reverse" : "flex-row")
      )}
    >
      {/* Avatar - Mobile: Top, Desktop: Side */}
      <div className={cn(
        "flex items-center gap-2",
        isMobile ? (isUser ? "justify-end" : "justify-start") : "flex-shrink-0",
        !isMobile && (isUser ? "animate-slide-in-right" : "animate-slide-in-left")
      )}>
        <Avatar className="w-8 h-8 border-2 border-white shadow-lg">
          {isUser ? (
            <>
              <AvatarImage src={userAvatar} alt="User" />
              <AvatarFallback className="bg-gradient-to-br from-purple-600 to-purple-700 text-white">
                <User className="w-4 h-4" />
              </AvatarFallback>
            </>
          ) : (
            <>
              <AvatarImage src="/kuroai.png" alt="Kuro AI" />
              <AvatarFallback className="bg-gradient-to-br from-purple-600 to-purple-700 text-white">
                <Bot className="w-4 h-4" />
              </AvatarFallback>
            </>
          )}
        </Avatar>
        
        {/* Name label for mobile */}
        {isMobile && (
          <span className="text-sm font-medium text-foreground">
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
        <div className="relative inline-block group w-full">
          <div className={cn(
            "px-4 py-3 rounded-2xl shadow-lg transition-smooth",
            isUser 
              ? "bg-gradient-to-br from-purple-600 to-purple-700 text-white" 
              : "bg-card border border-border text-foreground",
            isMobile ? (isUser ? "ml-auto mr-0 rounded-tr-md" : "mr-auto ml-0 rounded-tl-md") : 
                       (isUser ? "rounded-tr-md" : "rounded-tl-md"),
            isMobile ? "max-w-[85%]" : "w-full"
          )}>
            {isUser ? (
              <p className={cn(
                "text-sm leading-relaxed whitespace-pre-wrap",
                isUser ? "text-white" : "text-foreground"
              )}>
                {message.message}
              </p>
            ) : (
              <MarkdownMessage content={message.message} />
            )}

            {/* Fun decorative element */}
            {isUser && (
              <div className="absolute -bottom-1 -right-1 w-3 h-3 bg-gradient-to-br from-purple-500 to-purple-600 rounded-full opacity-60" />
            )}
            {!isUser && (
              <div className="absolute -bottom-1 -left-1 w-3 h-3 bg-gradient-to-br from-purple-400 to-purple-500 rounded-full opacity-60" />
            )}
          </div>
          {/* External copy button (outside bubble, right side) */}
          <button
            type="button"
            onClick={handleCopyFull}
            className={cn(
              "absolute top-2 -right-2 translate-x-full inline-flex items-center gap-1 rounded-md border text-[10px] px-2 py-1 transition-colors shadow-sm backdrop-blur-sm",
              isUser 
                ? "border-white/20 bg-white/10 hover:bg-white/20 text-white" 
                : "border-border/50 bg-background/70 hover:bg-background text-muted-foreground hover:text-foreground"
            )}
            aria-label={isUser ? "Copy your message" : "Copy full response"}
          >
            {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
            {copied ? 'Copied' : 'Copy'}
          </button>
        </div>
        
        {/* Timestamp */}
        <span className={cn(
          "text-xs text-muted-foreground px-1",
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