import { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Send, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';
import { useIsMobile } from '@/hooks/use-mobile';

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  placeholder?: string;
  showTypingIndicator?: boolean;
  sending?: boolean; // AI is responding
}

export const ChatInput = ({ 
  onSendMessage, 
  placeholder = "Ask me anything... ✨",
  sending = false
}: ChatInputProps) => {
  const [message, setMessage] = useState('');
  const [isFocused, setIsFocused] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const isMobile = useIsMobile();

  const handleSend = () => {
    if (message.trim() && !sending) {
      onSendMessage(message.trim());
      setMessage('');
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
        // Keep focus so mobile keyboard stays open
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

  const handleFocus = () => {
    setIsFocused(true);
  };

  const handleBlur = () => {
    setIsFocused(false);
  };

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [message]);

  // Initial focus (desktop only to avoid unexpected keyboard pop on mobile first load)
  useEffect(() => {
    if (!isMobile && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [isMobile]);

  return (
    <motion.div
      ref={containerRef}
      className={cn(
        "border-t backdrop-blur-sm bg-gradient-to-b from-background/80 to-background",
        // Simple sticky positioning for all devices
        "sticky bottom-0 z-10"
      )}
      initial={{ y: 0, opacity: 0 }}
      animate={{ 
        y: 0, 
        opacity: 1,
  scale: sending ? 0.98 : 1
      }}
      transition={{ 
        duration: 0.3,
        ease: "easeOut"
      }}
      data-typing={sending ? "true" : "false"}
    >
      <div className={cn(
        "max-w-4xl mx-auto p-4",
        isMobile && "px-3 pb-[calc(env(safe-area-inset-bottom)+0.75rem)]" // Better mobile spacing & safe area
      )}>
        <div className={cn(
          "relative flex items-end gap-3 p-3 rounded-xl border bg-card transition-all duration-300",
          isFocused ? "border-primary shadow-glow" : "border-border",
          sending && "opacity-70"
        )}>
          
          {/* Fun sparkle decoration */}
          {isFocused && (
            <motion.div
              className="absolute -top-2 -right-2"
              initial={{ scale: 0, rotate: 0 }}
              animate={{ scale: 1, rotate: 360 }}
              transition={{ duration: 0.5 }}
            >
              <Sparkles className="w-4 h-4 text-primary" />
            </motion.div>
          )}

          {/* Message input */}
          <div className="flex-1">
            <Textarea
              ref={textareaRef}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={handleKeyPress}
              onFocus={handleFocus}
              onBlur={handleBlur}
              placeholder={placeholder}
              className={cn(
                "min-h-[20px] max-h-32 resize-none border-none bg-transparent",
                "focus-visible:ring-0 focus-visible:ring-offset-0 p-0",
                "placeholder:text-muted-foreground/70 text-sm"
              )}
              rows={1}
            />
          </div>

          {/* Send button */}
          <motion.div
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            <Button
              onClick={handleSend}
              disabled={!message.trim() || sending}
              variant="chat"
              size="icon"
              className="rounded-full shadow-accent"
            >
              <Send className="w-4 h-4" />
            </Button>
          </motion.div>
        </div>

        {/* Helper text */}
        <p className="text-xs text-muted-foreground text-center mt-2 select-none">
          Press <kbd className="px-1 py-0.5 text-xs bg-muted rounded">Enter</kbd> to send
          <span className="mx-1">•</span>
          <kbd className="px-1 py-0.5 text-xs bg-muted rounded">Shift + Enter</kbd> = newline
        </p>
      </div>
    </motion.div>
  );
};