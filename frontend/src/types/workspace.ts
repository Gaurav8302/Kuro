export type DropTarget = 'full' | 'left' | 'right' | 'floating';

export type ChatPosition = DropTarget;

export type FloatingRect = {
  x: number;
  y: number;
  width: number;
  height: number;
};

export type ChatMessage = {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
};

export type OpenChat = {
  id: string;
  title: string;
  position: ChatPosition;
  rect?: FloatingRect; // for floating windows
  messages: ChatMessage[];
  isLoading?: boolean;
  sessionId?: string | null;
};

export type ChatItem = {
  id: string;
  title: string;
  lastMessage: string;
  timestamp: string;
};
