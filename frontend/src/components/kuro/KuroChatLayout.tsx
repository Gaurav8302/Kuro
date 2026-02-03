import { memo, ReactNode } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { Menu } from 'lucide-react';
import { KuroBackground } from './KuroBackground';
import { useIsMobile } from '@/hooks/use-mobile';
import { overlayVariants } from '@/utils/animations';

interface KuroChatLayoutProps {
  sidebar: ReactNode;
  sidebarOpen: boolean;
  header?: ReactNode;
  children: ReactNode;
  input: ReactNode;
  onToggleSidebar: () => void;
  onCloseSidebar: () => void;
  className?: string;
}

/**
 * KuroChatLayout - Professional chat layout
 * Clean layout with sidebar, main content, and fixed input
 */
export const KuroChatLayout = memo(function KuroChatLayout({
  sidebar,
  sidebarOpen,
  header,
  children,
  input,
  onToggleSidebar,
  onCloseSidebar,
  className,
}: KuroChatLayoutProps) {
  const isMobile = useIsMobile();

  return (
    <div className={cn('h-screen flex bg-background', className)}>
      <KuroBackground variant="subtle" />

      {/* Desktop sidebar */}
      {!isMobile && sidebarOpen && (
        <div className="relative z-20 flex-shrink-0">
          {sidebar}
        </div>
      )}

      {/* Mobile sidebar overlay */}
      <AnimatePresence>
        {isMobile && sidebarOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              className="fixed inset-0 z-30 bg-black/60 backdrop-blur-sm"
              variants={overlayVariants}
              initial="hidden"
              animate="visible"
              exit="exit"
              onClick={onCloseSidebar}
            />
            
            {/* Sidebar */}
            <motion.div
              className="fixed inset-y-0 left-0 z-40 w-72"
              initial={{ x: '-100%' }}
              animate={{ x: 0 }}
              exit={{ x: '-100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            >
              {sidebar}
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Main content area */}
      <div className="flex-1 flex flex-col relative z-10 min-w-0">
        {/* Header */}
        <header className="flex-shrink-0 h-14 flex items-center gap-3 px-4 border-b border-white/5">
          {/* Menu button */}
          <button
            onClick={onToggleSidebar}
            className={cn(
              'p-2 rounded-lg transition-colors',
              'text-muted-foreground hover:text-foreground',
              'hover:bg-white/5'
            )}
          >
            <Menu className="w-5 h-5" />
          </button>
          
          {header}
        </header>

        {/* Messages area */}
        <main className="flex-1 overflow-hidden">
          {children}
        </main>

        {/* Input area */}
        <div className="flex-shrink-0 border-t border-white/5">
          {input}
        </div>
      </div>
    </div>
  );
});

export default KuroChatLayout;
