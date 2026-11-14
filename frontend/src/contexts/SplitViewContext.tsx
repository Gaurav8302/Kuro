import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { SplitViewState, PanelPosition, PanelState, DropZone } from '@/types';
import { useIsMobile } from '@/hooks/use-mobile';
import { useToast } from '@/hooks/use-toast';

const STORAGE_KEY = 'kuro_layout_state';

interface SplitViewContextValue {
  layout: SplitViewState;
  isDragging: boolean;
  isMobileSplit: boolean;
  setIsDragging: (dragging: boolean) => void;
  openSessionInPanel: (sessionId: string, dropZone: DropZone, currentSessionId?: string | null) => void;
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
    (sessionId: string, dropZone: DropZone, currentSessionId?: string | null) => {
      setLayout((prev) => {
        if (dropZone === 'center') {
          // Replace current panel (primary) in single mode
          const primaryPos: PanelPosition = isMobile ? 'top' : 'left';
          const panels: PanelState[] = [{ sessionId, position: primaryPos }];
          return { mode: 'single', panels, panelSizes: [100] };
        }

        // Split drop zone (left/right on desktop, top/bottom on mobile)
        const primaryPos: PanelPosition = isMobile ? 'top' : 'left';
        const secondaryPos: PanelPosition = isMobile ? 'bottom' : 'right';
        const isDropOnPrimary = dropZone === 'left' || dropZone === 'top';

        if (prev.mode === 'single') {
          const existingSessionId = prev.panels[0]?.sessionId || currentSessionId || null;

          let firstPanelSession = isDropOnPrimary ? sessionId : existingSessionId;
          let secondPanelSession = isDropOnPrimary ? existingSessionId : sessionId;

          if (!firstPanelSession) firstPanelSession = sessionId;
          if (!secondPanelSession) secondPanelSession = sessionId;

          // If the dropped session is identical to the only open session, don't create duplicate panels
          if (firstPanelSession === secondPanelSession) {
            return {
              mode: 'single',
              panels: [{ sessionId: firstPanelSession, position: primaryPos }],
              panelSizes: [100],
            };
          }

          return {
            mode: 'split',
            panels: [
              { sessionId: firstPanelSession, position: primaryPos },
              { sessionId: secondPanelSession, position: secondaryPos },
            ],
            panelSizes: [50, 50],
          };
        }

        // Already in split mode:
        const currentFirst = prev.panels[0]?.sessionId || '';
        const currentSecond = prev.panels[1]?.sessionId || '';

        let nextFirst = currentFirst;
        let nextSecond = currentSecond;

        if (isDropOnPrimary) {
          // Replace top/left panel
          nextFirst = sessionId;
          // If the other panel had this same session, swap so both panels aren't the same
          if (nextSecond === sessionId && currentFirst && currentFirst !== sessionId) {
            nextSecond = currentFirst;
          }
        } else {
          // Replace bottom/right panel
          nextSecond = sessionId;
          // If the other panel had this same session, swap so both panels aren't the same
          if (nextFirst === sessionId && currentSecond && currentSecond !== sessionId) {
            nextFirst = currentSecond;
          }
        }

        // If somehow both panels ended up with the same session ID, collapse to single mode
        if (nextFirst === nextSecond) {
          return {
            mode: 'single',
            panels: [{ sessionId: nextFirst, position: primaryPos }],
            panelSizes: [100],
          };
        }

        return {
          mode: 'split',
          panels: [
            { sessionId: nextFirst, position: primaryPos },
            { sessionId: nextSecond, position: secondaryPos },
          ],
          panelSizes: prev.panelSizes && prev.panelSizes.length === 2 ? prev.panelSizes : [50, 50],
        };
      });
    },
    [isMobile]
  );

  const closePanel = useCallback((position: PanelPosition) => {
    setLayout((prev) => {
      const remaining = prev.panels.filter((p) => p.position !== position);
      if (remaining.length === 0) {
        return { mode: 'single', panels: [], panelSizes: [100] };
      }
      // Move remaining panel to primary position
      const primaryPos: PanelPosition = isMobile ? 'top' : 'left';
      return {
        mode: 'single',
        panels: [{ ...remaining[0], position: primaryPos }],
        panelSizes: [100],
      };
    });
  }, [isMobile]);

  const expandPanel = useCallback(
    (position: PanelPosition) => {
      setLayout((prev) => {
        const otherPanel = prev.panels.find((p) => p.position !== position);
        if (otherPanel) {
          const remaining = prev.panels.filter((p) => p.position === position);
          const primaryPos: PanelPosition = isMobile ? 'top' : 'left';
          return {
            mode: 'single',
            panels: remaining.length > 0 ? [{ ...remaining[0], position: primaryPos }] : [],
            panelSizes: [100],
          };
        }
        return prev;
      });
    },
    [isMobile]
  );

  const setPrimarySessionId = useCallback((sessionId: string) => {
    setLayout((prev) => {
      if (prev.panels.length === 0) {
        const primaryPos: PanelPosition = isMobile ? 'top' : 'left';
        return {
          ...prev,
          panels: [{ sessionId, position: primaryPos }],
        };
      }
      
      // OPTIMIZATION: Do not update layout state if the sessionId is already the primary one
      if (prev.panels[0].sessionId === sessionId) {
        return prev;
      }

      const panels = prev.panels.map((p, i) =>
        i === 0 ? { ...p, sessionId } : p
      );
      return { ...prev, panels };
    });
  }, [isMobile]);

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
