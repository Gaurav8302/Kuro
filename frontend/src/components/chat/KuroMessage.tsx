import React, { memo, useState } from 'react';
import { Copy, Check } from 'lucide-react';
import { Message } from '@/types';
import { cn } from '@/lib/utils';
import { MarkdownMessage } from '@/components/MarkdownMessage';
import { SystemMessage } from '@/components/SystemMessage';

interface KuroMessageProps {
  message: Message;
  onRetry?: () => void;
}

function timeOf(ts?: string) {
  if (!ts) return '';
  const d = new Date(ts);
  return isNaN(d.getTime()) ? '' : d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

async function copyText(text: string) {
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
}

/**
 * KuroMessage — a turn in the conversation.
 *
 *   Kuro   left, no container; a small mono label above the text.
 *   You    right, a quiet tinted block.
 *   System quiet inline notice.
 *
 * The pending state renders the same node the reply will fill, so completion
 * never remounts anything.
 */
export const KuroMessage = memo<KuroMessageProps>(
  function KuroMessage({ message, onRetry }) {
    const [copied, setCopied] = useState(false);
    const isUser = message.role === 'user';

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

    const onCopy = async () => {
      if (!message.message) return;
      await copyText(message.message);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1400);
    };

    if (isUser) {
      return (
        <div className="group mx-auto flex w-full max-w-[760px] justify-end px-5 md:px-6">
          <div className="max-w-[82%] md:max-w-[70%]">
            <div className="rounded-md bg-foreground/[0.05] px-4 py-3 text-[15px] leading-relaxed text-foreground/95 whitespace-pre-wrap">
              {message.message}
            </div>
            <div className="mt-1.5 flex items-center justify-end gap-3 pr-1">
              <span className="k-label !text-[10px] !text-muted-foreground/50">{timeOf(message.timestamp)}</span>
              <button
                type="button"
                onClick={onCopy}
                className="k-quiet !text-[10px] opacity-0 transition-opacity group-hover:opacity-100 focus-visible:opacity-100"
                aria-label="Copy message"
              >
                {copied ? 'Copied' : 'Copy'}
              </button>
            </div>
          </div>
        </div>
      );
    }

    return (
      <div className="group mx-auto w-full max-w-[760px] px-5 md:px-6">
        <div className="mb-2 flex items-center gap-3">
          <span className="k-label !text-[10px] !text-primary/80">Kuro</span>
          {!message.pending && (
            <span className="k-label !text-[10px] !text-muted-foreground/50">{timeOf(message.timestamp)}</span>
          )}
        </div>

        {message.pending ? (
          // Reserved geometry while Kuro generates. The Core carries the
          // thinking state; here we only hold the line.
          <div className="flex h-6 items-center" aria-live="polite" aria-label="Kuro is thinking">
            <span className="k-thinking-dot" />
          </div>
        ) : (
          <>
            <div className="text-[15px]">
              <MarkdownMessage content={message.message} />
            </div>
            <div className="mt-2 flex items-center gap-3">
              <button
                type="button"
                onClick={onCopy}
                className={cn(
                  'k-quiet inline-flex items-center gap-1.5 !text-[10px] opacity-0 transition-opacity',
                  'group-hover:opacity-100 focus-visible:opacity-100'
                )}
                aria-label="Copy reply"
              >
                {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                {copied ? 'Copied' : 'Copy'}
              </button>
              {message.model && (
                <span className="k-label !text-[10px] !text-muted-foreground/35 opacity-0 transition-opacity group-hover:opacity-100">
                  {message.model}
                  {typeof message.latency_ms === 'number' ? ` · ${(message.latency_ms / 1000).toFixed(1)}s` : ''}
                </span>
              )}
            </div>
          </>
        )}
      </div>
    );
  },
  (a, b) =>
    a.message.id === b.message.id &&
    a.message.message === b.message.message &&
    a.message.pending === b.message.pending &&
    a.message.role === b.message.role &&
    a.message.timestamp === b.message.timestamp &&
    a.onRetry === b.onRetry
);

export default KuroMessage;
