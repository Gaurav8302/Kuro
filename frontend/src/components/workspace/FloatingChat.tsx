import React from 'react';
import { Rnd } from 'react-rnd';
import ChatWindow from './ChatWindow';
import type { FloatingRect } from '@/types/workspace';

export type FloatingChatProps = {
  rect: FloatingRect;
  title: string;
  messages: { id: string; role: 'user' | 'assistant'; content: string }[];
  boundsRef: React.RefObject<HTMLDivElement>;
  onChange: (next: FloatingRect) => void;
};

export default function FloatingChat({ rect, title, messages, boundsRef, onChange }: FloatingChatProps) {
  return (
    <Rnd
      bounds={boundsRef.current || 'parent'}
      size={{ width: rect.width, height: rect.height }}
      position={{ x: rect.x, y: rect.y }}
      onDragStop={(_, d) => onChange({ ...rect, x: d.x, y: d.y })}
      onResizeStop={(_, __, ref, ___, pos) =>
        onChange({
          ...rect,
          width: ref.offsetWidth,
          height: ref.offsetHeight,
          x: pos.x,
          y: pos.y
        })
      }
      enableResizing={true}
      minWidth={260}
      minHeight={160}
      className="rounded-lg border bg-card shadow-lg overflow-hidden"
    >
      <ChatWindow title={title} messages={messages} />
    </Rnd>
  );
}
