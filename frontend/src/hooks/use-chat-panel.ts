import { useState, useEffect, useRef, useCallback } from 'react';
import { Message, ChatSession } from '@/types';
import { useToast } from '@/hooks/use-toast';

/**
 * Type for the Clerk API request function returned by useClerkApi().
 */
export type ClerkApiRequestFn = <T>(
  endpoint: string,
  method: 'get' | 'post' | 'put' | 'delete',
  data?: unknown,
  params?: Record<string, unknown>
) => Promise<T>;

export type ChatSkill = 'auto' | 'code' | 'explain' | 'creative' | 'problem';

interface UseChatPanelOptions {
  sessionId: string | null;
  sessions: ChatSession[];
  userId: string | undefined;
  clerkApiRequest: ClerkApiRequestFn;
  onSessionsChanged: () => void;
  /** Kuro is generating (drives the Core's `thinking` state). */
  onThinking?: (thinking: boolean) => void;
  /** A reply arrived (drives the Core's one-shot `responding` state). */
  onResponded?: () => void;
}

interface UseChatPanelReturn {
  messages: Message[];
  currentSession: ChatSession | null;
  isLoading: boolean;
  isTyping: boolean;
  error: string | null;
  lastFailedMessage: string | null;
  isGeneratingTitle: boolean;
  hasUserEditedTitle: boolean;

  messagesEndRef: React.RefObject<HTMLDivElement>;
  scrollContainerRef: React.RefObject<HTMLDivElement>;
  messagesContainerRef: React.RefObject<HTMLDivElement>;

  sendMessage: (message: string, searchMode?: boolean, skill?: ChatSkill) => Promise<void>;
  loadSession: (id: string) => Promise<void>;
  renameSession: (sessionId: string, newTitle: string) => Promise<void>;
  generateTitle: () => Promise<void>;
  retryMessage: () => Promise<void>;
  setError: (error: string | null) => void;
}

