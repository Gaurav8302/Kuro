import React, { memo, useState, useCallback, useEffect } from 'react';
import { AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { PanelPosition, ChatSession } from '@/types';
import { useChatPanel, ClerkApiRequestFn, ChatSkill } from '@/hooks/use-chat-panel';
import { useSplitView } from '@/contexts/SplitViewContext';
import { useTextSelection } from '@/hooks/use-text-selection';
import { useExperience } from '@/experience/ExperienceContext';
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
  /** Lets the parent (top bar) show/rename this panel's title in single view. */
  onSessionTitle?: (title: string | null, sessionId: string | null) => void;
}

/**
 * ChatPanel — one conversation.
 *
 * Owns its messages via useChatPanel. Reports thinking/response to the
 * environment so the Core carries the state instead of a "typing…" label.
 */
export const ChatPanel: React.FC<ChatPanelProps> = memo(
  ({ sessionId, sessions, userId, userAvatar, clerkApiRequest, panelPosition, isSplitMode, onSessionsChanged, onSessionTitle }) => {
    const splitView = useSplitView();
    const { setCoreMode, pulse, profile, reducedMotion } = useExperience();

    const onThinking = useCallback(
      (thinking: boolean) => {
        if (thinking) setCoreMode('thinking');
      },
      [setCoreMode]
    );
    const onResponded = useCallback(() => pulse(), [pulse]);

    const panel = useChatPanel({
      sessionId,
      sessions,
      userId,
      clerkApiRequest,
      onSessionsChanged,
      onThinking,
      onResponded,
    });

    // If a request fails (no reply), return the Core to idle.
    useEffect(() => {
      if (!panel.isTyping && panel.lastFailedMessage) setCoreMode('idle');
    }, [panel.isTyping, panel.lastFailedMessage, setCoreMode]);

    useEffect(() => {
      onSessionTitle?.(panel.currentSession?.title ?? null, panel.currentSession?.session_id ?? null);
    }, [panel.currentSession?.title, panel.currentSession?.session_id, onSessionTitle]);

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

    const handleSearchRequest = useCallback(
      (userMessage: string) => {
        if (userMessage) panel.sendMessage(userMessage, true, selectedSkill);
      },
      [panel.sendMessage, selectedSkill]
    );

    const shorten = (s: string) => (s.length > 80 ? s.slice(0, 77) + '...' : s);

    return (
      <div className="flex h-full min-h-0 w-full flex-col">
        {isSplitMode && (
          <KuroChatHeader
            title={panel.currentSession?.title || 'New conversation'}
            onRename={(t) => panel.currentSession && panel.renameSession(panel.currentSession.session_id, t)}
            hasSession={!!panel.currentSession}
            onClose={() => splitView.closePanel(panelPosition)}
            onExpand={() => splitView.expandPanel(panelPosition)}
          />
        )}

        {/* Scrollable conversation. `scroll-behavior: auto` — no smooth scroll
            competing with layout. */}
        <main ref={panel.scrollContainerRef} className={cn('relative flex min-h-0 flex-1 flex-col overflow-y-auto')}>
          <div ref={panel.messagesContainerRef} className="flex flex-1 flex-col">
            <KuroChatContent
              messages={panel.messages}
              userAvatar={userAvatar}
              isTyping={panel.isTyping}
              isLoading={panel.isLoading}
              onRetry={panel.retryMessage}
              onSearchRequest={handleSearchRequest}
              onSelectSkill={setSelectedSkill}
              messagesEndRef={panel.messagesEndRef}
              name={profile.name}
              reducedMotion={reducedMotion}
            />
          </div>

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
                    initialQuestion: `Explain what "${shorten(selection.text)}" means in this context.`,
                  });
                  clearSelection();
                }}
                onExample={() => {
                  setInlineAsk({
                    selectedText: selection.text,
                    context: selection.context,
                    parentMessage: selection.parentMessage,
                    messageIndex: selection.messageIndex,
                    initialQuestion: `Give me a clear example of "${shorten(selection.text)}".`,
                  });
                  clearSelection();
                }}
              />
            )}
          </AnimatePresence>

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

        <footer className="flex-shrink-0">
          <KuroChatInput
            onSendMessage={panel.sendMessage}
            selectedSkill={selectedSkill}
            onSkillChange={setSelectedSkill}
            sending={panel.isTyping}
            reducedMotion={reducedMotion}
          />
        </footer>
      </div>
    );
  }
);

ChatPanel.displayName = 'ChatPanel';

export default ChatPanel;
