import React from 'react';
import { X, RefreshCw } from 'lucide-react';
import { cn } from '@/lib/utils';

interface MemoryDebugSidebarProps {
  open: boolean;
  query: string;
  data: Record<string, unknown> | null;
  loading: boolean;
  error?: string | null;
  onClose: () => void;
  onRefresh: () => void;
}

export const MemoryDebugSidebar: React.FC<MemoryDebugSidebarProps> = ({
  open,
  query,
  data,
  loading,
  error,
  onClose,
  onRefresh,
}) => {
  if (!open) return null;

  return (
    <aside
      className={cn(
        'hidden md:flex flex-col h-screen w-80 border-l border-border/50 bg-background/95 backdrop-blur-xl',
        'relative z-20'
      )}
    >
      <div className="flex items-center justify-between px-4 h-12 border-b border-border/50">
        <div className="text-sm font-medium text-foreground">Memory Debug</div>
        <div className="flex items-center gap-2">
          <button
            onClick={onRefresh}
            className="h-8 w-8 rounded-md hover:bg-secondary flex items-center justify-center"
            title="Refresh"
          >
            <RefreshCw className="h-4 w-4 text-muted-foreground" />
          </button>
          <button
            onClick={onClose}
            className="h-8 w-8 rounded-md hover:bg-secondary flex items-center justify-center"
            title="Close"
          >
            <X className="h-4 w-4 text-muted-foreground" />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3 text-xs text-muted-foreground">
        <div>
          <div className="text-[11px] uppercase tracking-wide text-muted-foreground/70">Query</div>
          <div className="mt-1 text-foreground break-words">{query || '—'}</div>
        </div>

        {loading && (
          <div className="text-sm text-muted-foreground">Loading debug data...</div>
        )}

        {error && !loading && (
          <div className="text-sm text-red-400">{error}</div>
        )}

        {!loading && !error && (
          <pre className="whitespace-pre-wrap break-words text-[11px] leading-relaxed text-foreground/90">
{JSON.stringify(data || {}, null, 2)}
          </pre>
        )}
      </div>
    </aside>
  );
};

export default MemoryDebugSidebar;
