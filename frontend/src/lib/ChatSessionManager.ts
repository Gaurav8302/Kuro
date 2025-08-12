/*
  ChatSessionManager: manages up to 2 concurrent WebSocket sessions for real-time chat streaming.
  
  Features:
  - Concurrent sessions with independent message handling
  - Automatic cleanup and session limits
  - Message history persistence
  - Connection state management
  - Error handling and reconnection logic
*/

// lightweight uuidv4 generator to avoid extra dependency
function uuidv4() {
  // @ts-ignore
  return ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, (c: any) =>
    (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
  );
}

export type MessageHandler = (data: { 
  type: 'chunk' | 'done' | 'error' | 'connected' | 'disconnected'; 
  payload?: any;
  sessionId?: string;
}) => void;

export type SessionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

export interface SessionInfo {
  sessionId: string;
  chatId: string;
  status: SessionStatus;
  lastActivity: number;
  messageCount: number;
}

export class ChatSessionManager {
  private static instance: ChatSessionManager;
  private sockets = new Map<string, WebSocket>();
  private handlers = new Map<string, Set<MessageHandler>>();
  private history = new Map<string, any[]>();
  private sessionInfo = new Map<string, SessionInfo>();
  private maxSessions = 2;
  private reconnectAttempts = new Map<string, number>();
  private maxReconnectAttempts = 3;

  static getInstance() {
    if (!ChatSessionManager.instance) {
      ChatSessionManager.instance = new ChatSessionManager();
    }
    return ChatSessionManager.instance;
  }

  openSession(chatId: string, wsUrl: string): string {
    // Reuse existing session for a chat if present
    for (const [sid, sock] of this.sockets) {
      if ((sock as any).__chatId === chatId && sock.readyState === WebSocket.OPEN) {
        return sid;
      }
    }

    // Enforce max sessions: close the oldest if exceeding
    if (this.sockets.size >= this.maxSessions) {
      const oldest = this.sockets.keys().next().value as string | undefined;
      if (oldest) this.closeSession(oldest);
    }

    const sessionId = uuidv4();
    const ws = new WebSocket(wsUrl);
    (ws as any).__chatId = chatId;
    
    this.sockets.set(sessionId, ws);
    this.handlers.set(sessionId, new Set());
    this.history.set(sessionId, []);
    this.sessionInfo.set(sessionId, {
      sessionId,
      chatId,
      status: 'connecting',
      lastActivity: Date.now(),
      messageCount: 0
    });

    ws.onopen = () => {
      const info = this.sessionInfo.get(sessionId);
      if (info) {
        info.status = 'connected';
        info.lastActivity = Date.now();
        this.sessionInfo.set(sessionId, info);
      }
      this.handlers.get(sessionId)?.forEach((h) => h({ 
        type: 'connected', 
        sessionId,
        payload: { chatId } 
      }));
    };

    ws.onmessage = (ev) => {
      const msg = this.safeParse(ev.data);
      const type = msg?.type || 'chunk';
      const payload = msg?.payload ?? ev.data;
      
      // Update session info
      const info = this.sessionInfo.get(sessionId);
      if (info) {
        info.lastActivity = Date.now();
        info.messageCount++;
        this.sessionInfo.set(sessionId, info);
      }
      
      this.history.get(sessionId)?.push({ t: Date.now(), payload });
      this.handlers.get(sessionId)?.forEach((h) => h({ type, payload, sessionId }));
    };

    ws.onerror = (error) => {
      const info = this.sessionInfo.get(sessionId);
      if (info) {
        info.status = 'error';
        this.sessionInfo.set(sessionId, info);
      }
      this.handlers.get(sessionId)?.forEach((h) => h({ 
        type: 'error', 
        sessionId,
        payload: error 
      }));
      
      // Attempt reconnection if we haven't exceeded max attempts
      const attempts = this.reconnectAttempts.get(sessionId) || 0;
      if (attempts < this.maxReconnectAttempts) {
        this.reconnectAttempts.set(sessionId, attempts + 1);
        setTimeout(() => this.attemptReconnect(sessionId, chatId, wsUrl), 2000 * Math.pow(2, attempts));
      }
    };

    ws.onclose = () => {
      const info = this.sessionInfo.get(sessionId);
      if (info) {
        info.status = 'disconnected';
        this.sessionInfo.set(sessionId, info);
      }
      this.handlers.get(sessionId)?.forEach((h) => h({ 
        type: 'disconnected', 
        sessionId 
      }));
    };

    return sessionId;
  }

  private attemptReconnect(sessionId: string, chatId: string, wsUrl: string) {
    const ws = this.sockets.get(sessionId);
    if (!ws || ws.readyState === WebSocket.OPEN) return;
    
    this.closeSession(sessionId);
    this.openSession(chatId, wsUrl);
  }

  sendMessage(sessionId: string, message: string) {
    const ws = this.sockets.get(sessionId);
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send(JSON.stringify({ type: 'user_message', message }));
  }

  onMessage(sessionId: string, callback: MessageHandler) {
    let set = this.handlers.get(sessionId);
    if (!set) {
      set = new Set();
      this.handlers.set(sessionId, set);
    }
    set.add(callback);
    return () => set?.delete(callback);
  }

  closeSession(sessionId: string) {
    const ws = this.sockets.get(sessionId);
    try { 
      ws?.close(); 
    } catch {}
    
    this.sockets.delete(sessionId);
    this.handlers.delete(sessionId);
    this.history.delete(sessionId);
    this.sessionInfo.delete(sessionId);
    this.reconnectAttempts.delete(sessionId);
  }

  getHistory(sessionId: string) {
    return this.history.get(sessionId) || [];
  }

  getSessionInfo(sessionId: string): SessionInfo | undefined {
    return this.sessionInfo.get(sessionId);
  }

  getAllSessions(): SessionInfo[] {
    return Array.from(this.sessionInfo.values());
  }

  getSessionByChatId(chatId: string): SessionInfo | undefined {
    return Array.from(this.sessionInfo.values()).find(s => s.chatId === chatId);
  }

  private safeParse(data: any) {
    try {
      return typeof data === 'string' ? JSON.parse(data) : data;
    } catch { 
      return null; 
    }
  }
}
