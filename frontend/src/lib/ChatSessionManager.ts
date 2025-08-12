/*
  ChatSessionManager: manages up to 2 concurrent WebSocket sessions.
*/

// lightweight uuidv4 generator to avoid extra dependency
function uuidv4() {
  // @ts-ignore
  return ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, (c: any) =>
    (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
  );
}

export type MessageHandler = (data: { type: 'chunk' | 'done' | 'error'; payload?: any }) => void;

export class ChatSessionManager {
  private static instance: ChatSessionManager;
  private sockets = new Map<string, WebSocket>();
  private handlers = new Map<string, Set<MessageHandler>>();
  private history = new Map<string, any[]>();
  private maxSessions = 2;

  static getInstance() {
    if (!ChatSessionManager.instance) ChatSessionManager.instance = new ChatSessionManager();
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

    ws.onmessage = (ev) => {
      const msg = this.safeParse(ev.data);
      const type = msg?.type || 'chunk';
      const payload = msg?.payload ?? ev.data;
      this.history.get(sessionId)?.push({ t: Date.now(), payload });
      this.handlers.get(sessionId)?.forEach((h) => h({ type, payload }));
    };

    ws.onerror = () => {
      this.handlers.get(sessionId)?.forEach((h) => h({ type: 'error' }));
    };

    ws.onclose = () => {
      this.handlers.get(sessionId)?.forEach((h) => h({ type: 'done' }));
    };

    return sessionId;
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
    try { ws?.close(); } catch {}
    this.sockets.delete(sessionId);
    this.handlers.delete(sessionId);
    this.history.delete(sessionId);
  }

  getHistory(sessionId: string) {
    return this.history.get(sessionId) || [];
  }

  private safeParse(data: any) {
    try {
      return typeof data === 'string' ? JSON.parse(data) : data;
    } catch { return null; }
  }
}
