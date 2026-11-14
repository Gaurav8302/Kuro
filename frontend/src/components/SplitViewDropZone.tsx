import React from 'react';
import { useDroppable } from '@dnd-kit/core';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { LayoutMode } from '@/types';
import { PanelLeft, PanelRight, Maximize, PanelTop, PanelBottom, Columns3 } from 'lucide-react';
import { useIsMobile } from '@/hooks/use-mobile';
import { useSplitView } from '@/contexts/SplitViewContext';

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
        'flex flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed transition-all [transition-duration:150ms]',
        'min-h-[140px] min-w-[140px]',
        isOver
          ? 'border-primary bg-primary/[0.14] scale-[1.02] shadow-xl shadow-primary/10 ring-2 ring-primary/50'
          : 'border-border/80 bg-background/70 hover:border-primary/50',
        className
      )}
    >
      <div className={cn('transition-all duration-150', isOver ? 'text-primary scale-125' : 'text-muted-foreground/70')}>{icon}</div>
      <span className={cn('k-label !text-[11px] font-semibold transition-colors', isOver ? '!text-primary font-bold' : '!text-muted-foreground/80')}>{label}</span>
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
  const splitView = useSplitView();
  const panelsCount = splitView.layout.panels.length;

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
            isVisible ? 'pointer-events-auto' : 'pointer-events-none'
          )}
          initial={{ opacity: 0 }}
          animate={{ opacity: isVisible ? 1 : 0 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          style={{
            opacity,
            pointerEvents,
            visibility: isVisible ? 'visible' : 'hidden',
          }}>
          {/* Backdrop */}
          <div className="absolute inset-0 bg-background/80 pointer-events-none" />

          {/* Drop zones */}
          <div className={cn(
            'relative z-10 w-full h-full',
            isVisible ? 'pointer-events-auto' : 'pointer-events-none',
            isMobile ? 'flex flex-col gap-4' : 'flex gap-4'
          )}>
            {isMobile ? (
              currentMode === 'single' || panelsCount <= 1 ? (
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
              ) : panelsCount === 2 ? (
                <>
                  <DropZoneArea
                    id="drop-top"
                    label="Open on top (3-way)"
                    icon={<PanelTop className="w-6 h-6" />}
                    className="flex-1"
                  />
                  <DropZoneArea
                    id="drop-center"
                    label="Open in middle (3-way)"
                    icon={<Columns3 className="w-6 h-6" />}
                    className="flex-1"
                  />
                  <DropZoneArea
                    id="drop-bottom"
                    label="Open on bottom (3-way)"
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
                    id="drop-center"
                    label="Replace middle panel"
                    icon={<Columns3 className="w-6 h-6" />}
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
              currentMode === 'single' || panelsCount <= 1 ? (
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
              ) : panelsCount === 2 ? (
                <>
                  <DropZoneArea
                    id="drop-left"
                    label="Open on left (3-way)"
                    icon={<PanelLeft className="w-6 h-6" />}
                    className="flex-1"
                  />
                  <DropZoneArea
                    id="drop-center"
                    label="Open in middle (3-way)"
                    icon={<Columns3 className="w-6 h-6" />}
                    className="flex-1"
                  />
                  <DropZoneArea
                    id="drop-right"
                    label="Open on right (3-way)"
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
                    id="drop-center"
                    label="Replace middle panel"
                    icon={<Columns3 className="w-6 h-6" />}
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
