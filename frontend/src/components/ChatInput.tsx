import { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Send, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';
import { useIsMobile } from '@/hooks/use-mobile';

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
  showTypingIndicator?: boolean;
}

export const ChatInput = ({ 
  onSendMessage, 
  disabled = false, 
  placeholder = "Ask me anything... ✨" 
}: ChatInputProps) => {
  const [message, setMessage] = useState('');
  const [isFocused, setIsFocused] = useState(false);
  const [keyboardVisible, setKeyboardVisible] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const isMobile = useIsMobile();

  const handleSend = () => {
    if (message.trim() && !disabled) {
      onSendMessage(message.trim());
      setMessage('');
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
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

  // Handle viewport changes for mobile keyboard
  useEffect(() => {
    if (!isMobile) {
      // On desktop, always ensure keyboard is not visible
      setKeyboardVisible(false);
      return;
    }
    
    const handleVisualViewportChange = () => {
      if ('visualViewport' in window) {
        const viewport = window.visualViewport!;
        const viewportHeight = viewport.height;
        const windowHeight = window.innerHeight;
        const heightDifference = windowHeight - viewportHeight;
        
        // More sensitive keyboard detection - if viewport is reduced by more than 150px
        const isKeyboardOpen = heightDifference > 150;
        
        console.log('Viewport change:', { viewportHeight, windowHeight, heightDifference, isKeyboardOpen });
        setKeyboardVisible(isKeyboardOpen);
      } else {
        // Fallback: only set keyboard visible if input is focused
        setKeyboardVisible(isFocused);
      }
    };

    // Also listen for focus/blur events as fallback
    const handleInputFocus = () => {
      setTimeout(() => {
        if ('visualViewport' in window) {
          handleVisualViewportChange();
        } else {
          // Fallback: assume keyboard is open when input is focused on mobile
          setKeyboardVisible(true);
        }
      }, 300);
    };

    const handleInputBlur = () => {
      setTimeout(() => {
        // When input loses focus, keyboard should be closing
        setKeyboardVisible(false);
      }, 300);
    };

    // Initial check - keyboard should be closed initially
    setKeyboardVisible(false);
    
    if ('visualViewport' in window) {
      window.visualViewport?.addEventListener('resize', handleVisualViewportChange);
    }

    // Add focus/blur listeners as fallback
    if (textareaRef.current) {
      textareaRef.current.addEventListener('focus', handleInputFocus);
      textareaRef.current.addEventListener('blur', handleInputBlur);
    }

    return () => {
      if ('visualViewport' in window) {
        window.visualViewport?.removeEventListener('resize', handleVisualViewportChange);
      }
      if (textareaRef.current) {
        textareaRef.current.removeEventListener('focus', handleInputFocus);
        textareaRef.current.removeEventListener('blur', handleInputBlur);
      }
    };
  }, [isMobile, isFocused]);

  return (
    <motion.div
      ref={containerRef}
      className={cn(
        "border-t backdrop-blur-sm",
        "bg-gradient-to-b from-background/80 to-background",
        // Desktop: always sticky at bottom (normal behavior)
        // Mobile: only fixed when keyboard is actually open, otherwise normal flow
        !isMobile 
          ? "sticky bottom-0" 
          : keyboardVisible 
            ? "fixed bottom-0 left-0 right-0 z-50" 
            : "", // No positioning classes for mobile when keyboard is closed
        isMobile && keyboardVisible && "pb-safe" // Only add safe area when keyboard is open
      )}
      initial={{ y: 0, opacity: 0 }}
      animate={{ 
        y: 0, 
        opacity: 1,
        scale: disabled ? 0.98 : 1
      }}
      transition={{ 
        duration: 0.3,
        ease: "easeOut"
      }}
      data-typing={disabled ? "true" : "false"}
      data-keyboard-visible={keyboardVisible ? "true" : "false"}
      data-is-mobile={isMobile ? "true" : "false"}
    >
      <div className="max-w-4xl mx-auto p-4">
        <div className={cn(
          "relative flex items-end gap-3 p-3 rounded-xl border bg-card transition-all duration-300",
          isFocused ? "border-primary shadow-glow" : "border-border",
          disabled && "opacity-50"
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
              disabled={disabled}
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
              disabled={!message.trim() || disabled}
              variant="chat"
              size="icon"
              className="rounded-full shadow-accent"
            >
              <Send className="w-4 h-4" />
            </Button>
          </motion.div>
        </div>

        {/* Helper text */}
        <p className="text-xs text-muted-foreground text-center mt-2">
          Press <kbd className="px-1 py-0.5 text-xs bg-muted rounded">Enter</kbd> to send, 
          <kbd className="px-1 py-0.5 text-xs bg-muted rounded ml-1">Shift + Enter</kbd> for new line
        </p>
      </div>
    </motion.div>
  );
};