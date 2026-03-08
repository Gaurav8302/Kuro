import React, { memo, ReactNode } from 'react';
import { cn } from '@/lib/utils';
import { useIsMobile } from '@/hooks/use-mobile';

/**
 * ChatLayout - Stable layout shell that NEVER changes based on chat state.
 *
 * Architecture (NON-NEGOTIABLE):
 * - AppShell: 100dvh height, never changes
 * - Sidebar: Always mounted, visibility controlled via CSS transform
 * - MainPanel: Renders mainContent (1 or 2 ChatPanels)
 * - ChatInput: Fixed at bottom of each ChatPanel, never inside scroll container
 */

interface ChatLayoutProps {
  /** Sidebar content - always mounted, never conditionally rendered */
  sidebar: ReactNode;
  /** Whether sidebar is visually open (controls CSS transform, not mount) */
  sidebarOpen: boolean;
  /** Main content area - one ChatPanel (single) or ResizablePanelGroup (split) */
  mainContent: ReactNode;
  /** Overlay content (modals, intros, errors) */
  overlays?: ReactNode;
  /** Background element */
  background?: ReactNode;
  /** Callback when mobile overlay is clicked */
  onMobileOverlayClick?: () => void;
  /** Drop zone overlay shown during drag */
  dropZoneOverlay?: ReactNode;
}

/**
 * Desktop Sidebar wrapper - always rendered, uses CSS transform for visibility
 */
const DesktopSidebar = memo<{ children: ReactNode; isOpen: boolean }>(({ children, isOpen }) => (
  <div
    className={cn(
      "hidden md:flex flex-col h-full border-r border-border/50 bg-background/95 backdrop-blur-xl",
      "transition-all duration-300 ease-out transform-gpu",
      isOpen ? "w-72 translate-x-0 opacity-100" : "w-0 -translate-x-full opacity-0 overflow-hidden"
    )}
    style={{ flexShrink: 0 }}
  >
    <div className="w-72 h-full">
      {children}
    </div>
  </div>
));

DesktopSidebar.displayName = 'DesktopSidebar';

/**
 * Mobile Sidebar drawer - simplified for reliability
 */
const MobileSidebar: React.FC<{
  children: ReactNode;
  isOpen: boolean;
  onOverlayClick?: () => void;
}> = ({ children, isOpen, onOverlayClick }) => {
  return (
    <>
      {/* Backdrop overlay */}
      <div
        className="md:hidden fixed inset-0 z-40 bg-black/60 backdrop-blur-md"
        style={{
          opacity: isOpen ? 1 : 0,
          pointerEvents: isOpen ? 'auto' : 'none',
          transition: 'opacity 300ms ease-out'
        }}
        onClick={() => {
          if (onOverlayClick) onOverlayClick();
        }}
        aria-hidden={!isOpen}
      />

      {/* Sidebar drawer */}
      <div
        className="md:hidden fixed left-0 top-0 h-full w-72 z-50 glass shadow-xl border-r border-border/50"
        style={{
          transform: isOpen ? 'translateX(0)' : 'translateX(-100%)',
          transition: 'transform 300ms ease-out'
        }}
        aria-hidden={!isOpen}
      >
        {children}
      </div>
    </>
  );
};

MobileSidebar.displayName = 'MobileSidebar';

/**
 * ChatLayout - The stable app shell
 *
 * RULES:
 * - This component structure NEVER changes based on messages.length
 * - Sidebar is ALWAYS mounted (visibility via CSS)
 * - MainPanel renders the mainContent prop which contains 1 or 2 ChatPanels
 */
export const ChatLayout: React.FC<ChatLayoutProps> = memo(({
  sidebar,
  sidebarOpen,
  mainContent,
  overlays,
  background,
  onMobileOverlayClick,
  dropZoneOverlay,
}) => {
  const isMobile = useIsMobile();

  return (
    <div
      className={cn(
        "flex bg-background relative overflow-hidden",
        isMobile ? "h-[100dvh]" : "h-screen"
      )}
    >
      {/* Background - always present */}
      {background}

      {/* Desktop sidebar - always mounted */}
      <DesktopSidebar isOpen={sidebarOpen}>
        {sidebar}
      </DesktopSidebar>

      {/* Mobile sidebar drawer */}
      <MobileSidebar isOpen={sidebarOpen} onOverlayClick={onMobileOverlayClick}>
        {sidebar}
      </MobileSidebar>

      {/* Main panel - contains 1 or 2 ChatPanels */}
      <div className="flex flex-col h-full min-h-0 flex-1 relative w-full">
        {mainContent}
        {/* Drop zone overlay during drag */}
        {dropZoneOverlay}
      </div>

      {/* Overlays - modals, errors, intros */}
      {overlays}
    </div>
  );
});

ChatLayout.displayName = 'ChatLayout';

export default ChatLayout;
