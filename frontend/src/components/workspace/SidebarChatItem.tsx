import React from 'react';
import { useDrag } from 'react-dnd';
import { motion } from 'framer-motion';

export type SidebarChatItemProps = {
  chatId: string;
  title: string;
  onClick?: () => void;
};

export const DRAG_TYPE_CHAT = 'CHAT_ITEM';

export default function SidebarChatItem({ chatId, title, onClick }: SidebarChatItemProps) {
  const [{ isDragging }, drag, preview] = useDrag(() => ({
    type: DRAG_TYPE_CHAT,
    item: { chatId },
    collect: (monitor) => ({ isDragging: monitor.isDragging() })
  }), [chatId]);

  return (
    <>
      {/* custom preview: slightly transparent */}
      <div ref={preview} className="hidden" />
      <motion.div
        ref={drag}
        onClick={onClick}
        className="px-3 py-2 rounded-md cursor-move select-none"
        initial={{ opacity: 0.9 }}
        animate={{ opacity: isDragging ? 0.5 : 1 }}
        whileHover={{ scale: 1.02 }}
      >
        <div className="text-sm text-foreground/90 truncate">{title}</div>
      </motion.div>
    </>
  );
}
