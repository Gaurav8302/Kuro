import React, { useCallback, useMemo, useRef, useState } from 'react';
import { DndProvider } from 'react-dnd';
import { HTML5Backend } from 'react-dnd-html5-backend';
import { AnimatePresence, motion } from 'framer-motion';
import SidebarChatItem from './SidebarChatItem';
import WorkspaceDropZone from './WorkspaceDropZone';
import ChatWindow from './ChatWindow';
import FloatingChat from './FloatingChat';
import type { ChatPosition, DropTarget, FloatingRect, OpenChat } from '@/types/workspace';
import { ChatSessionManager } from '@/lib/ChatSessionManager';

const MAX_OPEN = 2;

export default function Workspace() {
  const [openChats, setOpenChats] = useState<OpenChat[]>([]);
  const [messages, setMessages] = useState<Record<string, { id: string; role: 'user' | 'assistant'; content: string }[]>>({});
  const boundsRef = useRef<HTMLDivElement>(null);
  const sessionManager = useMemo(() => ChatSessionManager.getInstance(), []);

  const attachSession = useCallback((chatId: string) => {
    const wsUrl = `${location.origin.replace(/^http/, 'ws')}/ws/${chatId}`; // example
    const sessionId = sessionManager.openSession(chatId, wsUrl);
    const off = sessionManager.onMessage(sessionId, ({ type, payload }) => {
      if (type === 'chunk' || type === 'done') {
        setMessages((prev) => ({
          ...prev,
          [chatId]: [...(prev[chatId] || []), { id: crypto.randomUUID(), role: 'assistant', content: String(payload || '') }]
        }));
      }
    });
    return { sessionId, off };
  }, [sessionManager]);

  const placeChat = useCallback((chatId: string, position: ChatPosition) => {
    setOpenChats((prev) => {
      let next = [...prev];
      const existingIdx = next.findIndex((c) => c.chatId === chatId);

      // Apply max-2 policy
      if (next.length >= MAX_OPEN && existingIdx === -1) {
        if (position === 'full') {
          next = [];
        } else if (position === 'left' || position === 'right') {
          const idx = position === 'left' ? next.findIndex((c) => c.position === 'left') : next.findIndex((c) => c.position === 'right');
          if (idx !== -1) next.splice(idx, 1);
        }
      }

      const item: OpenChat = { chatId, sessionId: null, position };
      if (existingIdx !== -1) next.splice(existingIdx, 1, item); else next.push(item);
      // Normalize split layout
      if (position === 'full') next = [item];
      if (position === 'left' && next.length === 2) next[1].position = 'right';
      return next.slice(0, MAX_OPEN);
    });

    const { sessionId } = attachSession(chatId);
    setOpenChats((prev) => prev.map((c) => c.chatId === chatId ? { ...c, sessionId } : c));
  }, [attachSession]);

  const onDropChat = useCallback((chatId: string, target: DropTarget) => {
    if (target === 'full') placeChat(chatId, 'full');
    if (target === 'left') placeChat(chatId, 'left');
    if (target === 'right') placeChat(chatId, 'right');
  }, [placeChat]);

  const addFloating = useCallback((chatId: string) => {
    setOpenChats((prev) => prev.map((c) => {
      if (c.chatId !== chatId) return c;
      const floats = c.floating || [];
      if (floats.length >= 2) return c; // limit 2
      const rect: FloatingRect = { id: crypto.randomUUID(), x: 40 + floats.length * 20, y: 40 + floats.length * 20, width: 360, height: 280 };
      return { ...c, floating: [...floats, rect], position: c.position };
    }));
  }, []);

  const updateFloating = useCallback((chatId: string, nextRect: FloatingRect) => {
    setOpenChats((prev) => prev.map((c) => {
      if (c.chatId !== chatId) return c;
      const floats = (c.floating || []).map((r) => r.id === nextRect.id ? nextRect : r);
      return { ...c, floating: floats };
    }));
  }, []);

  const layout = useMemo(() => {
    if (openChats.length === 0) return 'empty';
    if (openChats.length === 1 && openChats[0].position === 'full') return 'full';
    return 'split';
  }, [openChats]);

  return (
    <DndProvider backend={HTML5Backend}>
      <div className="flex h-full">
        {/* Sidebar example: map your actual chat list here */}
        <div className="w-64 p-3 border-r space-y-2">
          {['chat-a', 'chat-b', 'chat-c'].map((id) => (
            <SidebarChatItem key={id} chatId={id} title={`Chat ${id.toUpperCase()}`} />
          ))}
        </div>

        {/* Workspace */}
        <div className="flex-1 relative" ref={boundsRef}>
          {/* Drop overlays */}
          <div className="absolute inset-0 pointer-events-none">
            <WorkspaceDropZone target="full" onDropChat={onDropChat} />
            <div className="absolute inset-y-0 left-0 w-1/2">
              <WorkspaceDropZone target="left" onDropChat={onDropChat} />
            </div>
            <div className="absolute inset-y-0 right-0 w-1/2">
              <WorkspaceDropZone target="right" onDropChat={onDropChat} />
            </div>
          </div>

          {/* Layout */}
          {layout === 'empty' && (
            <div className="h-full flex items-center justify-center text-muted-foreground">Drag a chat here</div>
          )}

          {layout === 'full' && (
            <div className="p-4 h-full">
              <ChatWindow title={openChats[0].chatId} messages={messages[openChats[0].chatId] || []} />
              <button className="mt-3 text-xs text-primary" onClick={() => addFloating(openChats[0].chatId)}>Open floating window</button>
              {(openChats[0].floating || []).map((rect) => (
                <FloatingChat
                  key={rect.id}
                  rect={rect}
                  title={`${openChats[0].chatId} (Floating)`}
                  messages={messages[openChats[0].chatId] || []}
                  boundsRef={boundsRef}
                  onChange={(r) => updateFloating(openChats[0].chatId, r)}
                />
              ))}
            </div>
          )}

          {layout === 'split' && (
            <div className="grid grid-cols-2 gap-4 p-4 h-full">
              {openChats.slice(0, 2).map((c) => (
                <div key={c.chatId} className="relative h-full">
                  <ChatWindow title={c.chatId} messages={messages[c.chatId] || []} />
                  <button className="mt-2 text-xs text-primary" onClick={() => addFloating(c.chatId)}>Open floating window</button>
                  {(c.floating || []).map((rect) => (
                    <FloatingChat
                      key={rect.id}
                      rect={rect}
                      title={`${c.chatId} (Floating)`}
                      messages={messages[c.chatId] || []}
                      boundsRef={boundsRef}
                      onChange={(r) => updateFloating(c.chatId, r)}
                    />
                  ))}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </DndProvider>
  );
}
