import React, { memo } from 'react';
import { motion } from 'framer-motion';
import { Message } from '@/types';
import { ChatSkill } from '@/hooks/use-chat-panel';
import { MessageList } from '@/components/MessageList';
import { lineVariants, lineVariantsReduced } from '@/experience/motion';

interface KuroChatContentProps {
  messages: Message[];
  userAvatar: string;
  isTyping: boolean;
  isLoading: boolean;
  onRetry: () => void;
  onSearchRequest?: (userMessage: string) => void;
  onSelectSkill?: (skill: ChatSkill) => void;
  messagesEndRef: React.RefObject<HTMLDivElement>;
  /** Person's name, if Kuro knows it */
  name?: string | null;
  reducedMotion?: boolean;
}

const SKILLS: Array<{ id: ChatSkill; label: string }> = [
  { id: 'code', label: 'Write code' },
  { id: 'explain', label: 'Explain something' },
  { id: 'creative', label: 'Write with me' },
  { id: 'problem', label: 'Work through a problem' },
];

/**
 * EmptyState — a question, not a landing page.
 * The Core is already on screen (top-left); nothing else needs to announce Kuro.
 */
const EmptyState = memo<{
  isLoading: boolean;
  name?: string | null;
  reducedMotion?: boolean;
  onSelectSkill?: (skill: ChatSkill) => void;
}>(({ isLoading, name, reducedMotion, onSelectSkill }) => {
  const lv = reducedMotion ? lineVariantsReduced : lineVariants;

  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <span className="k-label">Opening conversation</span>
      </div>
    );
  }

  return (
    <div className="flex flex-1 items-center justify-center px-6">
      <motion.div className="flex w-[min(92vw,560px)] flex-col items-center text-center" initial="hidden" animate="show">
        <motion.p className="k-voice text-[clamp(1.35rem,2.6vw,1.9rem)]" variants={lv} custom={0}>
          {name ? `What are we working on, ${name}?` : 'What are we working on?'}
        </motion.p>
        <motion.div className="mt-8 flex flex-wrap items-center justify-center gap-x-6 gap-y-3" variants={lv} custom={1}>
          {SKILLS.map((s) => (
            <button key={s.id} type="button" className="k-quiet" onClick={() => onSelectSkill?.(s.id)}>
              {s.label}
            </button>
          ))}
        </motion.div>
      </motion.div>
    </div>
  );
});
EmptyState.displayName = 'EmptyState';

/**
 * KuroChatContent — either the empty question or the conversation.
 * Both live inside the same scroll container; the container never changes.
 */
export const KuroChatContent: React.FC<KuroChatContentProps> = memo(
  ({ messages, isLoading, onRetry, onSearchRequest, onSelectSkill, messagesEndRef, name, reducedMotion }) => {
    const hasMessages = messages.length > 0;

    if (!hasMessages) {
      return <EmptyState isLoading={isLoading} name={name} reducedMotion={reducedMotion} onSelectSkill={onSelectSkill} />;
    }

    return (
      <div className="w-full">
        <MessageList messages={messages} onRetry={onRetry} onSearchRequest={onSearchRequest} />
        <div ref={messagesEndRef} className="h-2" />
      </div>
    );
  }
);

KuroChatContent.displayName = 'KuroChatContent';

export default KuroChatContent;
