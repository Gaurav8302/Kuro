import React from 'react';
import { useDrop } from 'react-dnd';
import { motion } from 'framer-motion';
import { DRAG_TYPE_CHAT } from './SidebarChatItem';
import type { DropTarget } from '@/types/workspace';

export type WorkspaceDropZoneProps = {
  target: DropTarget;
  onDropChat: (chatId: string, target: DropTarget) => void;
  active?: boolean;
};

export default function WorkspaceDropZone({ target, onDropChat, active }: WorkspaceDropZoneProps) {
  const [{ isOver, canDrop }, drop] = useDrop(
    () => ({
      accept: DRAG_TYPE_CHAT,
      drop: (item: { chatId: string }) => onDropChat(item.chatId, target),
      collect: (monitor) => ({
        isOver: monitor.isOver({ shallow: true }),
        canDrop: monitor.canDrop()
      })
    }),
    [target, onDropChat]
  );

  const glow = isOver && canDrop ? 'ring-2 ring-primary shadow-[0_0_20px_rgba(99,102,241,0.6)]' : active ? 'ring-2 ring-primary/50' : 'ring-0';

  return (
    <motion.div
      ref={drop}
      className={`absolute inset-0 ${glow} rounded-xl transition-all`}
      initial={{ opacity: 0 }}
      animate={{ opacity: isOver ? 0.25 : 0 }}
      style={{ background: 'rgba(0,0,0,0.1)' }}
    />
  );
}
