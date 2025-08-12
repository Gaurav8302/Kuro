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
  const [messages, setMessages] = useState<Record<string, { id: string; role: 'user' | 'assistant'; content: string; timestamp: number }[]>>({});
  const boundsRef = useRef<HTMLDivElement>(null);
  const sessionManager = useMemo(() => ChatSessionManager.getInstance(), []);

  const attachSession = useCallback((chatId: string) => {
    const wsUrl = `${location.origin.replace(/^http/, 'ws')}/ws/${chatId}`; // example
    const sessionId = sessionManager.openSession(chatId, wsUrl);
    const off = sessionManager.onMessage(sessionId, ({ type, payload }) => {
      if (type === 'chunk' || type === 'done') {
        setMessages((prev) => ({
          ...prev,
          [chatId]: [...(prev[chatId] || []), { 
            id: crypto.randomUUID(), 
            role: 'assistant', 
            content: String(payload || ''),
            timestamp: Date.now()
          }]
        }));
      }
    });
    return { sessionId, off };
  }, [sessionManager]);

  const placeChat = useCallback((chatId: string, position: ChatPosition) => {
    setOpenChats((prev) => {
      let next = [...prev];
      const existingIdx = next.findIndex((c) => c.id === chatId);

      // Apply max-2 policy
      if (next.length >= MAX_OPEN && existingIdx === -1) {
        if (position === 'full') {
          next = [];
        } else if (position === 'left' || position === 'right') {
          const idx = position === 'left' ? next.findIndex((c) => c.position === 'left') : next.findIndex((c) => c.position === 'right');
          if (idx !== -1) next.splice(idx, 1);
        }
      }

      const item: OpenChat = { 
        id: chatId, 
        title: `Chat ${chatId}`,
        position,
        messages: [],
        sessionId: null
      };
      if (existingIdx !== -1) next.splice(existingIdx, 1, item); else next.push(item);
      
      // Normalize split layout
      if (position === 'full') next = [item];
      if (position === 'left' && next.length === 2) next[1].position = 'right';
      return next.slice(0, MAX_OPEN);
    });

    const { sessionId } = attachSession(chatId);
    setOpenChats((prev) => prev.map((c) => c.id === chatId ? { ...c, sessionId } : c));
  }, [attachSession]);

  const onDropChat = useCallback((chatId: string, target: DropTarget) => {
    if (target === 'full') placeChat(chatId, 'full');
    if (target === 'left') placeChat(chatId, 'left');
    if (target === 'right') placeChat(chatId, 'right');
    if (target === 'floating') {
      // For floating, we'll add it as a floating window to the first open chat or create a new one
      setOpenChats((prev) => {
        if (prev.length === 0) {
          const newChat: OpenChat = {
            id: chatId,
            title: `Chat ${chatId}`,
            position: 'floating',
            rect: { x: 100, y: 100, width: 400, height: 300 },
            messages: [],
            sessionId: null
          };
          return [newChat];
        }
        return prev;
      });
    }
  }, [placeChat]);

  const updateFloating = useCallback((chatId: string, nextRect: FloatingRect) => {
    setOpenChats((prev) => prev.map((c) => {
      if (c.id !== chatId) return c;
      return { ...c, rect: nextRect };
    }));
  }, []);

  const layout = useMemo(() => {
    if (openChats.length === 0) return 'empty';
    if (openChats.length === 1 && openChats[0].position === 'full') return 'full';
    return 'split';
  }, [openChats]);

  const floatingChats = openChats.filter(chat => chat.position === 'floating');
  const nonFloatingChats = openChats.filter(chat => chat.position !== 'floating');

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
            <div className="absolute inset-0">
              <WorkspaceDropZone target="floating" onDropChat={onDropChat} />
            </div>
          </div>

          {/* Layout */}
          {layout === 'empty' && (
            <div className="h-full flex items-center justify-center text-muted-foreground">Drag a chat here</div>
          )}

          {layout === 'full' && nonFloatingChats.length > 0 && (
            <div className="p-4 h-full">
              <ChatWindow 
                title={nonFloatingChats[0].title} 
                messages={messages[nonFloatingChats[0].id] || []} 
              />
            </div>
          )}

          {layout === 'split' && (
            <div className="grid grid-cols-2 gap-4 p-4 h-full">
              {nonFloatingChats.slice(0, 2).map((c) => (
                <div key={c.id} className="relative h-full">
                  <ChatWindow 
                    title={c.title} 
                    messages={messages[c.id] || []} 
                  />
                </div>
              ))}
            </div>
          )}

          {/* Floating Windows */}
          <AnimatePresence>
            {floatingChats.map((chat) => (
              <FloatingChat
                key={chat.id}
                rect={chat.rect || { x: 100, y: 100, width: 400, height: 300 }}
                title={chat.title}
                messages={messages[chat.id] || []}
                boundsRef={boundsRef}
                onChange={(r) => updateFloating(chat.id, r)}
                onClose={() => {
                  setOpenChats(prev => prev.filter(c => c.id !== chat.id));
                }}
              />
            ))}
          </AnimatePresence>
        </div>
      </div>
    </DndProvider>
  );
}
