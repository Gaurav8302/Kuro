import { motion } from 'framer-motion';
import { Message } from '@/types';
import { cn } from '@/lib/utils';
import { Bot, User } from 'lucide-react';
import { Avatar, AvatarImage, AvatarFallback } from '@/components/ui/avatar';

interface ChatBubbleProps {
  message: Message;
  userAvatar?: string;
}

const TypingIndicator = () => (
  <div className="flex space-x-1 items-center p-3">
    <div className="w-2 h-2 bg-primary rounded-full animate-typing"></div>
    <div className="w-2 h-2 bg-primary rounded-full animate-typing" style={{ animationDelay: '0.2s' }}></div>
    <div className="w-2 h-2 bg-primary rounded-full animate-typing" style={{ animationDelay: '0.4s' }}></div>
  </div>
);

export const ChatBubble = ({ message, userAvatar }: ChatBubbleProps) => {
  const isUser = message.role === 'user';

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={cn(
        "flex items-start gap-3 max-w-4xl mx-auto px-4 py-3",
        isUser ? "flex-row-reverse" : "flex-row"
      )}
    >
      {/* Avatar */}
      <div className={cn(
        "flex-shrink-0",
        isUser ? "animate-slide-in-right" : "animate-slide-in-left"
      )}>
        <Avatar className="w-8 h-8 border-2 border-white shadow-lg">
          {isUser ? (
            <>
              <AvatarImage src={userAvatar} alt="User" />
              <AvatarFallback className="bg-gradient-secondary text-white">
                <User className="w-4 h-4" />
              </AvatarFallback>
            </>
          ) : (
            <AvatarFallback className="bg-gradient-primary text-white">
              <Bot className="w-4 h-4" />
            </AvatarFallback>
          )}
        </Avatar>
      </div>

      {/* Message Bubble */}
      <div className={cn(
        "flex flex-col gap-1 max-w-[70%]",
        isUser ? "items-end" : "items-start"
      )}>
        <div className={cn(
          "px-4 py-3 rounded-2xl shadow-lg relative transition-smooth",
          isUser 
            ? "bg-gradient-primary text-white rounded-tr-md" 
            : "bg-card border border-border rounded-tl-md",
          // ...existing code...
        )}>
          <p className={cn(
            "text-sm leading-relaxed",
            isUser ? "text-white" : "text-foreground"
          )}>
            {message.message}
          </p>
          
          {/* Fun decorative element */}
          {isUser && (
            <div className="absolute -bottom-1 -right-1 w-3 h-3 bg-gradient-secondary rounded-full opacity-60" />
          )}
          {!isUser && (
            <div className="absolute -bottom-1 -left-1 w-3 h-3 bg-gradient-accent rounded-full opacity-60" />
          )}
        </div>
        
        {/* Timestamp */}
        <span className="text-xs text-muted-foreground px-1">
          {new Date(message.timestamp).toLocaleTimeString([], { 
            hour: '2-digit', 
            minute: '2-digit' 
          })}
        </span>
      </div>
    </motion.div>
  );
};