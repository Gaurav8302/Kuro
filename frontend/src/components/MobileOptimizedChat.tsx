import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Menu, X, Plus, Settings, Moon, Sun } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useIsMobile } from '@/hooks/use-mobile';
import { useTheme } from '@/components/ui/theme-provider';
import { Message } from '@/types';

interface MobileOptimizedChatProps {
  messages: Message[];
  onSendMessage: (message: string) => void;
  isLoading: boolean;
  className?: string;
}

// Lightweight message bubble component optimized for mobile
const MessageBubble = React.memo(({ message, index }: { message: Message; index: number }) => {
  const isUser = message.role === 'user';
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ 
        duration: 0.3,
        delay: index * 0.05,
        ease: "easeOut"
      }}
      className={cn(
        "flex w-full mb-3",
        isUser ? "justify-end" : "justify-start"
      )}
    >
      <div
        className={cn(
          "max-w-[85%] px-4 py-3 rounded-2xl text-sm leading-relaxed",
          "backdrop-blur-sm border transition-all duration-200",
          isUser
            ? "bg-primary/90 text-primary-foreground border-primary/20 rounded-br-md"
            : "bg-muted/80 text-foreground border-border/50 rounded-bl-md"
        )}
      >
        <p className="whitespace-pre-wrap break-words">{message.message}</p>
        <div className="text-xs opacity-60 mt-1">
          {new Date(message.timestamp || Date.now()).toLocaleTimeString([], { 
            hour: '2-digit', 
            minute: '2-digit' 
          })}
        </div>
      </div>
    </motion.div>
  );
});

MessageBubble.displayName = 'MessageBubble';

// Optimized typing indicator
const TypingIndicator = React.memo(() => (
  <motion.div
    initial={{ opacity: 0, scale: 0.8 }}
    animate={{ opacity: 1, scale: 1 }}
    exit={{ opacity: 0, scale: 0.8 }}
    className="flex justify-start mb-3"
  >
    <div className="bg-muted/80 backdrop-blur-sm border border-border/50 px-4 py-3 rounded-2xl rounded-bl-md">
      <div className="flex space-x-1">
        {[0, 1, 2].map((i) => (
          <motion.div
            key={i}
            className="w-2 h-2 bg-primary rounded-full"
            animate={{ scale: [1, 1.2, 1], opacity: [0.5, 1, 0.5] }}
            transition={{
              duration: 1,
              repeat: Infinity,
              delay: i * 0.2,
              ease: "easeInOut"
            }}
          />
        ))}
      </div>
    </div>
  </motion.div>
));

TypingIndicator.displayName = 'TypingIndicator';

