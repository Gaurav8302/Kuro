import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Send } from 'lucide-react';
import { cn } from '@/lib/utils';
import { MarkdownMessage } from '@/components/MarkdownMessage';
import { HoloSparklesIcon } from '@/components/HolographicIcons';
import { inlineQuery } from '@/lib/api';

interface InlineMessage {
  id: number;
  role: 'user' | 'assistant';
  content: string;
}

interface InlineChatPanelProps {
  /** The text the user originally selected */
  selectedText: string;
  /** Surrounding context from the message */
  context: string;
  /** Called when the panel is closed — parent should clear state */
  onClose: () => void;
}

/* ─── Holographic typing dots (matches main chat style) ─── */
const HoloTypingDots = () => (
  <div className="flex items-center gap-2 py-1">
    <div className="flex space-x-1.5 items-center">
      <div className="w-2 h-2 bg-holo-cyan-400 rounded-full animate-typing-dots shadow-holo-glow" />
      <div className="w-2 h-2 bg-holo-blue-400 rounded-full animate-typing-dots shadow-holo-blue" style={{ animationDelay: '0.2s' }} />
      <div className="w-2 h-2 bg-holo-purple-400 rounded-full animate-typing-dots shadow-holo-purple" style={{ animationDelay: '0.4s' }} />
    </div>
    <span className="text-[10px] text-holo-cyan-400/70 font-orbitron tracking-wider">PROCESSING</span>
  </div>
);

/* ─── Tiny floating particles (lightweight version of KuroIntro) ─── */
const MiniParticles = React.memo(() => {
  const particles = useMemo(() =>
    Array.from({ length: 12 }).map((_, i) => ({
      id: i,
      left: Math.random() * 100,
      top: Math.random() * 100,
      size: 1.5 + Math.random() * 3,
      delay: Math.random() * 6,
      duration: 6 + Math.random() * 8,
      opacity: 0.15 + Math.random() * 0.25,
      color: ['#00e6d6', '#8c1aff', '#1a8cff', '#ff1ab1'][i % 4],
    })),
  []);

  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden rounded-xl">
      {particles.map((p) => (
        <motion.span
          key={p.id}
          className="absolute rounded-full blur-[0.5px]"
          style={{
            left: `${p.left}%`,
            top: `${p.top}%`,
            width: p.size,
            height: p.size,
            backgroundColor: p.color,
            boxShadow: `0 0 ${p.size * 2}px ${p.color}`,
          }}
          animate={{
            y: [0, -20, 0],
            x: [0, 8, 0],
            scale: [1, 1.3, 1],
            opacity: [p.opacity, p.opacity * 1.6, p.opacity],
          }}
          transition={{
            duration: p.duration,
            repeat: Infinity,
            delay: p.delay,
            ease: 'easeInOut',
          }}
        />
      ))}
    </div>
  );
});
MiniParticles.displayName = 'MiniParticles';

/**
 * InlineChatPanel — holographic mini-chat window for ephemeral
 * side-questions about selected text. Matches the KuroIntro landing
 * page aesthetic. All state is frontend-only; nothing is stored in
 * the database or memory systems.
 */
