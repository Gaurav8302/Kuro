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

const defaultState: SplitViewState = {
  mode: 'single',
  panels: [],
  panelSizes: [100],
};

export const SplitViewProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const isMobile = useIsMobile();
  const { toast } = useToast();
  // Always start with a clean default state so new chat opens fresh
  const [layout, setLayout] = useState<SplitViewState>(defaultState);
  const [isDragging, setIsDragging] = useState(false);

  // Clear stale local storage on startup if it contains old single-mode sessions
  useEffect(() => {
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      // Ignore
    }
  }, []);

  // When switching between mobile and desktop, remap panel positions
  useEffect(() => {
    if (layout.mode !== 'split') return;

    setLayout((prev) => {
      if (prev.mode !== 'split') return prev;

      if (isMobile) {
        // Desktop → Mobile
        const remapped = prev.panels.map((p, i) => {
          let pos: PanelPosition = 'top';
          if (prev.panels.length === 2) {
            pos = i === 0 ? 'top' : 'bottom';
          } else if (prev.panels.length === 3) {
            pos = i === 0 ? 'top' : i === 1 ? 'center' : 'bottom';
          }
          return { ...p, position: pos };
        });
        return { ...prev, panels: remapped };
      } else {
        // Mobile → Desktop
        const remapped = prev.panels.map((p, i) => {
          let pos: PanelPosition = 'left';
          if (prev.panels.length === 2) {
            pos = i === 0 ? 'left' : 'right';
          } else if (prev.panels.length === 3) {
            pos = i === 0 ? 'left' : i === 1 ? 'center' : 'right';
          }
          return { ...p, position: pos };
        });
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
        const isDropLeftOrTop = dropZone === 'left' || dropZone === 'top';
        const isDropCenter = dropZone === 'center';
        const isDropRightOrBottom = dropZone === 'right' || dropZone === 'bottom';

        const posLeftTop: PanelPosition = isMobile ? 'top' : 'left';
        const posCenter: PanelPosition = 'center';
        const posRightBottom: PanelPosition = isMobile ? 'bottom' : 'right';

        // 1. If currently in SINGLE mode:
        if (prev.mode === 'single' || prev.panels.length <= 1) {
          if (isDropCenter) {
            // Replace current panel with dropped session in single mode
            return {
              mode: 'single',
              panels: [{ sessionId, position: posLeftTop }],
              panelSizes: [100],
            };
          }

          const existingSessionId = prev.panels[0]?.sessionId || currentSessionId || null;
          let firstSession = isDropLeftOrTop ? sessionId : existingSessionId;
          let secondSession = isDropLeftOrTop ? existingSessionId : sessionId;

          if (!firstSession) firstSession = sessionId;
          if (!secondSession) secondSession = sessionId;

          // If the dropped session is identical to the only open session, don't create duplicate panels
          if (firstSession === secondSession) {
            return {
              mode: 'single',
              panels: [{ sessionId: firstSession, position: posLeftTop }],
              panelSizes: [100],
            };
          }

          return {
            mode: 'split',
            panels: [
              { sessionId: firstSession, position: posLeftTop },
              { sessionId: secondSession, position: posRightBottom },
            ],
            panelSizes: [50, 50],
          };
        }

        // 2. If currently in 2-PANEL SPLIT mode -> dragging another session creates a 3-WAY SPLIT!
        if (prev.panels.length === 2) {
          const currentP0 = prev.panels[0]?.sessionId;
          const currentP1 = prev.panels[1]?.sessionId;

          // Remove any existing occurrences of sessionId to prevent duplicates
          const existingList = [currentP0, currentP1].filter((id) => Boolean(id) && id !== sessionId);

          let nextPanels: string[] = [];
          if (isDropLeftOrTop) {
            // Insert at beginning: [dropped, ...existingList]
            nextPanels = [sessionId, ...existingList];
          } else if (isDropCenter) {
            // Insert in middle: [existing0, dropped, existing1]
            if (existingList.length >= 2) {
              nextPanels = [existingList[0], sessionId, existingList[1]];
            } else {
              nextPanels = [currentP0, sessionId, currentP1];
            }
          } else {
            // Insert at end: [...existingList, dropped]
            nextPanels = [...existingList, sessionId];
          }

          // If less than 3 unique sessions exist, keep 2 panels
          if (nextPanels.length < 3) {
            return {
              mode: 'split',
              panels: [
                { sessionId: nextPanels[0], position: posLeftTop },
                { sessionId: nextPanels[1] || sessionId, position: posRightBottom },
              ],
              panelSizes: [50, 50],
            };
          }

          // 3-way split: 3 panels
          return {
            mode: 'split',
            panels: [
              { sessionId: nextPanels[0], position: posLeftTop },
              { sessionId: nextPanels[1], position: posCenter },
              { sessionId: nextPanels[2], position: posRightBottom },
            ],
            panelSizes: [33.33, 33.33, 33.34],
          };
        }

        // 3. If ALREADY in 3-PANEL SPLIT mode (max 3): replace the target zone panel
        const currentPanels = [...prev.panels];
        let targetIndex = 0;
        if (isDropCenter) targetIndex = 1;
        else if (isDropRightOrBottom) targetIndex = 2;

        const existingIdx = currentPanels.findIndex((p) => p.sessionId === sessionId);
        if (existingIdx !== -1 && existingIdx !== targetIndex) {
          // Swap positions if dropped session is already in another panel
          const temp = currentPanels[targetIndex].sessionId;
          currentPanels[targetIndex] = { ...currentPanels[targetIndex], sessionId };
          currentPanels[existingIdx] = { ...currentPanels[existingIdx], sessionId: temp };
        } else {
          currentPanels[targetIndex] = { ...currentPanels[targetIndex], sessionId };
        }

        return {
          mode: 'split',
          panels: currentPanels,
          panelSizes: prev.panelSizes && prev.panelSizes.length === 3 ? prev.panelSizes : [33.33, 33.33, 33.34],
        };
      });
    },
    [isMobile]
  );

  const closePanel = useCallback(
    (position: PanelPosition) => {
      setLayout((prev) => {
        const remaining = prev.panels.filter((p) => p.position !== position);
        if (remaining.length === 0) {
          return { mode: 'single', panels: [], panelSizes: [100] };
        }

        const posLeftTop: PanelPosition = isMobile ? 'top' : 'left';
        const posCenter: PanelPosition = 'center';
        const posRightBottom: PanelPosition = isMobile ? 'bottom' : 'right';

        // 1 panel remaining -> return to single mode
        if (remaining.length === 1) {
          return {
            mode: 'single',
            panels: [{ ...remaining[0], position: posLeftTop }],
            panelSizes: [100],
          };
        }

        // 2 panels remaining -> return to 2-panel split
        if (remaining.length === 2) {
          return {
            mode: 'split',
            panels: [
              { ...remaining[0], position: posLeftTop },
              { ...remaining[1], position: posRightBottom },
            ],
            panelSizes: [50, 50],
          };
        }

        // 3 panels remaining
        return {
          mode: 'split',
          panels: [
            { ...remaining[0], position: posLeftTop },
            { ...remaining[1], position: posCenter },
            { ...remaining[2], position: posRightBottom },
          ],
          panelSizes: [33.33, 33.33, 33.34],
        };
      });
    },
    [isMobile]
  );

  const expandPanel = useCallback(
    (position: PanelPosition) => {
      setLayout((prev) => {
        const target = prev.panels.find((p) => p.position === position) || prev.panels[0];
        const primaryPos: PanelPosition = isMobile ? 'top' : 'left';
        if (target) {
          return {
            mode: 'single',
            panels: [{ ...target, position: primaryPos }],
            panelSizes: [100],
          };
        }
        return prev;
      });
    },
    [isMobile]
  );

  const setPrimarySessionId = useCallback(
    (sessionId: string) => {
      setLayout((prev) => {
        if (prev.panels.length === 0) {
          const primaryPos: PanelPosition = isMobile ? 'top' : 'left';
          return {
            ...prev,
            panels: [{ sessionId, position: primaryPos }],
          };
        }

        if (prev.panels[0].sessionId === sessionId) {
          return prev;
        }

        const panels = prev.panels.map((p, i) => (i === 0 ? { ...p, sessionId } : p));
        return { ...prev, panels };
      });
    },
    [isMobile]
  );

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

export const useSplitView = (): SplitViewContextValue => {
  const context = useContext(SplitViewContext);
  if (!context) {
    throw new Error('useSplitView must be used within a SplitViewProvider');
  }
  return context;
};