export const MobileOptimizedChat: React.FC<MobileOptimizedChatProps> = ({
  messages,
  onSendMessage,
  isLoading,
  className
}) => {
  const [inputValue, setInputValue] = useState('');
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const isMobile = useIsMobile();
  const { theme, setTheme } = useTheme();

  // Auto-scroll to bottom with performance optimization
  const scrollToBottom = useCallback(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ 
        behavior: 'smooth',
        block: 'end'
      });
    }
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // Handle send with optimizations
  const handleSend = useCallback(() => {
    const trimmed = inputValue.trim();
    if (trimmed && !isLoading) {
      onSendMessage(trimmed);
      setInputValue('');
      
      // Reset textarea height
      if (inputRef.current) {
        inputRef.current.style.height = 'auto';
      }
    }
  }, [inputValue, isLoading, onSendMessage]);

  // Auto-resize textarea
  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputValue(e.target.value);
    
    // Auto-resize
    const textarea = e.target;
    textarea.style.height = 'auto';
    textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
  }, []);

  // Keyboard handling
  const handleKeyPress = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }, [handleSend]);

  // Memoized messages for performance
  const renderedMessages = useMemo(() => 
    messages.map((message, index) => (
      <MessageBubble key={`${message.timestamp}-${index}`} message={message} index={index} />
    )),
    [messages]
  );

  return (
    <div className={cn("flex h-screen bg-background", className)}>
      {/* Mobile Sidebar Overlay */}
      <AnimatePresence>
        {isMobile && isSidebarOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40"
              onClick={() => setIsSidebarOpen(false)}
            />
            <motion.div
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ type: "spring", damping: 25, stiffness: 200 }}
              className="fixed left-0 top-0 h-full w-80 bg-background/95 backdrop-blur-xl border-r border-border z-50"
            >
              <div className="p-4 border-b border-border">
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold">Chat History</h2>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => setIsSidebarOpen(false)}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              <div className="p-4">
                <Button className="w-full mb-4">
                  <Plus className="h-4 w-4 mr-2" />
                  New Chat
                </Button>
                {/* Session list would go here */}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Desktop Sidebar */}
      {!isMobile && (
        <motion.div
          initial={{ x: -20, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          className="w-80 bg-background/95 backdrop-blur-xl border-r border-border"
        >
          <div className="p-4 border-b border-border">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">Kuro AI</h2>
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
                >
                  {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
                </Button>
                <Button variant="ghost" size="icon">
                  <Settings className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>
          <div className="p-4">
            <Button className="w-full mb-4">
              <Plus className="h-4 w-4 mr-2" />
              New Chat
            </Button>
            {/* Session list would go here */}
          </div>
        </motion.div>
      )}

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-h-0">
        {/* Mobile Header */}
        {isMobile && (
          <motion.header
            initial={{ y: -20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            className="flex items-center justify-between p-4 border-b border-border bg-background/95 backdrop-blur-xl"
          >
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setIsSidebarOpen(true)}
            >
              <Menu className="h-5 w-5" />
            </Button>
            <h1 className="text-lg font-semibold">Kuro AI</h1>
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
              >
                {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
              </Button>
              <Button variant="ghost" size="icon">
                <Settings className="h-4 w-4" />
              </Button>
            </div>
          </motion.header>
        )}

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-4 space-y-1">
          {messages.length === 0 ? (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex flex-col items-center justify-center h-full text-center"
            >
              <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mb-4">
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 8, repeat: Infinity, ease: "linear" }}
                >
                  <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full" />
                </motion.div>
              </div>
              <h3 className="text-xl font-semibold mb-2">Welcome to Kuro AI</h3>
              <p className="text-muted-foreground max-w-sm">
                Start a conversation with your AI assistant. Ask questions, get help, or just chat!
              </p>
            </motion.div>
          ) : (
            <>
              {renderedMessages}
              {isLoading && <TypingIndicator />}
            </>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <motion.div
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          className="p-4 border-t border-border bg-background/95 backdrop-blur-xl"
        >
          <div className="flex items-end gap-3 max-w-4xl mx-auto">
            <div className="flex-1 relative">
              <textarea
                ref={inputRef}
                value={inputValue}
                onChange={handleInputChange}
                onKeyDown={handleKeyPress}
                placeholder="Type your message..."
                className={cn(
                  "w-full min-h-[44px] max-h-[120px] px-4 py-3 pr-12",
                  "bg-muted/50 border border-border rounded-2xl",
                  "resize-none outline-none focus:ring-2 focus:ring-primary/50",
                  "placeholder:text-muted-foreground text-sm leading-relaxed",
                  "transition-all duration-200"
                )}
                rows={1}
                disabled={isLoading}
              />
              <motion.button
                onClick={handleSend}
                disabled={!inputValue.trim() || isLoading}
                className={cn(
                  "absolute right-2 bottom-2 w-8 h-8 rounded-full",
                  "bg-primary text-primary-foreground",
                  "flex items-center justify-center",
                  "disabled:opacity-50 disabled:cursor-not-allowed",
                  "transition-all duration-200"
                )}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                {isLoading ? (
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                  >
                    <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full" />
                  </motion.div>
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </motion.button>
            </div>
          </div>
          
          {/* Mobile keyboard spacing */}
          {isMobile && (
            <div className="h-[env(keyboard-inset-height,0px)]" />
          )}
        </motion.div>
      </div>
    </div>
  );
};

export default MobileOptimizedChat;