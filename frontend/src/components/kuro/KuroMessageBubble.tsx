import { memo, useState } from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { Message } from '@/types';
import { Copy, Check, User, RefreshCw, AlertCircle } from 'lucide-react';
import { Avatar, AvatarImage, AvatarFallback } from '@/components/ui/avatar';
import { KuroAvatar } from './KuroAvatar';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface KuroMessageBubbleProps {
  message: Message;
  userAvatar?: string;
  onRetry?: () => void;
}

/**
 * KuroMessageBubble - Professional chat message bubble
 * Clean flat cards, no speech-bubble cartoon styling
 */
export const KuroMessageBubble = memo(function KuroMessageBubble({
  message,
  userAvatar,
  onRetry,
}: KuroMessageBubbleProps) {
  const [copied, setCopied] = useState(false);
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';
  const isError = message.messageType === 'error' || message.messageType === 'rate_limit';

  const handleCopy = async () => {
    if (!message.message) return;
    try {
      await navigator.clipboard.writeText(message.message);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for older browsers
      const textarea = document.createElement('textarea');
      textarea.value = message.message;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  // System/Error message styling
  if (isSystem) {
    return (
      <div
        className={cn(
          'flex items-start gap-3 p-4 rounded-xl',
          'glass border',
          isError 
            ? 'border-red-500/30 bg-red-500/5' 
            : 'border-amber-500/30 bg-amber-500/5'
        )}
      >
        <div className={cn(
          'w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0',
          isError ? 'bg-red-500/20' : 'bg-amber-500/20'
        )}>
          <AlertCircle className={cn(
            'w-4 h-4',
            isError ? 'text-red-400' : 'text-amber-400'
          )} />
        </div>
        <div className="flex-1 min-w-0">
          <p className={cn(
            'text-sm leading-relaxed',
            isError ? 'text-red-300' : 'text-amber-300'
          )}>
            {message.message}
          </p>
          {onRetry && (
            <button
              onClick={onRetry}
              className={cn(
                'mt-3 inline-flex items-center gap-2 px-3 py-1.5 text-xs',
                'rounded-md transition-colors',
                isError 
                  ? 'bg-red-500/20 text-red-300 hover:bg-red-500/30'
                  : 'bg-amber-500/20 text-amber-300 hover:bg-amber-500/30'
              )}
            >
              <RefreshCw className="w-3 h-3" />
              Retry
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        'flex gap-3',
        isUser ? 'flex-row-reverse' : 'flex-row'
      )}
    >
      {/* Avatar */}
      {isUser ? (
        <Avatar className={cn(
          'w-8 h-8 flex-shrink-0',
          'border border-white/10'
        )}>
          <AvatarImage src={userAvatar} alt="You" />
          <AvatarFallback className="bg-primary/20 text-primary">
            <User className="w-4 h-4" />
          </AvatarFallback>
        </Avatar>
      ) : (
        <KuroAvatar size={32} animated={false} showGlow={false} className="flex-shrink-0" />
      )}

      {/* Message content */}
      <div
        className={cn(
          'group relative max-w-[85%] md:max-w-[75%]',
          'rounded-xl px-4 py-3',
          isUser
            ? 'bg-primary text-primary-foreground'
            : 'glass border border-white/10 text-foreground'
        )}
      >
        {/* Message text */}
        <div className={cn(
          'text-sm leading-relaxed',
          isUser ? 'text-white' : 'prose prose-invert prose-sm max-w-none'
        )}>
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.message}</p>
          ) : (
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                // Custom styling for markdown elements
                p: ({ children }) => <p className="mb-3 last:mb-0">{children}</p>,
                code: ({ className, children, ...props }) => {
                  const isInline = !className;
                  return isInline ? (
                    <code 
                      className="px-1.5 py-0.5 rounded bg-white/10 text-primary text-xs font-mono"
                      {...props}
                    >
                      {children}
                    </code>
                  ) : (
                    <code 
                      className={cn(
                        'block p-3 rounded-lg bg-black/20 text-xs font-mono overflow-x-auto',
                        className
                      )}
                      {...props}
                    >
                      {children}
                    </code>
                  );
                },
                pre: ({ children }) => (
                  <pre className="my-3 overflow-x-auto">{children}</pre>
                ),
                ul: ({ children }) => (
                  <ul className="list-disc list-inside mb-3 space-y-1">{children}</ul>
                ),
                ol: ({ children }) => (
                  <ol className="list-decimal list-inside mb-3 space-y-1">{children}</ol>
                ),
                a: ({ href, children }) => (
                  <a 
                    href={href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary hover:underline"
                  >
                    {children}
                  </a>
                ),
              }}
            >
              {message.message}
            </ReactMarkdown>
          )}
        </div>

        {/* Copy button - only for assistant messages */}
        {!isUser && (
          <motion.button
            onClick={handleCopy}
            className={cn(
              'absolute -bottom-2 right-2 p-1.5 rounded-md',
              'glass border border-white/10',
              'opacity-0 group-hover:opacity-100 transition-opacity',
              'text-muted-foreground hover:text-foreground'
            )}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            {copied ? (
              <Check className="w-3 h-3 text-green-400" />
            ) : (
              <Copy className="w-3 h-3" />
            )}
          </motion.button>
        )}
      </div>
    </div>
  );
});

export default KuroMessageBubble;
