import React from 'react';
import { useDrop } from 'react-dnd';
import { motion, AnimatePresence } from 'framer-motion';
import { DRAG_TYPE_CHAT } from './SidebarChatItem';
import type { DropTarget } from '@/types/workspace';

export type WorkspaceDropZoneProps = {
  target: DropTarget;
  onDropChat: (chatId: string, target: DropTarget) => void;
  active?: boolean;
  className?: string;
};

export default function WorkspaceDropZone({ 
  target, 
  onDropChat, 
  active, 
  className = '' 
}: WorkspaceDropZoneProps) {
  const [{ isOver, canDrop }, drop] = useDrop(
    () => ({
      accept: DRAG_TYPE_CHAT,
      drop: (item: { chatId: string }) => {
        console.log('📥 Drop received on', target, 'for chat:', item.chatId);
        onDropChat(item.chatId, target);
      },
      collect: (monitor) => ({
        isOver: monitor.isOver({ shallow: true }),
        canDrop: monitor.canDrop()
      }),
      hover: (item: { chatId: string }) => {
        console.log('👆 Hovering over', target, 'with chat:', item.chatId);
      }
    }),
    [target, onDropChat]
  );

  const isActive = isOver && canDrop;

  return (
    <div 
      ref={drop} 
      className={`absolute z-10 ${className}`}
    >
      <AnimatePresence>
        {isActive && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ 
              opacity: 1, 
              scale: 1,
            }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ 
              duration: 0.2, 
              ease: "easeOut",
            }}
            className={`
              absolute inset-0 rounded-xl border-2 border-primary
              bg-primary/10 backdrop-blur-sm
              shadow-[0_0_30px_rgba(99,102,241,0.4)]
              ${target === 'full' ? 'animate-pulse' : ''}
            `}
            style={{
              boxShadow: isActive 
                ? '0 0 30px rgba(99, 102, 241, 0.6), inset 0 0 20px rgba(99, 102, 241, 0.1)'
                : undefined
            }}
          >
            {/* Visual indicator text */}
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="absolute inset-0 flex items-center justify-center"
            >
              <div className="bg-primary/90 text-primary-foreground px-4 py-2 rounded-lg font-medium text-sm shadow-lg">
                {target === 'full' && 'Drop to open fullscreen'}
                {target === 'left' && 'Drop to open on left'}
                {target === 'right' && 'Drop to open on right'}
                {target === 'floating' && 'Drop to create floating window'}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
