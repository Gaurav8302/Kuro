import React, { useRef, useState, useCallback, useEffect, useMemo } from 'react';
import { DndProvider } from 'react-dnd';
import { HTML5Backend } from 'react-dnd-html5-backend';
import { TouchBackend } from 'react-dnd-touch-backend';
import { Plus, Grid3X3, MessageSquare } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

import { Button } from '@/components/ui/button';
import SidebarChatItem from './SidebarChatItem';
import WorkspaceDropZone from './WorkspaceDropZone';
import ChatWindow from './ChatWindow';
import FloatingChat from './FloatingChat';
import type { DropTarget } from '@/types/workspace';
import { toast } from '@/hooks/use-toast';
import { ChatWorkspaceProvider, useChatWorkspace } from '@/state/ChatWorkspaceContext';
import { getDebugDnd, setDebugDnd } from '@/state/debug';

// Mock chat list - replace with real data from your API
const mockChats = [
  { id: '1', title: 'AI Ethics Discussion', lastMessage: 'Thanks for the insights!', timestamp: '2 min ago' },
  { id: '2', title: 'Code Review Help', lastMessage: 'Let me check that function...', timestamp: '5 min ago' },
  { id: '3', title: 'Project Planning', lastMessage: 'We should prioritize this feature', timestamp: '1 hour ago' },
  { id: '4', title: 'React Best Practices', lastMessage: 'Use useCallback for this scenario', timestamp: '2 hours ago' },
  { id: '5', title: 'Database Design', lastMessage: 'Consider adding an index here', timestamp: '1 day ago' },
  { id: '6', title: 'UI/UX Feedback', lastMessage: 'The new design looks great!', timestamp: '1 day ago' },
];

