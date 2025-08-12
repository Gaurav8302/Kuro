import React, { useRef, useEffect } from 'react';
import { useDrag, useDragLayer } from 'react-dnd';
import { motion } from 'framer-motion';
import { getEmptyImage } from 'react-dnd-html5-backend';
import { MessageSquare, GripVertical } from 'lucide-react';

export type SidebarChatItemProps = {
  chatId: string;
  title: string;
  onClick?: () => void;
  lastMessage?: string;
  timestamp?: number;
  isActive?: boolean;
};

export const DRAG_TYPE_CHAT = 'CHAT_ITEM';

// Custom drag preview component
function DragPreview() {
  const { isDragging, item, currentOffset } = useDragLayer((monitor) => ({
    item: monitor.getItem(),
    isDragging: monitor.isDragging(),
    currentOffset: monitor.getClientOffset(),
  }));

  if (!isDragging || !currentOffset) return null;

  return (
    <div
      style={{
        position: 'fixed',
        pointerEvents: 'none',
        left: currentOffset.x,
        top: currentOffset.y,
        transform: 'translate(-50%, -50%)',
        zIndex: 1000,
      }}
    >
      <motion.div
        initial={{ scale: 1, opacity: 0.9 }}
        animate={{ scale: 1.05, opacity: 0.8 }}
        className="bg-card border rounded-lg p-3 shadow-xl max-w-[200px]"
      >
        <div className="flex items-center gap-2">
          <MessageSquare className="w-4 h-4 text-muted-foreground" />
          <span className="text-sm font-medium truncate">{item?.title}</span>
        </div>
      </motion.div>
    </div>
  );
}

export default function SidebarChatItem({ 
  chatId, 
  title, 
  onClick, 
  lastMessage,
  timestamp,
  isActive 
}: SidebarChatItemProps) {
  const ref = useRef<HTMLDivElement>(null);
  
  const [{ isDragging }, drag, preview] = useDrag(() => ({
    type: DRAG_TYPE_CHAT,
    item: { chatId, title },
    collect: (monitor) => ({ 
      isDragging: monitor.isDragging() 
    })
  }), [chatId, title]);

  // Use empty image for drag preview - we'll use our custom one
  useEffect(() => {
    preview(getEmptyImage(), { captureDraggingState: true });
  }, [preview]);

  const handleClick = () => {
    if (!isDragging) {
      onClick?.();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleClick();
    }
  };

  const formatTime = (ts?: number) => {
    if (!ts) return '';
    const date = new Date(ts);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    
    if (diff < 60000) return 'now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h`;
    return `${Math.floor(diff / 86400000)}d`;
  };

  return (
    <>
      <DragPreview />
      <motion.div
        ref={(node) => {
          ref.current = node;
          drag(node);
        }}
        onClick={handleClick}
        onKeyDown={handleKeyDown}
        tabIndex={0}
        role="button"
        aria-label={`Chat: ${title}. ${lastMessage ? `Last message: ${lastMessage}` : ''}`}
        className={`
          group relative px-3 py-3 rounded-lg cursor-pointer select-none
          border transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary
          ${isActive 
            ? 'bg-primary/10 border-primary/20' 
            : 'bg-card border-border hover:bg-accent hover:border-accent-foreground/20'
          }
          ${isDragging ? 'opacity-50 scale-95' : 'opacity-100 scale-100'}
        `}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        whileHover={{ scale: isDragging ? 0.95 : 1.02 }}
        whileTap={{ scale: 0.98 }}
      >
        {/* Drag handle */}
        <div className="absolute left-1 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity">
          <GripVertical className="w-3 h-3 text-muted-foreground" />
        </div>

        <div className="ml-4">
          <div className="flex items-center justify-between mb-1">
            <h3 className="text-sm font-medium truncate pr-2">{title}</h3>
            {timestamp && (
              <span className="text-xs text-muted-foreground flex-shrink-0">
                {formatTime(timestamp)}
              </span>
            )}
          </div>
          
          {lastMessage && (
            <p className="text-xs text-muted-foreground truncate">
              {lastMessage}
            </p>
          )}
        </div>

        {/* Active indicator */}
        {isActive && (
          <motion.div
            initial={{ scaleY: 0 }}
            animate={{ scaleY: 1 }}
            className="absolute left-0 top-2 bottom-2 w-1 bg-primary rounded-r"
          />
        )}
      </motion.div>
    </>
  );
}
