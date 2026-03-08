import { useState, useEffect, useRef, useCallback } from 'react';
import { Message, ChatSession } from '@/types';
import { useToast } from '@/hooks/use-toast';

/**
 * Type for the Clerk API request function returned by useClerkApi().
 */
export type ClerkApiRequestFn = <T>(
  endpoint: string,
  method: 'get' | 'post' | 'put' | 'delete',
  data?: any,
  params?: any
) => Promise<T>;

interface UseChatPanelOptions {
  sessionId: string | null;
  sessions: ChatSession[];
  userId: string | undefined;
  clerkApiRequest: ClerkApiRequestFn;
  onSessionsChanged: () => void;
}

interface UseChatPanelReturn {
  // State
  messages: Message[];
  currentSession: ChatSession | null;
  isLoading: boolean;
  isTyping: boolean;
  error: string | null;
  lastFailedMessage: string | null;
  isGeneratingTitle: boolean;
  hasUserEditedTitle: boolean;

  // Refs
  messagesEndRef: React.RefObject<HTMLDivElement>;
  scrollContainerRef: React.RefObject<HTMLDivElement>;
  messagesContainerRef: React.RefObject<HTMLDivElement>;

  // Handlers
  sendMessage: (message: string, searchMode?: boolean) => Promise<void>;
  loadSession: (id: string) => Promise<void>;
  renameSession: (sessionId: string, newTitle: string) => Promise<void>;
  generateTitle: () => Promise<void>;
  retryMessage: () => Promise<void>;
  setError: (error: string | null) => void;
}

/**
 * Helper: detect if a message is a system/rate-limit/error message.
 */
function detectSystemMessage(messageText: string): {
  isSystem: boolean;
  messageType: 'normal' | 'rate_limit' | 'error' | 'warning';
} {
  const isRateLimitMessage =
    messageText.includes('Rate Limit') ||
    messageText.includes('rate limit') ||
    messageText.includes('\u23F0') ||
    messageText.includes('Quota') ||
    messageText.includes('quota') ||
    messageText.includes('Service Configuration') ||
    messageText.includes('Server Error') ||
    messageText.includes('Temporarily Down');

  if (!isRateLimitMessage) return { isSystem: false, messageType: 'normal' };

  if (messageText.includes('Rate Limit') || messageText.includes('\u23F0'))
    return { isSystem: true, messageType: 'rate_limit' };
  if (messageText.includes('Quota') || messageText.includes('\uD83D\uDCCA'))
    return { isSystem: true, messageType: 'rate_limit' };
  if (messageText.includes('Configuration') || messageText.includes('\uD83D\uDD10'))
    return { isSystem: true, messageType: 'error' };
  if (messageText.includes('Server Error') || messageText.includes('\uD83D\uDD27'))
    return { isSystem: true, messageType: 'warning' };
  return { isSystem: true, messageType: 'normal' };
}

/**
 * Map raw backend history to Message[].
 */
function mapHistory(history: any[]): Message[] {
  const mapped: Message[] = [];
  history.forEach((item: any) => {
    if (item.user) {
      mapped.push({
        message: item.user,
        reply: '',
        timestamp: item.timestamp,
        role: 'user',
      });
    }
    if (item.assistant) {
      const systemInfo = detectSystemMessage(item.assistant);
      mapped.push({
        message: item.assistant,
        reply: '',
        timestamp: item.timestamp,
        role: systemInfo.isSystem ? 'system' : 'assistant',
        messageType: systemInfo.messageType,
      });
    }
  });
  return mapped;
}

/**
 * useChatPanel - Encapsulates all per-session chat state and handlers.
 *
 * Each ChatPanel instance calls this hook with its own sessionId to get
 * fully isolated state: messages, loading, typing, scroll, etc.
 */
