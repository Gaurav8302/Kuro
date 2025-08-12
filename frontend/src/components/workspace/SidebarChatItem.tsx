import React, { useRef, useEffect, useState } from 'react';
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
  onDragStart?: (chatId: string) => void;
  onDragEnd?: () => void;
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
  isActive,
  onDragStart,
  onDragEnd,
}: SidebarChatItemProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [clickCount, setClickCount] = useState(0);
  const [isDoubleTapReady, setIsDoubleTapReady] = useState(false);
  const clickTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const [isTouchDevice, setIsTouchDevice] = useState(false);

  useEffect(() => {
    const coarse = typeof window !== 'undefined' && window.matchMedia ? window.matchMedia('(pointer: coarse)').matches : false;
    const touchCap = typeof navigator !== 'undefined' && (navigator.maxTouchPoints || (navigator as any).msMaxTouchPoints);
    setIsTouchDevice(!!coarse || (touchCap ?? 0) > 0);
  }, []);
  
  const [{ isDragging }, drag, preview] = useDrag(() => ({
    type: DRAG_TYPE_CHAT,
    item: { chatId, title },
    collect: (monitor) => ({ 
      isDragging: monitor.isDragging() 
    }),
    begin: (monitor) => {
      // Log drag begin for diagnostics
      console.log('[DnD] begin drag chat', chatId);
      onDragStart?.(chatId);
      return { chatId, title };
    },
    end: (item, monitor) => {
      onDragEnd?.();
      setIsDoubleTapReady(false); // Reset double tap state
    },
    canDrag: () => {
      // On desktop allow immediate drag; on touch require double tap
      return isTouchDevice ? isDoubleTapReady : true;
    }
  }), [chatId, title, onDragStart, onDragEnd, isDoubleTapReady, isTouchDevice]);

  // Connect drag to the ref
  useEffect(() => {
    drag(ref.current);
  }, [drag]);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (clickTimeoutRef.current) {
        clearTimeout(clickTimeoutRef.current);
      }
    };
  }, []);

  // Use empty image for drag preview - we'll use our custom one
  useEffect(() => {
    preview(getEmptyImage(), { captureDraggingState: true });
  }, [preview]);

  const handleClick = () => {
    if (!isDragging) {
      setClickCount(prev => prev + 1);
      
      if (clickCount === 0) {
        // First click - start timer for double click detection
        clickTimeoutRef.current = setTimeout(() => {
          onClick?.(); // Single click opens the chat
          setClickCount(0);
        }, 300); // 300ms window for double click
      } else if (clickCount === 1) {
        // Second click within timeout - this is a double click
        if (clickTimeoutRef.current) {
          clearTimeout(clickTimeoutRef.current);
        }
        setIsDoubleTapReady(true);
        setClickCount(0);
        
        // Reset double tap ready state after 3 seconds if no drag occurs
        setTimeout(() => {
          setIsDoubleTapReady(false);
        }, 3000);
      }
    }
  };

  const handleMouseDown = (e: React.MouseEvent) => {};
  const handleMouseUp = (e: React.MouseEvent) => {};

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
        ref={ref}
        onClick={handleClick}
        onMouseDown={handleMouseDown}
        onMouseUp={handleMouseUp}
        onKeyDown={handleKeyDown}
        tabIndex={0}
        role="button"
        aria-label={`Chat: ${title}. ${lastMessage ? `Last message: ${lastMessage}` : ''}`}
        draggable={false}
        data-chat-id={chatId}
        className={`
          group relative px-3 py-3 rounded-lg select-none
          border transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary
          ${isActive 
            ? 'bg-primary/10 border-primary/20' 
            : 'bg-card border-border hover:bg-accent hover:border-accent-foreground/20'
          }
          ${isDragging ? 'opacity-50 scale-95 cursor-grabbing' : 'opacity-100 scale-100'}
          ${isDoubleTapReady 
            ? 'cursor-grab border-green-400 bg-green-50 dark:bg-green-950' 
            : 'cursor-pointer'
          }
        `}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        whileHover={{ scale: isDragging ? 0.95 : 1.02 }}
        whileTap={{ scale: 0.98 }}
      >
        {/* Drag handle - more visible when drag ready */}
        <div className={`absolute left-1 top-1/2 -translate-y-1/2 transition-all ${
          isDoubleTapReady 
            ? 'opacity-100 text-green-600' 
            : 'opacity-60 group-hover:opacity-100'
        }`}>
          <GripVertical className="w-4 h-4 text-current" />
        </div>

        <div className="ml-4">
          {isDoubleTapReady && (
            <div className="absolute top-1 right-1 text-xs text-green-600 font-medium bg-green-100 dark:bg-green-900 px-2 py-1 rounded">
              🎯 Drag Ready
            </div>
          )}
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
