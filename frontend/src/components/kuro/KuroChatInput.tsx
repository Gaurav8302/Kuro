import { memo, useState, useRef, KeyboardEvent } from 'react';
import { cn } from '@/lib/utils';
import { Send, Loader2, Sparkles, X, ChevronDown } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { SearchButton } from '@/components/kuro/SearchButton';
import { ChatSkill } from '@/hooks/use-chat-panel';

const SKILLS: Array<{ id: ChatSkill; name: string }> = [
  { id: 'auto', name: 'Auto' },
  { id: 'code', name: 'Write Code' },
  { id: 'explain', name: 'Explain Concepts' },
  { id: 'creative', name: 'Creative Writing' },
  { id: 'problem', name: 'Problem Solving' },
  { id: 'web', name: 'Web Research' },
];

const SKILL_LABELS: Record<ChatSkill, string> = {
  auto: 'Auto',
  code: 'Write Code',
  explain: 'Explain Concepts',
  creative: 'Creative Writing',
  problem: 'Problem Solving',
  web: 'Web Research',
};

interface KuroChatInputProps {
  onSendMessage: (message: string, searchMode?: boolean, skill?: ChatSkill) => void;
  selectedSkill: ChatSkill;
  onSkillChange: (skill: ChatSkill) => void;
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
  selectedSkill,
  onSkillChange,
  disabled = false,
  sending = false,
  placeholder = 'Message Kuro...',
  className,
}: KuroChatInputProps) {
  const [message, setMessage] = useState('');
  const [isFocused, setIsFocused] = useState(false);
  const [searchMode, setSearchMode] = useState(false);
  const [showSkills, setShowSkills] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = () => {
    const trimmed = message.trim();
    if (!trimmed || disabled || sending) return;

    let finalSkill = selectedSkill;
    let finalMessage = trimmed;

    const slashMatch = trimmed.match(/^\/(auto|code|explain|creative|problem|web)\b/i);
    if (slashMatch) {
      finalSkill = slashMatch[1].toLowerCase() as ChatSkill;
      onSkillChange(finalSkill);
      finalMessage = trimmed.replace(/^\/(auto|code|explain|creative|problem|web)\b\s*/i, '').trim();
      if (!finalMessage) {
        setMessage('');
        return;
      }
    }

    onSendMessage(finalMessage, searchMode, finalSkill);
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
        <div className="flex items-center justify-between mb-2 px-1">
          <div className="inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-3 py-1 text-xs text-foreground">
            <Sparkles className="h-3 w-3 text-primary" />
            <span>{SKILL_LABELS[selectedSkill]}</span>
            {selectedSkill !== 'auto' && (
              <button
                type="button"
                onClick={() => onSkillChange('auto')}
                className="ml-1 text-muted-foreground hover:text-foreground transition-colors"
                aria-label="Reset skill to auto"
              >
                <X className="h-3 w-3" />
              </button>
            )}
          </div>
        </div>

        <div className={cn(
          'relative rounded-2xl overflow-visible',
          'bg-secondary/50 border',
          'transition-all duration-200',
          isFocused
            ? 'border-primary/50 shadow-lg shadow-primary/10'
            : 'border-border/50'
        )}>
          {showSkills && (
            <div className="absolute bottom-14 left-2 z-20 w-56 rounded-xl border border-border/70 bg-background/95 p-2 shadow-xl backdrop-blur">
              <p className="px-2 py-1 text-xs text-muted-foreground">Select Skill</p>
              {SKILLS.map((skill) => (
                <button
                  type="button"
                  key={skill.id}
                  onClick={() => {
                    onSkillChange(skill.id);
                    setShowSkills(false);
                  }}
                  className={cn(
                    'w-full rounded-md px-3 py-2 text-left text-sm transition-colors',
                    selectedSkill === skill.id
                      ? 'bg-primary/20 text-foreground'
                      : 'hover:bg-secondary text-muted-foreground hover:text-foreground'
                  )}
                >
                  {skill.name}
                </button>
              ))}
            </div>
          )}

          <div className="flex items-center gap-2 p-2">
            <button
              type="button"
              onClick={() => setShowSkills((prev) => !prev)}
              className="inline-flex h-10 items-center gap-2 rounded-lg border border-border/70 bg-background/40 px-3 text-sm text-foreground transition-colors hover:bg-secondary/60"
              aria-expanded={showSkills}
              aria-label="Open skill selector"
            >
              <Sparkles className="h-4 w-4 text-primary" />
              <span>Skills</span>
              <ChevronDown className="h-3 w-3 text-muted-foreground" />
            </button>

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
                'min-w-0 flex-1 bg-transparent px-2 py-3',
                'text-sm text-foreground',
                'placeholder:text-muted-foreground',
                'focus:outline-none',
                'disabled:opacity-50 disabled:cursor-not-allowed'
              )}
            />

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
