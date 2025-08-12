export type DropTarget = 'full' | 'left' | 'right';

export type ChatPosition = DropTarget | 'floating';

export type FloatingRect = {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
};

export type OpenChat = {
  chatId: string;
  sessionId: string | null;
  position: ChatPosition;
  floating?: FloatingRect[]; // up to 2 floating windows per chat
};

export type ChatMessage = {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
};
