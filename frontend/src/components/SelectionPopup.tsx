import React, { useEffect, useRef, useState } from 'react';
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
 * A small floating popup shown near the cursor when the user selects text
 * inside an assistant message. Offers "Copy" and "Ask Kuro" actions.
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
    let top = y - rect.height - 8; // place above the selection

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
    <div
      ref={ref}
      className={cn(
        'fixed z-[9999] flex items-center gap-1 px-1.5 py-1 rounded-lg',
        'glass border border-white/15 shadow-lg backdrop-blur-xl',
        'animate-fade-in-up'
      )}
      style={{
        left: pos.left,
        top: pos.top,
      }}
      // Prevent the popup from interfering with the selection
      onMouseDown={(e) => e.preventDefault()}
    >
      <button
        type="button"
        onClick={handleCopy}
        className={cn(
          'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium',
          'transition-all duration-150 hover:scale-105 active:scale-95',
          'bg-holo-cyan-500/15 hover:bg-holo-cyan-500/25 text-holo-cyan-300',
          'border border-holo-cyan-400/20 hover:border-holo-cyan-400/40'
        )}
      >
        {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
        {copied ? 'Copied' : 'Copy'}
      </button>

      <button
        type="button"
        onClick={onAskKuro}
        className={cn(
          'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium',
          'transition-all duration-150 hover:scale-105 active:scale-95',
          'bg-holo-purple-500/15 hover:bg-holo-purple-500/25 text-holo-purple-300',
          'border border-holo-purple-400/20 hover:border-holo-purple-400/40'
        )}
      >
        <MessageCircleQuestion className="w-3.5 h-3.5" />
        Ask Kuro
      </button>
    </div>
  );
};

export default SelectionPopup;
