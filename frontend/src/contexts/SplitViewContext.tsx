import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { SplitViewState, PanelPosition, PanelState, DropZone } from '@/types';
import { useIsMobile } from '@/hooks/use-mobile';
import { useToast } from '@/hooks/use-toast';

const STORAGE_KEY = 'kuro_layout_state';

interface SplitViewContextValue {
  layout: SplitViewState;
  isDragging: boolean;
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

export const SplitViewProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const isMobile = useIsMobile();
  const { toast } = useToast();
  const [layout, setLayout] = useState<SplitViewState>(() => {
    if (isMobile) return defaultState;
    return loadFromStorage() || defaultState;
  });
  const [isDragging, setIsDragging] = useState(false);

  // Persist layout changes
  useEffect(() => {
    saveToStorage(layout);
  }, [layout]);

  // Force single mode on mobile
  useEffect(() => {
    if (isMobile && layout.mode === 'split') {
      setLayout((prev) => ({
        mode: 'single',
        panels: prev.panels.length > 0 ? [prev.panels[0]] : [],
        panelSizes: [100],
      }));
    }
  }, [isMobile]);

  const isSessionInAnyPanel = useCallback(
    (sessionId: string) => {
      return layout.panels.some((p) => p.sessionId === sessionId);
    },
    [layout.panels]
  );

  const openSessionInPanel = useCallback(
    (sessionId: string, dropZone: DropZone) => {
      if (isMobile) return;

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
        if (dropZone === 'center') {
          // Replace current panel (primary)
          const panels: PanelState[] =
            prev.panels.length === 0
              ? [{ sessionId, position: 'left' }]
              : prev.panels.map((p, i) =>
                  i === 0 ? { ...p, sessionId } : p
                );
          return { ...prev, panels };
        }

        // Left or right drop zone → split mode
        if (prev.mode === 'single') {
          const existingSessionId = prev.panels[0]?.sessionId;
          if (!existingSessionId) {
            // No existing panel, just put it in the drop zone
            return {
              mode: 'single',
              panels: [{ sessionId, position: dropZone as PanelPosition }],
              panelSizes: [100],
            };
          }

          // Create split: existing goes to opposite side, new to drop zone
          const leftPanel: PanelState =
            dropZone === 'left'
              ? { sessionId, position: 'left' }
              : { sessionId: existingSessionId, position: 'left' };
          const rightPanel: PanelState =
            dropZone === 'right'
              ? { sessionId, position: 'right' }
              : { sessionId: existingSessionId, position: 'right' };

          // Avoid same session in both
          if (leftPanel.sessionId === rightPanel.sessionId) {
            toast({
              title: 'Already open',
              description: 'This session is already open.',
              variant: 'destructive',
            });
            return prev;
          }

          return {
            mode: 'split',
            panels: [leftPanel, rightPanel],
            panelSizes: [50, 50],
          };
        }

        // Already in split mode → replace the panel at the drop position
        const panels = prev.panels.map((p) =>
          p.position === dropZone ? { ...p, sessionId } : p
        );
        return { ...prev, panels };
      });
    },
    [isMobile, isSessionInAnyPanel, toast]
  );

  const closePanel = useCallback((position: PanelPosition) => {
    setLayout((prev) => {
      const remaining = prev.panels.filter((p) => p.position !== position);
      if (remaining.length === 0) {
        return { mode: 'single', panels: [], panelSizes: [100] };
      }
      // Move remaining panel to left position
      return {
        mode: 'single',
        panels: [{ ...remaining[0], position: 'left' }],
        panelSizes: [100],
      };
    });
  }, []);

  const expandPanel = useCallback(
    (position: PanelPosition) => {
      // Close the other panel
      const oppositePosition: PanelPosition = position === 'left' ? 'right' : 'left';
      closePanel(oppositePosition);
    },
    [closePanel]
  );

  const setPrimarySessionId = useCallback((sessionId: string) => {
    setLayout((prev) => {
      if (prev.panels.length === 0) {
        return {
          ...prev,
          panels: [{ sessionId, position: 'left' as PanelPosition }],
        };
      }
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
