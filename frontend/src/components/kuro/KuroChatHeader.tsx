import React, { memo, useState } from 'react';
import { Edit3, Check, X, Sparkles, Menu, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface KuroChatHeaderProps {
  title: string;
  onToggleSidebar: () => void;
  onRename: (newTitle: string) => void;
  onGenerateTitle: () => void;
  isGeneratingTitle: boolean;
  hasSession: boolean;
}

/**
 * KuroChatHeader - Professional chat header
 * Clean, minimal design with glass effect
 */
export const KuroChatHeader: React.FC<KuroChatHeaderProps> = memo(({
  title,
  onToggleSidebar,
  onRename,
  onGenerateTitle,
  isGeneratingTitle,
  hasSession
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(title);

  const handleSave = () => {
    if (editValue.trim()) {
      onRename(editValue.trim());
    }
    setIsEditing(false);
  };

  const handleCancel = () => {
    setEditValue(title);
    setIsEditing(false);
  };

  const handleStartEdit = () => {
    setEditValue(title);
    setIsEditing(true);
  };

  return (
    <header className="h-16 px-4 flex items-center gap-4 border-b border-border/50 glass">
      {/* Menu Button */}
      <Button
        variant="ghost"
        size="icon"
        onClick={onToggleSidebar}
        className="h-8 w-8"
      >
        <Menu className="h-4 w-4" />
      </Button>
      
      <div className="flex-1 flex items-center gap-3">
        {/* Status indicator */}
        <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
        
        {isEditing ? (
          <div className="flex items-center gap-2 flex-1">
            <input
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleSave();
                if (e.key === 'Escape') handleCancel();
              }}
              className={cn(
                "flex-1 min-w-[200px] px-3 py-1.5 rounded-lg",
                "bg-secondary border border-border",
                "text-foreground text-sm",
                "focus:outline-none focus:border-primary/50"
              )}
              autoFocus
            />
            <button 
              onClick={handleSave}
              className="p-1.5 rounded-md bg-green-500/20 hover:bg-green-500/30 transition-colors"
            >
              <Check className="w-4 h-4 text-green-400" />
            </button>
            <button 
              onClick={handleCancel}
              className="p-1.5 rounded-md bg-destructive/20 hover:bg-destructive/30 transition-colors"
            >
              <X className="w-4 h-4 text-destructive" />
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <div>
              <h1 className="text-sm font-medium text-foreground">
                {title || 'New conversation'}
              </h1>
              <p className="text-xs text-muted-foreground">Kuro is ready to assist</p>
            </div>
            <button
              onClick={handleStartEdit}
              className="p-1 rounded hover:bg-secondary transition-colors"
            >
              <Edit3 className="w-3.5 h-3.5 text-muted-foreground hover:text-foreground" />
            </button>
          </div>
        )}
      </div>

      {/* Generate Title Button */}
      {!isEditing && (
        <Button
          variant="ghost"
          size="sm"
          disabled={isGeneratingTitle || !hasSession}
          onClick={onGenerateTitle}
          className="gap-2"
        >
          {isGeneratingTitle ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Sparkles className="w-4 h-4 text-primary" />
          )}
          <span className="hidden sm:inline">
            {isGeneratingTitle ? 'Generating...' : 'Generate title'}
          </span>
        </Button>
      )}
    </header>
  );
});

KuroChatHeader.displayName = 'KuroChatHeader';

export default KuroChatHeader;
