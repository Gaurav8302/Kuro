import React, { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Menu, Plus, Settings } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarImage, AvatarFallback } from '@/components/ui/avatar';
import { Message, ChatSession, User } from '@/types';
import { cn } from '@/lib/utils';
import { useIsMobile } from '@/hooks/use-mobile';
import { ThemeToggle } from '@/components/ui/theme-toggle';
import { MobileSidebar } from '@/components/MobileSidebar';
import { OptimizedMarkdown } from '@/components/OptimizedMarkdown';
import { PerformanceOptimizedBackground } from '@/components/PerformanceOptimizedBackground';

interface MobileChatProps {
  messages: Message[];
  sessions: ChatSession[];
  currentSessionId?: string;
  user?: User;
  isLoading: boolean;
  onSendMessage: (message: string) => void;
  onNewChat: () => void;
  onSelectSession: (sessionId: string) => void;
  onRenameSession: (sessionId: string, newTitle: string) => void;
  onDeleteSession: (sessionId: string) => void;
  onSignOut: () => void;
  onRetry?: () => void;
}

// Optimized message component with lazy rendering
const MessageItem = React.memo(({ 
  message, 
  index, 
  userAvatar 
}: { 
  message: Message; 
  index: number; 
  userAvatar?: string;
}) => {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';

  if (isSystem) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.3, delay: index * 0.02 }}
        className="flex justify-center mb-4"
      >
        <div className="bg-muted/60 border border-border/50 rounded-xl px-4 py-3 max-w-[90%] text-center">
          <p className="text-sm text-muted-foreground">{message.message}</p>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 15, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ 
        duration: 0.3,
        delay: index * 0.02,
        ease: "easeOut"
      }}
      className={cn(
        "flex w-full mb-4",
        isUser ? "justify-end" : "justify-start"
      )}
    >
      <div className={cn(
        "flex gap-3 max-w-[85%]",
        isUser ? "flex-row-reverse" : "flex-row"
      )}>
        {/* Avatar */}
        <Avatar className="h-8 w-8 flex-shrink-0">
          {isUser ? (
            <>
              <AvatarImage src={userAvatar} alt="You" />
              <AvatarFallback className="bg-primary text-primary-foreground text-xs">
                U
              </AvatarFallback>
            </>
          ) : (
            <>
              <AvatarImage src="/kuroai.png" alt="Kuro AI" />
              <AvatarFallback className="bg-secondary text-secondary-foreground text-xs">
                AI
              </AvatarFallback>
            </>
          )}
        </Avatar>

        {/* Message bubble */}
        <div
          className={cn(
            "px-4 py-3 rounded-2xl backdrop-blur-sm border transition-all duration-200",
            isUser
              ? "bg-primary/90 text-primary-foreground border-primary/20 rounded-br-md"
              : "bg-muted/80 text-foreground border-border/50 rounded-bl-md"
          )}
        >
          {isUser ? (
            <p className="text-sm leading-relaxed whitespace-pre-wrap break-words">
              {message.message}
            </p>
          ) : (
            <OptimizedMarkdown content={message.message} />
          )}
          
          <div className="text-xs opacity-60 mt-2">
            {new Date(message.timestamp || Date.now()).toLocaleTimeString([], { 
              hour: '2-digit', 
              minute: '2-digit' 
            })}
          </div>
        </div>
      </div>
    </motion.div>
  );
});

MessageItem.displayName = 'MessageItem';

export const MobileChat: React.FC<MobileChatProps> = ({
  messages,
  sessions,
  currentSessionId,
  user,
  isLoading,
  onSendMessage,
  onNewChat,
  onSelectSession,
  onRenameSession,
  onDeleteSession,
  onSignOut,
  onRetry
}) => {
  const [inputValue, setInputValue] = useState('');
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const isMobile = useIsMobile();

  // Optimized scroll to bottom
  const scrollToBottom = useCallback(() => {
    requestAnimationFrame(() => {
      messagesEndRef.current?.scrollIntoView({ 
        behavior: 'smooth',
        block: 'end'
      });
    });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // Handle send with performance optimizations
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
    
    // Auto-resize with max height
    const textarea = e.target;
    textarea.style.height = 'auto';
    textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
  }, []);

  const handleKeyPress = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }, [handleSend]);

  // Find current session title
  const currentSession = sessions.find(s => s.session_id === currentSessionId);
  const sessionTitle = currentSession?.title || 'New Chat';

  return (
    <div className="flex h-screen bg-background relative">
      <PerformanceOptimizedBackground variant={isMobile ? 'minimal' : 'standard'} />
      
      {/* Mobile Sidebar */}
      <MobileSidebar
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
        sessions={sessions}
        currentSessionId={currentSessionId}
        user={user}
        onNewChat={onNewChat}
        onSelectSession={onSelectSession}
        onRenameSession={onRenameSession}
        onDeleteSession={onDeleteSession}
        onSignOut={onSignOut}
      />

      {/* Main Chat Container */}
      <div className="flex-1 flex flex-col min-h-0 relative z-10">
        {/* Header */}
        <motion.header
          initial={{ y: -20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          className="flex items-center justify-between p-4 border-b border-border bg-background/95 backdrop-blur-xl"
        >
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setIsSidebarOpen(true)}
              className="h-9 w-9"
            >
              <Menu className="h-4 w-4" />
            </Button>
            <div>
              <h1 className="text-lg font-semibold truncate max-w-[200px]">
                {sessionTitle}
              </h1>
              <p className="text-xs text-muted-foreground">AI Assistant</p>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              onClick={onNewChat}
              className="h-9 w-9"
            >
              <Plus className="h-4 w-4" />
            </Button>
            <ThemeToggle />
          </div>
        </motion.header>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto">
          <div className="p-4 space-y-1 min-h-full">
            {messages.length === 0 ? (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex flex-col items-center justify-center h-full text-center py-12"
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
                <p className="text-muted-foreground max-w-sm text-sm leading-relaxed">
                  Your intelligent conversation partner. Ask questions, get help, or explore ideas together.
                </p>
              </motion.div>
            ) : (
              <>
                {messages.map((message, index) => (
                  <MessageItem
                    key={`${message.timestamp}-${index}`}
                    message={message}
                    index={index}
                    userAvatar={user?.avatar}
                  />
                ))}
                
                {/* Typing indicator */}
                <AnimatePresence>
                  {isLoading && (
                    <motion.div
                      initial={{ opacity: 0, scale: 0.8 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0, scale: 0.8 }}
                      className="flex justify-start mb-4"
                    >
                      <div className="flex gap-3">
                        <Avatar className="h-8 w-8">
                          <AvatarImage src="/kuroai.png" alt="Kuro AI" />
                          <AvatarFallback className="bg-secondary text-secondary-foreground text-xs">
                            AI
                          </AvatarFallback>
                        </Avatar>
                        <div className="bg-muted/80 backdrop-blur-sm border border-border/50 px-4 py-3 rounded-2xl rounded-bl-md">
                          <div className="flex space-x-1">
                            {[0, 1, 2].map((i) => (
                              <motion.div
                                key={i}
                                className="w-2 h-2 bg-primary rounded-full"
                                animate={{ 
                                  scale: [1, 1.2, 1], 
                                  opacity: [0.5, 1, 0.5] 
                                }}
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
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </>
            )}
            <div ref={messagesEndRef} />
          </div>
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
          
          {/* Safe area spacing for mobile */}
          <div className="h-[env(safe-area-inset-bottom,0px)]" />
        </motion.div>
      </div>
    </div>
  );
};

export default MobileChat;