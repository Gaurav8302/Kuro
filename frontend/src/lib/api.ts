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
      throw new Error(error.response.data.detail || error.response.data.message || 'Server error');
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
