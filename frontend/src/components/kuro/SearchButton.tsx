import { memo } from 'react';
import { cn } from '@/lib/utils';
import { Globe, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface SearchButtonProps {
  active: boolean;
  loading?: boolean;
  onClick: () => void;
  disabled?: boolean;
  className?: string;
}

/**
 * SearchButton — toggles search_mode for the chat input.
 * When active, the next message will force compound research via web search.
 */
export const SearchButton = memo(function SearchButton({
  active,
  loading = false,
  onClick,
  disabled = false,
  className,
}: SearchButtonProps) {
  return (
    <Button
      type="button"
      variant="ghost"
      size="icon"
      onClick={onClick}
      disabled={disabled || loading}
      title={active ? 'Web search enabled' : 'Enable web search'}
      className={cn(
        'h-10 w-10 rounded-xl transition-all duration-200',
        active
          ? 'bg-primary/20 text-primary hover:bg-primary/30 ring-1 ring-primary/40'
          : 'hover:bg-primary/10 text-muted-foreground',
        className
      )}
    >
      {loading ? (
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : (
        <Globe className={cn('h-4 w-4', active && 'text-primary')} />
      )}
    </Button>
  );
});

export default SearchButton;
