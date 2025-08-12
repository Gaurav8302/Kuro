import React from 'react';
import { useDrop } from 'react-dnd';
import { motion, AnimatePresence } from 'framer-motion';
import { DRAG_TYPE_CHAT } from './SidebarChatItem';
import type { DropTarget } from '@/types/workspace';
import { getDebugDnd } from '@/state/debug';

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
  const debug = getDebugDnd();
  const [{ isOver, canDrop }, drop] = useDrop(
    () => ({
      accept: DRAG_TYPE_CHAT,
      drop: (item: { chatId: string }) => {
        if (debug) console.log('📥 Drop received on', target, 'for chat:', item.chatId);
        onDropChat(item.chatId, target);
      },
      collect: (monitor) => ({
        isOver: monitor.isOver({ shallow: true }),
        canDrop: monitor.canDrop()
      }),
      hover: (item: { chatId: string }) => {
        if (debug) console.log('👆 Hovering over', target, 'with chat:', item.chatId);
      }
    }),
    [target, onDropChat]
  );

  const isActive = isOver && canDrop;

  return (
    <div 
  ref={drop} 
  className={`absolute z-10 ${className}`}
  data-drop-target={target}
  onDragOver={(e) => { if (debug) console.log(`[native:onDragOver] zone:${target}`); e.preventDefault(); }}
  onDrop={(e) => { if (debug) console.log(`[native:onDrop] zone:${target}`); }}
    >
      {isActive ? (
        debug ? (
          <div className={`absolute inset-0 rounded-xl border-2 border-primary bg-primary/10`}>
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="bg-primary/90 text-primary-foreground px-4 py-2 rounded-lg font-medium text-sm shadow-lg">
                {target === 'full' && 'Drop to open fullscreen'}
                {target === 'left' && 'Drop to open on left'}
                {target === 'right' && 'Drop to open on right'}
                {target === 'floating' && 'Drop to create floating window'}
              </div>
            </div>
          </div>
        ) : (
          <AnimatePresence>
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ duration: 0.2, ease: 'easeOut' }}
              className={`absolute inset-0 rounded-xl border-2 border-primary bg-primary/10 backdrop-blur-sm shadow-[0_0_30px_rgba(99,102,241,0.4)] ${target === 'full' ? 'animate-pulse' : ''}`}
              style={{ boxShadow: isActive ? '0 0 30px rgba(99, 102, 241, 0.6), inset 0 0 20px rgba(99, 102, 241, 0.1)' : undefined }}
            >
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="absolute inset-0 flex items-center justify-center">
                <div className="bg-primary/90 text-primary-foreground px-4 py-2 rounded-lg font-medium text-sm shadow-lg">
                  {target === 'full' && 'Drop to open fullscreen'}
                  {target === 'left' && 'Drop to open on left'}
                  {target === 'right' && 'Drop to open on right'}
                  {target === 'floating' && 'Drop to create floating window'}
                </div>
              </motion.div>
            </motion.div>
          </AnimatePresence>
        )
      ) : null}
      {debug && !isActive && (
        <div className="absolute inset-0 pointer-events-none border border-dashed border-border/50 opacity-30" />
      )}
    </div>
  );
}
