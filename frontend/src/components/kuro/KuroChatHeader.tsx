import React, { memo, useEffect, useState } from 'react';
import { X, Maximize2 } from 'lucide-react';
import { cn } from '@/lib/utils';

/**
 * EditableTitle — the conversation's name. Click to rename; Enter saves,
 * Escape cancels. No icons, no buttons: the text is the control.
 */
export const EditableTitle: React.FC<{
  title: string;
  onRename: (t: string) => void;
  disabled?: boolean;
  className?: string;
  align?: 'left' | 'center';
}> = memo(({ title, onRename, disabled, className, align = 'left' }) => {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(title);

  useEffect(() => {
    if (!editing) setValue(title);
  }, [title, editing]);

  const save = () => {
    const t = value.trim();
    if (t && t !== title) onRename(t);
    setEditing(false);
  };

  if (editing) {
    return (
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onBlur={save}
        onKeyDown={(e) => {
          if (e.key === 'Enter') save();
          if (e.key === 'Escape') {
            setValue(title);
            setEditing(false);
          }
        }}
        autoFocus
        aria-label="Conversation title"
        className={cn(
          'k-field w-full max-w-[420px] bg-transparent text-[13px] text-foreground outline-none',
          'border-b border-foreground/30 pb-0.5',
          align === 'center' && 'text-center',
          className
        )}
      />
    );
  }

  return (
    <button
      type="button"
      onClick={() => !disabled && setEditing(true)}
      disabled={disabled}
      title={disabled ? undefined : 'Rename'}
      className={cn(
        'max-w-full truncate text-[13px] text-foreground/80 transition-colors [transition-duration:180ms]',
        !disabled && 'hover:text-foreground',
        align === 'center' && 'text-center',
        className
      )}
    >
      {title}
    </button>
  );
});
EditableTitle.displayName = 'EditableTitle';

interface KuroChatHeaderProps {
  title: string;
  onRename: (newTitle: string) => void;
  hasSession: boolean;
  onClose?: () => void;
  onExpand?: () => void;
}

/**
 * KuroChatHeader — slim header for a panel in split view.
 * (In single view the title lives in the chat top bar instead.)
 */
export const KuroChatHeader: React.FC<KuroChatHeaderProps> = memo(({ title, onRename, hasSession, onClose, onExpand }) => {
  return (
    <header className="flex h-10 items-center gap-3 border-b border-border/60 px-4">
      <div className="min-w-0 flex-1">
        <EditableTitle title={title || 'New conversation'} onRename={onRename} disabled={!hasSession} />
      </div>
      <div className="flex items-center gap-1">
        {onExpand && (
          <button type="button" onClick={onExpand} className="k-quiet p-1.5" title="Expand panel" aria-label="Expand panel">
            <Maximize2 className="h-3.5 w-3.5" />
          </button>
        )}
        {onClose && (
          <button type="button" onClick={onClose} className="k-quiet p-1.5" title="Close panel" aria-label="Close panel">
            <X className="h-3.5 w-3.5" />
          </button>
        )}
      </div>
    </header>
  );
});

KuroChatHeader.displayName = 'KuroChatHeader';

export default KuroChatHeader;
