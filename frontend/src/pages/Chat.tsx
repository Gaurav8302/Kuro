import { useState, useEffect, useRef, useCallback, memo, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { OptimizedSidebar } from '@/components/OptimizedSidebar';
import { OptimizedKuroIntro } from '@/components/OptimizedKuroIntro';
import { OptimizedChatBubble } from '@/components/OptimizedChatBubble';
import { OptimizedChatInput } from '@/components/OptimizedChatInput';
import { OptimizedHolographicBackground } from '@/components/OptimizedHolographicBackground';
import { TypingIndicator } from '@/components/TypingIndicator';
import { MessageList } from '@/components/MessageList';
import NameSetupModal from '@/components/NameSetupModal';
import { Input } from '@/components/ui/input';
import { 
  Edit3,
  Check,
  X,
  AlertTriangle,
  Loader2,
  Menu,
  Zap,
  Brain
} from 'lucide-react';
import { Message, ChatSession } from '@/types';
import { useToast } from '@/hooks/use-toast';
import { cn } from '@/lib/utils';
import { useClerkApi, setUserName, getUserName, checkUserHasName, getIntroShown, setIntroShown } from '@/lib/api';
import { useAuth, useUser } from '@clerk/clerk-react';
import { useIsMobile } from '@/hooks/use-mobile';
import { OptimizedHolographicCard } from '@/components/OptimizedHolographicCard';
import { HolographicButton } from '@/components/HolographicButton';
import { HoloMenuIcon, HoloSparklesIcon } from '@/components/HolographicIcons';
import { useOptimizedAnimations } from '@/hooks/use-performance';

const Chat = () => {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const clerkApiRequest = useClerkApi();
  const { user, isLoaded } = useUser();
  const { signOut } = useAuth();
  const isMobile = useIsMobile();
  const { shouldReduceAnimations, animationDuration } = useOptimizedAnimations();
  
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
  // Show first-time welcome animation after initial sign-in only once per user
  const [showFirstTimeIntro, setShowFirstTimeIntro] = useState(false);
  const [introChecking, setIntroChecking] = useState(true);
  const [displayedName, setDisplayedName] = useState(user?.fullName || user?.username || '');

  useEffect(() => {
    setDisplayedName(user?.fullName || user?.username || '');
  }, [user]);
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

  // First-time intro logic - show after name is set or if user already has name
  useEffect(() => {
    const checkIntro = async () => {
      if (!user || !isLoaded) return;
      
      // Wait for name check to complete first
      if (!hasCheckedName) return;
      
      // Don't show intro if name modal is currently open
      if (showNameModal) return;
      
      try {
        const { intro_shown } = await getIntroShown(user.id);
        
        // Show intro if it hasn't been shown yet (regardless of name status)
        if (!intro_shown) {
          setShowFirstTimeIntro(true);
          // Persist immediately so even if user refreshes it's not shown again
          await setIntroShown(user.id);
          // Auto dismiss after 7s
          setTimeout(() => setShowFirstTimeIntro(false), 7000);
        }
      } catch (e) {
        console.error('Error checking intro status:', e);
        // Fallback to localStorage if backend call fails (offline tolerance)
        const fallbackKey = `kuro_intro_shown_${user.id}`;
        if (!localStorage.getItem(fallbackKey)) {
          localStorage.setItem(fallbackKey, '1');
          setShowFirstTimeIntro(true);
          setTimeout(() => setShowFirstTimeIntro(false), 7000);
        }
      } finally {
        setIntroChecking(false);
      }
    };
    checkIntro();
  }, [user, isLoaded, hasCheckedName, showNameModal]);

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
  // Smarter scroll-to-bottom with edge detection to avoid yanking user upward while reading history
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const isUserNearBottomRef = useRef(true);

  const scrollToBottom = (behavior: ScrollBehavior = 'smooth') => {
    // Use requestAnimationFrame to ensure layout is settled (especially after images / code blocks)
    requestAnimationFrame(() => {
      if (messagesEndRef.current) {
        messagesEndRef.current.scrollIntoView({ behavior });
      }
    });
  };

  const handleScroll = useCallback(() => {
    if (!scrollContainerRef.current) return;
    const el = scrollContainerRef.current;
    const threshold = 160; // px from bottom to still auto-stick
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    isUserNearBottomRef.current = distanceFromBottom < threshold;
  }, []);

  // Attach scroll listener to main messages container
  useEffect(() => {
    const el = scrollContainerRef.current;
    if (!el) return;
    el.addEventListener('scroll', handleScroll, { passive: true });
    return () => el.removeEventListener('scroll', handleScroll);
  }, []);

  useEffect(() => {
    // Only auto-scroll if user is already near bottom or it's a brand new session
    if (isUserNearBottomRef.current || messages.length <= 2) {
      scrollToBottom(messages.length <= 2 ? 'auto' : 'smooth');
    }
  }, [messages]);

  // Also scroll when typing indicator appears if user is near bottom
  useEffect(() => {
    if (isTyping && isUserNearBottomRef.current) {
      scrollToBottom('smooth');
    }
  }, [isTyping]);

  // Dynamic viewport height variable for mobile (accounts for URL bar / keyboard)
  useEffect(() => {
    const setAppHeight = () => {
      const vh = window.innerHeight * 0.01;
      document.documentElement.style.setProperty('--app-height', `${vh * 100}px`);
    };
    setAppHeight();
    window.addEventListener('resize', setAppHeight);
    window.addEventListener('orientationchange', setAppHeight);
    return () => {
      window.removeEventListener('resize', setAppHeight);
      window.removeEventListener('orientationchange', setAppHeight);
    };
  }, []);

  // When virtual keyboard opens (mobile), ensure last message visible after a tick
  useEffect(() => {
    if (!isMobile) return;
    const handleFocus = () => setTimeout(() => scrollToBottom('auto'), 50);
    window.addEventListener('focusin', handleFocus);
    return () => window.removeEventListener('focusin', handleFocus);
  }, [isMobile]);

  // Check if user needs to set their name (only for authenticated users)
  useEffect(() => {
    const checkUserName = async () => {
      if (!user || hasCheckedName) return;
      
      console.log('🔍 Checking if user has name set...', user.id);
      
      try {
        const { has_name } = await checkUserHasName(user.id);
        console.log('📝 User has name:', has_name);
        
        if (!has_name) {
          console.log('🔔 Showing name setup modal');
          setShowNameModal(true);
        } else {
          // If user has a name, load it
          try {
            const { name } = await getUserName(user.id);
            if (name) {
              console.log('👤 Loaded user name:', name);
              setDisplayedName(name);
            }
          } catch (error) {
            console.error('Error loading user name:', error);
            // Use fallback from Clerk if backend fails
          }
        }
      } catch (error) {
        console.error('Error checking user name:', error);
        // If backend is not available, show name modal to be safe
        console.log('⚠️ Backend error - showing name modal as fallback');
        setShowNameModal(true);
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
      setDisplayedName(name);
      toast({
        title: "Welcome!",
        description: `Nice to meet you, ${name}! 🎉`,
      });
      
      // Show intro animation after name setup is complete
      const introTimeout1 = setTimeout(() => {
        if (!showFirstTimeIntro) {
          setShowFirstTimeIntro(true);
          const introTimeout2 = setTimeout(() => setShowFirstTimeIntro(false), 7000);
          // Store timeout reference for potential cleanup
          return () => {
            clearTimeout(introTimeout2);
          };
        }
      }, 500);
      
      // Store timeout for cleanup if needed
      return () => {
        clearTimeout(introTimeout1);
      };
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
    
    // Show intro animation after skip
    setTimeout(() => {
      if (!showFirstTimeIntro) {
        setShowFirstTimeIntro(true);
        setTimeout(() => setShowFirstTimeIntro(false), 7000);
      }
    }, 500);
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
      const response = await clerkApiRequest<{ 
        reply: string;
        model?: string;
        route_rule?: string;
        latency_ms?: number;
        intents?: string[];
      }>(
        `/chat`,
        'post',
        { user_id: user.id, message, session_id: sessionToUse.session_id }
      );

      // Detect if the response is a rate limit or system message
      const isRateLimitMessage = response.reply.includes('Rate Limit') || 
                                response.reply.includes('rate limit') || 
                                response.reply.includes('⏰') ||
                                response.reply.includes('Quota') ||
                                response.reply.includes('quota') ||
                                response.reply.includes('Service Configuration') ||
                                response.reply.includes('Server Error') ||
                                response.reply.includes('Temporarily Down');

      const getMessageType = (message: string): 'normal' | 'rate_limit' | 'error' | 'warning' => {
        if (message.includes('Rate Limit') || message.includes('⏰')) return 'rate_limit';
        if (message.includes('Quota') || message.includes('📊')) return 'rate_limit';
        if (message.includes('Configuration') || message.includes('🔐')) return 'error';
        if (message.includes('Server Error') || message.includes('🔧')) return 'warning';
        return 'normal';
      };

      // Add AI response with model information and appropriate role and type
      setMessages(prev => [
        ...prev,
        {
          message: response.reply,
          reply: '',
          timestamp: new Date().toISOString(),
          role: isRateLimitMessage ? 'system' : 'assistant',
          messageType: isRateLimitMessage ? getMessageType(response.reply) : 'normal',
          model: response.model,
          route_rule: response.route_rule,
          latency_ms: response.latency_ms,
          intents: response.intents
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
          const firstAssistantMessage = mappedMessages.find(m => m.role === 'assistant')?.message || response.reply;

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
      <div className="h-screen flex items-center justify-center bg-background relative overflow-hidden">
        <OptimizedHolographicBackground variant="subtle" />
        <div className="text-center">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ 
              duration: shouldReduceAnimations ? 1 : 2, 
              repeat: Infinity, 
              ease: 'linear' 
            }}
            className="w-16 h-16 mx-auto mb-6"
          >
            <div className="w-full h-full rounded-full border-4 border-holo-cyan-400/30 border-t-holo-cyan-400 shadow-holo-glow" />
          </motion.div>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: shouldReduceAnimations ? 0.1 : 0.3 }}
          >
            <h3 className="text-xl font-orbitron text-holo-cyan-400 text-holo-glow mb-2">
              INITIALIZING NEURAL INTERFACE
            </h3>
            <p className="text-holo-cyan-400/60 font-rajdhani tracking-wide">
            {!isLoaded ? "Loading..." : !user ? "Loading chat..." : "Setting up your session..."}
          </p>
          {isInitializing && (
            <p className="text-xs text-holo-cyan-400/50 mt-4 font-orbitron">
              HAVING TROUBLE CONNECTING? <button 
                onClick={() => setIsInitializing(false)} 
                className="text-holo-cyan-400 underline hover:text-holo-cyan-300 transition-colors"
              >
                SKIP AND CONTINUE
              </button>
            </p>
          )}
          </motion.div>
        </div>
      </div>
    );
  }

  return (
  <div className={cn(
    "flex bg-background relative overflow-hidden",
    isMobile ? "min-app-height" : "h-screen"
  )}>
      <OptimizedHolographicBackground variant="default" />
      
      <AnimatePresence>
        {showFirstTimeIntro && !showNameModal && (
          <motion.div
            key="intro-overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: animationDuration }}
            className="fixed inset-0 z-[9998]"
          >
            <OptimizedKuroIntro
              phrases={[
                displayedName ? `Welcome, ${displayedName}` : 'Welcome',
                "Let's Imagine",
                "Let's Build",
                'Kuro AI'
              ]}
              cycleMs={1600}
              fullscreen
              onFinish={() => {/* keep visible until user closes or timeout */}}
            />
            {/* Skip / Close button */}
            <motion.button
              onClick={() => setShowFirstTimeIntro(false)}
              className="absolute top-6 right-6 z-[10000] px-6 py-3 rounded-full glass-panel border-holo-cyan-400/30 text-holo-cyan-300 hover:text-holo-cyan-100 hover:shadow-holo-glow text-sm font-orbitron tracking-wide transition-all duration-300"
              whileHover={shouldReduceAnimations ? undefined : { 
                scale: 1.05, 
                boxShadow: '0 0 30px rgba(0, 230, 214, 0.4)' 
              }}
              whileTap={{ scale: 0.95 }}
            >
              SKIP TRANSMISSION
            </motion.button>
          </motion.div>
        )}
      </AnimatePresence>
      
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
            initial={{ opacity: 0, y: -30, scale: 0.8 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -30, scale: 0.8 }}
            transition={{ duration: animationDuration, ease: 'easeOut' }}
          >
            <OptimizedHolographicCard variant="intense" className="bg-holo-magenta-500/10 border-holo-magenta-400/30">
              <div className="px-4 py-3 flex items-center gap-3">
                <AlertTriangle className="h-5 w-5 text-holo-magenta-400" />
                <p className="text-sm text-holo-magenta-200 font-space">{error}</p>
                <motion.button
                className="ml-auto w-6 h-6 rounded bg-holo-magenta-500/20 hover:bg-holo-magenta-500/30 border border-holo-magenta-400/30 flex items-center justify-center transition-all duration-300"
                onClick={() => setError(null)}
                whileHover={shouldReduceAnimations ? undefined : { scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
              >
                <X className="h-3 w-3 text-holo-magenta-400" />
              </motion.button>
              </div>
            </OptimizedHolographicCard>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Mobile Sidebar Overlay */}
      <AnimatePresence>
        {isMobile && isSidebarOpen && (
          <motion.div
            className="fixed inset-0 z-40 bg-black/60 backdrop-blur-md"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: animationDuration }}
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
              "z-50 bg-background/95 backdrop-blur-xl",
              isMobile 
                ? "fixed left-0 top-0 h-full w-80 shadow-holo-glow border-r border-holo-cyan-500/30" 
                : "relative w-80 border-r border-holo-cyan-500/20"
            )}
            initial={isMobile ? { x: "-100%", opacity: 0 } : { opacity: 1, x: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={isMobile ? { x: "-100%", opacity: 0 } : { opacity: 0, x: 0 }}
            transition={{ 
              duration: shouldReduceAnimations ? 0.15 : 0.25, 
              ease: [0.25, 0.1, 0.25, 1]
            }}
          >
            <OptimizedSidebar
              sessions={sessions}
              currentSessionId={currentSession?.session_id}
              user={user ? {
                id: user.id,
                name: displayedName || 'User',
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
        // Flex column so header, scrollable messages, and input stack; input naturally at bottom
        "flex flex-col h-full min-h-0 relative",
        isMobile ? "flex-1" : (isSidebarOpen ? "flex-1" : "w-full")
      )}>
        {/* Chat Header */}
        <motion.header 
          className="p-4 border-b border-holo-cyan-500/20 glass-panel backdrop-blur-xl relative overflow-hidden"
          initial={{ y: -50, opacity: 0, filter: 'blur(10px)' }}
          animate={{ y: 0, opacity: 1, filter: 'blur(0px)' }}
          transition={{ duration: animationDuration, ease: 'easeOut' }}
        >
          {/* Header scan line */}
          {!shouldReduceAnimations && <motion.div
            className="absolute bottom-0 left-0 w-full h-0.5 bg-gradient-to-r from-transparent via-holo-cyan-400 to-transparent"
            animate={{ opacity: [0.3, 0.8, 0.3] }}
            transition={{ duration: 2, repeat: Infinity }}
          />}
          
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {/* Menu Button for all devices */}
              <button
                onClick={toggleSidebar}
                className="shrink-0 w-10 h-10 rounded-lg glass-panel border-holo-cyan-400/30 hover:shadow-holo-glow transition-all duration-200 flex items-center justify-center transform-gpu hover:scale-110 active:scale-95"
                title={isSidebarOpen ? "Close Sidebar" : "Open Sidebar"}
              >
                <HoloMenuIcon size={20} />
              </button>
              
              {isEditingTitle ? (
                <div className="flex items-center gap-2">
                  <Input
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleSaveTitle();
                      if (e.key === 'Escape') setIsEditingTitle(false);
                    }}
                    className="h-8 min-w-[200px] glass-panel border-holo-cyan-400/30 text-holo-cyan-100 font-space"
                    autoFocus
                  />
                  <button 
                    onClick={handleSaveTitle}
                    className="w-8 h-8 rounded glass-panel border-holo-green-400/30 hover:shadow-holo-green transition-all duration-200 flex items-center justify-center transform-gpu hover:scale-110 active:scale-95"
                  >
                    <Check className="w-4 h-4 text-holo-green-400" />
                  </button>
                  <button 
                    onClick={() => setIsEditingTitle(false)}
                    className="w-8 h-8 rounded glass-panel border-holo-magenta-400/30 hover:shadow-holo-magenta transition-all duration-200 flex items-center justify-center transform-gpu hover:scale-110 active:scale-95"
                  >
                    <X className="w-4 h-4 text-holo-magenta-400" />
                  </button>
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <h1 className="text-xl font-semibold text-holo-cyan-300 text-holo-glow font-orbitron tracking-wide">
                    {currentSession?.title || 'New Chat'}
                  </h1>
                  <button
                    onClick={() => setIsEditingTitle(true)}
                    className="w-6 h-6 rounded glass-panel border-holo-cyan-400/20 hover:border-holo-cyan-400/40 hover:shadow-holo-glow transition-all duration-200 flex items-center justify-center transform-gpu hover:scale-110 active:scale-95"
                  >
                    <Edit3 className="w-3 h-3 text-holo-cyan-400" />
                  </button>
                  <HolographicButton
                    variant="ghost"
                    size="sm"
                    disabled={isGeneratingTitle || !currentSession}
                    onClick={handleGenerateTitle}
                    className="h-7 px-3 text-xs font-orbitron tracking-wide"
                  >
                    {isGeneratingTitle ? (
                      <span className="flex items-center gap-1">
                        <motion.div
                          animate={{ rotate: 360 }}
                          transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                        >
                          <Zap className="h-3 w-3" />
                        </motion.div>
                        GENERATING...
                      </span>
                    ) : (
                      <>
                        <Brain className="w-3 h-3 mr-1" />
                        GENERATE TITLE
                      </>
                    )}
                  </HolographicButton>
                </div>
              )}
            </div>
          </div>
        </motion.header>

        {/* Messages Area */}
        <div
          ref={scrollContainerRef}
          className={cn(
            // flex-1 so it grows and leaves room for input; min-h-0 to allow shrinking
            "flex-1 overflow-y-auto min-h-0 relative scroll-smooth",
            isMobile && "pb-28 px-1"
          )}
        >
          {/* Chat area background effects */}
          {!shouldReduceAnimations && (
            <>
              <div className="absolute inset-0 bg-gradient-to-b from-background/40 to-background/60" />
              <div className="absolute inset-0 holo-grid-bg opacity-20" />
            </>
          )}
          
          <div className={cn(
            "py-8 space-y-6 relative z-10",
            isMobile && "space-y-3 py-6" // tighter vertical rhythm on mobile
          )}>
            <AnimatePresence mode="wait">
              {messages.length === 0 && isLoading ? (
                <motion.div
                  key="loading"
                  initial={{ opacity: 0, y: 30, scale: 0.8 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -30, scale: 0.8 }}
                  transition={{ duration: animationDuration, ease: 'easeOut' }}
                  className="text-center py-16"
                >
                  <div className="max-w-md mx-auto">
                    <motion.div
                      animate={{ rotate: 360 }}
                      transition={{ 
                        duration: shouldReduceAnimations ? 1 : 2, 
                        repeat: Infinity, 
                        ease: 'linear' 
                      }}
                      className="w-16 h-16 mx-auto mb-6"
                    >
                      <div className="w-full h-full rounded-full border-4 border-holo-cyan-400/30 border-t-holo-cyan-400 shadow-holo-glow" />
                    </motion.div>
                    <h3 className="text-xl font-semibold mb-2 text-holo-cyan-300 text-holo-glow font-orbitron">
                      LOADING TRANSMISSION...
                    </h3>
                  </div>
                </motion.div>
              ) : messages.length === 0 && !isLoading ? (
                <motion.div
                  key="empty"
                  initial={{ opacity: 0, y: 30, scale: 0.8 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -30, scale: 0.8 }}
                  transition={{ duration: animationDuration * 1.2, ease: 'easeOut' }}
                  className="text-center py-16"
                >
                  <div className="max-w-lg mx-auto">
                    <motion.div
                      animate={shouldReduceAnimations ? {} : { 
                        scale: [1, 1.1, 1],
                        rotate: [0, 5, -5, 0]
                      }}
                      transition={{ 
                        duration: shouldReduceAnimations ? 0 : 4, 
                        repeat: shouldReduceAnimations ? 0 : Infinity 
                      }}
                      className="w-20 h-20 mx-auto mb-6 bg-gradient-to-br from-holo-cyan-500 to-holo-purple-500 rounded-full flex items-center justify-center shadow-holo-glow"
                    >
                      <HoloSparklesIcon size={32} className="text-white" />
                    </motion.div>
                    <h3 className="text-2xl font-semibold mb-4 text-holo-cyan-300 text-holo-glow font-orbitron tracking-wide">
                      NEURAL INTERFACE READY
                    </h3>
                    <p className="text-holo-cyan-100 text-lg mb-3 font-space">
                      How may I assist your mission today?
                    </p>
                    <p className="text-xs text-holo-cyan-400/60 font-orbitron tracking-wider">
                      POWERED BY GROQ LLAMA 3 70B NEURAL CORE
                    </p>
                  </div>
                </motion.div>
              ) : (
                <MessageList
                  key="messages"
                  messages={messages}
                  userAvatar={user?.imageUrl || ''}
                  isTyping={isTyping}
                  onRetry={handleRetryMessage}
                />
              )}
            </AnimatePresence>
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Chat Input */}
        <OptimizedChatInput
          onSendMessage={handleSendMessage}
          sending={isTyping || isLoading}
          placeholder={
            (isTyping || isLoading)
              ? "KURO IS RESPONDING..." 
              : "TRANSMIT YOUR QUERY..."
          }
        />
      </div>
    </div>
  );
}

export default Chat;