import { memo, useEffect, useRef, useState, KeyboardEvent } from 'react';
import { ArrowUp } from 'lucide-react';
import { AnimatePresence, motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { ChatSkill } from '@/hooks/use-chat-panel';
import { DUR, EASE } from '@/experience/motion';

const SKILLS: Array<{ id: ChatSkill; name: string }> = [
  { id: 'auto', name: 'Auto' },
  { id: 'code', name: 'Code' },
  { id: 'explain', name: 'Explain' },
  { id: 'creative', name: 'Creative' },
  { id: 'problem', name: 'Problem solving' },
];

const SKILL_NAME: Record<ChatSkill, string> = Object.fromEntries(SKILLS.map((s) => [s.id, s.name])) as Record<
  ChatSkill,
  string
>;

interface KuroChatInputProps {
  onSendMessage: (message: string, searchMode?: boolean, skill?: ChatSkill) => void;
  selectedSkill: ChatSkill;
  onSkillChange: (skill: ChatSkill) => void;
  disabled?: boolean;
  sending?: boolean;
  placeholder?: string;
  className?: string;
  reducedMotion?: boolean;
}

const MAX_HEIGHT = 168;

/**
 * KuroChatInput — one hairline, one field, two quiet modifiers, one action.
 *
 * The field grows with what is typed (up to ~6 lines) and never resizes on
 * its own: completion of a reply does not touch it.
 */
export const KuroChatInput = memo(function KuroChatInput({
  onSendMessage,
  selectedSkill,
  onSkillChange,
  disabled = false,
  sending = false,
  placeholder = 'Message Kuro',
  className,
  reducedMotion = false,
}: KuroChatInputProps) {
  const [message, setMessage] = useState('');
  const [searchMode, setSearchMode] = useState(false);
  const [showSkills, setShowSkills] = useState(false);
  const ref = useRef<HTMLTextAreaElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  // Auto-size the field to its content.
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = '0px';
    el.style.height = Math.min(el.scrollHeight, MAX_HEIGHT) + 'px';
    el.style.overflowY = el.scrollHeight > MAX_HEIGHT ? 'auto' : 'hidden';
  }, [message]);

  // Close the skill list on outside click / escape.
  useEffect(() => {
    if (!showSkills) return;
    const onDown = (e: PointerEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setShowSkills(false);
    };
    const onKey = (e: globalThis.KeyboardEvent) => {
      if (e.key === 'Escape') setShowSkills(false);
    };
    window.addEventListener('pointerdown', onDown);
    window.addEventListener('keydown', onKey);
    return () => {
      window.removeEventListener('pointerdown', onDown);
      window.removeEventListener('keydown', onKey);
    };
  }, [showSkills]);

  const submit = () => {
    const trimmed = message.trim();
    // Typing stays possible while Kuro thinks; sending waits for the reply.
    if (!trimmed || disabled || sending) return;

    let finalSkill = selectedSkill;
    let finalMessage = trimmed;
    const slash = trimmed.match(/^\/(auto|code|explain|creative|problem)\b/i);
    if (slash) {
      finalSkill = slash[1].toLowerCase() as ChatSkill;
      onSkillChange(finalSkill);
      finalMessage = trimmed.replace(/^\/(auto|code|explain|creative|problem)\b\s*/i, '').trim();
      if (!finalMessage) {
        setMessage('');
        return;
      }
    }

    onSendMessage(finalMessage, searchMode, finalSkill);
    setMessage('');
    setSearchMode(false);
    // Keep focus so the person can continue; the reply fills in above.
    requestAnimationFrame(() => ref.current?.focus());
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const canSend = message.trim().length > 0 && !disabled && !sending;
  const t = reducedMotion ? { duration: 0 } : { duration: DUR.micro + 0.06, ease: EASE.out };

  return (
    <div className={cn('mx-auto w-full max-w-[760px] px-5 pb-[max(16px,env(safe-area-inset-bottom))] pt-2 md:px-6', className)}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
        className="relative"
      >
        <div className="k-hairline mb-3 h-px w-full" />

        <div className="flex items-end gap-3">
          <textarea
            ref={ref}
            rows={1}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder={searchMode ? 'Search the web, then answer' : placeholder}
            disabled={disabled}
            aria-label="Message Kuro"
            className={cn(
              'k-field min-h-[28px] flex-1 resize-none bg-transparent py-1 text-[15px] leading-[1.5] text-foreground',
              'placeholder:text-muted-foreground/60 focus:outline-none disabled:opacity-60'
            )}
          />
          <button
            type="submit"
            disabled={!canSend}
            aria-label="Send"
            className={cn(
              'mb-0.5 flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full transition-colors [transition-duration:180ms]',
              canSend ? 'bg-foreground text-background' : 'bg-foreground/10 text-muted-foreground/50'
            )}
          >
            <ArrowUp className="h-3.5 w-3.5" />
          </button>
        </div>

        <div className="mt-3 flex items-center gap-5">
          <div ref={menuRef} className="relative">
            <button
              type="button"
              onClick={() => setShowSkills((v) => !v)}
              className={cn('k-quiet', selectedSkill !== 'auto' && '!text-foreground/85')}
              aria-haspopup="listbox"
              aria-expanded={showSkills}
            >
              {selectedSkill === 'auto' ? 'Auto' : SKILL_NAME[selectedSkill]}
            </button>
            <AnimatePresence>
              {showSkills && (
                <motion.ul
                  role="listbox"
                  className="k-surface absolute bottom-7 left-0 z-20 flex min-w-[180px] flex-col py-2"
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 4 }}
                  transition={t}
                >
                  {SKILLS.map((s) => (
                    <li key={s.id}>
                      <button
                        type="button"
                        role="option"
                        aria-selected={selectedSkill === s.id}
                        onClick={() => {
                          onSkillChange(s.id);
                          setShowSkills(false);
                        }}
                        className={cn(
                          'k-quiet w-full px-4 py-1.5 text-left',
                          selectedSkill === s.id && '!text-foreground'
                        )}
                      >
                        {s.name}
                      </button>
                    </li>
                  ))}
                </motion.ul>
              )}
            </AnimatePresence>
          </div>

          <button
            type="button"
            onClick={() => setSearchMode((v) => !v)}
            disabled={disabled}
            className={cn('k-quiet', searchMode && '!text-foreground/85')}
            aria-pressed={searchMode}
            title={searchMode ? 'Web search on' : 'Search the web for this message'}
          >
            {searchMode ? 'Web · on' : 'Web'}
          </button>

          <span className="ml-auto k-label !text-[10px] !text-muted-foreground/40">
            {sending ? 'Kuro is thinking' : 'Enter to send'}
          </span>
        </div>
      </form>
    </div>
  );
});

export default KuroChatInput;
