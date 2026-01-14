import React, { memo, useState } from 'react';
import { motion } from 'framer-motion';
import { Edit3, Check, X, Zap, Brain } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { HolographicButton } from '@/components/HolographicButton';
import { HoloMenuIcon } from '@/components/HolographicIcons';
import { useOptimizedAnimations } from '@/hooks/use-performance';
import { cn } from '@/lib/utils';

interface ChatHeaderProps {
  title: string;
  onToggleSidebar: () => void;
  onRename: (newTitle: string) => void;
  onGenerateTitle: () => void;
  isGeneratingTitle: boolean;
  hasSession: boolean;
}

export const ChatHeader: React.FC<ChatHeaderProps> = memo(({
  title,
  onToggleSidebar,
  onRename,
  onGenerateTitle,
  isGeneratingTitle,
  hasSession
}) => {
  const { shouldReduceAnimations, animationDuration } = useOptimizedAnimations();
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
    <div className="p-4 border-b border-holo-cyan-500/20 glass-panel backdrop-blur-xl relative overflow-hidden">
      {/* Header scan line */}
      {!shouldReduceAnimations && (
        <motion.div
          className="absolute bottom-0 left-0 w-full h-0.5 bg-gradient-to-r from-transparent via-holo-cyan-400 to-transparent"
          animate={{ opacity: [0.3, 0.8, 0.3] }}
          transition={{ duration: 2, repeat: Infinity }}
        />
      )}
      
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {/* Menu Button */}
          <button
            onClick={onToggleSidebar}
            className="shrink-0 w-10 h-10 rounded-lg glass-panel border-holo-cyan-400/30 hover:shadow-holo-glow transition-all duration-200 flex items-center justify-center transform-gpu hover:scale-110 active:scale-95"
            title="Toggle Sidebar"
          >
            <HoloMenuIcon size={20} />
          </button>
          
          {isEditing ? (
            <div className="flex items-center gap-2">
              <Input
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleSave();
                  if (e.key === 'Escape') handleCancel();
                }}
                className="h-8 min-w-[200px] glass-panel border-holo-cyan-400/30 text-holo-cyan-100 font-space"
                autoFocus
              />
              <button 
                onClick={handleSave}
                className="w-8 h-8 rounded glass-panel border-holo-green-400/30 hover:shadow-holo-green transition-all duration-200 flex items-center justify-center transform-gpu hover:scale-110 active:scale-95"
              >
                <Check className="w-4 h-4 text-holo-green-400" />
              </button>
              <button 
                onClick={handleCancel}
                className="w-8 h-8 rounded glass-panel border-holo-magenta-400/30 hover:shadow-holo-magenta transition-all duration-200 flex items-center justify-center transform-gpu hover:scale-110 active:scale-95"
              >
                <X className="w-4 h-4 text-holo-magenta-400" />
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-semibold text-holo-cyan-300 text-holo-glow font-orbitron tracking-wide">
                {title || 'New Chat'}
              </h1>
              <button
                onClick={handleStartEdit}
                className="w-6 h-6 rounded glass-panel border-holo-cyan-400/20 hover:border-holo-cyan-400/40 hover:shadow-holo-glow transition-all duration-200 flex items-center justify-center transform-gpu hover:scale-110 active:scale-95"
              >
                <Edit3 className="w-3 h-3 text-holo-cyan-400" />
              </button>
              <HolographicButton
                variant="ghost"
                size="sm"
                disabled={isGeneratingTitle || !hasSession}
                onClick={onGenerateTitle}
                className="h-7 px-3 text-xs font-orbitron tracking-wide"
              >
                {isGeneratingTitle ? (
                  <span className="flex items-center gap-1">
                    <motion.div
                      animate={{ rotate: 360 }}
                      transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                    >
                      <Zap className="h-3 w-3" />
                    </motion.div>
                    GENERATING...
                  </span>
                ) : (
                  <>
                    <Brain className="w-3 h-3 mr-1" />
                    GENERATE TITLE
                  </>
                )}
              </HolographicButton>
            </div>
          )}
        </div>
      </div>
    </div>
  );
});

ChatHeader.displayName = 'ChatHeader';

export default ChatHeader;