function WorkspaceInner() {
  const workspaceRef = useRef<HTMLDivElement>(null);
  const [draggedChatId, setDraggedChatId] = useState<string | null>(null);
  const { state, dropChatTo, closeChat, sendMessage, setFloatingRect, closeWindow } = useChatWorkspace();
  const [debug, setDebug] = useState(getDebugDnd());
  useEffect(() => setDebugDnd(debug), [debug]);

  // Choose DnD backend dynamically (touch vs mouse)
  const isTouch = useMemo(() => {
    try {
      const coarse = typeof window !== 'undefined' && window.matchMedia ? window.matchMedia('(pointer: coarse)').matches : false;
      const touchCap = typeof navigator !== 'undefined' && (navigator.maxTouchPoints || (navigator as any).msMaxTouchPoints);
      return !!coarse || (touchCap ?? 0) > 0;
    } catch {
      return false;
    }
  }, []);

  // Debug + native drag event taps
  useEffect(() => {
    if (!debug) return;
    console.log('🏗️ WorkspaceV2 component mounted');
    const log = (e: Event) => {
      const evt = e as DragEvent;
      const types = evt.dataTransfer?.types ? Array.from(evt.dataTransfer.types) : [];
      console.log(`[native:${e.type}]`, { target: (e.target as HTMLElement)?.dataset?.dropTarget, types });
    };
    const preventOver = (e: Event) => {
      const evt = e as DragEvent;
      evt.preventDefault();
      log(e);
    };
    window.addEventListener('dragstart', log, true);
    window.addEventListener('dragend', log, true);
    window.addEventListener('dragleave', log, true);
    window.addEventListener('drop', log, true);
    window.addEventListener('dragover', preventOver, true);
    return () => {
      window.removeEventListener('dragstart', log, true);
      window.removeEventListener('dragend', log, true);
      window.removeEventListener('dragleave', log, true);
      window.removeEventListener('drop', log, true);
      window.removeEventListener('dragover', preventOver, true);
    };
  }, [debug]);

  // Handle chat item drag start
  const handleDragStart = useCallback((chatId: string) => {
    console.log('🎯 Setting dragged chat ID:', chatId);
    setDraggedChatId(chatId);
  }, []);

  // Handle chat item drag end
  const handleDragEnd = useCallback(() => {
    console.log('🛑 Clearing dragged chat ID');
    setDraggedChatId(null);
  }, []);

  // Handle drop on workspace zones
  const handleDrop = useCallback(async (chatId: string, target: DropTarget) => {
    const chat = mockChats.find(c => c.id === chatId);
    if (!chat) return;
    const bounds = workspaceRef.current?.getBoundingClientRect();
  if (debug) console.log('[DnD] drop', { chatId, target, bounds });
    const res = dropChatTo(chatId, target, bounds);
    if (!res.ok) {
      if ('reason' in res && res.reason === 'limit') {
        toast({ title: 'Limit reached', description: 'Max 2 chats can be open at once.' });
      } else if ('reason' in res && res.reason === 'duplicate') {
        toast({ title: 'Already there', description: 'That chat is already in that position.' });
      }
      return;
    }
    toast({ title: 'Chat Opened', description: `"${chat.title}" placed in ${target}.` });
  }, [dropChatTo]);

  // Handle sending message
  const handleSendMessage = useCallback(async (chatId: string, message: string) => {
    try {
  if (debug) console.log('[Chat] send', { chatId, message });
      await sendMessage(chatId, message);
    } catch (error) {
      toast({ title: 'Message Error', description: 'Failed to send message.', variant: 'destructive' });
    }
  }, [sendMessage]);

  // Handle closing chat
  const handleCloseChat = useCallback((chatId: string) => {
    closeChat(chatId);
    const chatInfo = mockChats.find(c => c.id === chatId);
    if (chatInfo) {
      toast({ title: 'Chat Closed', description: `"${chatInfo.title}" has been closed.` });
    }
  }, [closeChat]);

  // Memoized selectors
  const leftDock = useMemo(() => state.windows.find(w => w.kind === 'left'), [state.windows]);
  const rightDock = useMemo(() => state.windows.find(w => w.kind === 'right'), [state.windows]);
  const fullDock = useMemo(() => state.windows.find(w => w.kind === 'full'), [state.windows]);
  const floatingWins = useMemo(() => state.windows.filter(w => w.kind === 'floating'), [state.windows]);
  const openCount = useMemo(() => new Set(state.windows.map(w => w.chatId)).size, [state.windows]);

  // sessions are managed by provider

  return (
    <DndProvider backend={isTouch ? (TouchBackend as any) : HTML5Backend} options={isTouch ? { enableMouseEvents: true } : undefined}>
      <div className="h-screen flex bg-background">
        {/* Debug toggle */}
        {debug && (
          <div className="fixed top-2 left-1/2 -translate-x-1/2 z-[1000] bg-amber-50 text-amber-900 border border-amber-300 px-3 py-1 rounded shadow">
            DnD Debug ON
          </div>
        )}
        {/* Sidebar */}
        <motion.div 
          initial={{ x: -300 }}
          animate={{ x: 0 }}
          transition={{ duration: 0.3, ease: 'easeOut' }}
          className={`w-80 bg-card border-r flex flex-col ${
            draggedChatId ? 'opacity-75 border-primary border-2' : ''
          }`}
        >
          {/* Sidebar Header */}
          <div className="p-4 border-b">
            <div className="flex items-center gap-2 mb-4">
              <Grid3X3 className="w-5 h-5 text-primary" />
              <h1 className="font-semibold text-lg">Chat Workspace</h1>
            </div>
            <div className="flex gap-2">
              <Button size="sm" className="w-full">
              <Plus className="w-4 h-4 mr-2" />
              New Chat
              </Button>
              <Button variant={debug ? 'destructive' : 'outline'} size="sm" onClick={() => setDebug(v => !v)}>
                {debug ? 'Debug: On' : 'Debug: Off'}
              </Button>
            </div>
          </div>

          {/* Chat List */}
          <div className="flex-1 overflow-y-auto p-2 space-y-1">
      {mockChats.map(chat => (
              <SidebarChatItem
                key={chat.id}
                chatId={chat.id}
                title={chat.title}
                lastMessage={chat.lastMessage}
                timestamp={Date.parse(chat.timestamp) || Date.now()}
        isActive={state.windows.some(w => w.chatId === chat.id)}
                onDragStart={handleDragStart}
                onDragEnd={handleDragEnd}
              />
            ))}
          </div>

          {/* Sidebar Footer */}
          <div className="p-4 border-t text-sm text-muted-foreground">
            <div className="flex items-center gap-2 mb-2">
              <MessageSquare className="w-4 h-4" />
              <span>{openCount} chat{openCount !== 1 ? 's' : ''} open</span>
            </div>
            {draggedChatId && (
              <div className="mb-2 text-primary font-medium">
                🎯 Dragging: {mockChats.find(c => c.id === draggedChatId)?.title}
              </div>
            )}
            <div className="text-xs space-y-1">
              <p>💡 <strong>How to use:</strong></p>
              <p>• Desktop: Click and drag a chat into the workspace</p>
              <p>• Touch: Double-tap to enable drag, then drag into a zone</p>
              <p>• Drop center for full, left/right for split, or anywhere for floating</p>
            </div>
          </div>
        </motion.div>

        {/* Main Workspace */}
        <div className={`flex-1 relative ${
          draggedChatId ? 'bg-primary/5 border-2 border-dashed border-primary' : ''
        }`} ref={workspaceRef}
          onDragOver={(e) => { if (debug) console.log('[native:onDragOver] workspace'); e.preventDefault(); }}
          onDrop={() => { if (debug) console.log('[native:onDrop] workspace'); }}
        >
          {debug && (
            <div className="absolute top-2 right-2 z-[1000] bg-card border rounded p-2 text-xs max-w-sm shadow">
              <div className="font-medium mb-1">State Snapshot</div>
              <pre className="whitespace-pre-wrap max-h-64 overflow-auto">
{JSON.stringify({
  windows: state.windows,
  chats: Array.from(new Set(state.windows.map(w => w.chatId))),
  isLoading: state.isLoading,
}, null, 2)}
              </pre>
              <div className="mt-2 flex flex-wrap gap-1">
                {/* Programmatic drop helpers for debugging */}
                <button className="px-2 py-1 text-xs border rounded" onClick={() => handleDrop('1', 'left')}>Open 1 Left</button>
                <button className="px-2 py-1 text-xs border rounded" onClick={() => handleDrop('2', 'right')}>Open 2 Right</button>
                <button className="px-2 py-1 text-xs border rounded" onClick={() => handleDrop('3', 'full')}>Open 3 Full</button>
                <button className="px-2 py-1 text-xs border rounded" onClick={() => handleDrop('4', 'floating')}>Open 4 Float</button>
              </div>
            </div>
          )}
          {/* Drop Zones */}
          <WorkspaceDropZone
            target="left"
            active={true}
            onDropChat={handleDrop}
            className="inset-y-0 left-0 w-1/2"
          />
          
          <WorkspaceDropZone
            target="right"
            active={true}
            onDropChat={handleDrop}
            className="inset-y-0 right-0 w-1/2"
          />
          
          <WorkspaceDropZone
            target="full"
            active={true}
            onDropChat={handleDrop}
            className="inset-14"
          />

          <WorkspaceDropZone
            target="floating"
            active={true}
            onDropChat={handleDrop}
            className="inset-0"
          />

          {/* Chat Windows for Left/Right */}
          {!fullDock && leftDock && (
            <div className="absolute left-0 top-0 w-1/2 h-full p-4">
              <ChatWindow
                title={mockChats.find(c => c.id === leftDock.chatId)?.title || 'Chat'}
                messages={(state.messages[leftDock.chatId] || [])}
                onSendMessage={(message) => handleSendMessage(leftDock.chatId, message)}
                onClose={() => handleCloseChat(leftDock.chatId)}
                isLoading={!!state.isLoading[leftDock.chatId]}
              />
            </div>
          )}

          {!fullDock && rightDock && (
            <div className="absolute right-0 top-0 w-1/2 h-full p-4">
              <ChatWindow
                title={mockChats.find(c => c.id === rightDock.chatId)?.title || 'Chat'}
                messages={(state.messages[rightDock.chatId] || [])}
                onSendMessage={(message) => handleSendMessage(rightDock.chatId, message)}
                onClose={() => handleCloseChat(rightDock.chatId)}
                isLoading={!!state.isLoading[rightDock.chatId]}
              />
            </div>
          )}

          {/* Full-screen dock */}
          {fullDock && (
            <div className="absolute inset-0 p-4">
              <ChatWindow
                title={mockChats.find(c => c.id === fullDock.chatId)?.title || 'Chat'}
                messages={(state.messages[fullDock.chatId] || [])}
                onSendMessage={(message) => handleSendMessage(fullDock.chatId, message)}
                onClose={() => handleCloseChat(fullDock.chatId)}
                isLoading={!!state.isLoading[fullDock.chatId]}
              />
            </div>
          )}

          {/* Empty State */}
          {state.windows.length === 0 && !draggedChatId && (
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="absolute inset-0 flex items-center justify-center"
            >
              <div className="text-center">
                <Grid3X3 className="w-16 h-16 text-muted-foreground mx-auto mb-4" />
                <h2 className="text-xl font-semibold text-muted-foreground mb-2">
                  Welcome to Chat Workspace
                </h2>
                <p className="text-muted-foreground max-w-md">
                  Drag chats from the sidebar to create your workspace. 
                  You can snap them to the left, right, or create floating windows.
                </p>
              </div>
            </motion.div>
          )}

          {/* Floating Chats */}
          <AnimatePresence>
            {floatingWins.map(win => (
              win.rect && (
                <FloatingChat
                  key={win.id}
                  rect={win.rect}
                  title={mockChats.find(c => c.id === win.chatId)?.title || 'Chat'}
                  messages={(state.messages[win.chatId] || [])}
                  boundsRef={workspaceRef}
                  onChange={(rect) => setFloatingRect(win.id, rect)}
                  onClose={() => closeWindow(win.id)}
                  onSendMessage={(message) => handleSendMessage(win.chatId, message)}
                  isLoading={!!state.isLoading[win.chatId]}
                />
              )
            ))}
          </AnimatePresence>
        </div>
      </div>
    </DndProvider>
  );
}

export default function WorkspaceV2() {
  return (
    <ChatWorkspaceProvider>
      <WorkspaceInner />
    </ChatWorkspaceProvider>
  );
}
