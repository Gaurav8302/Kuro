import React, { createContext, useCallback, useContext, useMemo, useReducer, useRef } from 'react';
import { ChatSessionManager } from '@/lib/ChatSessionManager';
import type { FloatingRect } from '@/types/workspace';

export type DockKind = 'full' | 'left' | 'right';
export type WindowKind = DockKind | 'floating';

export type ChatMessage = {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
};

export type ChatWindowEntry = {
  id: string; // window id
  kind: WindowKind;
  chatId: string;
  rect?: FloatingRect; // for floating
};

type State = {
  activeChats: string[]; // up to 2 distinct chatIds
  windows: ChatWindowEntry[]; // dock + floating windows
  messages: Record<string, ChatMessage[]>; // per chatId
  isLoading: Record<string, boolean>; // per chatId
  sessions: Record<string, string | undefined>; // chatId -> sessionId
};

export type DropResult = { ok: true } | { ok: false; reason: 'limit' | 'duplicate' };

type Action =
  | { type: 'SET_WINDOW'; window: ChatWindowEntry }
  | { type: 'REPLACE_DOCK'; kind: DockKind; chatId: string }
  | { type: 'REMOVE_WINDOW'; windowId: string }
  | { type: 'SET_FLOAT_RECT'; windowId: string; rect: FloatingRect }
  | { type: 'ENSURE_ACTIVE_CHAT'; chatId: string }
  | { type: 'DEACTIVATE_CHAT'; chatId: string }
  | { type: 'APPEND_MESSAGE'; chatId: string; message: ChatMessage }
  | { type: 'SET_LOADING'; chatId: string; value: boolean }
  | { type: 'SET_SESSION'; chatId: string; sessionId?: string };

const initialState: State = {
  activeChats: [],
  windows: [],
  messages: {},
  isLoading: {},
  sessions: {},
};

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'ENSURE_ACTIVE_CHAT': {
      if (state.activeChats.includes(action.chatId)) return state;
      return { ...state, activeChats: [...state.activeChats, action.chatId].slice(-2) };
    }
    case 'DEACTIVATE_CHAT': {
      const activeChats = state.activeChats.filter(id => id !== action.chatId);
      const windows = state.windows.filter(w => w.chatId !== action.chatId);
      const { [action.chatId]: _omitM, ...messages } = state.messages;
      const { [action.chatId]: _omitL, ...isLoading } = state.isLoading;
      const { [action.chatId]: _omitS, ...sessions } = state.sessions;
      return { ...state, activeChats, windows, messages, isLoading, sessions };
    }
    case 'SET_WINDOW': {
      const idx = state.windows.findIndex(w => w.id === action.window.id);
      const windows = idx >= 0
        ? state.windows.map(w => (w.id === action.window.id ? action.window : w))
        : [...state.windows, action.window];
      return { ...state, windows };
    }
    case 'REPLACE_DOCK': {
      const existing = state.windows.find(w => w.kind === action.kind);
      const windowId = existing?.id || `${action.kind}-dock`;
      const otherWindows = state.windows.filter(w => w.id !== windowId && !(action.kind === 'full' && (w.kind === 'left' || w.kind === 'right')));
      const newWindow: ChatWindowEntry = { id: windowId, kind: action.kind, chatId: action.chatId };
      return { ...state, windows: [...otherWindows, newWindow] };
    }
    case 'REMOVE_WINDOW': {
      return { ...state, windows: state.windows.filter(w => w.id !== action.windowId) };
    }
    case 'SET_FLOAT_RECT': {
      return { ...state, windows: state.windows.map(w => (w.id === action.windowId ? { ...w, rect: action.rect } : w)) };
    }
    case 'APPEND_MESSAGE': {
      const prev = state.messages[action.chatId] || [];
      return { ...state, messages: { ...state.messages, [action.chatId]: [...prev, action.message] } };
    }
    case 'SET_LOADING': {
      return { ...state, isLoading: { ...state.isLoading, [action.chatId]: action.value } };
    }
    case 'SET_SESSION': {
      return { ...state, sessions: { ...state.sessions, [action.chatId]: action.sessionId } };
    }
    default:
      return state;
  }
}

type Ctx = {
  state: State;
  dropChatTo: (chatId: string, target: WindowKind, bounds?: DOMRect) => DropResult;
  openFloating: (chatId: string, bounds?: DOMRect) => DropResult;
  closeWindow: (windowId: string) => void;
  closeChat: (chatId: string) => void;
  sendMessage: (chatId: string, content: string) => Promise<void>;
  setFloatingRect: (windowId: string, rect: FloatingRect) => void;
};

const ChatWorkspaceContext = createContext<Ctx | null>(null);

export function useChatWorkspace() {
  const ctx = useContext(ChatWorkspaceContext);
  if (!ctx) throw new Error('useChatWorkspace must be used within ChatWorkspaceProvider');
  return ctx;
}

function nextFloatRect(existing: FloatingRect[], bounds?: DOMRect): FloatingRect {
  const baseWidth = 420;
  const baseHeight = 320;
  const margin = 16;
  const bx = bounds ? bounds.width : 1200;
  const by = bounds ? bounds.height : 800;
  const positions = [
    { x: margin, y: margin },
    { x: bx - baseWidth - margin, y: margin },
    { x: margin, y: by - baseHeight - margin },
    { x: bx - baseWidth - margin, y: by - baseHeight - margin },
    { x: (bx - baseWidth) / 2, y: (by - baseHeight) / 2 },
  ];
  for (const pos of positions) {
    const rect: FloatingRect = { x: Math.max(margin, pos.x), y: Math.max(margin, pos.y), width: baseWidth, height: baseHeight };
    const overlaps = existing.some(r => !(rect.x + rect.width + 8 < r.x || r.x + r.width + 8 < rect.x || rect.y + rect.height + 8 < r.y || r.y + r.height + 8 < rect.y));
    if (!overlaps) return rect;
  }
  const n = existing.length;
  return { x: margin + 24 * n, y: margin + 24 * n, width: baseWidth, height: baseHeight };
}

