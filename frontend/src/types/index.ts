// Type definitions for the AI Chatbot

export interface Message {
  message: string;
  reply: string;
  timestamp?: string;
  role?: 'user' | 'assistant';
}

export interface ChatSession {
  session_id: string;
  title?: string;
  created_at?: string;
  updated_at?: string;
}

export interface User {
  id: string;
  name: string;
  email: string;
  avatar?: string;
}

// API Response types for future backend integration
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface ChatResponse {
  message: string;
  sessionId: string;
  messageId: string;
}

export interface MemoryContext {
  context: string;
  relevanceScore: number;
  source: 'conversation' | 'long_term' | 'personal';
}