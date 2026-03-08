import React, { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react';
import { SplitViewState, PanelPosition, PanelState, DropZone } from '@/types';
import { useIsMobile } from '@/hooks/use-mobile';
import { useToast } from '@/hooks/use-toast';

const STORAGE_KEY = 'kuro_layout_state';

interface SplitViewContextValue {
  layout: SplitViewState;
  isDragging: boolean;
  isMobileSplit: boolean;
  setIsDragging: (dragging: boolean) => void;
  openSessionInPanel: (sessionId: string, dropZone: DropZone) => void;
  closePanel: (position: PanelPosition) => void;
  expandPanel: (position: PanelPosition) => void;
  isSessionInAnyPanel: (sessionId: string) => boolean;
  setPrimarySessionId: (sessionId: string) => void;
  updatePanelSizes: (sizes: number[]) => void;
}

const SplitViewContext = createContext<SplitViewContextValue | null>(null);

function loadFromStorage(): SplitViewState | null {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored) as SplitViewState;
      if (parsed.mode && parsed.panels) return parsed;
    }
  } catch {
    // Ignore
  }
  return null;
}

function saveToStorage(state: SplitViewState) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    // Ignore
  }
}

const defaultState: SplitViewState = {
  mode: 'single',
  panels: [],
  panelSizes: [50, 50],
};

/**
 * Map desktop drop zones (left/right) to mobile equivalents (top/bottom)
 * and vice versa when needed.
 */
function mobilePanelPosition(dropZone: DropZone): PanelPosition {
  if (dropZone === 'left' || dropZone === 'top') return 'top';
  if (dropZone === 'right' || dropZone === 'bottom') return 'bottom';
  return 'top'; // center -> primary -> top
}

function desktopPanelPosition(dropZone: DropZone): PanelPosition {
  if (dropZone === 'top' || dropZone === 'left') return 'left';
  if (dropZone === 'bottom' || dropZone === 'right') return 'right';
  return 'left';
}

