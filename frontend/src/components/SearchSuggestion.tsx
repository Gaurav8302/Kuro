import { memo } from 'react';
import { motion } from 'framer-motion';
import { Globe, ArrowRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

interface SearchSuggestionProps {
  onSearchClick: () => void;
  className?: string;
}

/**
 * SearchSuggestion — inline banner shown after an AI response that suggests
 * the user should enable browser search for real-time information.
 */
export const SearchSuggestion = memo(function SearchSuggestion({
  onSearchClick,
  className,
}: SearchSuggestionProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.2 }}
      className={cn(
        'max-w-4xl mx-auto px-4 py-2',
        className
      )}
    >
      <div className={cn(
        'flex items-center gap-3 px-4 py-3 rounded-xl',
        'bg-primary/5 border border-primary/20',
        'transition-all duration-200 hover:bg-primary/10 hover:border-primary/30'
      )}>
        <div className="flex items-center justify-center w-8 h-8 rounded-full bg-primary/15">
          <Globe className="w-4 h-4 text-primary" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm text-foreground/80">
            Want the latest information? Try a web search.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={onSearchClick}
          className={cn(
            'flex items-center gap-1.5 rounded-lg',
            'border-primary/30 text-primary hover:bg-primary/10',
            'transition-all duration-200'
          )}
        >
          <Globe className="w-3.5 h-3.5" />
          Search Web
          <ArrowRight className="w-3 h-3" />
        </Button>
      </div>
    </motion.div>
  );
});

export default SearchSuggestion;