function newId(prefix = 'm'): string {
  const c = typeof crypto !== 'undefined' && 'randomUUID' in crypto ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`;
  return `${prefix}-${c}`;
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
 * Map raw backend history to Message[] with deterministic ids.
 * The API has no message ids, so ids are derived from session + turn index +
 * role — stable across reloads of the same session.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapHistory(sessionId: string, history: any[]): Message[] {
  const mapped: Message[] = [];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  history.forEach((item: any, turn: number) => {
    if (item.user) {
      mapped.push({
        id: `h-${sessionId}-${turn}-u`,
        message: item.user,
        reply: '',
        timestamp: item.timestamp,
        role: 'user',
      });
    }
    if (item.assistant) {
      const systemInfo = detectSystemMessage(item.assistant);
      mapped.push({
        id: `h-${sessionId}-${turn}-a`,
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
 * useChatPanel — per-session chat state.
 *
 * Flicker fix (see KURO_FLICKER_DIAGNOSIS.md):
 *   • Messages have stable ids; keys never change for the same turn.
 *   • The reply is written INTO a pending assistant row that already exists,
 *     so completion updates one node in place — no unmount, no remount.
 *   • There is NO post-send history refetch/replace. /chat already persisted.
 *   • One scroll path: an effect on `messages`, using instant scroll when the
 *     person is already near the bottom.
 */
export function useChatPanel({
  sessionId,
  sessions,
  userId,
  clerkApiRequest,
  onSessionsChanged,
  onThinking,
  onResponded,
}: UseChatPanelOptions): UseChatPanelReturn {
  const { toast } = useToast();

  const [messages, setMessages] = useState<Message[]>([]);
  const [currentSession, setCurrentSession] = useState<ChatSession | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastFailedMessage, setLastFailedMessage] = useState<string | null>(null);
  const [hasUserEditedTitle, setHasUserEditedTitle] = useState(false);
  const [isGeneratingTitle, setIsGeneratingTitle] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const isUserNearBottomRef = useRef(true);

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

  // Report thinking state outward (Core).
  useEffect(() => {
    onThinking?.(isTyping);
  }, [isTyping, onThinking]);

  // --- Scroll: a single path ---
  const handleScroll = useCallback(() => {
    const el = scrollContainerRef.current;
    if (!el) return;
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    isUserNearBottomRef.current = distanceFromBottom < 160;
  }, []);

  useEffect(() => {
    const el = scrollContainerRef.current;
    if (!el) return;
    el.addEventListener('scroll', handleScroll, { passive: true });
    return () => el.removeEventListener('scroll', handleScroll);
  }, [handleScroll]);

  useEffect(() => {
    const el = scrollContainerRef.current;
    if (!el) return;
    if (!isUserNearBottomRef.current && messages.length > 2) return;
    // Instant, geometry-stable scroll. Smooth scrolling competing with layout
    // was one of the visible "jumps" in the old implementation.
    el.scrollTop = el.scrollHeight;
  }, [messages]);

  // Loading failsafe timer
  useEffect(() => {
    if (!isLoading) return;
    const failsafe = setTimeout(() => {
      console.warn('[useChatPanel] failsafe: resetting stuck loading state');
      setIsLoading(false);
      setIsTyping(false);
      setMessages((prev) => prev.filter((m) => !m.pending));
    }, 45000);
    return () => clearTimeout(failsafe);
  }, [isLoading]);

  // --- Load session ---
  const loadSession = useCallback(
    async (id: string) => {
      setIsLoading(true);
      setError(null);
      setMessages([]);
      try {
        const data = await clerkApiRequest<{ history: any[] }>(`/chat/${id}`, 'get');
        setMessages(mapHistory(id, data.history));
        const session = sessions.find((s) => s.session_id === id);
        if (session) {
          setCurrentSession(session);
          setHasUserEditedTitle(session.title !== 'New Chat');
        } else {
          setCurrentSession({ session_id: id, title: 'Chat Session' });
          setHasUserEditedTitle(true);
        }
      } catch (err: unknown) {
        console.error('[useChatPanel] Error loading session:', err);
        const errorMessage = err instanceof Error ? err.message : 'Unknown error';
        setError(isDev ? maintenanceMessage : 'Failed to load session messages: ' + errorMessage);
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

  const sessionsRef = useRef(sessions);
  sessionsRef.current = sessions;

  useEffect(() => {
    if (sessionId && userId) {
      if (sessionsRef.current.length === 0) return;
      const exists = sessionsRef.current.find((s) => s.session_id === sessionId);
      if (exists && currentSession?.session_id !== sessionId) {
        loadSession(sessionId);
      }
    } else if (!sessionId) {
      setMessages([]);
      setCurrentSession(null);
      setHasUserEditedTitle(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId, userId]);

  const hasLoadedInitialRef = useRef(false);
  useEffect(() => {
    if (hasLoadedInitialRef.current) return;
    if (sessionId && userId && sessions.length > 0 && !currentSession) {
      const exists = sessions.find((s) => s.session_id === sessionId);
      if (exists) {
        hasLoadedInitialRef.current = true;
        loadSession(sessionId);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessions.length]);

  // --- Rename ---
  const renameSession = useCallback(
    async (sid: string, newTitle: string, quiet = false) => {
      try {
        await clerkApiRequest(`/session/${sid}`, 'put', { new_title: newTitle });
        onSessionsChanged();
        if (currentSession?.session_id === sid) {
          setCurrentSession((prev) => (prev ? { ...prev, title: newTitle } : null));
        }
        if (!quiet) {
          toast({ title: 'Renamed', description: 'The conversation title was updated.' });
        }
      } catch (err: unknown) {
        const errorMessage = err instanceof Error ? err.message : 'Unknown error';
        showErrorToast('Error', 'Failed to rename session: ' + errorMessage);
      }
    },
    [clerkApiRequest, currentSession, onSessionsChanged, toast, showErrorToast]
  );

  // --- Send ---
  const sendMessage = useCallback(
    async (message: string, searchMode?: boolean, skill: ChatSkill = 'auto') => {
      if (!userId) return;
      setIsLoading(true);
      setIsTyping(true);
      setError(null);

      const userMsgId = newId('u');
      const assistantMsgId = newId('a');

      try {
        let sessionToUse = currentSession;
        if (!sessionToUse) {
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

        // The user's message and a pending row for Kuro's reply are added
        // together. The reply will fill the pending row in place.
        const now = new Date().toISOString();
        setMessages((prev) => [
          ...prev,
          { id: userMsgId, message, reply: '', timestamp: now, role: 'user' },
          { id: assistantMsgId, message: '', reply: '', timestamp: now, role: 'assistant', pending: true },
        ]);

        const response = await clerkApiRequest<{
          reply: string;
          model?: string;
          route_rule?: string;
          latency_ms?: number;
          intents?: string[];
          suggest_search?: boolean;
        }>('/chat', 'post', {
          user_id: userId,
          message,
          session_id: sessionToUse.session_id,
          search_mode: searchMode || false,
          skill,
        });

        const systemInfo = detectSystemMessage(response.reply);

        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId
              ? {
                  ...m,
                  pending: false,
                  message: response.reply,
                  timestamp: new Date().toISOString(),
                  role: systemInfo.isSystem ? 'system' : 'assistant',
                  messageType: systemInfo.messageType,
                  model: response.model,
                  route_rule: response.route_rule,
                  latency_ms: response.latency_ms,
                  intents: response.intents,
                  suggest_search: response.suggest_search || false,
                }
              : m
          )
        );
        setIsTyping(false);
        onResponded?.();

        // Auto-title on the first exchange (quiet — no toast).
        if (sessionToUse.title === 'New Chat' && !hasUserEditedTitle) {
          try {
            const base = message
              .replace(/^(please|hey|hi|hello|can you|could you|explain|write|generate)\b/i, '')
              .trim();
            let candidate = base || response.reply.split('\n')[0];
            candidate = candidate.replace(/[*#`>_~]/g, '').trim().replace(/\s{2,}/g, ' ');
            candidate = candidate.charAt(0).toUpperCase() + candidate.slice(1);
            if (candidate.length > 48) candidate = candidate.substring(0, 45).trimEnd() + '\u2026';
            if (candidate.length < 3) candidate = 'Conversation';
            await renameSession(sessionToUse.session_id, candidate, true);
            setHasUserEditedTitle(true);
          } catch (err) {
            console.log('Auto-naming failed:', err);
          }
        }
      } catch (err: unknown) {
        setIsTyping(false);
        setLastFailedMessage(message);
        // Remove the pending row; the person's message stays so they can retry.
        setMessages((prev) => prev.filter((m) => m.id !== assistantMsgId));
        const errorMessage = err instanceof Error ? err.message : 'Unknown error';
        showErrorToast('Error', errorMessage);
      } finally {
        setIsLoading(false);
      }
    },
    [userId, currentSession, hasUserEditedTitle, clerkApiRequest, onSessionsChanged, renameSession, showErrorToast, onResponded]
  );

  // --- Generate title ---
  const generateTitle = useCallback(async () => {
    if (!currentSession || isGeneratingTitle) return;
    setIsGeneratingTitle(true);
    try {
      const userMessages = messages.filter((m) => m.role === 'user');
      const assistantMessages = messages.filter((m) => m.role === 'assistant' && !m.pending);
      const lastUser = userMessages[userMessages.length - 1]?.message || '';
      const firstUser = userMessages[0]?.message || '';
      const firstAssistant = assistantMessages[0]?.message || '';
      let base = lastUser || firstUser || firstAssistant || 'Conversation';
      base = base.replace(/^(please|hey|hi|hello|can you|could you|explain|write|generate)\b/i, '').trim();
      let candidate = base.split('\n')[0].replace(/[*#`>_~]/g, '').trim().replace(/\s{2,}/g, ' ');
      if (candidate) candidate = candidate.charAt(0).toUpperCase() + candidate.slice(1);
      if (candidate.length > 48) candidate = candidate.substring(0, 45).trimEnd() + '\u2026';
      if (candidate.length < 3) candidate = 'Conversation';
      await renameSession(currentSession.session_id, candidate);
      setHasUserEditedTitle(true);
    } catch (err: unknown) {
      toast({
        title: 'Title generation failed',
        description: err instanceof Error ? err.message : 'Could not generate a title right now.',
        variant: 'destructive',
      });
    } finally {
      setIsGeneratingTitle(false);
    }
  }, [currentSession, isGeneratingTitle, messages, renameSession, toast]);

  const retryMessage = useCallback(async () => {
    if (lastFailedMessage) {
      const messageToRetry = lastFailedMessage;
      setLastFailedMessage(null);
      // Drop the unanswered user row before re-sending so it isn't duplicated.
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        return last?.role === 'user' && last.message === messageToRetry ? prev.slice(0, -1) : prev;
      });
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
    renameSession: (sid: string, title: string) => renameSession(sid, title),
    generateTitle,
    retryMessage,
    setError,
  };
}
