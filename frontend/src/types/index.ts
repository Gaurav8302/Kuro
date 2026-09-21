// Type definitions for the AI Chatbot

export interface Message {
  /**
   * Stable identity for React keys. Local messages get a client id at
   * creation; loaded history gets a deterministic id. Never derived from
   * timestamps, which differ between client and server for the same turn.
   */
  id?: string;
  /** True while Kuro is generating this (assistant) message. */
  pending?: boolean;
  message: string;
  reply: string;
  timestamp?: string;
  role?: 'user' | 'assistant' | 'system';
  messageType?: 'normal' | 'rate_limit' | 'error' | 'warning';
  model?: string;
  route_rule?: string;
  latency_ms?: number;
  intents?: string[];
  suggest_search?: boolean;
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

// Split-view layout types
export type PanelPosition = 'left' | 'right' | 'top' | 'bottom';
export type LayoutMode = 'single' | 'split';
export type DropZone = 'left' | 'right' | 'center' | 'top' | 'bottom';

export interface PanelState {
  sessionId: string;
  position: PanelPosition;
}

export interface SplitViewState {
  mode: LayoutMode;
  panels: PanelState[];
  panelSizes?: number[];
}