export const SplitViewProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const isMobile = useIsMobile();
  const isMobileRef = useRef(isMobile);
  isMobileRef.current = isMobile;
  const { toast } = useToast();
  const [layout, setLayout] = useState<SplitViewState>(() => {
    // On mobile, always start with clean default (no restored split)
    if (isMobile) return defaultState;
    return loadFromStorage() || defaultState;
  });
  const [isDragging, setIsDragging] = useState(false);

  // Persist layout changes
  useEffect(() => {
    saveToStorage(layout);
  }, [layout]);

  // When switching between mobile and desktop, remap panel positions
  useEffect(() => {
    if (layout.mode !== 'split') return;

    setLayout((prev) => {
      if (prev.mode !== 'split') return prev;

      if (isMobile) {
        // Desktop → Mobile: remap left/right → top/bottom
        const remapped = prev.panels.map((p, i) => ({
          ...p,
          position: (i === 0 ? 'top' : 'bottom') as PanelPosition,
        }));
        return { ...prev, panels: remapped };
      } else {
        // Mobile → Desktop: remap top/bottom → left/right
        const remapped = prev.panels.map((p, i) => ({
          ...p,
          position: (i === 0 ? 'left' : 'right') as PanelPosition,
        }));
        return { ...prev, panels: remapped };
      }
    });
  }, [isMobile]);

  const isMobileSplit = isMobile && layout.mode === 'split';

  const isSessionInAnyPanel = useCallback(
    (sessionId: string) => {
      return layout.panels.some((p) => p.sessionId === sessionId);
    },
    [layout.panels]
  );

  const openSessionInPanel = useCallback(
    (sessionId: string, dropZone: DropZone) => {
      // Check duplicate
      if (isSessionInAnyPanel(sessionId)) {
        toast({
          title: 'Already open',
          description: 'This session is already open in a panel.',
          variant: 'destructive',
        });
        return;
      }

      setLayout((prev) => {
        const mobile = isMobileRef.current;
        const positionFn = mobile ? mobilePanelPosition : desktopPanelPosition;

        if (dropZone === 'center') {
          // Replace current panel (primary)
          const panels: PanelState[] =
            prev.panels.length === 0
              ? [{ sessionId, position: mobile ? 'top' : 'left' }]
              : prev.panels.map((p, i) =>
                  i === 0 ? { ...p, sessionId } : p
                );
          return { ...prev, panels };
        }

        // Split drop zone
        if (prev.mode === 'single') {
          const existingSessionId = prev.panels[0]?.sessionId;
          if (!existingSessionId) {
            return {
              mode: 'single',
              panels: [{ sessionId, position: positionFn(dropZone) }],
              panelSizes: [100],
            };
          }

          // Create split
          const primaryPos: PanelPosition = mobile ? 'top' : 'left';
          const secondaryPos: PanelPosition = mobile ? 'bottom' : 'right';

          const isDropOnPrimary = dropZone === 'left' || dropZone === 'top';

          const firstPanel: PanelState = isDropOnPrimary
            ? { sessionId, position: primaryPos }
            : { sessionId: existingSessionId, position: primaryPos };
          const secondPanel: PanelState = isDropOnPrimary
            ? { sessionId: existingSessionId, position: secondaryPos }
            : { sessionId, position: secondaryPos };

          // Avoid same session in both
          if (firstPanel.sessionId === secondPanel.sessionId) {
            toast({
              title: 'Already open',
              description: 'This session is already open.',
              variant: 'destructive',
            });
            return prev;
          }

          return {
            mode: 'split',
            panels: [firstPanel, secondPanel],
            panelSizes: [50, 50],
          };
        }

        // Already in split mode → replace the panel at the drop position
        const targetPos = positionFn(dropZone);
        const panels = prev.panels.map((p) =>
          p.position === targetPos ? { ...p, sessionId } : p
        );
        return { ...prev, panels };
      });
    },
    [isSessionInAnyPanel, toast]
  );

  const closePanel = useCallback((position: PanelPosition) => {
    setLayout((prev) => {
      const remaining = prev.panels.filter((p) => p.position !== position);
      if (remaining.length === 0) {
        return { mode: 'single', panels: [], panelSizes: [100] };
      }
      // Move remaining panel to primary position
      const primaryPos: PanelPosition = isMobileRef.current ? 'top' : 'left';
      return {
        mode: 'single',
        panels: [{ ...remaining[0], position: primaryPos }],
        panelSizes: [100],
      };
    });
  }, []);

  const expandPanel = useCallback(
    (position: PanelPosition) => {
      setLayout((prev) => {
        const kept = prev.panels.find((p) => p.position === position);
        if (!kept) return prev;
        const primaryPos: PanelPosition = isMobileRef.current ? 'top' : 'left';
        return {
          mode: 'single',
          panels: [{ ...kept, position: primaryPos }],
          panelSizes: [100],
        };
      });
    },
    []
  );

  const setPrimarySessionId = useCallback((sessionId: string) => {
    setLayout((prev) => {
      if (prev.panels.length === 0) {
        const primaryPos: PanelPosition = isMobileRef.current ? 'top' : 'left';
        return {
          ...prev,
          panels: [{ sessionId, position: primaryPos }],
        };
      }
      // Only update if actually different
      if (prev.panels[0]?.sessionId === sessionId) return prev;
      const panels = prev.panels.map((p, i) =>
        i === 0 ? { ...p, sessionId } : p
      );
      return { ...prev, panels };
    });
  }, []);

  const updatePanelSizes = useCallback((sizes: number[]) => {
    setLayout((prev) => ({ ...prev, panelSizes: sizes }));
  }, []);

  return (
    <SplitViewContext.Provider
      value={{
        layout,
        isDragging,
        isMobileSplit,
        setIsDragging,
        openSessionInPanel,
        closePanel,
        expandPanel,
        isSessionInAnyPanel,
        setPrimarySessionId,
        updatePanelSizes,
      }}
    >
      {children}
    </SplitViewContext.Provider>
  );
};

export function useSplitView() {
  const ctx = useContext(SplitViewContext);
  if (!ctx) {
    throw new Error('useSplitView must be used within a SplitViewProvider');
  }
  return ctx;
}
