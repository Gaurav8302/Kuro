import React, { memo, ReactNode } from 'react';

/**
 * ChatLayout — the stable chat shell inside the Kuro environment.
 *
 *   ┌ topBar (60px) ─────────────────────────────┐   ← Core + wordmark live here (from the environment/rail)
 *   ├ mainContent ───────────────────────────────┤   ← one ChatPanel, or two in split view
 *   └────────────────────────────────────────────┘
 *
 * The structure never changes with message state. There is no background of
 * its own: the environment behind it is the background.
 */
interface ChatLayoutProps {
  topBar: ReactNode;
  mainContent: ReactNode;
  overlays?: ReactNode;
  dropZoneOverlay?: ReactNode;
}

export const ChatLayout: React.FC<ChatLayoutProps> = memo(({ topBar, mainContent, overlays, dropZoneOverlay }) => {
  return (
    <div className="relative flex h-[100dvh] w-full flex-col overflow-hidden">
      <div className="relative z-20 h-[60px] flex-shrink-0">{topBar}</div>
      <div className="relative flex min-h-0 w-full flex-1 flex-col">
        {mainContent}
        {dropZoneOverlay}
      </div>
      {overlays}
    </div>
  );
});

ChatLayout.displayName = 'ChatLayout';

export default ChatLayout;
