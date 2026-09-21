import { cn } from '@/lib/utils';

interface SystemMessageProps {
  message: string;
  messageType: 'rate_limit' | 'error' | 'warning' | 'normal';
  timestamp: string;
  onRetry?: () => void;
}

/**
 * SystemMessage — a quiet inline notice (rate limit, provider error, ...).
 * No card, no icon animation. Hierarchy comes from a hairline and a label.
 */
export const SystemMessage = ({ message, messageType, timestamp, onRetry }: SystemMessageProps) => {
  const label =
    messageType === 'rate_limit'
      ? 'Paused'
      : messageType === 'error'
        ? 'Unavailable'
        : messageType === 'warning'
          ? 'Notice'
          : 'System';

  const showRetry =
    !!onRetry &&
    (messageType === 'rate_limit' || /rate limit|quota/i.test(message));

  const lines = message.split('\n').filter((l) => l.trim().length > 0);

  return (
    <div className="mx-auto w-full max-w-[760px] px-5 md:px-6">
      <div
        className={cn(
          'border-l pl-4',
          messageType === 'error' ? 'border-destructive/60' : 'border-foreground/20'
        )}
      >
        <div className="mb-1.5 flex items-center gap-3">
          <span className={cn('k-label !text-[10px]', messageType === 'error' ? '!text-destructive' : '!text-muted-foreground')}>
            {label}
          </span>
          <span className="k-label !text-[10px] !text-muted-foreground/50">
            {new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        </div>
        <div className="text-[14px] leading-relaxed text-muted-foreground">
          {lines.map((line, i) => (
            <p key={i} className={cn(i > 0 && 'mt-1')}>
              {line.replace(/\*\*/g, '').replace(/^•\s?/, '— ')}
            </p>
          ))}
        </div>
        {showRetry && (
          <button type="button" onClick={onRetry} className="k-quiet mt-3 !text-[10px] !text-foreground/80">
            Try again
          </button>
        )}
      </div>
    </div>
  );
};

export default SystemMessage;
