import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Sidebar } from '@/components/Sidebar';
import { ChatBubble } from '@/components/ChatBubble';
import { ChatInput } from '@/components/ChatInput';
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
import { useClerkApi } from '@/lib/api';
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
  
  // Redirect to sign-in if user is not authenticated
  useEffect(() => {
    if (isLoaded && !user) {
      navigate('/auth/signin');
    }
  }, [isLoaded, user, navigate]);
  
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
        loadSession(sessionId);
      }
    } catch (err: any) {
      toast({ title: 'Error', description: err.message, variant: 'destructive' });
    }
  };

  // Load session messages from backend and map to Message[]
  const loadSession = async (id: string) => {
    setIsLoading(true);
    try {
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
          mappedMessages.push({
            message: item.assistant,
            reply: '',
            timestamp: item.timestamp,
            role: 'assistant'
          });
        }
      });
      // Always fully replace messages with the latest backend history
      setMessages(mappedMessages);
      setCurrentSession(sessions.find(s => s.session_id === id) || null);
    } catch (err: any) {
      toast({ title: 'Error', description: err.message, variant: 'destructive' });
    } finally {
      setIsLoading(false);
    }
  };
  // Load session on sessionId change
  useEffect(() => {
    if (sessionId && sessions.length > 0) {
      loadSession(sessionId);
    }
  }, [sessionId, sessions]);
  // Fetch sessions on mount and when user changes
  useEffect(() => {
    fetchSessions();
  }, [user]);

  // Create new session in backend
  const handleNewChat = async () => {
    setIsLoading(true);
    try {
      if (!user) return;
      const data = await clerkApiRequest<{ session_id: string }>(`/session/create`, 'post', null, { user_id: user.id });
      await fetchSessions();
      navigate(`/chat/${data.session_id}`);
      // After navigating, clear messages and set current session
      setMessages([]);
      setCurrentSession({ session_id: data.session_id, title: 'New Chat' });
      
      // Close sidebar on mobile after creating new chat
      if (isMobile) {
        setIsSidebarOpen(false);
      }
    } catch (err: any) {
      toast({ title: 'Error', description: err.message, variant: 'destructive' });
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
      if (!user || !currentSession) return;

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
        { user_id: user.id, message, session_id: currentSession.session_id }
      );

      // Add AI response
      setMessages(prev => [
        ...prev,
        {
          message: reply,
          reply: '',
          timestamp: new Date().toISOString(),
          role: 'assistant'
        }
      ]);
      setIsTyping(false); // <-- Fix: stop typing indicator after AI reply
      scrollToBottom();

      // Refresh chat history to ensure sync
      const data = await clerkApiRequest<{ history: any[] }>(`/chat/${currentSession.session_id}`, 'get');
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
          mappedMessages.push({
            message: item.assistant,
            reply: '',
            timestamp: item.timestamp,
            role: 'assistant'
          });
        }
      });
      setMessages(mappedMessages);

      // Auto-name session after 3-4 messages if still "New Chat"
      if (mappedMessages.length >= 6 && currentSession.title === 'New Chat') { // 6 messages = 3 exchanges
        try {
          // Generate title from first user message
          const firstUserMessage = mappedMessages.find(m => m.role === 'user')?.message || message;
          const generatedTitle = firstUserMessage.length > 50 
            ? firstUserMessage.substring(0, 47) + '...' 
            : firstUserMessage;
          
          await handleRenameSession(currentSession.session_id, generatedTitle);
        } catch (err) {
          // Ignore auto-naming errors, not critical
          console.log('Auto-naming failed:', err);
        }
      }

      // Close sidebar on mobile after sending message
      if (isMobile) {
        setIsSidebarOpen(false);
      }
    } catch (err: any) {
      setIsTyping(false); // <-- Also stop typing on error
      toast({ title: 'Error', description: err.message, variant: 'destructive' });
    } finally {
      setIsLoading(false);
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
      toast({ 
        title: 'Error', 
        description: 'Failed to rename session: ' + err.message, 
        variant: 'destructive' 
      });
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
        navigate('/chat');
      }
    } catch (err: any) {
      toast({ 
        title: 'Error', 
        description: 'Failed to delete session: ' + err.message, 
        variant: 'destructive' 
      });
    }
  };

  const handleSaveTitle = async () => {
    if (currentSession && editTitle.trim()) {
      await handleRenameSession(currentSession.session_id, editTitle.trim());
      setIsEditingTitle(false);
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
  const handleSelectSession = (id: string) => {
    navigate(`/chat/${id}`);
    if (isMobile) {
      setIsSidebarOpen(false);
    }
  };

  // Show loading screen while checking authentication
  if (!isLoaded) {
    return (
      <div className="h-screen flex items-center justify-center bg-background">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin mx-auto mb-4 text-primary" />
          <p className="text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  // Redirect will happen in useEffect if user is not authenticated
  if (!user) {
    return (
      <div className="h-screen flex items-center justify-center bg-background">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin mx-auto mb-4 text-primary" />
          <p className="text-muted-foreground">Redirecting to sign in...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen-mobile flex bg-background">
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
                : "relative"
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
        "flex flex-col transition-all duration-300",
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
                      Powered by Gemini Free Version
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