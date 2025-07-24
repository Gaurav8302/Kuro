import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Plus, 
  MessageSquare, 
  MoreHorizontal, 
  Trash2, 
  Edit3, 
  LogOut,
  Menu,
  X,
  Sparkles,
  Brain,
  Heart
} from 'lucide-react';
import { ChatSession, User } from '@/types';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarImage, AvatarFallback } from '@/components/ui/avatar';
import { 
  DropdownMenu, 
  DropdownMenuContent, 
  DropdownMenuItem, 
  DropdownMenuTrigger 
} from '@/components/ui/dropdown-menu';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';
import { useIsMobile } from '@/hooks/use-mobile';

interface SidebarProps {
  sessions: ChatSession[];
  currentSessionId?: string;
  user?: User;
  onNewChat: () => void;
  onSelectSession: (sessionId: string) => void;
  onRenameSession: (sessionId: string, newTitle: string) => void;
  onDeleteSession: (sessionId: string) => void;
  onSignOut: () => void;
  onClose?: () => void; // New prop for closing sidebar
  className?: string;
}

export const Sidebar = ({
  sessions,
  currentSessionId,
  user,
  onNewChat,
  onSelectSession,
  onRenameSession,
  onDeleteSession,
  onSignOut,
  onClose,
  className
}: SidebarProps) => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const isMobile = useIsMobile();

  const handleRename = (sessionId: string, currentTitle: string) => {
    setEditingSessionId(sessionId);
    setEditTitle(currentTitle);
  };

  const handleSaveRename = () => {
    if (editingSessionId && editTitle.trim()) {
      onRenameSession(editingSessionId, editTitle.trim());
    }
    setEditingSessionId(null);
    setEditTitle('');
  };

  const handleCancelRename = () => {
    setEditingSessionId(null);
    setEditTitle('');
  };

  const handleCloseClick = () => {
    if (isMobile && onClose) {
      // On mobile, close the entire sidebar
      onClose();
    } else {
      // On desktop, just collapse/expand
      setIsCollapsed(!isCollapsed);
    }
  };

  return (
    <motion.div
      className={cn(
        "h-full bg-gradient-chat border-r border-border/50 flex flex-col",
        isCollapsed ? "w-16" : "w-80",
        className
      )}
      initial={{ x: -320 }}
      animate={{ x: 0 }}
      transition={{ duration: 0.3 }}
    >
      {/* Header */}
      <div className="p-4 border-b border-border/50">
        <div className="flex items-center justify-between">
          {!isCollapsed && (
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-gradient-to-br from-purple-600 to-purple-700 rounded-lg flex items-center justify-center">
                <Brain className="w-4 h-4 text-white" />
              </div>
              <div>
                <h2 className="font-handwriting text-xl font-bold bg-gradient-to-r from-purple-600 to-purple-700 bg-clip-text text-transparent">
                  Kuro
                </h2>
                <p className="text-xs text-muted-foreground">Your AI Assistant</p>
              </div>
            </div>
          )}
          
          <Button
            variant="ghost"
            size="icon"
            onClick={handleCloseClick}
            className="hover:bg-accent/20"
          >
            {isCollapsed ? <Menu className="w-4 h-4" /> : <X className="w-4 h-4" />}
          </Button>
        </div>

        {/* New Chat Button */}
        {!isCollapsed && (
          <motion.div
            className="mt-4"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            <Button
              onClick={onNewChat}
              variant="hero"
              className="w-full"
              size="lg"
            >
              <Plus className="w-4 h-4 mr-2" />
              New Chat
              <Sparkles className="w-4 h-4 ml-2" />
            </Button>
          </motion.div>
        )}

        {isCollapsed && (
          <motion.div
            className="mt-4"
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
          >
            <Button
              onClick={onNewChat}
              variant="hero"
              size="icon"
              className="w-full aspect-square"
            >
              <Plus className="w-4 h-4" />
            </Button>
          </motion.div>
        )}
      </div>

      {/* Sessions List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {!isCollapsed && (
          <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3">
            Recent Chats
          </h3>
        )}
        
        <AnimatePresence>
          {sessions.map((session, index) => (
            <motion.div
              key={session.session_id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ delay: index * 0.05 }}
              className="group"
            >
              <div className={cn(
                "flex items-center gap-2 p-3 rounded-lg transition-all duration-200 cursor-pointer",
                currentSessionId === session.session_id
                  ? "bg-primary/10 border border-primary/20"
                  : "hover:bg-accent/20 hover:shadow-sm",
                isCollapsed && "justify-center"
              )}
              onClick={() => onSelectSession(session.session_id)}
              >
                <MessageSquare className={cn(
                  "w-4 h-4 flex-shrink-0",
                  currentSessionId === session.session_id ? "text-primary" : "text-muted-foreground"
                )} />
                
                {!isCollapsed && (
                  <>
                    <div className="flex-1 min-w-0">
                      {editingSessionId === session.session_id ? (
                        <Input
                          value={editTitle}
                          onChange={(e) => setEditTitle(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') handleSaveRename();
                            if (e.key === 'Escape') handleCancelRename();
                          }}
                          onBlur={handleSaveRename}
                          className="h-6 text-sm border-none p-0 focus-visible:ring-0"
                          autoFocus
                        />
                      ) : (
                        <p className="text-sm font-medium truncate group-hover:text-foreground">
                          {session.title}
                        </p>
                      )}
                      <p className="text-xs text-muted-foreground truncate">
                        {(() => {
                          const dateStr = session.updated_at || session.created_at;
                          if (!dateStr) return '';
                          const date = new Date(dateStr);
                          return isNaN(date.getTime()) ? '' : date.toLocaleDateString();
                        })()}
                      </p>
                    </div>

                    {/* Session Actions */}
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="w-6 h-6 opacity-0 group-hover:opacity-100 transition-opacity"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <MoreHorizontal className="w-3 h-3" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem
                          onClick={(e) => {
                            e.stopPropagation();
                            handleRename(session.session_id, session.title);
                          }}
                        >
                          <Edit3 className="w-3 h-3 mr-2" />
                          Rename
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onClick={(e) => {
                            e.stopPropagation();
                            onDeleteSession(session.session_id);
                          }}
                          className="text-destructive"
                        >
                          <Trash2 className="w-3 h-3 mr-2" />
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </>
                )}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {/* User Profile */}
      {user && (
        <div className="p-4 border-t border-border/50">
          <div className={cn(
            "flex items-center gap-3 mb-3",
            isCollapsed && "justify-center"
          )}>
            <Avatar className="w-8 h-8 border-2 border-primary/20">
              <AvatarImage src={user.avatar} alt={user.name} />
              <AvatarFallback className="bg-gradient-to-br from-purple-600 to-purple-700 text-white text-sm font-medium">
                {user.name.split(' ').map(n => n[0]).join('')}
              </AvatarFallback>
            </Avatar>
            
            {!isCollapsed && (
              <>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{user.name}</p>
                  <p className="text-xs text-muted-foreground truncate">{user.email}</p>
                </div>
                
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={onSignOut}
                  className="w-8 h-8 hover:bg-destructive/10 hover:text-destructive"
                >
                  <LogOut className="w-4 h-4" />
                </Button>
              </>
            )}
          </div>
          
          {/* Donate Button - Always below user info */}
          {!isCollapsed && (
            <div className="w-full">
              <Button
                variant="outline"
                size="sm"
                className="w-full text-xs"
                onClick={() => window.open('https://github.com/sponsors/Gaurav8302', '_blank')}
              >
                <Heart className="w-3 h-3 mr-2" />
                Help Make Kuro Smarter
              </Button>
            </div>
          )}
        </div>
      )}
    </motion.div>
  );
};