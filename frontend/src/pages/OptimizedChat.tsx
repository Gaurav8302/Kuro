import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth, useUser } from '@clerk/clerk-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Loader2, AlertTriangle } from 'lucide-react';
import { Message, ChatSession } from '@/types';
import { useToast } from '@/hooks/use-toast';
import { useClerkApi } from '@/lib/api';
import { useIsMobile } from '@/hooks/use-mobile';
import { MobileChat } from '@/components/MobileChat';
import { PerformanceOptimizedBackground } from '@/components/PerformanceOptimizedBackground';
import { Alert, AlertDescription } from '@/components/ui/alert';

const OptimizedChat = () => {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const clerkApiRequest = useClerkApi();
  const { user, isLoaded } = useUser();
  const { signOut } = useAuth();
  const isMobile = useIsMobile();
  
  // State management
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isInitializing, setIsInitializing] = useState(true);

  // Memoized current session
  const currentSession = useMemo(() => 
    sessions.find(s => s.session_id === sessionId),
    [sessions, sessionId]
  );

  // Fetch sessions with error handling
  const fetchSessions = useCallback(async () => {
    if (!user) return;
    
    try {
      const data = await clerkApiRequest<{ sessions: ChatSession[] }>(`/sessions/${user.id}`, 'get');
      setSessions(data.sessions);
      
      // Auto-create session if none exist
      if (data.sessions.length === 0 && !sessionId) {
        await handleNewChat();
      }
    } catch (err: any) {
      console.error('Error fetching sessions:', err);
      setError('Failed to load chat sessions');
    } finally {
      setIsInitializing(false);
    }
  }, [user, sessionId]);

  // Load specific session
  const loadSession = useCallback(async (id: string) => {
    if (!user) return;
    
    setIsLoading(true);
    try {
      const data = await clerkApiRequest<{ history: any[] }>(`/chat/${id}`, 'get');
      
      // Transform backend data to frontend format
      const transformedMessages: Message[] = [];
      data.history.forEach((item: any) => {
        if (item.user) {
          transformedMessages.push({
            message: item.user,
            reply: '',
            timestamp: item.timestamp,
            role: 'user'
          });
        }
        if (item.assistant) {
          transformedMessages.push({
            message: item.assistant,
            reply: '',
            timestamp: item.timestamp,
            role: 'assistant'
          });
        }
      });
      
      setMessages(transformedMessages);
      setError(null);
    } catch (err: any) {
      console.error('Error loading session:', err);
      setError('Failed to load session messages');
    } finally {
      setIsLoading(false);
    }
  }, [user, clerkApiRequest]);

  // Create new chat session
  const handleNewChat = useCallback(async () => {
    if (!user) return;
    
    try {
      setIsLoading(true);
      const data = await clerkApiRequest<{ session_id: string }>(`/session/create`, 'post', null, { user_id: user.id });
      
      // Clear current state
      setMessages([]);
      
      // Update sessions and navigate
      await fetchSessions();
      navigate(`/chat/${data.session_id}`);
      
      toast({
        title: "New chat created",
        description: "Ready for your next conversation!"
      });
    } catch (err: any) {
      console.error('Error creating new chat:', err);
      toast({
        title: "Error",
        description: "Failed to create new chat",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  }, [user, clerkApiRequest, fetchSessions, navigate, toast]);

  // Send message with optimistic updates
  const handleSendMessage = useCallback(async (message: string) => {
    if (!user) return;

    // Optimistic update
    const userMessage: Message = {
      message,
      reply: '',
      timestamp: new Date().toISOString(),
      role: 'user'
    };
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      let sessionToUse = currentSession;
      
      // Create session if needed
      if (!sessionToUse) {
        const sessionData = await clerkApiRequest<{ session_id: string }>(`/session/create`, 'post', null, { user_id: user.id });
        sessionToUse = { session_id: sessionData.session_id, title: 'New Chat' };
        navigate(`/chat/${sessionData.session_id}`);
      }

      // Send message
      const { reply } = await clerkApiRequest<{ reply: string }>(
        `/chat`,
        'post',
        { user_id: user.id, message, session_id: sessionToUse.session_id }
      );

      // Add AI response
      const aiMessage: Message = {
        message: reply,
        reply: '',
        timestamp: new Date().toISOString(),
        role: 'assistant'
      };
      setMessages(prev => [...prev, aiMessage]);
      
      // Refresh sessions to update titles
      await fetchSessions();
      
    } catch (err: any) {
      console.error('Error sending message:', err);
      // Remove optimistic update on error
      setMessages(prev => prev.slice(0, -1));
      toast({
        title: "Error",
        description: "Failed to send message. Please try again.",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  }, [user, currentSession, clerkApiRequest, navigate, fetchSessions, toast]);

  // Other handlers
  const handleSelectSession = useCallback((id: string) => {
    navigate(`/chat/${id}`);
  }, [navigate]);

  const handleRenameSession = useCallback(async (sessionId: string, newTitle: string) => {
    try {
      await clerkApiRequest(`/session/${sessionId}`, 'put', { new_title: newTitle });
      await fetchSessions();
      toast({
        title: "Session renamed",
        description: "Chat title updated successfully"
      });
    } catch (err: any) {
      toast({
        title: "Error",
        description: "Failed to rename session",
        variant: "destructive"
      });
    }
  }, [clerkApiRequest, fetchSessions, toast]);

  const handleDeleteSession = useCallback(async (sessionId: string) => {
    try {
      await clerkApiRequest(`/session/${sessionId}`, 'delete');
      await fetchSessions();
      
      if (sessionId === currentSession?.session_id) {
        setMessages([]);
        navigate('/chat');
      }
      
      toast({
        title: "Session deleted",
        description: "Chat session removed successfully"
      });
    } catch (err: any) {
      toast({
        title: "Error",
        description: "Failed to delete session",
        variant: "destructive"
      });
    }
  }, [clerkApiRequest, fetchSessions, currentSession, navigate, toast]);

  const handleSignOut = useCallback(async () => {
    await signOut();
    navigate('/');
  }, [signOut, navigate]);

  // Load data on mount
  useEffect(() => {
    if (user) {
      fetchSessions();
    }
  }, [user, fetchSessions]);

  // Load session when URL changes
  useEffect(() => {
    if (sessionId && sessions.length > 0) {
      loadSession(sessionId);
    }
  }, [sessionId, sessions, loadSession]);

  // Loading state
  if (!isLoaded || !user || isInitializing) {
    return (
      <div className="h-screen flex items-center justify-center bg-background relative">
        <PerformanceOptimizedBackground variant="minimal" />
        <div className="text-center relative z-10">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
            className="w-12 h-12 mx-auto mb-4"
          >
            <Loader2 className="w-full h-full text-primary" />
          </motion.div>
          <p className="text-muted-foreground">Loading Kuro AI...</p>
        </div>
      </div>
    );
  }

  return (
    <>
      {/* Error Alert */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -50 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -50 }}
            className="fixed top-4 left-4 right-4 z-50"
          >
            <Alert variant="destructive" className="max-w-md mx-auto">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Chat Interface */}
      <MobileChat
        messages={messages}
        sessions={sessions}
        currentSessionId={sessionId}
        user={user ? {
          id: user.id,
          name: user.fullName || user.username || 'User',
          email: user.emailAddresses?.[0]?.emailAddress || '',
          avatar: user.imageUrl
        } : undefined}
        isLoading={isLoading}
        onSendMessage={handleSendMessage}
        onNewChat={handleNewChat}
        onSelectSession={handleSelectSession}
        onRenameSession={handleRenameSession}
        onDeleteSession={handleDeleteSession}
        onSignOut={handleSignOut}
      />
    </>
  );
};

export default OptimizedChat;