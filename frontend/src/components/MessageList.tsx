import React, { memo, useRef } from 'react';
import { Message } from '@/types';
import { KuroMessage } from '@/components/chat/KuroMessage';
import { SearchSuggestion } from '@/components/SearchSuggestion';

interface MessageListProps {
  messages: Message[];
  userAvatar?: string;
  isTyping?: boolean;
  onRetry: () => void;
  onSearchRequest?: (userMessage: string) => void;
}

/**
 * MessageList — stable geometry.
 *
 *   • Keys are message ids (never timestamps or indexes).
 *   • Entrance motion is applied ONLY to messages that appear after the list
 *     has already been shown once. Loaded history and re-renders never
 *     animate, so nothing "flickers back in".
 *   • The pending assistant row is a normal list item that later receives its
 *     content — completion is an in-place update.
 */
export const MessageList: React.FC<MessageListProps> = memo(function MessageList({
  messages,
  onRetry,
  onSearchRequest,
}) {
  const seen = useRef<Set<string>>(new Set());
  const initialised = useRef(false);

  // A session switch empties the list first; treat the next fill as a load
  // (no entrance motion), not as new messages.
  if (messages.length === 0) {
    initialised.current = false;
    seen.current.clear();
  }

  const findPrecedingUserMessage = (idx: number): string => {
    for (let i = idx - 1; i >= 0; i--) {
      if (messages[i].role === 'user') return messages[i].message;
    }
    return '';
  };

  const items = messages.map((message, idx) => {
    const key = message.id ?? `fallback-${idx}`;
    const fresh = initialised.current && !seen.current.has(key);
    return (
      <React.Fragment key={key}>
        <div className={fresh ? 'k-enter' : undefined}>
          <KuroMessage message={message} onRetry={onRetry} />
        </div>
        {message.suggest_search && message.role === 'assistant' && !message.pending && onSearchRequest && (
          <SearchSuggestion onSearchClick={() => onSearchRequest(findPrecedingUserMessage(idx))} />
        )}
      </React.Fragment>
    );
  });

  // Mark everything rendered so far as seen. After the first non-empty
  // render, new ids are "fresh" and get the entrance motion.
  messages.forEach((m, idx) => seen.current.add(m.id ?? `fallback-${idx}`));
  if (messages.length > 0) initialised.current = true;

  return <div className="flex flex-col gap-7 py-6">{items}</div>;
});

MessageList.displayName = 'MessageList';

export default MessageList;
