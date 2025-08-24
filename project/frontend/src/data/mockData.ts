// Mock data for development - replace with real API calls later
import { ChatSession, Message, User } from '@/types';

export const mockUser: User = {
  id: '1',
  name: 'Alex Chen',
  email: 'alex@example.com',
  avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=Alex'
};

export const mockMessages: Message[] = [
  {
    id: '1',
    content: "Hi! I'm your personal AI assistant. How can I help you today?",
    role: 'assistant',
    timestamp: new Date('2024-01-15T10:00:00')
  },
  {
    id: '2',
    content: "I'd like to brainstorm some creative project ideas for my portfolio.",
    role: 'user',
    timestamp: new Date('2024-01-15T10:01:00')
  },
  {
    id: '3',
    content: "That's exciting! I'd love to help you brainstorm. What type of creative field are you working in? Are you looking for digital art, writing, design, music, or something else?",
    role: 'assistant',
    timestamp: new Date('2024-01-15T10:01:30')
  }
];

export const mockSessions: ChatSession[] = [
  {
    id: '1',
    title: 'Creative Portfolio Brainstorming',
    messages: mockMessages,
    createdAt: new Date('2024-01-15T10:00:00'),
    updatedAt: new Date('2024-01-15T10:01:30'),
    summary: 'Discussed creative project ideas for portfolio development'
  },
  {
    id: '2',
    title: 'Marketing Strategy Discussion',
    messages: [],
    createdAt: new Date('2024-01-14T15:30:00'),
    updatedAt: new Date('2024-01-14T16:15:00'),
    summary: 'Explored various marketing approaches for small business'
  },
  {
    id: '3',
    title: 'Learning Plan for JavaScript',
    messages: [],
    createdAt: new Date('2024-01-13T09:00:00'),
    updatedAt: new Date('2024-01-13T10:30:00'),
    summary: 'Created structured learning path for advanced JavaScript concepts'
  },
  {
    id: '4',
    title: 'Recipe Ideas & Meal Planning',
    messages: [],
    createdAt: new Date('2024-01-12T18:00:00'),
    updatedAt: new Date('2024-01-12T18:45:00'),
    summary: 'Generated healthy meal ideas and weekly planning strategies'
  }
];

// Simulated API delay for realistic feel
export const simulateApiDelay = (ms: number = 1000) => 
  new Promise(resolve => setTimeout(resolve, ms));

// Mock API functions with TODO comments for backend integration
export const mockApiCalls = {
  // TODO: Replace with fetch('/api/chat', { method: 'POST', body: JSON.stringify({ message, sessionId }) })
  // Hooks into backend route: POST /chat
  sendMessage: async (message: string, sessionId: string): Promise<string> => {
    await simulateApiDelay(1500);
    const responses = [
      "That's a great question! Let me think about that...",
      "I understand what you're looking for. Here's my perspective...",
      "Interesting point! Here's how I see it...",
      "Let me help you with that. Based on what you've told me...",
      "That's a creative approach! I'd suggest considering..."
    ];
    return responses[Math.floor(Math.random() * responses.length)];
  },

  // TODO: Replace with fetch(`/api/sessions/${userId}`)
  // Hooks into backend route: GET /sessions/:user_id
  getUserSessions: async (userId: string): Promise<ChatSession[]> => {
    await simulateApiDelay(500);
    return mockSessions;
  },

  // TODO: Replace with fetch(`/api/sessions/${sessionId}`)
  // Hooks into backend route: GET /chat/:session_id
  getSession: async (sessionId: string): Promise<ChatSession | null> => {
    await simulateApiDelay(300);
    return mockSessions.find(s => s.id === sessionId) || null;
  },

  // TODO: Replace with fetch(`/api/sessions`, { method: 'POST', body: JSON.stringify({ title, userId }) })
  // Hooks into backend route: POST /session/create
  createSession: async (title: string, userId: string): Promise<ChatSession> => {
    await simulateApiDelay(400);
    const newSession: ChatSession = {
      id: Math.random().toString(36).substr(2, 9),
      title: title || 'New Chat',
      messages: [],
      createdAt: new Date(),
      updatedAt: new Date()
    };
    return newSession;
  },

  // TODO: Replace with fetch(`/api/sessions/${sessionId}`, { method: 'PUT', body: JSON.stringify({ title }) })
  // Hooks into backend route: PUT /session/:session_id (rename)
  renameSession: async (sessionId: string, newTitle: string): Promise<boolean> => {
    await simulateApiDelay(300);
    return true;
  },

  // TODO: Replace with fetch(`/api/sessions/${sessionId}`, { method: 'DELETE' })
  // Hooks into backend route: DELETE /session/:session_id
  deleteSession: async (sessionId: string): Promise<boolean> => {
    await simulateApiDelay(300);
    return true;
  },

  // TODO: Replace with fetch(`/api/sessions/${sessionId}/summarize`, { method: 'POST' })
  // Hooks into backend route: POST /session/summarize/:session_id
  summarizeSession: async (sessionId: string): Promise<string> => {
    await simulateApiDelay(800);
    return "This conversation covered creative brainstorming and project planning strategies.";
  },

  // TODO: Replace with fetch('/api/memory/store', { method: 'POST', body: JSON.stringify({ context, sessionId }) })
  // Hooks into backend route: POST /store-memory
  storeMemory: async (context: string, sessionId: string): Promise<boolean> => {
    await simulateApiDelay(200);
    return true;
  },

  // TODO: Replace with fetch('/api/memory/retrieve', { method: 'POST', body: JSON.stringify({ query }) })
  // Hooks into backend route: POST /retrieve-memory
  retrieveMemory: async (query: string): Promise<string[]> => {
    await simulateApiDelay(400);
    return ["Previous context about user's interests in creative projects", "User prefers detailed explanations"];
  }
};