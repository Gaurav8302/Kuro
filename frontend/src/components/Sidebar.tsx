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
  Brain
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
import { HolographicCard } from '@/components/HolographicCard';
import { HolographicButton } from '@/components/HolographicButton';
import { HoloMessageIcon, HoloDeleteIcon, HoloSparklesIcon } from '@/components/HolographicIcons';
import HolographicParticles from '@/components/HolographicParticles';

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
        "h-full bg-gradient-to-b from-background/95 to-background/80 backdrop-blur-xl border-r border-holo-cyan-500/20 flex flex-col relative overflow-hidden",
        isCollapsed ? "w-20" : "w-80",
        className
      )}
      initial={{ x: -320, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ duration: 0.5, ease: 'easeOut' }}
    >
      {/* Holographic background effects */}
      <HolographicParticles count={15} size="sm" className="opacity-30" />
      
      {/* Vertical scan line */}
      <motion.div
        className="absolute right-0 top-0 w-0.5 h-full bg-gradient-to-b from-transparent via-holo-cyan-400 to-transparent"
        animate={{ opacity: [0.3, 0.8, 0.3] }}
        transition={{ duration: 3, repeat: Infinity }}
      />
      
      {/* Header */}
      <div className="p-4 border-b border-holo-cyan-500/20 relative">
        <div className="flex items-center justify-between">
          {!isCollapsed && (
            <div className="flex items-center gap-2">
              <motion.div 
                className="w-10 h-10 bg-gradient-to-br from-holo-purple-500 to-holo-magenta-500 rounded-full flex items-center justify-center overflow-hidden border-2 border-holo-purple-400/50 shadow-holo-purple"
                whileHover={{ scale: 1.1, rotate: 5 }}
                transition={{ duration: 0.2 }}
              >
                <img src="/kuroai.png" alt="Kuro AI" className="w-full h-full object-cover rounded-full" />
              </motion.div>
              <div>
                <h2 className="font-orbitron text-xl font-bold text-holo-cyan-400 text-holo-glow">
                  Kuro
                </h2>
                <p className="text-xs text-holo-cyan-400/60 font-rajdhani tracking-wider">AI ASSISTANT</p>
              </div>
            </div>
          )}
          
          <motion.button
            onClick={handleCloseClick}
            className="w-8 h-8 rounded-lg bg-holo-cyan-500/10 border border-holo-cyan-400/30 hover:bg-holo-cyan-500/20 hover:shadow-holo-glow transition-all duration-300 flex items-center justify-center"
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
          >
            {isCollapsed ? 
              <Menu className="w-4 h-4 text-holo-cyan-400" /> : 
              <X className="w-4 h-4 text-holo-cyan-400" />
            }
          </motion.button>
        </div>

        {/* New Chat Button */}
        {!isCollapsed && (
          <motion.div
            className="mt-4"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <HolographicButton
              onClick={onNewChat}
              variant="primary"
              size="lg"
              className="w-full font-orbitron tracking-wide"
            >
              <Plus className="w-5 h-5 mr-2" />
              NEW CHAT
              <HoloSparklesIcon size={16} className="ml-2" />
            </HolographicButton>
          </motion.div>
        )}

        {isCollapsed && (
          <motion.div
            className="mt-4"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.2 }}
          >
            <HolographicButton
              onClick={onNewChat}
              variant="primary"
              className="w-full aspect-square"
            >
              <Plus className="w-5 h-5" />
            </HolographicButton>
          </motion.div>
        )}
      </div>

      {/* Sessions List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3 relative">
        {!isCollapsed && (
          <h3 className="text-xs font-semibold text-holo-cyan-400/80 uppercase tracking-wider mb-4 font-orbitron">
            CHATS
          </h3>
        )}
        
        <AnimatePresence>
          {sessions.map((session, index) => (
            <motion.div
              key={session.session_id}
              initial={{ opacity: 0, x: -50, scale: 0.9 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: -50, scale: 0.9 }}
              transition={{ delay: index * 0.08, duration: 0.4, ease: 'easeOut' }}
              className="group"
            >
              <HolographicCard
                variant={currentSessionId === session.session_id ? 'glow' : 'default'}
                hover={true}
                scanLine={currentSessionId === session.session_id}
                className={cn(
                  "cursor-pointer transition-all duration-300",
                  currentSessionId === session.session_id && "border-holo-cyan-400/50 shadow-holo-glow",
                  isCollapsed && "flex justify-center"
                )}
              >
                <div
                  className="flex items-center gap-3 p-3"
                  role="button"
                  tabIndex={0}
                  onClick={() => onSelectSession(session.session_id)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      onSelectSession(session.session_id);
                    }
                  }}
                >
                  <HoloMessageIcon 
                    size={18}
                    className={cn(
                      "flex-shrink-0",
                      currentSessionId === session.session_id ? "text-holo-cyan-400" : "text-holo-cyan-400/60"
                    )} 
                  />
                
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
                          className="h-6 text-sm border-none p-0 focus-visible:ring-0 bg-transparent text-holo-cyan-100 font-space"
                          autoFocus
                        />
                      ) : (
                        <p className="text-sm font-medium truncate text-holo-cyan-100 group-hover:text-holo-cyan-200 font-space">
                          {session.title}
                        </p>
                      )}
                      <p className="text-xs text-holo-cyan-400/50 truncate font-orbitron">
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
                        <motion.button
                          className="w-6 h-6 rounded-md bg-holo-cyan-500/10 border border-holo-cyan-400/20 hover:bg-holo-cyan-500/20 hover:shadow-holo-glow transition-all duration-300 flex items-center justify-center flex-shrink-0"
                          onClick={(e) => e.stopPropagation()}
                          whileHover={{ scale: 1.1 }}
                          whileTap={{ scale: 0.9 }}
                        >
                          <MoreHorizontal className="w-3 h-3 text-holo-cyan-400" />
                        </motion.button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="glass-panel border-holo-cyan-500/20">
                        <DropdownMenuItem
                          onClick={(e) => {
                            e.stopPropagation();
                            handleRename(session.session_id, session.title);
                          }}
                          className="text-holo-cyan-300 hover:text-holo-cyan-100 hover:bg-holo-cyan-500/20 font-rajdhani"
                        >
                          <Edit3 className="w-3 h-3 mr-2" />
                          RENAME
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onClick={(e) => {
                            e.stopPropagation();
                            onDeleteSession(session.session_id);
                          }}
                          className="text-holo-magenta-400 hover:text-holo-magenta-300 hover:bg-holo-magenta-500/20 font-rajdhani"
                        >
                          <HoloDeleteIcon size={12} className="mr-2" />
                          DELETE
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </>
                )}
                </div>
              </HolographicCard>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {/* User Profile Section - Pushed to the bottom */}
      <div className="mt-auto p-4 border-t border-holo-cyan-500/20 relative">
        {user && (
          <>
            {/* Horizontal scan line */}
            <motion.div
              className="absolute top-0 left-0 w-full h-0.5 bg-gradient-to-r from-transparent via-holo-cyan-400 to-transparent"
              animate={{ opacity: [0.3, 0.8, 0.3] }}
              transition={{ duration: 2, repeat: Infinity }}
            />
            
            <div className={cn(
              "flex items-center gap-3 mb-3",
              isCollapsed && "justify-center"
            )}>
              <motion.div
                whileHover={{ scale: 1.1, rotate: 5 }}
                transition={{ duration: 0.2 }}
              >
                <Avatar className="w-10 h-10 border-2 border-holo-blue-400/50 shadow-holo-blue">
                <AvatarImage src={user.avatar} alt={user.name} />
                <AvatarFallback className="bg-gradient-to-br from-holo-blue-500 to-holo-cyan-500 text-white text-sm font-medium font-orbitron">
                  {user.name.split(' ').map(n => n[0]).join('')}
                </AvatarFallback>
                </Avatar>
              </motion.div>
              
              {!isCollapsed && (
                <>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate text-holo-cyan-100 font-space">{user.name}</p>
                    <p className="text-xs text-holo-cyan-400/60 truncate font-orbitron">{user.email}</p>
                  </div>
                  
                  <motion.button
                    onClick={onSignOut}
                    className="inline-flex items-center gap-2 px-3 h-8 rounded-lg bg-holo-magenta-500/10 border border-holo-magenta-400/30 hover:bg-holo-magenta-500/20 hover:shadow-holo-magenta transition-all duration-300"
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.97 }}
                  >
                    <LogOut className="w-4 h-4 text-holo-magenta-400" />
                    <span className="text-xs font-orbitron text-holo-magenta-300 tracking-wide">LOG OUT</span>
                  </motion.button>
                </>
              )}
            </div>
            
            {/* Support Button - Always below user info */}
            {!isCollapsed && (
              <motion.div 
                className="w-full"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
              >
                <HolographicButton
                  variant="ghost"
                  size="sm"
                  className="w-full text-xs font-orbitron tracking-wide"
                  onClick={() => window.open('https://github.com/sponsors/Gaurav8302', '_blank')}
                >
                  <Brain className="w-3 h-3 mr-2" />
                  SPONSOR
                </HolographicButton>
              </motion.div>
            )}
          </>
        )}
      </div>
    </motion.div>
  );
};