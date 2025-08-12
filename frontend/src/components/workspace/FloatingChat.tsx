import React, { useCallback } from 'react';
import { Rnd } from 'react-rnd';
import { motion } from 'framer-motion';
import ChatWindow, { type ChatMessage } from './ChatWindow';
import type { FloatingRect } from '@/types/workspace';

export type FloatingChatProps = {
  rect: FloatingRect;
  title: string;
  messages: ChatMessage[];
  boundsRef: React.RefObject<HTMLDivElement>;
  onChange: (next: FloatingRect) => void;
  onClose: () => void;
  onSendMessage?: (message: string) => void;
  isLoading?: boolean;
};

export default function FloatingChat({ 
  rect, 
  title, 
  messages, 
  boundsRef, 
  onChange, 
  onClose,
  onSendMessage,
  isLoading
}: FloatingChatProps) {
  
  const handleDragStop = useCallback((_, d) => {
    onChange({ ...rect, x: d.x, y: d.y });
  }, [rect, onChange]);

  const handleResizeStop = useCallback((_, __, ref, ___, pos) => {
    onChange({
      ...rect,
      width: ref.offsetWidth,
      height: ref.offsetHeight,
      x: pos.x,
      y: pos.y
    });
  }, [rect, onChange]);

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
      transition={{ duration: 0.2 }}
    >
      <Rnd
        bounds={boundsRef.current || 'parent'}
        size={{ width: rect.width, height: rect.height }}
        position={{ x: rect.x, y: rect.y }}
        onDragStop={handleDragStop}
        onResizeStop={handleResizeStop}
        enableResizing={{
          top: true,
          right: true,
          bottom: true,
          left: true,
          topRight: true,
          bottomRight: true,
          bottomLeft: true,
          topLeft: true,
        }}
        resizeHandleStyles={{
          top: { cursor: 'n-resize' },
          right: { cursor: 'e-resize' },
          bottom: { cursor: 's-resize' },
          left: { cursor: 'w-resize' },
          topRight: { cursor: 'ne-resize' },
          bottomRight: { cursor: 'se-resize' },
          bottomLeft: { cursor: 'sw-resize' },
          topLeft: { cursor: 'nw-resize' },
        }}
        minWidth={280}
        minHeight={200}
        maxWidth={800}
        maxHeight={600}
        dragHandleClassName="drag-handle"
        className="rounded-lg shadow-2xl border-2 border-border/50 overflow-hidden backdrop-blur-sm"
        style={{
          background: 'rgba(255, 255, 255, 0.95)',
        }}
      >
        <div className="h-full">
          <ChatWindow 
            title={title}
            messages={messages}
            onSendMessage={onSendMessage}
            onClose={onClose}
            isFloating={true}
            isLoading={isLoading}
            className="border-0 shadow-none drag-handle"
          />
        </div>
      </Rnd>
    </motion.div>
  );
}
