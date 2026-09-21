// src/lib/api.ts
import { useAuth } from '@clerk/clerk-react';
import axios from 'axios';

// Use environment-specific API base URL
// Prefer VITE_API_URL; fallback to VITE_API_BASE_URL; default to local dev
const API_BASE =
  import.meta.env.VITE_API_URL ||
  import.meta.env.VITE_API_BASE_URL ||
  'http://localhost:8000';

console.log('🔗 API Base URL:', API_BASE, '| Environment:', import.meta.env.VITE_ENVIRONMENT || 'development');

export async function apiRequest<T>(endpoint: string, method: 'get' | 'post' | 'put' | 'delete', data?: any, params?: any, token?: string): Promise<T> {
  try {
    const response = await axios({
      url: `${API_BASE}${endpoint}`,
      method,
      data,
      params,
      withCredentials: true,
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    return response.data;
  } catch (error: any) {
    if (error.response) {
      const data = error.response.data;
      const detail = data?.detail;
      if (typeof detail === 'string') {
        throw new Error(detail);
      }
      if (detail && typeof detail === 'object') {
        throw new Error(detail.message || detail.error || 'Server error');
      }
      if (typeof data?.message === 'string') {
        throw new Error(data.message);
      }
      if (typeof data?.error === 'string') {
        throw new Error(data.error);
      }
      throw new Error('Server error');
    }
    throw new Error('Network error');
  }
}

// Custom hook to get Clerk JWT
export function useClerkApi() {
  const { getToken } = useAuth();
  return async function clerkApiRequest<T>(endpoint: string, method: 'get' | 'post' | 'put' | 'delete', data?: any, params?: any): Promise<T> {
    const token = await getToken();
    return apiRequest<T>(endpoint, method, data, params, token);
  };
}

export default apiRequest;

// Name management functions
export async function setUserName(userId: string, name: string): Promise<{ status: string; message: string }> {
  return apiRequest(`/user/${userId}/set-name`, 'post', { name });
}

export async function getUserName(userId: string): Promise<{ user_id: string; name: string | null }> {
  return apiRequest(`/user/${userId}/name`, 'get');
}

export async function checkUserHasName(userId: string): Promise<{ user_id: string; has_name: boolean }> {
  return apiRequest(`/user/${userId}/has-name`, 'get');
}

// Intro animation persistence
export async function getIntroShown(userId: string): Promise<{ user_id: string; intro_shown: boolean }> {
  return apiRequest(`/user/${userId}/intro-shown`, 'get');
}

export async function setIntroShown(userId: string): Promise<{ status: string; user_id: string; intro_shown: boolean }> {
  return apiRequest(`/user/${userId}/intro-shown`, 'post', { shown: true });
}

// Memory (existing endpoints) — used by onboarding and the Memory view
export interface StoredMemory {
  text: string;
  score: number;
  importance: number;
  category: string;
  timestamp: string;
}

export async function storeMemory(
  userId: string,
  text: string,
  metadata: Record<string, unknown> = {},
  token?: string
): Promise<{ status: string; memory_id: string }> {
  return apiRequest('/store-memory', 'post', { user_id: userId, text, metadata }, undefined, token);
}

export async function retrieveMemory(
  userId: string,
  query: string,
  topK = 12,
  token?: string
): Promise<{ query: string; results: StoredMemory[] }> {
  return apiRequest('/retrieve-memory', 'post', { user_id: userId, query, top_k: topK }, undefined, token);
}

// Inline Ask - ephemeral side-question with read-only session context
export async function inlineQuery(
  selectedText: string,
  context: string,
  question: string,
  options?: {
    parentMessage?: string;
    sessionId?: string;
    userId?: string;
    messageIndex?: number;
  }
): Promise<{ answer: string }> {
  return apiRequest('/inline-query', 'post', {
    selected_text: selectedText,
    context,
    question,
    parent_message: options?.parentMessage || '',
    session_id: options?.sessionId || null,
    user_id: options?.userId || null,
    message_index: options?.messageIndex ?? null,
  });
}
