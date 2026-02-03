import { memo } from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { Link } from 'react-router-dom';
import { 
  Plus, 
  MessageSquare, 
  LogOut, 
  Trash2, 
  Edit2, 
  Check, 
  X,
  ChevronLeft,
  Settings
} from 'lucide-react';
import { Avatar, AvatarImage, AvatarFallback } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import { useState } from 'react';
import { sidebarVariants } from '@/utils/animations';

interface ChatSession {
  session_id: string;
  title: string;
}

interface User {
  id: string;
  name: string;
  email: string;
  avatar?: string;
}

interface KuroSidebarProps {
  sessions: ChatSession[];
  currentSessionId?: string;
  user?: User;
  onNewChat: () => void;
  onSelectSession: (id: string) => void;
  onRenameSession: (id: string, title: string) => void;
  onDeleteSession: (id: string) => void;
  onSignOut: () => void;
  onClose?: () => void;
  isOpen?: boolean;
  className?: string;
}

/**
 * KuroSidebar - Professional chat sidebar
 * Clean, modern design with glass effect
 */
export const KuroSidebar = memo(function KuroSidebar({
  sessions,
  currentSessionId,
  user,
  onNewChat,
  onSelectSession,
  onRenameSession,
  onDeleteSession,
  onSignOut,
  onClose,
  isOpen = true,
  className,
}: KuroSidebarProps) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const handleStartEdit = (session: ChatSession) => {
    setEditingId(session.session_id);
    setEditTitle(session.title);
  };

  const handleSaveEdit = (id: string) => {
    if (editTitle.trim()) {
      onRenameSession(id, editTitle.trim());
    }
    setEditingId(null);
    setEditTitle('');
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setEditTitle('');
  };

  const handleConfirmDelete = (id: string) => {
    onDeleteSession(id);
    setDeletingId(null);
  };

  return (
    <motion.aside
      className={cn(
        'flex flex-col h-full w-72',
        'glass border-r border-border/50',
        className
      )}
      variants={sidebarVariants}
      initial="closed"
      animate={isOpen ? 'open' : 'closed'}
    >
      {/* Sidebar Header */}
      <div className="h-16 px-4 flex items-center justify-between border-b border-border/50">
        <Link to="/" className="flex items-center gap-2 group">
          <div className="w-8 h-8 rounded-lg overflow-hidden shadow-lg shadow-primary/20">
            <img src="/kuroai.png" alt="Kuro" className="w-full h-full object-cover" />
          </div>
          <span className="font-semibold text-foreground group-hover:text-primary transition-colors">
            Kuro
          </span>
        </Link>
        {onClose && (
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            className="h-8 w-8"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
        )}
      </div>

      {/* New Chat Button */}
      <div className="p-3">
        <Button 
          variant="outline" 
          className="w-full justify-start gap-2 border-primary/30 hover:border-primary/50 hover:bg-primary/10"
          onClick={onNewChat}
        >
          <Plus className="h-4 w-4 text-primary" />
          New chat
        </Button>
      </div>

      {/* Chat List */}
      <div className="flex-1 overflow-y-auto px-3 py-2">
        {sessions.length > 0 && (
          <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-3 px-2">
            Recent
          </div>
        )}
        <div className="space-y-1">
          {sessions.map((session) => {
            const isActive = session.session_id === currentSessionId;
            const isEditing = editingId === session.session_id;
            const isDeleting = deletingId === session.session_id;

            return (
              <motion.div
                key={session.session_id}
                className={cn(
                  'group relative rounded-xl transition-all',
                  isActive 
                    ? 'bg-primary/5 border border-primary/20' 
                    : 'hover:bg-primary/5 border border-transparent hover:border-primary/20'
                )}
                whileHover={{ x: 4 }}
                transition={{ duration: 0.15 }}
              >
                {isEditing ? (
                  // Edit mode
                  <div className="flex items-center gap-2 p-3">
                    <input
                      type="text"
                      value={editTitle}
                      onChange={(e) => setEditTitle(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleSaveEdit(session.session_id);
                        if (e.key === 'Escape') handleCancelEdit();
                      }}
                      className={cn(
                        'flex-1 px-2 py-1 text-sm rounded-lg',
                        'bg-secondary border border-border',
                        'text-foreground placeholder:text-muted-foreground',
                        'focus:outline-none focus:border-primary/50'
                      )}
                      autoFocus
                    />
                    <button
                      onClick={() => handleSaveEdit(session.session_id)}
                      className="p-1 text-green-400 hover:text-green-300"
                    >
                      <Check className="w-4 h-4" />
                    </button>
                    <button
                      onClick={handleCancelEdit}
                      className="p-1 text-muted-foreground hover:text-foreground"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ) : isDeleting ? (
                  // Delete confirmation
                  <div className="flex items-center justify-between p-3">
                    <span className="text-sm text-destructive">Delete?</span>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => handleConfirmDelete(session.session_id)}
                        className="px-2 py-1 text-xs bg-destructive/20 text-destructive rounded hover:bg-destructive/30"
                      >
                        Yes
                      </button>
                      <button
                        onClick={() => setDeletingId(null)}
                        className="px-2 py-1 text-xs bg-secondary text-muted-foreground rounded hover:bg-secondary/80"
                      >
                        No
                      </button>
                    </div>
                  </div>
                ) : (
                  // Normal mode
                  <button
                    onClick={() => onSelectSession(session.session_id)}
                    className="w-full text-left p-3"
                  >
                    <div className="flex items-start gap-3">
                      <div className="p-1.5 rounded-lg bg-secondary">
                        <MessageSquare className={cn(
                          'h-3.5 w-3.5',
                          isActive ? 'text-primary' : 'text-muted-foreground'
                        )} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className={cn(
                          'text-sm font-medium truncate',
                          isActive ? 'text-foreground' : 'text-foreground'
                        )}>
                          {session.title}
                        </div>
                      </div>
                      {/* Action buttons */}
                      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleStartEdit(session);
                          }}
                          className="p-1 text-muted-foreground hover:text-foreground"
                        >
                          <Edit2 className="w-3 h-3" />
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setDeletingId(session.session_id);
                          }}
                          className="p-1 text-muted-foreground hover:text-destructive"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>
                    </div>
                  </button>
                )}
              </motion.div>
            );
          })}
        </div>

        {sessions.length === 0 && (
          <div className="text-center py-8">
            <MessageSquare className="w-8 h-8 mx-auto mb-2 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">No conversations yet</p>
          </div>
        )}
      </div>

      {/* Sidebar Footer */}
      <div className="p-3 border-t border-border/50">
        {user && (
          <div className="flex items-center gap-3 p-2 rounded-xl hover:bg-primary/5 transition-colors">
            <Avatar className="w-8 h-8 border border-border">
              <AvatarImage src={user.avatar} alt={user.name} />
              <AvatarFallback className="bg-primary/10 text-primary text-xs font-semibold">
                {user.name.charAt(0).toUpperCase()}
              </AvatarFallback>
            </Avatar>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-foreground truncate">
                {user.name}
              </p>
              <p className="text-xs text-muted-foreground truncate">
                {user.email}
              </p>
            </div>
            <button
              onClick={onSignOut}
              className="p-2 text-muted-foreground hover:text-foreground hover:bg-secondary rounded-lg transition-colors"
              title="Sign out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </motion.aside>
  );
});

export default KuroSidebar;