export function ChatWorkspaceProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState);
  const sessionMgrRef = useRef(ChatSessionManager.getInstance());

  const ensureSession = useCallback((chatId: string) => {
    const existingSessionId = state.sessions[chatId];
    if (existingSessionId) return existingSessionId;
    const wsUrl = `ws://localhost:8000/ws/${chatId}`; // TODO: replace with real
    const sessionId = sessionMgrRef.current.openSession(chatId, wsUrl);
    dispatch({ type: 'SET_SESSION', chatId, sessionId });
    sessionMgrRef.current.onMessage(sessionId, ({ type, payload }) => {
      if (type === 'chunk' || type === 'done') {
        const content = String(payload ?? '');
        dispatch({ type: 'APPEND_MESSAGE', chatId, message: { id: `${Date.now()}`, role: 'assistant', content, timestamp: Date.now() } });
        dispatch({ type: 'SET_LOADING', chatId, value: false });
      } else if (type === 'error') {
        dispatch({ type: 'SET_LOADING', chatId, value: false });
      }
    });
    return sessionId;
  }, [state.sessions]);

  const enforceMaxTwoChats = useCallback((chatId: string): DropResult => {
    const uniqueChats = new Set(state.windows.map(w => w.chatId));
    if (!uniqueChats.has(chatId)) uniqueChats.add(chatId);
    if (uniqueChats.size > 2) return { ok: false, reason: 'limit' };
    return { ok: true };
  }, [state.windows]);

  const dropChatTo = useCallback((chatId: string, target: WindowKind, bounds?: DOMRect): DropResult => {
    // prevent duplicate in same dock position
    if (target !== 'floating') {
      const existingSame = state.windows.find(w => w.kind === target && w.chatId === chatId);
      if (existingSame) return { ok: false, reason: 'duplicate' };
    }

    const limit = enforceMaxTwoChats(chatId);
    if (!limit.ok) return limit;

    dispatch({ type: 'ENSURE_ACTIVE_CHAT', chatId });
    ensureSession(chatId);

    if (target === 'full') {
      dispatch({ type: 'REPLACE_DOCK', kind: 'full', chatId });
    } else if (target === 'left' || target === 'right') {
      const fullDock = state.windows.find(w => w.kind === 'full');
      if (fullDock && fullDock.chatId !== chatId) {
        dispatch({ type: 'REPLACE_DOCK', kind: target, chatId });
        const otherSide: DockKind = target === 'left' ? 'right' : 'left';
        dispatch({ type: 'REPLACE_DOCK', kind: otherSide, chatId: fullDock.chatId });
      } else {
        dispatch({ type: 'REPLACE_DOCK', kind: target, chatId });
      }
    } else {
      const existingFloats = state.windows.filter(w => w.kind === 'floating' && w.chatId === chatId);
      if (existingFloats.length >= 2) {
        return { ok: false, reason: 'duplicate' };
      }
      const floatRects = state.windows.filter(w => w.kind === 'floating' && w.rect).map(w => w.rect!) as FloatingRect[];
      const rect = nextFloatRect(floatRects, bounds);
      const windowId = `float-${chatId}-${Date.now()}`;
      dispatch({ type: 'SET_WINDOW', window: { id: windowId, kind: 'floating', chatId, rect } });
    }

    return { ok: true };
  }, [ensureSession, enforceMaxTwoChats, state.windows]);

  const openFloating = useCallback((chatId: string, bounds?: DOMRect): DropResult => dropChatTo(chatId, 'floating', bounds), [dropChatTo]);

  const closeWindow = useCallback((windowId: string) => {
    dispatch({ type: 'REMOVE_WINDOW', windowId });
  }, []);

  const closeChat = useCallback((chatId: string) => {
    const sessionId = state.sessions[chatId];
    if (sessionId) sessionMgrRef.current.closeSession(sessionId);
    dispatch({ type: 'DEACTIVATE_CHAT', chatId });
  }, [state.sessions]);

  const sendMessage = useCallback(async (chatId: string, content: string) => {
    dispatch({ type: 'APPEND_MESSAGE', chatId, message: { id: `${Date.now()}-u`, role: 'user', content, timestamp: Date.now() } });
    dispatch({ type: 'SET_LOADING', chatId, value: true });
    const sessionId = ensureSession(chatId);
    try {
      sessionMgrRef.current.sendMessage(sessionId, content);
    } catch {
      dispatch({ type: 'SET_LOADING', chatId, value: false });
    }
  }, [ensureSession]);

  const setFloatingRect = useCallback((windowId: string, rect: FloatingRect) => {
    dispatch({ type: 'SET_FLOAT_RECT', windowId, rect });
  }, []);

  const value = useMemo<Ctx>(() => ({ state, dropChatTo, openFloating, closeWindow, closeChat, sendMessage, setFloatingRect }), [state, dropChatTo, openFloating, closeWindow, closeChat, sendMessage, setFloatingRect]);

  return <ChatWorkspaceContext.Provider value={value}>{children}</ChatWorkspaceContext.Provider>;
}