export function useChatPanel({
  sessionId,
  sessions,
  userId,
  clerkApiRequest,
  onSessionsChanged,
}: UseChatPanelOptions): UseChatPanelReturn {
  const { toast } = useToast();

  // Per-panel state
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentSession, setCurrentSession] = useState<ChatSession | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastFailedMessage, setLastFailedMessage] = useState<string | null>(null);
  const [hasUserEditedTitle, setHasUserEditedTitle] = useState(false);
  const [isGeneratingTitle, setIsGeneratingTitle] = useState(false);

  // Scroll refs
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const isUserNearBottomRef = useRef(true);

  // Dev mode
  const isDev = import.meta.env.DEV;
  const maintenanceMessage = 'Maintenance in progress. Please try again later.';

  const showErrorToast = useCallback(
    (fallbackTitle: string, fallbackDescription: string) => {
      toast({
        title: isDev ? 'Maintenance' : fallbackTitle,
        description: isDev ? maintenanceMessage : fallbackDescription,
        variant: 'destructive',
      });
    },
    [toast, isDev]
  );

  // Scroll helpers
  const scrollToBottom = useCallback((behavior: ScrollBehavior = 'smooth') => {
    requestAnimationFrame(() => {
      if (messagesEndRef.current) {
        messagesEndRef.current.scrollIntoView({ behavior });
      }
    });
  }, []);

  const handleScroll = useCallback(() => {
    if (!scrollContainerRef.current) return;
    const el = scrollContainerRef.current;
    const threshold = 160;
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    isUserNearBottomRef.current = distanceFromBottom < threshold;
  }, []);

  // Attach scroll listener
  useEffect(() => {
    const el = scrollContainerRef.current;
    if (!el) return;
    el.addEventListener('scroll', handleScroll, { passive: true });
    return () => el.removeEventListener('scroll', handleScroll);
  }, [handleScroll]);

  // Auto-scroll on new messages
  useEffect(() => {
    if (isUserNearBottomRef.current || messages.length <= 2) {
      scrollToBottom(messages.length <= 2 ? 'auto' : 'smooth');
    }
  }, [messages, scrollToBottom]);

  // Auto-scroll on typing indicator
  useEffect(() => {
    if (isTyping && isUserNearBottomRef.current) {
      scrollToBottom('smooth');
    }
  }, [isTyping, scrollToBottom]);

  // Loading failsafe timer
  useEffect(() => {
    const failsafe = setTimeout(() => {
      if (isLoading) {
        console.log('\u26A0\uFE0F Failsafe: Resetting stuck loading state');
        setIsLoading(false);
        setIsTyping(false);
      }
    }, 30000);
    return () => clearTimeout(failsafe);
  }, [isLoading]);

  // Load session messages
  const loadSession = useCallback(
    async (id: string) => {
      setIsLoading(true);
      setError(null);

      try {
        console.log('[useChatPanel] Loading session:', id);
        const data = await clerkApiRequest<{ history: any[] }>(`/chat/${id}`, 'get');
        const mappedMessages = mapHistory(data.history);
        setMessages(mappedMessages);

        const session = sessions.find((s) => s.session_id === id);
        if (session) {
          setCurrentSession(session);
          setHasUserEditedTitle(session.title !== 'New Chat');
        } else {
          setCurrentSession({ session_id: id, title: 'Chat Session' });
          setHasUserEditedTitle(true);
        }
      } catch (err: any) {
        console.error('[useChatPanel] Error loading session:', err);
        setError(isDev ? maintenanceMessage : 'Failed to load session messages');
        const session = sessions.find((s) => s.session_id === id);
        if (session) {
          setCurrentSession(session);
          setMessages([]);
        }
        showErrorToast('Load Error', 'Failed to load session messages.');
      } finally {
        setIsLoading(false);
      }
    },
    [clerkApiRequest, sessions, isDev, showErrorToast]
  );

  // Load session when sessionId changes
  // Track the last loaded sessionId to avoid redundant loads
  const lastLoadedSessionIdRef = useRef<string | null>(null);

  useEffect(() => {
    if (sessionId && userId) {
      // Check if session exists in the sessions list
      const exists = sessions.find((s) => s.session_id === sessionId);
      if (exists && lastLoadedSessionIdRef.current !== sessionId) {
        lastLoadedSessionIdRef.current = sessionId;
        loadSession(sessionId);
      }
      // If sessions haven't loaded yet (empty), we skip and let the
      // dependency on `sessions` retrigger this effect once they arrive
    } else if (!sessionId) {
      lastLoadedSessionIdRef.current = null;
      setMessages([]);
      setCurrentSession(null);
      setHasUserEditedTitle(false);
    }
  }, [sessionId, userId, sessions, loadSession]);

  // Rename session
  const renameSession = useCallback(
    async (sid: string, newTitle: string) => {
      try {
        await clerkApiRequest(`/session/${sid}`, 'put', { new_title: newTitle });
        onSessionsChanged();
        if (currentSession?.session_id === sid) {
          setCurrentSession((prev) => (prev ? { ...prev, title: newTitle } : null));
        }
        toast({
          title: 'Session renamed',
          description: 'Chat session title has been updated successfully.',
        });
      } catch (err: any) {
        showErrorToast('Error', 'Failed to rename session: ' + err.message);
      }
    },
    [clerkApiRequest, currentSession, onSessionsChanged, toast, showErrorToast]
  );

  // Send message
  const sendMessage = useCallback(
    async (message: string, searchMode?: boolean) => {
      setIsLoading(true);
      setIsTyping(true);
      setError(null);

      try {
        if (!userId) return;

        let sessionToUse = currentSession;
        if (!sessionToUse) {
          // Create a session if none exists
          const data = await clerkApiRequest<{ session_id: string }>(
            '/session/create',
            'post',
            null,
            { user_id: userId }
          );
          sessionToUse = { session_id: data.session_id, title: 'New Chat' };
          setCurrentSession(sessionToUse);
          onSessionsChanged();
        }

        // Optimistic user message
        setMessages((prev) => [
          ...prev,
          {
            message,
            reply: '',
            timestamp: new Date().toISOString(),
            role: 'user',
          },
        ]);
        scrollToBottom();

        // Send to backend
        const response = await clerkApiRequest<{
          reply: string;
          model?: string;
          route_rule?: string;
          latency_ms?: number;
          intents?: string[];
        }>('/chat', 'post', {
          user_id: userId,
          message,
          session_id: sessionToUse.session_id,
          search_mode: searchMode || false,
        });

        const isRateLimitReply =
          response.reply.includes('Rate Limit') ||
          response.reply.includes('rate limit') ||
          response.reply.includes('\u23F0') ||
          response.reply.includes('Quota') ||
          response.reply.includes('quota') ||
          response.reply.includes('Service Configuration') ||
          response.reply.includes('Server Error') ||
          response.reply.includes('Temporarily Down');

        const getMessageType = (
          msg: string
        ): 'normal' | 'rate_limit' | 'error' | 'warning' => {
          if (msg.includes('Rate Limit') || msg.includes('\u23F0')) return 'rate_limit';
          if (msg.includes('Quota') || msg.includes('\uD83D\uDCCA')) return 'rate_limit';
          if (msg.includes('Configuration') || msg.includes('\uD83D\uDD10')) return 'error';
          if (msg.includes('Server Error') || msg.includes('\uD83D\uDD27')) return 'warning';
          return 'normal';
        };

        // Add AI response
        setMessages((prev) => [
          ...prev,
          {
            message: response.reply,
            reply: '',
            timestamp: new Date().toISOString(),
            role: isRateLimitReply ? 'system' : 'assistant',
            messageType: isRateLimitReply ? getMessageType(response.reply) : 'normal',
            model: response.model,
            route_rule: response.route_rule,
            latency_ms: response.latency_ms,
            intents: response.intents,
          },
        ]);
        setIsTyping(false);
        scrollToBottom();

        // Refresh from backend to ensure sync
        const data = await clerkApiRequest<{ history: any[] }>(
          `/chat/${sessionToUse.session_id}`,
          'get'
        );
        const mappedMessages = mapHistory(data.history);
        setMessages(mappedMessages);

        // Auto-naming
        if (sessionToUse.title === 'New Chat' && !hasUserEditedTitle) {
          try {
            const firstUserMsg =
              mappedMessages.find((m) => m.role === 'user')?.message || message;
            const firstAssistantMsg =
              mappedMessages.find((m) => m.role === 'assistant')?.message || response.reply;

            if (firstUserMsg && firstAssistantMsg) {
              const base = firstUserMsg
                .replace(
                  /^(please|hey|hi|hello|can you|could you|explain|write|generate)\b/i,
                  ''
                )
                .trim();
              let candidate = base || firstAssistantMsg.split('\n')[0];
              candidate = candidate.replace(/[*#`>_~]/g, '').trim();
              candidate = candidate.replace(/\s{2,}/g, ' ');
              candidate = candidate.charAt(0).toUpperCase() + candidate.slice(1);
              if (candidate.length > 48)
                candidate = candidate.substring(0, 45).trimEnd() + '\u2026';
              if (candidate.length < 3) candidate = 'Chat Session';
              await renameSession(sessionToUse.session_id, candidate);
              setHasUserEditedTitle(true);
            }
          } catch (err) {
            console.log('Auto-naming failed:', err);
          }
        }
      } catch (err: any) {
        setIsTyping(false);
        setLastFailedMessage(message);
        showErrorToast('Error', err.message);
      } finally {
        setIsLoading(false);
      }
    },
    [
      userId,
      currentSession,
      hasUserEditedTitle,
      clerkApiRequest,
      onSessionsChanged,
      renameSession,
      scrollToBottom,
      showErrorToast,
    ]
  );

  // Generate title
  const generateTitle = useCallback(async () => {
    if (!currentSession || isGeneratingTitle) return;
    setIsGeneratingTitle(true);
    try {
      const userMessages = messages.filter((m) => m.role === 'user');
      const assistantMessages = messages.filter((m) => m.role === 'assistant');
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
      if (candidate.length > 48) candidate = candidate.substring(0, 45).trimEnd() + '\u2026';
      if (candidate.length < 3) candidate = 'Chat Session';
      await renameSession(currentSession.session_id, candidate);
      setHasUserEditedTitle(true);
    } catch (err: any) {
      toast({
        title: 'Title generation failed',
        description: err.message || 'Could not generate a title right now.',
        variant: 'destructive',
      });
    } finally {
      setIsGeneratingTitle(false);
    }
  }, [currentSession, isGeneratingTitle, messages, renameSession, toast]);

  // Retry last failed message
  const retryMessage = useCallback(async () => {
    if (lastFailedMessage) {
      const messageToRetry = lastFailedMessage;
      setLastFailedMessage(null);
      await sendMessage(messageToRetry);
    }
  }, [lastFailedMessage, sendMessage]);

  return {
    messages,
    currentSession,
    isLoading,
    isTyping,
    error,
    lastFailedMessage,
    isGeneratingTitle,
    hasUserEditedTitle,
    messagesEndRef,
    scrollContainerRef,
    messagesContainerRef,
    sendMessage,
    loadSession,
    renameSession,
    generateTitle,
    retryMessage,
    setError,
  };
}
