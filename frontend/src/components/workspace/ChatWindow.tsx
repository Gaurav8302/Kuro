import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';

export type ChatWindowProps = {
  title: string;
  messages: { id: string; role: 'user' | 'assistant'; content: string }[];
};

export default function ChatWindow({ title, messages }: ChatWindowProps) {
  return (
    <motion.div className="h-full w-full rounded-lg border bg-card overflow-hidden">
      <div className="px-4 py-2 border-b text-sm font-medium">{title}</div>
      <div className="p-4 space-y-3 h-[calc(100%-40px)] overflow-auto">
        <AnimatePresence initial={false}>
          {messages.map((m) => (
            <motion.div
              key={m.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              className={`px-3 py-2 rounded-md text-sm ${m.role === 'user' ? 'bg-primary/10' : 'bg-muted'}`}
            >
              {m.content}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}
