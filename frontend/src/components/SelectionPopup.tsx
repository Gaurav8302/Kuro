import React, { useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { Copy, Check, MessageCircleQuestion } from 'lucide-react';
import { cn } from '@/lib/utils';

interface SelectionPopupProps {
  /** Selected text */
  text: string;
  /** Anchor position (center-x of selection, top-y of selection) */
  x: number;
  y: number;
  onCopy: () => void;
  onAskKuro: () => void;
}

/**
 * A small holographic floating popup shown near the cursor when the user
 * selects text inside an assistant message. Offers "Copy" and "Ask Kuro" actions.
 */
export const SelectionPopup: React.FC<SelectionPopupProps> = ({
  text,
  x,
  y,
  onCopy,
  onAskKuro,
}) => {
  const ref = useRef<HTMLDivElement>(null);
  const [copied, setCopied] = useState(false);
  const [pos, setPos] = useState({ left: x, top: y });

  // Keep popup within viewport
  useEffect(() => {
    if (!ref.current) return;
    const el = ref.current;
    const rect = el.getBoundingClientRect();
    const pad = 8;

    let left = x - rect.width / 2;
    let top = y - rect.height - 10; // place above the selection

    // Clamp horizontal
    if (left < pad) left = pad;
    if (left + rect.width > window.innerWidth - pad) {
      left = window.innerWidth - pad - rect.width;
    }

    // If no room above, place below
    if (top < pad) {
      top = y + 24;
    }

    setPos({ left, top });
  }, [x, y]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const ta = document.createElement('textarea');
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 1200);
    onCopy();
  };

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 6, scale: 0.9, filter: 'blur(4px)' }}
      animate={{ opacity: 1, y: 0, scale: 1, filter: 'blur(0px)' }}
      exit={{ opacity: 0, y: 4, scale: 0.95 }}
      transition={{ duration: 0.2, ease: 'easeOut' }}
      className={cn(
        'fixed z-[9999] flex items-center gap-1 px-1.5 py-1 rounded-lg',
        'bg-background/80 backdrop-blur-2xl',
        'border border-holo-cyan-400/20 shadow-lg shadow-holo-cyan-500/10',
      )}
      style={{
        left: pos.left,
        top: pos.top,
      }}
      // Prevent the popup from interfering with the selection
      onMouseDown={(e) => e.preventDefault()}
    >
      {/* Subtle holographic glow behind */}
      <div className="pointer-events-none absolute inset-0 rounded-lg opacity-30 bg-[radial-gradient(circle_at_30%_50%,rgba(0,230,214,0.3),transparent_70%)]" />

      <motion.button
        type="button"
        onClick={handleCopy}
        whileHover={{ scale: 1.06 }}
        whileTap={{ scale: 0.94 }}
        className={cn(
          'relative inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium',
          'transition-colors duration-150',
          'bg-holo-cyan-500/15 hover:bg-holo-cyan-500/25 text-holo-cyan-300',
          'border border-holo-cyan-400/20 hover:border-holo-cyan-400/40'
        )}
      >
        {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
        {copied ? 'Copied' : 'Copy'}
      </motion.button>

      <motion.button
        type="button"
        onClick={onAskKuro}
        whileHover={{ scale: 1.06 }}
        whileTap={{ scale: 0.94 }}
        className={cn(
          'relative inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium',
          'transition-colors duration-150',
          'bg-holo-purple-500/15 hover:bg-holo-purple-500/25 text-holo-purple-300',
          'border border-holo-purple-400/20 hover:border-holo-purple-400/40'
        )}
      >
        <MessageCircleQuestion className="w-3.5 h-3.5" />
        Ask Kuro
      </motion.button>
    </motion.div>
  );
};

export default SelectionPopup;
