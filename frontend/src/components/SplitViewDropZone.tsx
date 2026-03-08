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
        'flex flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed transition-all duration-200',
        isOver
          ? 'border-primary bg-primary/10 scale-[1.02]'
          : 'border-muted-foreground/30 bg-background/50',
        className
      )}
    >
      <div
        className={cn(
          'p-3 rounded-xl transition-colors',
          isOver ? 'bg-primary/20 text-primary' : 'bg-secondary text-muted-foreground'
        )}
      >
        {icon}
      </div>
      <span
        className={cn(
          'text-sm font-medium transition-colors',
          isOver ? 'text-primary' : 'text-muted-foreground'
        )}
      >
        {label}
      </span>
    </div>
  );
};

interface SplitViewDropZoneProps {
  isVisible: boolean;
  currentMode: LayoutMode;
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
}) => {
  const isMobile = useIsMobile();

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          className={cn(
            'absolute inset-0 z-40 p-6',
            isMobile ? 'flex flex-col gap-4' : 'flex gap-4'
          )}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
        >
          {/* Backdrop */}
          <div className="absolute inset-0 bg-background/80 backdrop-blur-sm rounded-lg" />

          {/* Drop zones */}
          <div className={cn(
            'relative z-10 w-full h-full',
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
