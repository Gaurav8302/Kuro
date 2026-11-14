import React from 'react';
import { useDroppable } from '@dnd-kit/core';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { LayoutMode } from '@/types';
import { PanelLeft, PanelRight, Maximize, PanelTop, PanelBottom } from 'lucide-react';
import { useIsMobile } from '@/hooks/use-mobile';

interface DropZoneAreaProps {
  id: string;
  label: string;
  icon: React.ReactNode;
  className?: string;
}

const DropZoneArea: React.FC<DropZoneAreaProps> = ({ id, label, icon, className }) => {
  const { isOver, setNodeRef } = useDroppable({ id });

  return (
    <div
      ref={setNodeRef}
      className={cn(
        'flex flex-col items-center justify-center gap-3 rounded-md border border-dashed transition-colors [transition-duration:180ms]',
        'min-h-[180px] min-w-[180px]', // Ensure minimum hit area for reliable drop detection
        isOver ? 'border-primary/70 bg-primary/[0.06]' : 'border-border',
        className
      )}
    >
      <div className={cn('transition-colors', isOver ? 'text-primary' : 'text-muted-foreground/70')}>{icon}</div>
      <span className={cn('k-label !text-[10px]', isOver ? '!text-primary' : '!text-muted-foreground/70')}>{label}</span>
    </div>
  );
};

interface SplitViewDropZoneProps {
  isVisible: boolean;
  currentMode: LayoutMode;
  alwaysMounted?: boolean;
}

/**
 * SplitViewDropZone - Overlay rendered during drag operations.
 *
 * Shows visual drop targets over the main content area:
 * - Desktop single mode: left / center / right zones
 * - Desktop split mode: left / right zones (replace existing panel)
 * - Mobile single mode: top / center / bottom zones
 * - Mobile split mode: top / bottom zones (replace existing panel)
 */
export const SplitViewDropZone: React.FC<SplitViewDropZoneProps> = ({
  isVisible,
  currentMode,
  alwaysMounted = false,
}) => {
  const isMobile = useIsMobile();

  // When alwaysMounted is true, we always render but control visibility via CSS
  // This ensures droppable zones are registered before drag starts
  const shouldRender = alwaysMounted || isVisible;
  const opacity = isVisible ? 1 : 0;
  const pointerEvents = isVisible ? 'auto' : 'none';

  return (
    <AnimatePresence>
      {shouldRender && (
        <motion.div
          className={cn(
            'p-6',
            // On mobile use fixed positioning with high z-index to render above the sidebar (z-50)
            isMobile
              ? 'fixed inset-0 z-[60] flex flex-col gap-4'
              : 'absolute inset-0 z-40 flex gap-4',
          )}
          initial={{ opacity: 0 }}
          animate={{ opacity: isVisible ? 1 : 0 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          style={{ opacity, pointerEvents }}>
          {/* Backdrop */}
          <div className="absolute inset-0 bg-background/80 pointer-events-none" />

          {/* Drop zones */}
          <div className={cn(
            'relative z-10 w-full h-full pointer-events-auto',
            isMobile ? 'flex flex-col gap-4' : 'flex gap-4'
          )}>
            {isMobile ? (
              // Mobile: top / center / bottom (or top / bottom in split)
              currentMode === 'single' ? (
                <>
                  <DropZoneArea
                    id="drop-top"
                    label="Open on top"
                    icon={<PanelTop className="w-6 h-6" />}
                    className="flex-1"
                  />
                  <DropZoneArea
                    id="drop-center"
                    label="Replace current"
                    icon={<Maximize className="w-6 h-6" />}
                    className="flex-1"
                  />
                  <DropZoneArea
                    id="drop-bottom"
                    label="Open on bottom"
                    icon={<PanelBottom className="w-6 h-6" />}
                    className="flex-1"
                  />
                </>
              ) : (
                <>
                  <DropZoneArea
                    id="drop-top"
                    label="Replace top panel"
                    icon={<PanelTop className="w-6 h-6" />}
                    className="flex-1"
                  />
                  <DropZoneArea
                    id="drop-bottom"
                    label="Replace bottom panel"
                    icon={<PanelBottom className="w-6 h-6" />}
                    className="flex-1"
                  />
                </>
              )
            ) : (
              // Desktop: left / center / right (or left / right in split)
              currentMode === 'single' ? (
                <>
                  <DropZoneArea
                    id="drop-left"
                    label="Open on left"
                    icon={<PanelLeft className="w-6 h-6" />}
                    className="flex-1"
                  />
                  <DropZoneArea
                    id="drop-center"
                    label="Replace current"
                    icon={<Maximize className="w-6 h-6" />}
                    className="flex-1"
                  />
                  <DropZoneArea
                    id="drop-right"
                    label="Open on right"
                    icon={<PanelRight className="w-6 h-6" />}
                    className="flex-1"
                  />
                </>
              ) : (
                <>
                  <DropZoneArea
                    id="drop-left"
                    label="Replace left panel"
                    icon={<PanelLeft className="w-6 h-6" />}
                    className="flex-1"
                  />
                  <DropZoneArea
                    id="drop-right"
                    label="Replace right panel"
                    icon={<PanelRight className="w-6 h-6" />}
                    className="flex-1"
                  />
                </>
              )
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default SplitViewDropZone;
