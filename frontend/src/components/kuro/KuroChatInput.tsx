import { memo, useState, useRef, KeyboardEvent } from 'react';
import { cn } from '@/lib/utils';
import { Send, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { SearchButton } from '@/components/kuro/SearchButton';

interface KuroChatInputProps {
  onSendMessage: (message: string, searchMode?: boolean) => void;
  disabled?: boolean;
  sending?: boolean;
  placeholder?: string;
  className?: string;
}

/**
 * KuroChatInput - Professional chat input component
 * Fixed at bottom with glass effect and smooth animations.
 * Includes a search toggle button for manual web search.
 */
export const KuroChatInput = memo(function KuroChatInput({
  onSendMessage,
  disabled = false,
  sending = false,
  placeholder = 'Message Kuro...',
  className,
}: KuroChatInputProps) {
  const [message, setMessage] = useState('');
  const [isFocused, setIsFocused] = useState(false);
  const [searchMode, setSearchMode] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = () => {
    const trimmed = message.trim();
    if (!trimmed || disabled || sending) return;

    onSendMessage(trimmed, searchMode);
    setMessage('');
    // Reset search mode after sending
    setSearchMode(false);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const isDisabled = disabled || sending;
  const canSend = message.trim().length > 0 && !isDisabled;

  return (
    <div className={cn('p-4 border-t border-border/50 glass', className)}>
      <form onSubmit={(e) => { e.preventDefault(); handleSubmit(); }} className="max-w-3xl mx-auto">
        <div className={cn(
          'relative rounded-2xl overflow-hidden',
          'bg-secondary/50 border',
          'transition-all duration-200',
          isFocused
            ? 'border-primary/50 shadow-lg shadow-primary/10'
            : 'border-border/50'
        )}>
          <input
            ref={inputRef}
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            placeholder={searchMode ? 'Search the web...' : placeholder}
            disabled={isDisabled}
            className={cn(
              'w-full bg-transparent',
              'px-5 py-4 pr-28',
              'text-sm text-foreground',
              'placeholder:text-muted-foreground',
              'focus:outline-none',
              'disabled:opacity-50 disabled:cursor-not-allowed'
            )}
          />
          <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
            <SearchButton
              active={searchMode}
              loading={false}
              onClick={() => setSearchMode((prev) => !prev)}
              disabled={isDisabled}
            />
            <Button
              type="submit"
              variant="ghost"
              size="icon"
              className={cn(
                'h-10 w-10 rounded-xl',
                'transition-all duration-200',
                canSend
                  ? 'bg-gradient-to-r from-primary to-accent text-primary-foreground hover:opacity-90'
                  : 'hover:bg-primary/10'
              )}
              disabled={!canSend}
            >
              {sending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className={cn('h-4 w-4', !canSend && 'text-muted-foreground')} />
              )}
            </Button>
          </div>
        </div>
        <p className="text-xs text-center text-muted-foreground/70 mt-3">
          Kuro can make mistakes. Consider checking important information.
        </p>
      </form>
    </div>
  );
});

export default KuroChatInput;
