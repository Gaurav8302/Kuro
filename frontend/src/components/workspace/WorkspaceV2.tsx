import React, { useRef, useState, useCallback, useEffect } from 'react';
import { DndProvider } from 'react-dnd';
import { HTML5Backend } from 'react-dnd-html5-backend';
import { Plus, Grid3X3, MessageSquare } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

import { Button } from '@/components/ui/button';
import SidebarChatItem from './SidebarChatItem';
import WorkspaceDropZone from './WorkspaceDropZone';
import ChatWindow from './ChatWindow';
import FloatingChat from './FloatingChat';
import { ChatSessionManager } from '@/lib/ChatSessionManager';
import type { DropTarget, ChatPosition, OpenChat, FloatingRect } from '@/types/workspace';
import { toast } from '@/hooks/use-toast';

// Mock chat list - replace with real data from your API
const mockChats = [
  { id: '1', title: 'AI Ethics Discussion', lastMessage: 'Thanks for the insights!', timestamp: '2 min ago' },
  { id: '2', title: 'Code Review Help', lastMessage: 'Let me check that function...', timestamp: '5 min ago' },
  { id: '3', title: 'Project Planning', lastMessage: 'We should prioritize this feature', timestamp: '1 hour ago' },
  { id: '4', title: 'React Best Practices', lastMessage: 'Use useCallback for this scenario', timestamp: '2 hours ago' },
  { id: '5', title: 'Database Design', lastMessage: 'Consider adding an index here', timestamp: '1 day ago' },
  { id: '6', title: 'UI/UX Feedback', lastMessage: 'The new design looks great!', timestamp: '1 day ago' },
];

