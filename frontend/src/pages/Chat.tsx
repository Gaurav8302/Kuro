import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Sidebar } from '@/components/Sidebar';
import { ChatBubble } from '@/components/ChatBubble';
import { ChatInput } from '@/components/ChatInput';
import NameSetupModal from '@/components/NameSetupModal';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { 
  Edit3,
  Check,
  X,
  AlertTriangle,
  Loader2,
  Menu
} from 'lucide-react';
import { Message, ChatSession } from '@/types';
// import { mockSessions, mockApiCalls } from '@/data/mockData';
import { useToast } from '@/hooks/use-toast';
import { cn } from '@/lib/utils';
import { useClerkApi, setUserName, checkUserHasName } from '@/lib/api';
import { useAuth, useUser } from '@clerk/clerk-react';
import { useIsMobile } from '@/hooks/use-mobile';

const Chat = () => {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const clerkApiRequest = useClerkApi();
  const { user, isLoaded } = useUser();
  const { signOut } = useAuth();
  const isMobile = useIsMobile();
  
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSession, setCurrentSession] = useState<ChatSession | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [editTitle, setEditTitle] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false); // Always start closed
  const [hasAutoCreatedSession, setHasAutoCreatedSession] = useState(false);
  const [showNameModal, setShowNameModal] = useState(false);
  const [hasCheckedName, setHasCheckedName] = useState(false);
  const [isInitializing, setIsInitializing] = useState(true); // New state for initial load
  const [lastFailedMessage, setLastFailedMessage] = useState<string | null>(null);
  // Track if user manually edited or generated a title to prevent further auto-naming
  const [hasUserEditedTitle, setHasUserEditedTitle] = useState(false);
  const [isGeneratingTitle, setIsGeneratingTitle] = useState(false);
  // Maintenance / friendly error handling in development
  const maintenanceMessage = 'Maintenance in progress. Please try again later.';
  const isDev = import.meta.env.DEV;
  const showErrorToast = (fallbackTitle: string, fallbackDescription: string) => {
    toast({
      title: isDev ? 'Maintenance' : fallbackTitle,
      description: isDev ? maintenanceMessage : fallbackDescription,
      variant: 'destructive'
    });
  };

  // Ensure loading state is never stuck on - failsafe
  useEffect(() => {
    const failsafe = setTimeout(() => {
      if (isLoading) {
        console.log('⚠️ Failsafe: Resetting stuck loading state');
        setIsLoading(false);
        setIsTyping(false);
      }
    }, 30000); // 30 second failsafe
    
    return () => clearTimeout(failsafe);
  }, [isLoading]);

  // Update sidebar state when mobile state changes
  useEffect(() => {
    if (isMobile) {
      setIsSidebarOpen(false); // Always close sidebar on mobile
    } else {
      setIsSidebarOpen(true); // Open sidebar on desktop
    }
  }, [isMobile]);

  // Scroll to bottom when new messages arrive
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Check if user needs to set their name (only for authenticated users)
  useEffect(() => {
    const checkUserName = async () => {
      if (!user || hasCheckedName) return;
      
      try {
        const { has_name } = await checkUserHasName(user.id);
        if (!has_name) {
          setShowNameModal(true);
        }
      } catch (error) {
        console.error('Error checking user name:', error);
        // Don't show error to user for name check - just continue
      } finally {
        setHasCheckedName(true); // Always mark as checked to avoid infinite loop
      }
    };

    if (user) {
      checkUserName();
    }
  }, [user, hasCheckedName]);

  // Handle name setup completion
  const handleNameSetup = async (name: string) => {
    if (!user) return;
    
    try {
      await setUserName(user.id, name);
      setShowNameModal(false);
      toast({
        title: "Welcome!",
        description: `Nice to meet you, ${name}! 🎉`,
      });
    } catch (error) {
      console.error('Error setting name:', error);
      setShowNameModal(false); // Close modal even if error to avoid blocking user
      toast({
        title: "Welcome!",
        description: "Let's start chatting! 🎉",
      });
    }
  };

  // Handle name setup skip
  const handleNameSkip = () => {
    setShowNameModal(false);
    toast({
      title: "Welcome!",
      description: "Let's start chatting! 🎉",
    });
  };

  // Fetch sessions from backend
  const fetchSessions = async () => {
    if (!user) return;
    try {
      const data = await clerkApiRequest<{ sessions: ChatSession[] }>(`/sessions/${user.id}`, 'get');
      setSessions(data.sessions);
      
      // Auto-create new session if none exist and user hasn't already done this
      if (data.sessions.length === 0 && !sessionId && !hasAutoCreatedSession) {
        setHasAutoCreatedSession(true);
        await handleNewChat();
        return;
      }
      
      // If sessionId exists, load that session after sessions are set
      if (sessionId && data.sessions.length > 0) {
        const session = data.sessions.find(s => s.session_id === sessionId);
        if (session) {
          await loadSession(sessionId);
        } else {
          // Session doesn't exist, redirect to create new one
          navigate('/chat');
        }
      }
    } catch (err: any) {
  console.error('Error fetching sessions:', err);
  // Don't block the UI if sessions fail to load - user can still chat
  showErrorToast('Connection Issue', 'Having trouble loading sessions. You can still start a new chat!');
    } finally {
      setIsInitializing(false); // Always mark initialization as complete
    }
  };

  // Load session messages from backend and map to Message[]
  const loadSession = async (id: string) => {
    setIsLoading(true);
    setError(null);
    
    try {
      console.log('📡 Loading session:', id);
      const data = await clerkApiRequest<{ history: any[] }>(`/chat/${id}`, 'get');
      
      // Map backend chat history to frontend Message format, preserving order and growing chat
      const mappedMessages: Message[] = [];
      data.history.forEach((item: any) => {
        if (item.user) {
          mappedMessages.push({
            message: item.user,
            reply: '',
            timestamp: item.timestamp,
            role: 'user'
          });
        }
        if (item.assistant) {
          const systemInfo = detectSystemMessage(item.assistant);
          mappedMessages.push({
            message: item.assistant,
            reply: '',
            timestamp: item.timestamp,
            role: systemInfo.isSystem ? 'system' : 'assistant',
            messageType: systemInfo.messageType
          });
        }
      });
      // Always fully replace messages with the latest backend history
      setMessages(mappedMessages);
      
      // Find and set the current session
      const session = sessions.find(s => s.session_id === id);
      if (session) {
        setCurrentSession(session);
  // If the session already has a non-default title, suppress auto-naming
  setHasUserEditedTitle(session.title !== 'New Chat');
        console.log('✅ Session loaded successfully:', id);
        toast({ 
          title: 'Session Loaded', 
          description: 'Chat session loaded successfully.' 
        });
      } else {
        // Create a temporary session object if not found in list
        setCurrentSession({ session_id: id, title: 'Chat Session' });
  setHasUserEditedTitle(true); // Avoid auto-renaming unknown sessions
        console.log('⚠️ Session not found in list, created temporary:', id);
      }
    } catch (err: any) {
      console.error('❌ Error loading session:', err);
      setError(isDev ? maintenanceMessage : 'Failed to load session messages');
      
      // Still set the session as current to avoid UI issues
      const session = sessions.find(s => s.session_id === id);
      if (session) {
        setCurrentSession(session);
        setMessages([]);
      }
      
      showErrorToast('Load Error', 'Failed to load session messages. You can still send new messages.');
    } finally {
      setIsLoading(false);
    }
  };
  
  // Fetch sessions on mount and when user changes
  useEffect(() => {
    if (user) {
      fetchSessions();
    } else {
      setIsInitializing(false);
    }
    
    // Failsafe: Always stop initializing after 10 seconds
    const timeout = setTimeout(() => {
      setIsInitializing(false);
    }, 10000);
    
    return () => clearTimeout(timeout);
  }, [user]);

  // Handle URL parameter changes for session switching
  useEffect(() => {
    const loadSessionFromUrl = async () => {
      if (!user || !sessionId || sessions.length === 0) return;
      
      console.log('🔄 URL changed to session:', sessionId);
      
      // Check if this session exists in our sessions list
      const session = sessions.find(s => s.session_id === sessionId);
      if (session) {
        // Only load if it's not the current session
        if (currentSession?.session_id !== sessionId) {
          console.log('📡 Loading session from URL:', sessionId);
          await loadSession(sessionId);
        }
      } else {
        console.log('❌ Session not found in list:', sessionId);
        toast({ 
          title: 'Session Not Found', 
          description: 'The requested session could not be found.', 
          variant: 'destructive' 
        });
        navigate('/chat');
      }
    };

    if (sessions.length > 0) {
      loadSessionFromUrl();
    }
  }, [sessionId, sessions, user]);

  // Create new session in backend
  const handleNewChat = async () => {
    setIsLoading(true);
    try {
      if (!user) return;
      
      // Clear current state immediately
      setMessages([]);
      setCurrentSession(null);
  setHasUserEditedTitle(false); // Reset for brand new chat
      
      const data = await clerkApiRequest<{ session_id: string }>(`/session/create`, 'post', null, { user_id: user.id });
      
      // Set the new session immediately
      const newSession = { session_id: data.session_id, title: 'New Chat' };
      setCurrentSession(newSession);
      
      // Update sessions list
      await fetchSessions();
      
      // Navigate to the new session
      navigate(`/chat/${data.session_id}`);
      
      // Close sidebar on mobile after creating new chat
      if (isMobile) {
        setIsSidebarOpen(false);
      }
    } catch (err: any) {
  showErrorToast('Error', err.message);
    } finally {
      setIsLoading(false);
    }
  };

  // Send message to backend and reload chat history
  const handleSendMessage = async (message: string) => {
    setIsLoading(true);
    setIsTyping(true);
    setError(null);

    try {
      if (!user) return;

      // If no current session, create one first
      let sessionToUse = currentSession;
      if (!sessionToUse) {
        const data = await clerkApiRequest<{ session_id: string }>(`/session/create`, 'post', null, { user_id: user.id });
        sessionToUse = { session_id: data.session_id, title: 'New Chat' };
        setCurrentSession(sessionToUse);
        
        // Update sessions list and navigate
        await fetchSessions();
        navigate(`/chat/${data.session_id}`);
      }

      // Immediately show user message
      setMessages(prev => [
        ...prev,
        {
          message,
          reply: '',
          timestamp: new Date().toISOString(),
          role: 'user'
        }
      ]);
      scrollToBottom();

      // Send message to backend
      const { reply } = await clerkApiRequest<{ reply: string }>(
        `/chat`,
        'post',
        { user_id: user.id, message, session_id: sessionToUse.session_id }
      );

      // Detect if the response is a rate limit or system message
      const isRateLimitMessage = reply.includes('Rate Limit') || 
                                reply.includes('rate limit') || 
                                reply.includes('⏰') ||
                                reply.includes('Quota') ||
                                reply.includes('quota') ||
                                reply.includes('Service Configuration') ||
                                reply.includes('Server Error') ||
                                reply.includes('Temporarily Down');

      const getMessageType = (message: string): 'normal' | 'rate_limit' | 'error' | 'warning' => {
        if (message.includes('Rate Limit') || message.includes('⏰')) return 'rate_limit';
        if (message.includes('Quota') || message.includes('📊')) return 'rate_limit';
        if (message.includes('Configuration') || message.includes('🔐')) return 'error';
        if (message.includes('Server Error') || message.includes('🔧')) return 'warning';
        return 'normal';
      };

      // Add AI response with appropriate role and type
      setMessages(prev => [
        ...prev,
        {
          message: reply,
          reply: '',
          timestamp: new Date().toISOString(),
          role: isRateLimitMessage ? 'system' : 'assistant',
          messageType: isRateLimitMessage ? getMessageType(reply) : 'normal'
        }
      ]);
      setIsTyping(false); // <-- Fix: stop typing indicator after AI reply
      scrollToBottom();

      // Refresh chat history to ensure sync
      const data = await clerkApiRequest<{ history: any[] }>(`/chat/${sessionToUse.session_id}`, 'get');
      // Map backend chat history to frontend Message format (show both user and assistant as separate bubbles)
      const mappedMessages: Message[] = [];
      data.history.forEach((item: any) => {
        if (item.user) {
          mappedMessages.push({
            message: item.user,
            reply: '',
            timestamp: item.timestamp,
            role: 'user'
          });
        }
        if (item.assistant) {
          const systemInfo = detectSystemMessage(item.assistant);
          mappedMessages.push({
            message: item.assistant,
            reply: '',
            timestamp: item.timestamp,
            role: systemInfo.isSystem ? 'system' : 'assistant',
            messageType: systemInfo.messageType
          });
        }
      });
      setMessages(mappedMessages);

      // Improved auto-naming: trigger after first successful assistant reply if still default
      if (sessionToUse.title === 'New Chat') {
    // Skip auto-naming if user already manually edited / generated a title
    if (!hasUserEditedTitle) {
        try {
          const firstUserMessage = mappedMessages.find(m => m.role === 'user')?.message || message;
          const firstAssistantMessage = mappedMessages.find(m => m.role === 'assistant')?.message || reply;

          if (firstUserMessage && firstAssistantMessage) {
            // Derive a concise title using heuristics: prefer user intent keywords
            const base = firstUserMessage
              .replace(/^(please|hey|hi|hello|can you|could you|explain|write|generate)\b/i, '')
              .trim();
            let candidate = base || firstAssistantMessage.split('\n')[0];
            // Remove markdown formatting asterisks and hashes
            candidate = candidate.replace(/[*#`>_~]/g, '').trim();
            // Collapse whitespace
            candidate = candidate.replace(/\s{2,}/g, ' ');
            // Capitalize first letter
            candidate = candidate.charAt(0).toUpperCase() + candidate.slice(1);
            // Truncate
            if (candidate.length > 48) candidate = candidate.substring(0, 45).trimEnd() + '…';
            // Avoid empty
            if (candidate.length < 3) candidate = 'Chat Session';
            await handleRenameSession(sessionToUse.session_id, candidate);
      // Mark as user-edited equivalent to stop further auto attempts
      setHasUserEditedTitle(true);
          }
        } catch (err) {
          console.log('Auto-naming failed:', err);
        }
    }
      }

      // Close sidebar on mobile after sending message
      if (isMobile) {
        setIsSidebarOpen(false);
      }
    } catch (err: any) {
      setIsTyping(false); // <-- Also stop typing on error
      setLastFailedMessage(message); // Store the message for retry
  showErrorToast('Error', err.message);
    } finally {
      setIsLoading(false);
    }
  };

  // Helper function to detect and categorize system messages
  const detectSystemMessage = (messageText: string): { isSystem: boolean; messageType: 'normal' | 'rate_limit' | 'error' | 'warning' } => {
    const isRateLimitMessage = messageText.includes('Rate Limit') || 
                              messageText.includes('rate limit') || 
                              messageText.includes('⏰') ||
                              messageText.includes('Quota') ||
                              messageText.includes('quota') ||
                              messageText.includes('Service Configuration') ||
                              messageText.includes('Server Error') ||
                              messageText.includes('Temporarily Down');

    if (!isRateLimitMessage) return { isSystem: false, messageType: 'normal' };

    if (messageText.includes('Rate Limit') || messageText.includes('⏰')) return { isSystem: true, messageType: 'rate_limit' };
    if (messageText.includes('Quota') || messageText.includes('📊')) return { isSystem: true, messageType: 'rate_limit' };
    if (messageText.includes('Configuration') || messageText.includes('🔐')) return { isSystem: true, messageType: 'error' };
    if (messageText.includes('Server Error') || messageText.includes('🔧')) return { isSystem: true, messageType: 'warning' };
    return { isSystem: true, messageType: 'normal' };
  };

  // Retry the last failed message
  const handleRetryMessage = async () => {
    if (lastFailedMessage) {
      const messageToRetry = lastFailedMessage;
      setLastFailedMessage(null);
      await handleSendMessage(messageToRetry);
    }
  };

  const handleRenameSession = async (sessionId: string, newTitle: string) => {
    try {
      // Call backend to rename the session
      await clerkApiRequest(
        `/session/${sessionId}`,
        'put',
        { new_title: newTitle }
      );
      
      // Update sessions list
      await fetchSessions();
      
      // Update current session if it's the one being renamed
      if (currentSession?.session_id === sessionId) {
        setCurrentSession(prev => prev ? { ...prev, title: newTitle } : null);
      }
      
      toast({
        title: "Session renamed",
        description: "Chat session title has been updated successfully.",
      });
    } catch (err: any) {
  showErrorToast('Error', 'Failed to rename session: ' + err.message);
    }
  };

  const handleDeleteSession = async (sessionId: string) => {
    try {
      // Call backend to delete the session
      await clerkApiRequest(`/session/${sessionId}`, 'delete');
      
      // Show success message
      toast({
        title: "Session deleted",
        description: "The chat session has been deleted successfully.",
      });
      
      // Refresh sessions list
      await fetchSessions();
      
      // If we deleted the current session, redirect to /chat to start a new one
      if (currentSession?.session_id === sessionId) {
  // Clear chat area immediately for better UX
  setMessages([]);
  setCurrentSession(null);
  navigate('/chat');
      }
    } catch (err: any) {
  showErrorToast('Error', 'Failed to delete session: ' + err.message);
    }
  };

  const handleSaveTitle = async () => {
    if (currentSession && editTitle.trim()) {
      await handleRenameSession(currentSession.session_id, editTitle.trim());
      setIsEditingTitle(false);
      setHasUserEditedTitle(true); // User manually chose a title
    }
  };

  // Generate a title suggestion based on recent messages
  const handleGenerateTitle = async () => {
    if (!currentSession || isGeneratingTitle) return;
    setIsGeneratingTitle(true);
    try {
      // Gather candidate text: prefer last user message, fallback to first user or first assistant
      const userMessages = messages.filter(m => m.role === 'user');
      const assistantMessages = messages.filter(m => m.role === 'assistant');
      const lastUser = userMessages[userMessages.length - 1]?.message || '';
      const firstUser = userMessages[0]?.message || '';
      const firstAssistant = assistantMessages[0]?.message || '';
      let base = lastUser || firstUser || firstAssistant || 'Chat Session';
      base = base
        .replace(/^(please|hey|hi|hello|can you|could you|explain|write|generate)\b/i, '')
        .trim();
      let candidate = base.split('\n')[0];
      candidate = candidate.replace(/[*#`>_~]/g, '').trim();
      candidate = candidate.replace(/\s{2,}/g, ' ');
      if (candidate) {
        candidate = candidate.charAt(0).toUpperCase() + candidate.slice(1);
      }
      if (candidate.length > 48) candidate = candidate.substring(0, 45).trimEnd() + '…';
      if (candidate.length < 3) candidate = 'Chat Session';
      await handleRenameSession(currentSession.session_id, candidate);
      setHasUserEditedTitle(true); // Prevent further auto renames
    } catch (err: any) {
      toast({
        title: 'Title generation failed',
        description: err.message || 'Could not generate a title right now.',
        variant: 'destructive'
      });
    } finally {
      setIsGeneratingTitle(false);
    }
  };

  const handleSignOut = async () => {
    await signOut();
    navigate('/');
    toast({
      title: "Signed out",
      description: "Come back soon!"
    });
  };

  // Toggle sidebar visibility
  const toggleSidebar = () => {
    setIsSidebarOpen(!isSidebarOpen);
  };

  // Handle session selection and close sidebar on mobile
  const handleSelectSession = async (id: string) => {
    if (!user || !id) return;
    
    try {
      // Prevent selecting the same session
      if (currentSession?.session_id === id) {
        if (isMobile) {
          setIsSidebarOpen(false);
        }
        return;
      }
      
      console.log('🔄 Switching to session:', id);
      setIsLoading(true);
      setError(null);
      
      // Load the session data
      await loadSession(id);
      
      // Navigate to the session URL
      navigate(`/chat/${id}`);
      
      // Close sidebar on mobile
      if (isMobile) {
        setIsSidebarOpen(false);
      }
      
      console.log('✅ Session switch completed:', id);
    } catch (err: any) {
  console.error('❌ Session switch failed:', err);
  showErrorToast('Error', 'Failed to load session: ' + err.message);
    } finally {
      setIsLoading(false);
    }
  };

  // Show loading screen while user data loads or during initialization (with timeout)
  if (!isLoaded || !user || (isInitializing && user)) {
    return (
      <div className="h-screen flex items-center justify-center bg-background">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin mx-auto mb-4 text-primary" />
          <p className="text-muted-foreground">
            {!isLoaded ? "Loading..." : !user ? "Loading chat..." : "Setting up your session..."}
          </p>
          {isInitializing && (
            <p className="text-xs text-muted-foreground mt-2">
              Having trouble connecting? <button 
                onClick={() => setIsInitializing(false)} 
                className="text-primary underline"
              >
                Skip and continue
              </button>
            </p>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex bg-background">
      {/* Name Setup Modal */}
      <NameSetupModal
        isOpen={showNameModal}
        onComplete={handleNameSetup}
        onSkip={handleNameSkip}
      />
      
      <AnimatePresence>
        {error && (
          <motion.div 
            className="fixed top-4 right-4 z-50 max-w-md"
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
          >
            <div className="bg-destructive/15 border border-destructive text-destructive px-4 py-3 rounded-lg flex items-center gap-3">
              <AlertTriangle className="h-5 w-5" />
              <p className="text-sm">{error}</p>
              <Button 
                variant="ghost" 
                size="icon" 
                className="ml-auto" 
                onClick={() => setError(null)}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Mobile Sidebar Overlay */}
      <AnimatePresence>
        {isMobile && isSidebarOpen && (
          <motion.div
            className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={() => setIsSidebarOpen(false)}
            onTouchStart={() => setIsSidebarOpen(false)} // Handle touch events
          />
        )}
      </AnimatePresence>

      {/* Sidebar */}
      <AnimatePresence>
        {isSidebarOpen && (
          <motion.div
            className={cn(
              "z-50 bg-background",
              isMobile 
                ? "fixed left-0 top-0 h-full w-80 shadow-xl" 
                : "relative w-80 border-r border-border"
            )}
            initial={isMobile ? { x: "-100%", opacity: 0 } : { opacity: 1, x: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={isMobile ? { x: "-100%", opacity: 0 } : { opacity: 0, x: 0 }}
            transition={{ 
              duration: 0.3, 
              ease: "easeInOut",
              opacity: { duration: isMobile ? 0.2 : 0.3 }
            }}
          >
            <Sidebar
              sessions={sessions}
              currentSessionId={currentSession?.session_id}
              user={user ? {
                id: user.id,
                name: user.fullName || user.username || user.emailAddresses?.[0]?.emailAddress || 'User',
                email: user.emailAddresses?.[0]?.emailAddress || '',
                avatar: user.imageUrl
              } : undefined}
              onNewChat={handleNewChat}
              onSelectSession={handleSelectSession}
              onRenameSession={handleRenameSession}
              onDeleteSession={handleDeleteSession}
              onSignOut={handleSignOut}
              onClose={() => setIsSidebarOpen(false)}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Chat Area */}
      <div className={cn(
        "flex flex-col h-full min-h-0",
        isMobile ? "flex-1" : (isSidebarOpen ? "flex-1" : "w-full")
      )}>
        {/* Chat Header */}
        <motion.header 
          className="p-4 border-b border-border/50 bg-card/50 backdrop-blur-sm"
          initial={{ y: -50, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.3 }}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {/* Mobile Menu Button */}
              {isMobile && (
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={toggleSidebar}
                  className="shrink-0"
                >
                  <Menu className="h-5 w-5" />
                </Button>
              )}
              
              {isEditingTitle ? (
                <div className="flex items-center gap-2">
                  <Input
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleSaveTitle();
                      if (e.key === 'Escape') setIsEditingTitle(false);
                    }}
                    className="h-8 min-w-[200px]"
                    autoFocus
                  />
                  <Button variant="ghost" size="icon" onClick={handleSaveTitle}>
                    <Check className="w-4 h-4 text-green-600" />
                  </Button>
                  <Button variant="ghost" size="icon" onClick={() => setIsEditingTitle(false)}>
                    <X className="w-4 h-4 text-destructive" />
                  </Button>
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <h1 className="text-xl font-semibold text-foreground">
                    {currentSession?.title || 'New Chat'}
                  </h1>
                  <Button 
                    variant="ghost" 
                    size="icon"
                    onClick={() => setIsEditingTitle(true)}
                    className="w-6 h-6"
                  >
                    <Edit3 className="w-3 h-3" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={isGeneratingTitle || !currentSession}
                    onClick={handleGenerateTitle}
                    className="h-7 px-2 text-xs"
                  >
                    {isGeneratingTitle ? (
                      <span className="flex items-center gap-1"><Loader2 className="h-3 w-3 animate-spin" />Generating…</span>
                    ) : 'Generate Title'}
                  </Button>
                </div>
              )}
            </div>
          </div>
        </motion.header>

        {/* Messages Area */}
        <div className={cn(
          "flex-1 overflow-y-auto bg-gradient-chat min-h-0"
        )}>
          <div className="py-8 space-y-4 min-h-full">
            <AnimatePresence mode="wait">
              {messages.length === 0 && isLoading ? (
                <motion.div
                  key="loading"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  className="text-center py-16"
                >
                  <div className="max-w-md mx-auto">
                    <Loader2 className="w-8 h-8 animate-spin mx-auto mb-4 text-primary" />
                    <h3 className="text-xl font-semibold mb-2 text-foreground">
                      Loading chat...
                    </h3>
                  </div>
                </motion.div>
              ) : messages.length === 0 && !isLoading ? (
                <motion.div
                  key="empty"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  className="text-center py-16"
                >
                  <div className="max-w-md mx-auto">
                    <h3 className="text-xl font-semibold mb-2 text-foreground">
                      Start chatting with Kuro
                    </h3>
                    <p className="text-muted-foreground text-lg mb-2">
                      How can I help you today?
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Powered by Groq LLaMA 3 70B
                    </p>
                  </div>
                </motion.div>
              ) : (
                <motion.div
                  key="messages"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="space-y-4"
                >
                  {messages.map((message, idx) => (
                    <motion.div
                      key={message.timestamp + idx}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: idx * 0.1 }}
                    >
                      <ChatBubble
                        message={message}
                        userAvatar={user?.imageUrl || ''}
                        onRetry={handleRetryMessage}
                      />
                    </motion.div>
                  ))}
                  {isTyping && (
                    <motion.div
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: 20 }}
                      className="flex items-center gap-2 px-4 py-2"
                    >
                      <div className="flex space-x-2">
                        <div className="w-2 h-2 rounded-full bg-primary/40 animate-bounce [animation-delay:-0.3s]"></div>
                        <div className="w-2 h-2 rounded-full bg-primary/40 animate-bounce [animation-delay:-0.15s]"></div>
                        <div className="w-2 h-2 rounded-full bg-primary/40 animate-bounce"></div>
                      </div>
                      <span className="text-sm text-muted-foreground">Kuro is typing...</span>
                    </motion.div>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Chat Input */}
        <ChatInput
          onSendMessage={handleSendMessage}
          disabled={isLoading}
          showTypingIndicator={isTyping}
          placeholder={
            isLoading 
              ? "Kuro is thinking..." 
              : isTyping 
                ? "Kuro is typing..." 
                : "Type your message..."
          }
        />
      </div>
    </div>
  );
}

export default Chat;