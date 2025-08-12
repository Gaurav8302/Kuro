import React, { useRef, useEffect, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, User, Bot, Maximize2, Minimize2, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';

export type ChatMessage = {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
  isStreaming?: boolean;
};

export type ChatWindowProps = {
  title: string;
  messages: ChatMessage[];
  onSendMessage?: (message: string) => void;
  onClose?: () => void;
  onToggleFloating?: () => void;
  isFloating?: boolean;
  isLoading?: boolean;
  className?: string;
};

export default function ChatWindow({ 
  title, 
  messages, 
  onSendMessage,
  onClose,
  onToggleFloating,
  isFloating = false,
  isLoading = false,
  className = ''
}: ChatWindowProps) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const handleSend = useCallback(() => {
    if (input.trim() && onSendMessage && !isLoading) {
      onSendMessage(input.trim());
      setInput('');
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  }, [input, onSendMessage, isLoading]);

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
  }, [input]);

  const formatTime = (timestamp: number) => {
    return new Date(timestamp).toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  return (
    <motion.div 
      className={cn(
        "flex flex-col h-full bg-card border rounded-lg overflow-hidden",
        className
      )}
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ duration: 0.2 }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b bg-muted/50">
        <div className="flex items-center gap-2">
          <Bot className="w-4 h-4 text-primary" />
          <h3 className="font-medium text-sm truncate">{title}</h3>
        </div>
        
        <div className="flex items-center gap-1">
          {onToggleFloating && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onToggleFloating}
              className="h-7 w-7 p-0"
              title={isFloating ? "Dock window" : "Open floating window"}
            >
              {isFloating ? (
                <Minimize2 className="w-3 h-3" />
              ) : (
                <Maximize2 className="w-3 h-3" />
              )}
            </Button>
          )}
          
          {onClose && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              className="h-7 w-7 p-0 text-muted-foreground hover:text-destructive"
              title="Close chat"
            >
              <X className="w-3 h-3" />
            </Button>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <AnimatePresence initial={false}>
          {messages.map((message) => (
            <motion.div
              key={message.id}
              initial={{ opacity: 0, y: 10, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -10, scale: 0.95 }}
              transition={{ duration: 0.2 }}
              className={cn(
                "flex gap-3",
                message.role === 'user' ? 'justify-end' : 'justify-start'
              )}
            >
              {message.role === 'assistant' && (
                <div className="w-7 h-7 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                  <Bot className="w-3 h-3 text-primary" />
                </div>
              )}
              
              <div
                className={cn(
                  "max-w-[70%] rounded-lg px-3 py-2 text-sm",
                  message.role === 'user'
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-muted',
                  message.isStreaming && 'animate-pulse'
                )}
              >
                <div className="whitespace-pre-wrap break-words">
                  {message.content}
                </div>
                <div className={cn(
                  "text-xs mt-1",
                  message.role === 'user' 
                    ? 'text-primary-foreground/70' 
                    : 'text-muted-foreground'
                )}>
                  {formatTime(message.timestamp)}
                </div>
              </div>

              {message.role === 'user' && (
                <div className="w-7 h-7 rounded-full bg-primary flex items-center justify-center flex-shrink-0">
                  <User className="w-3 h-3 text-primary-foreground" />
                </div>
              )}
            </motion.div>
          ))}
        </AnimatePresence>
        
        {isLoading && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex gap-3"
          >
            <div className="w-7 h-7 rounded-full bg-primary/10 flex items-center justify-center">
              <Bot className="w-3 h-3 text-primary" />
            </div>
            <div className="bg-muted rounded-lg px-3 py-2">
              <div className="flex space-x-1">
                <div className="w-2 h-2 rounded-full bg-muted-foreground/40 animate-bounce [animation-delay:-0.3s]" />
                <div className="w-2 h-2 rounded-full bg-muted-foreground/40 animate-bounce [animation-delay:-0.15s]" />
                <div className="w-2 h-2 rounded-full bg-muted-foreground/40 animate-bounce" />
              </div>
            </div>
          </motion.div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      {onSendMessage && (
        <div className="border-t p-4">
          <div className="flex gap-2">
            <Textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyPress}
              placeholder="Type your message..."
              className="flex-1 min-h-[40px] max-h-[120px] resize-none"
              disabled={isLoading}
            />
            <Button
              onClick={handleSend}
              disabled={!input.trim() || isLoading}
              size="sm"
              className="px-3"
            >
              <Send className="w-4 h-4" />
            </Button>
          </div>
        </div>
      )}
    </motion.div>
  );
}