export default function WorkspaceV2() {
  const workspaceRef = useRef<HTMLDivElement>(null);
  const [openChats, setOpenChats] = useState<OpenChat[]>([]);
  const [draggedChatId, setDraggedChatId] = useState<string | null>(null);
  const chatManagerRef = useRef(new ChatSessionManager());

  // Debug message
  useEffect(() => {
    console.log('🏗️ WorkspaceV2 component mounted');
  }, []);

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

    // Check if chat is already open
    const existingChat = openChats.find(c => c.id === chatId);
    if (existingChat) {
      toast({
        title: 'Chat Already Open',
        description: `"${chat.title}" is already open in the workspace.`,
      });
      return;
    }

    let position: ChatPosition;
    let rect: FloatingRect | undefined;

    if (target === 'floating') {
      // Position floating window near center with slight offset
      const workspaceRect = workspaceRef.current?.getBoundingClientRect();
      if (workspaceRect) {
        const openFloatingChats = openChats.filter(c => c.position === 'floating').length;
        rect = {
          x: Math.max(20, (workspaceRect.width - 400) / 2 + openFloatingChats * 30),
          y: Math.max(20, (workspaceRect.height - 300) / 2 + openFloatingChats * 30),
          width: 400,
          height: 300,
        };
      } else {
        rect = { x: 100, y: 100, width: 400, height: 300 };
      }
      position = 'floating';
    } else {
      position = target;
      // If dropping on left/right and there's already a chat there, close it
      const existingPositionChat = openChats.find(c => c.position === target);
      if (existingPositionChat) {
        handleCloseChat(existingPositionChat.id);
      }
    }

    const newChat: OpenChat = {
      id: chatId,
      title: chat.title,
      position,
      rect,
      messages: [
        {
          id: 'welcome',
          role: 'assistant',
          content: `Hello! I'm ready to help you with "${chat.title}". What would you like to discuss?`,
          timestamp: new Date(),
        }
      ],
      isLoading: false,
    };

    setOpenChats(prev => [...prev, newChat]);

    // Start chat session
    try {
      const sessionId = chatManagerRef.current.openSession(chatId, `ws://localhost:8000/ws/${chatId}`);
      
      // Set up message handler
      const unsubscribe = chatManagerRef.current.onMessage(sessionId, ({ type, payload }) => {
        if (type === 'chunk' || type === 'done') {
          setOpenChats(prev => 
            prev.map(openChat => 
              openChat.id === chatId 
                ? { 
                    ...openChat, 
                    messages: [...openChat.messages, {
                      id: Date.now().toString(),
                      role: 'assistant',
                      content: String(payload || ''),
                      timestamp: new Date(),
                    }],
                    isLoading: false
                  }
                : openChat
            )
          );
        } else if (type === 'error') {
          console.error('Chat session error:', payload);
          toast({
            title: 'Connection Error',
            description: 'Failed to connect to chat service. Please try again.',
            variant: 'destructive',
          });
          setOpenChats(prev => 
            prev.map(openChat => 
              openChat.id === chatId ? { ...openChat, isLoading: false } : openChat
            )
          );
        }
      });

      // Store the session ID and unsubscribe function
      setOpenChats(prev => 
        prev.map(openChat => 
          openChat.id === chatId ? { ...openChat, sessionId } : openChat
        )
      );

      toast({
        title: 'Chat Opened',
        description: `"${chat.title}" is now active in ${position} mode.`,
      });

    } catch (error) {
      console.error('Failed to start chat session:', error);
      toast({
        title: 'Session Error',
        description: 'Failed to start chat session. Please try again.',
        variant: 'destructive',
      });
    }
  }, [openChats]);

  // Handle sending message
  const handleSendMessage = useCallback(async (chatId: string, message: string) => {
    // Add user message immediately
    setOpenChats(prev => 
      prev.map(chat => 
        chat.id === chatId 
          ? { 
              ...chat, 
              messages: [...chat.messages, {
                id: Date.now().toString(),
                role: 'user',
                content: message,
                timestamp: new Date(),
              }],
              isLoading: true
            }
          : chat
      )
    );

    // Send message through session manager
    try {
      await chatManagerRef.current.sendMessage(chatId, message);
    } catch (error) {
      console.error('Failed to send message:', error);
      toast({
        title: 'Message Error',
        description: 'Failed to send message. Please try again.',
        variant: 'destructive',
      });
      setOpenChats(prev => 
        prev.map(chat => 
          chat.id === chatId ? { ...chat, isLoading: false } : chat
        )
      );
    }
  }, []);

  // Handle closing chat
  const handleCloseChat = useCallback((chatId: string) => {
    const chat = openChats.find(c => c.id === chatId);
    if (chat?.sessionId) {
      chatManagerRef.current.closeSession(chat.sessionId);
    }
    
    setOpenChats(prev => prev.filter(chat => chat.id !== chatId));
    
    const chatInfo = mockChats.find(c => c.id === chatId);
    if (chatInfo) {
      toast({
        title: 'Chat Closed',
        description: `"${chatInfo.title}" has been closed.`,
      });
    }
  }, [openChats]);

  // Handle floating chat position/size change
  const handleFloatingChatChange = useCallback((chatId: string, rect: FloatingRect) => {
    setOpenChats(prev => 
      prev.map(chat => 
        chat.id === chatId ? { ...chat, rect } : chat
      )
    );
  }, []);

  // Clean up sessions on unmount
  useEffect(() => {
    const chatManager = chatManagerRef.current;
    return () => {
      // Close all open sessions
      openChats.forEach(chat => {
        if (chat.sessionId) {
          chatManager.closeSession(chat.sessionId);
        }
      });
    };
  }, [openChats]);

  const leftChat = openChats.find(chat => chat.position === 'left');
  const rightChat = openChats.find(chat => chat.position === 'right');
  const floatingChats = openChats.filter(chat => chat.position === 'floating');

  return (
    <DndProvider backend={HTML5Backend}>
      <div className="h-screen flex bg-background">
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
            <Button size="sm" className="w-full">
              <Plus className="w-4 h-4 mr-2" />
              New Chat
            </Button>
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
                isActive={openChats.some(c => c.id === chat.id)}
                onDragStart={handleDragStart}
                onDragEnd={handleDragEnd}
              />
            ))}
          </div>

          {/* Sidebar Footer */}
          <div className="p-4 border-t text-sm text-muted-foreground">
            <div className="flex items-center gap-2 mb-2">
              <MessageSquare className="w-4 h-4" />
              <span>{openChats.length} chat{openChats.length !== 1 ? 's' : ''} open</span>
            </div>
            {draggedChatId && (
              <div className="mb-2 text-primary font-medium">
                🎯 Dragging: {mockChats.find(c => c.id === draggedChatId)?.title}
              </div>
            )}
            <p>Drag chats to workspace areas to start conversations</p>
          </div>
        </motion.div>

        {/* Main Workspace */}
        <div className={`flex-1 relative ${
          draggedChatId ? 'bg-primary/5 border-2 border-dashed border-primary' : ''
        }`} ref={workspaceRef}>
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
            target="floating"
            active={true}
            onDropChat={handleDrop}
            className="inset-0"
          />

          {/* Chat Windows for Left/Right */}
          {leftChat && (
            <div className="absolute left-0 top-0 w-1/2 h-full p-4">
              <ChatWindow
                title={leftChat.title}
                messages={leftChat.messages.map(msg => ({
                  ...msg,
                  timestamp: msg.timestamp.getTime()
                }))}
                onSendMessage={(message) => handleSendMessage(leftChat.id, message)}
                onClose={() => handleCloseChat(leftChat.id)}
                isLoading={leftChat.isLoading}
              />
            </div>
          )}

          {rightChat && (
            <div className="absolute right-0 top-0 w-1/2 h-full p-4">
              <ChatWindow
                title={rightChat.title}
                messages={rightChat.messages.map(msg => ({
                  ...msg,
                  timestamp: msg.timestamp.getTime()
                }))}
                onSendMessage={(message) => handleSendMessage(rightChat.id, message)}
                onClose={() => handleCloseChat(rightChat.id)}
                isLoading={rightChat.isLoading}
              />
            </div>
          )}

          {/* Empty State */}
          {openChats.length === 0 && !draggedChatId && (
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
            {floatingChats.map(chat => (
              <FloatingChat
                key={chat.id}
                rect={chat.rect!}
                title={chat.title}
                messages={chat.messages.map(msg => ({
                  ...msg,
                  timestamp: msg.timestamp.getTime()
                }))}
                boundsRef={workspaceRef}
                onChange={(rect) => handleFloatingChatChange(chat.id, rect)}
                onClose={() => handleCloseChat(chat.id)}
                onSendMessage={(message) => handleSendMessage(chat.id, message)}
                isLoading={chat.isLoading}
              />
            ))}
          </AnimatePresence>
        </div>
      </div>
    </DndProvider>
  );
}
