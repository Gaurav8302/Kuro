import React, { memo, ReactNode, forwardRef } from 'react';
import { cn } from '@/lib/utils';
import { useIsMobile } from '@/hooks/use-mobile';

/**
 * ChatLayout - Stable layout shell that NEVER changes based on chat state.
 * 
 * Architecture (NON-NEGOTIABLE):
 * - AppShell: 100dvh height, never changes
 * - Sidebar: Always mounted, visibility controlled via CSS transform
 * - MainPanel: Flex column, contains header + scrollable area + input
 * - ChatArea: Only this area's CONTENT changes based on messages
 * - ChatInput: Fixed at bottom, never moves, never inside scroll container
 */

interface ChatLayoutProps {
  /** Sidebar content - always mounted, never conditionally rendered */
  sidebar: ReactNode;
  /** Whether sidebar is visually open (controls CSS transform, not mount) */
  sidebarOpen: boolean;
  /** Chat header content */
  header: ReactNode;
  /** Chat messages area - only content inside changes */
  children: ReactNode;
  /** Chat input - always visible at bottom */
  input: ReactNode;
  /** Overlay content (modals, intros, errors) */
  overlays?: ReactNode;
  /** Background element */
  background?: ReactNode;
  /** Callback when mobile overlay is clicked */
  onMobileOverlayClick?: () => void;
  /** Ref for scroll container */
  scrollContainerRef?: React.RefObject<HTMLDivElement>;
}

/**
 * Desktop Sidebar wrapper - always rendered, uses CSS transform for visibility
 */
const DesktopSidebar = memo<{ children: ReactNode; isOpen: boolean }>(({ children, isOpen }) => (
  <div
    className={cn(
      "hidden md:flex flex-col h-full border-r border-border/50 bg-background/95 backdrop-blur-xl",
      "transition-all duration-300 ease-out transform-gpu",
      // Width controlled by CSS, not by mount/unmount
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
 * Uses inline styles to guarantee state is applied correctly
 */
const MobileSidebar: React.FC<{ 
  children: ReactNode; 
  isOpen: boolean; 
  onOverlayClick?: () => void;
}> = ({ children, isOpen, onOverlayClick }) => {
  // Log state changes for debugging
  React.useEffect(() => {
    console.log('[MobileSidebar] isOpen changed to:', isOpen);
  }, [isOpen]);

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
          console.log('[MobileSidebar] Overlay clicked');
          if (onOverlayClick) onOverlayClick();
        }}
        aria-hidden={!isOpen}
      />
      
      {/* Sidebar drawer - uses inline transform for guaranteed state sync */}
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
 * Main panel - flex column layout for header, scrollable content, fixed input
 */
interface MainPanelProps {
  header: ReactNode; 
  children: ReactNode; 
  input: ReactNode;
  isMobile: boolean;
  scrollContainerRef?: React.RefObject<HTMLDivElement>;
}

const MainPanel = memo<MainPanelProps>(({ header, children, input, isMobile, scrollContainerRef }) => (
  <div 
    className={cn(
      "flex flex-col h-full min-h-0 flex-1 relative",
      // Ensure main panel always takes remaining space
      "w-full"
    )}
  >
    {/* Header - fixed height, never scrolls */}
    <header className="flex-shrink-0">
      {header}
    </header>
    
    {/* Chat area - flex-grow, scrollable, content changes based on messages */}
    <main 
      ref={scrollContainerRef}
      className={cn(
        "flex-1 overflow-y-auto min-h-0 relative scroll-smooth",
        isMobile && "pb-4 px-1"
      )}
    >
      {children}
    </main>
    
    {/* Input - fixed at bottom, never moves, never inside scroll */}
    <footer className="flex-shrink-0">
      {input}
    </footer>
  </div>
));

MainPanel.displayName = 'MainPanel';

/**
 * ChatLayout - The stable app shell
 * 
 * RULES:
 * - This component structure NEVER changes based on messages.length
 * - Sidebar is ALWAYS mounted (visibility via CSS)
 * - MainPanel structure is ALWAYS the same
 * - Only the children (ChatArea content) changes
 */
export const ChatLayout: React.FC<ChatLayoutProps> = memo(({
  sidebar,
  sidebarOpen,
  header,
  children,
  input,
  overlays,
  background,
  onMobileOverlayClick,
  scrollContainerRef
}) => {
  const isMobile = useIsMobile();

  return (
    <div 
      className={cn(
        "flex bg-background relative overflow-hidden",
        // Use dvh for mobile viewport handling (iOS Safari, Android keyboard)
        isMobile ? "h-[100dvh]" : "h-screen"
      )}
    >
      {/* Background - always present */}
      {background}
      
      {/* Desktop sidebar - always mounted */}
      <DesktopSidebar isOpen={sidebarOpen}>
        {sidebar}
      </DesktopSidebar>
      
      {/* Mobile sidebar drawer - pass sidebarOpen directly, md:hidden handles desktop hiding */}
      <MobileSidebar isOpen={sidebarOpen} onOverlayClick={onMobileOverlayClick}>
        {sidebar}
      </MobileSidebar>
      
      {/* Main panel - always same structure */}
      <MainPanel header={header} input={input} isMobile={isMobile} scrollContainerRef={scrollContainerRef}>
        {children}
      </MainPanel>
      
      {/* Overlays - modals, errors, intros */}
      {overlays}
    </div>
  );
});

ChatLayout.displayName = 'ChatLayout';

export default ChatLayout;
