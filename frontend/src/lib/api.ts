// src/lib/api.ts
import { useAuth } from '@clerk/clerk-react';
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

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
