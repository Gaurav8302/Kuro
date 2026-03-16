import React, { memo, useState, useCallback } from 'react';
import { AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { PanelPosition, ChatSession } from '@/types';
import { useChatPanel, ClerkApiRequestFn, ChatSkill } from '@/hooks/use-chat-panel';
import { useSplitView } from '@/contexts/SplitViewContext';
import { useTextSelection } from '@/hooks/use-text-selection';
import { useIsMobile } from '@/hooks/use-mobile';
import { KuroChatHeader } from '@/components/kuro/KuroChatHeader';
import { KuroChatContent } from '@/components/kuro/KuroChatContent';
import { KuroChatInput } from '@/components/kuro/KuroChatInput';
import { SelectionPopup } from '@/components/SelectionPopup';
import { InlineChatPanel } from '@/components/InlineChatPanel';

interface ChatPanelProps {
  sessionId: string | null;
  sessions: ChatSession[];
  userId: string | undefined;
  userAvatar: string;
  clerkApiRequest: ClerkApiRequestFn;
  panelPosition: PanelPosition;
  isSplitMode: boolean;
  onSessionsChanged: () => void;
  onToggleSidebar?: () => void;
}

/**
 * ChatPanel - Self-contained chat panel component.
 *
 * Each instance manages its own messages, loading, typing, and scroll state
 * via the useChatPanel hook. In split mode, it includes close/expand buttons.
 */
export const ChatPanel: React.FC<ChatPanelProps> = memo(({
  sessionId,
  sessions,
  userId,
  userAvatar,
  clerkApiRequest,
  panelPosition,
  isSplitMode,
  onSessionsChanged,
  onToggleSidebar,
}) => {
  const isMobile = useIsMobile();
  const splitView = useSplitView();

  const panel = useChatPanel({
    sessionId,
    sessions,
    userId,
    clerkApiRequest,
    onSessionsChanged,
  });

  // Text selection / inline ask (per-panel)
  const { selection, clearSelection } = useTextSelection(panel.messagesContainerRef);
  const [inlineAsk, setInlineAsk] = useState<{
    selectedText: string;
    context: string;
    parentMessage: string;
    messageIndex: number;
    initialQuestion?: string;
  } | null>(null);
  const [selectedSkill, setSelectedSkill] = useState<ChatSkill>('auto');

  // Handle search request from SearchSuggestion button
  const handleSearchRequest = useCallback(
    (userMessage: string) => {
      if (userMessage) {
        panel.sendMessage(userMessage, true, selectedSkill);
      }
    },
    [panel.sendMessage, selectedSkill]
  );

  const showSidebarToggle = panelPosition === 'left' || panelPosition === 'top' || !isSplitMode;

  return (
    <div className="flex flex-col h-full min-h-0 w-full">
      {/* Header */}
      <header className="flex-shrink-0">
        <KuroChatHeader
          title={panel.currentSession?.title || 'New Chat'}
          onToggleSidebar={onToggleSidebar || (() => {})}
          onRename={(newTitle) => {
            if (panel.currentSession) {
              panel.renameSession(panel.currentSession.session_id, newTitle);
            }
          }}
          hasSession={!!panel.currentSession}
          isSplitMode={isSplitMode}
          showSidebarToggle={showSidebarToggle}
          onClose={
            isSplitMode
              ? () => splitView.closePanel(panelPosition)
              : undefined
          }
          onExpand={
            isSplitMode
              ? () => splitView.expandPanel(panelPosition)
              : undefined
          }
        />
      </header>

      {/* Scrollable messages area */}
      <main
        ref={panel.scrollContainerRef}
        className={cn(
          'flex-1 overflow-y-auto min-h-0 relative scroll-smooth',
          isMobile && 'pb-4 px-1'
        )}
      >
        <div ref={panel.messagesContainerRef} className="h-full">
          <KuroChatContent
            messages={panel.messages}
            userAvatar={userAvatar}
            isTyping={panel.isTyping}
            isLoading={panel.isLoading}
            onRetry={panel.retryMessage}
            onSearchRequest={handleSearchRequest}
            onSelectSkill={setSelectedSkill}
            messagesEndRef={panel.messagesEndRef}
          />
        </div>

        {/* Inline Ask: selection popup */}
        <AnimatePresence>
          {selection && !inlineAsk && (
            <SelectionPopup
              text={selection.text}
              x={selection.x}
              y={selection.y}
              onCopy={clearSelection}
              onAskKuro={() => {
                setInlineAsk({
                  selectedText: selection.text,
                  context: selection.context,
                  parentMessage: selection.parentMessage,
                  messageIndex: selection.messageIndex,
                });
                clearSelection();
              }}
              onExplain={() => {
                setInlineAsk({
                  selectedText: selection.text,
                  context: selection.context,
                  parentMessage: selection.parentMessage,
                  messageIndex: selection.messageIndex,
                  initialQuestion: `Explain what "${selection.text.length > 80 ? selection.text.slice(0, 77) + '...' : selection.text}" means in this context.`,
                });
                clearSelection();
              }}
              onExample={() => {
                setInlineAsk({
                  selectedText: selection.text,
                  context: selection.context,
                  parentMessage: selection.parentMessage,
                  messageIndex: selection.messageIndex,
                  initialQuestion: `Give me a clear example of "${selection.text.length > 80 ? selection.text.slice(0, 77) + '...' : selection.text}".`,
                });
                clearSelection();
              }}
            />
          )}
        </AnimatePresence>

        {/* Inline Ask: mini-chat panel */}
        <AnimatePresence>
          {inlineAsk && (
            <InlineChatPanel
              selectedText={inlineAsk.selectedText}
              context={inlineAsk.context}
              parentMessage={inlineAsk.parentMessage}
              sessionId={panel.currentSession?.session_id}
              userId={userId}
              messageIndex={inlineAsk.messageIndex}
              initialQuestion={inlineAsk.initialQuestion}
              onClose={() => setInlineAsk(null)}
            />
          )}
        </AnimatePresence>
      </main>

      {/* Input - fixed at bottom */}
      <footer className="flex-shrink-0">
        <KuroChatInput
          onSendMessage={panel.sendMessage}
          selectedSkill={selectedSkill}
          onSkillChange={setSelectedSkill}
          sending={panel.isTyping || panel.isLoading}
          placeholder={
            panel.isTyping || panel.isLoading
              ? 'Kuro is responding...'
              : 'Type a message...'
          }
        />
      </footer>
    </div>
  );
});

ChatPanel.displayName = 'ChatPanel';

export default ChatPanel;