export const InlineChatPanel: React.FC<InlineChatPanelProps> = ({
  selectedText,
  context,
  onClose,
}) => {
  const [messages, setMessages] = useState<InlineMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const msgIdRef = useRef(0);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  // Auto-focus the input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // Scroll to bottom when messages change
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  // Close on Escape key
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [onClose]);

  const handleSend = useCallback(async () => {
    const question = input.trim();
    if (!question || isLoading) return;

    setInput('');
    const userMsgId = ++msgIdRef.current;
    setMessages((prev) => [...prev, { id: userMsgId, role: 'user', content: question }]);
    setIsLoading(true);

    try {
      const { answer } = await inlineQuery(selectedText, context, question);
      const aiMsgId = ++msgIdRef.current;
      setMessages((prev) => [...prev, { id: aiMsgId, role: 'assistant', content: answer }]);
    } catch {
      const errMsgId = ++msgIdRef.current;
      setMessages((prev) => [
        ...prev,
        { id: errMsgId, role: 'assistant', content: 'Sorry, I couldn\'t generate an answer right now. Please try again.' },
      ]);
    } finally {
      setIsLoading(false);
    }
  }, [input, isLoading, selectedText, context]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Truncate displayed selected text
  const displayText =
    selectedText.length > 120 ? selectedText.slice(0, 117) + '…' : selectedText;

  return (
    <motion.div
      ref={panelRef}
      initial={{ opacity: 0, y: 30, scale: 0.92, filter: 'blur(8px)' }}
      animate={{ opacity: 1, y: 0, scale: 1, filter: 'blur(0px)' }}
      exit={{ opacity: 0, y: 20, scale: 0.95, filter: 'blur(4px)' }}
      transition={{ duration: 0.4, ease: [0.25, 0.8, 0.25, 1] }}
      className={cn(
        'fixed z-[9998] flex flex-col',
        'w-[380px] max-w-[92vw] h-[440px] max-h-[70vh]',
        'rounded-xl overflow-hidden',
        'border border-holo-cyan-400/20 shadow-2xl',
        'bg-background/80 backdrop-blur-2xl',
        'bottom-24 right-4 md:right-8',
      )}
    >
      {/* Holographic background layers (like KuroIntro but subtle) */}
      <div className="pointer-events-none absolute inset-0 opacity-40">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_30%,rgba(0,230,214,0.25),transparent_60%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_80%_70%,rgba(140,26,255,0.2),transparent_65%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_10%,rgba(26,140,255,0.15),transparent_70%)]" />
      </div>

      {/* Holographic grid (subtle) */}
      <div className="pointer-events-none absolute inset-0 opacity-[0.06]" style={{
        background: `
          linear-gradient(rgba(0,230,214,0.4) 1px, transparent 1px),
          linear-gradient(90deg, rgba(0,230,214,0.4) 1px, transparent 1px)
        `,
        backgroundSize: '32px 32px',
      }} />

      {/* Floating particles */}
      <MiniParticles />

      {/* Scan line (KuroIntro-style) */}
      <motion.div
        className="pointer-events-none absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-holo-cyan-400/60 to-transparent"
        animate={{ y: [0, 440] }}
        transition={{ duration: 5, repeat: Infinity, ease: 'linear' }}
      />

      {/* ─── Header ─── */}
      <div className="relative flex items-center justify-between px-4 py-3 border-b border-holo-cyan-400/15">
        <div className="flex items-center gap-2.5 min-w-0">
          {/* Holographic Kuro avatar (matches ChatBubble AI avatar) */}
          <motion.div
            className="relative flex-shrink-0"
            whileHover={{ scale: 1.1, rotate: 5 }}
            transition={{ duration: 0.2 }}
          >
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-holo-purple-500 to-holo-magenta-500 flex items-center justify-center border border-holo-purple-400/40 shadow-holo-purple">
              <HoloSparklesIcon size={14} />
            </div>
            {/* Pulse ring */}
            <motion.div
              className="absolute -inset-0.5 rounded-full border border-holo-cyan-400/40"
              animate={{ scale: [1, 1.3, 1], opacity: [0.6, 0, 0.6] }}
              transition={{ duration: 2.5, repeat: Infinity }}
            />
          </motion.div>
          <div className="flex flex-col min-w-0">
            <span className="text-sm font-semibold text-holo-cyan-100 font-orbitron tracking-wide truncate">
              Ask Kuro
            </span>
            <span className="text-[10px] text-holo-cyan-400/50 font-space">
              Ephemeral &middot; Not saved
            </span>
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          className={cn(
            'w-7 h-7 rounded-md flex items-center justify-center flex-shrink-0',
            'transition-all duration-150 hover:scale-110 active:scale-95',
            'bg-white/5 hover:bg-white/10 text-muted-foreground hover:text-foreground',
            'border border-white/10 hover:border-holo-cyan-400/30'
          )}
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* ─── Selected text context badge ─── */}
      <div className="relative px-4 py-2 border-b border-holo-purple-400/10">
        <p className="text-[10px] text-muted-foreground/70 mb-1 font-orbitron tracking-wider uppercase">Selected text</p>
        <p className="text-xs text-holo-cyan-300 bg-holo-cyan-500/8 border border-holo-cyan-400/15 rounded-lg px-2.5 py-1.5 line-clamp-2 font-space leading-relaxed">
          &ldquo;{displayText}&rdquo;
        </p>
      </div>

      {/* ─── Messages area ─── */}
      <div
        ref={scrollRef}
        className="relative flex-1 overflow-y-auto px-4 py-3 space-y-3 min-h-0"
      >
        {/* Empty state with holographic bot indicator */}
        {messages.length === 0 && !isLoading && (
          <div className="flex flex-col items-center justify-center pt-8 gap-3">
            <motion.div
              animate={{
                scale: [1, 1.08, 1],
                opacity: [0.6, 1, 0.6],
              }}
              transition={{ duration: 3, repeat: Infinity }}
              className="w-10 h-10 rounded-full bg-gradient-to-br from-holo-cyan-500/20 to-holo-purple-500/20 border border-holo-cyan-400/20 flex items-center justify-center"
            >
              <HoloSparklesIcon size={18} />
            </motion.div>
            <p className="text-xs text-muted-foreground/60 text-center font-space">
              Ask a question about the selected text
            </p>
          </div>
        )}

        <AnimatePresence initial={false}>
          {messages.map((msg) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 12, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={{ duration: 0.3, ease: 'easeOut' }}
              className={cn(
                'max-w-[90%]',
                msg.role === 'user' ? 'ml-auto' : 'mr-auto'
              )}
            >
              <div
                className={cn(
                  'px-3 py-2 rounded-lg text-sm',
                  msg.role === 'user'
                    ? 'bg-gradient-to-br from-holo-blue-500/20 to-holo-cyan-500/15 text-holo-cyan-100 border border-holo-cyan-400/20'
                    : 'bg-gradient-to-br from-holo-purple-500/10 to-holo-magenta-500/5 text-foreground border border-holo-purple-400/15'
                )}
              >
                {msg.role === 'assistant' ? (
                  <MarkdownMessage content={msg.content} />
                ) : (
                  <p className="whitespace-pre-wrap font-space">{msg.content}</p>
                )}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {isLoading && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="mr-auto px-3 py-2 rounded-lg bg-holo-purple-500/10 border border-holo-purple-400/15"
          >
            <HoloTypingDots />
          </motion.div>
        )}
      </div>

      {/* ─── Input area ─── */}
      <div className="relative px-3 py-2.5 border-t border-holo-cyan-400/15">
        <div className="flex items-center gap-2">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about this text..."
            disabled={isLoading}
            className={cn(
              'flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground/50 font-space',
              'outline-none border-none ring-0 focus:ring-0',
              'disabled:opacity-50'
            )}
          />
          <motion.button
            type="button"
            onClick={handleSend}
            disabled={isLoading || !input.trim()}
            whileHover={{ scale: 1.08 }}
            whileTap={{ scale: 0.92 }}
            className={cn(
              'w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0',
              'transition-colors duration-150',
              'bg-gradient-to-br from-holo-purple-500/25 to-holo-cyan-500/15',
              'hover:from-holo-purple-500/35 hover:to-holo-cyan-500/25',
              'text-holo-purple-300 hover:text-holo-cyan-300',
              'border border-holo-purple-400/25 hover:border-holo-cyan-400/40',
              'shadow-sm hover:shadow-holo-glow',
              'disabled:opacity-40 disabled:pointer-events-none'
            )}
          >
            <Send className="w-3.5 h-3.5" />
          </motion.button>
        </div>
      </div>
    </motion.div>
  );
};

export default InlineChatPanel;
