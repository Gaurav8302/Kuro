import { useState, memo } from 'react';
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
  Brain
} from 'lucide-react';
import { ChatSession, User } from '@/types';
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
import { useOptimizedAnimations } from '@/hooks/use-performance';
import { OptimizedHolographicCard } from '@/components/OptimizedHolographicCard';
import { HolographicButton } from '@/components/HolographicButton';
import { HoloMessageIcon, HoloDeleteIcon, HoloSparklesIcon } from '@/components/HolographicIcons';

interface OptimizedSidebarProps {
  sessions: ChatSession[];
  currentSessionId?: string;
  user?: User;
  onNewChat: () => void;
  onSelectSession: (sessionId: string) => void;
  onRenameSession: (sessionId: string, newTitle: string) => void;
  onDeleteSession: (sessionId: string) => void;
  onSignOut: () => void;
  onClose?: () => void;
  className?: string;
}

// Lightweight sidebar for mobile
const LightweightSidebar: React.FC<OptimizedSidebarProps> = memo(({
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
}) => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');

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

  return (
    <div className={cn(
      "h-full bg-gradient-to-b from-background/95 to-background/80 backdrop-blur-xl border-r border-holo-cyan-500/20 flex flex-col relative overflow-hidden",
      isCollapsed ? "w-20" : "w-80",
      className
    )}>
      {/* Simple background pattern */}
      <div className="absolute inset-0 opacity-10 bg-gradient-to-b from-holo-cyan-500/5 to-holo-purple-500/5" />
      
      {/* Header */}
      <div className="p-4 border-b border-holo-cyan-500/20 relative flex-shrink-0">
        <div className="flex items-center justify-between">
          {!isCollapsed && (
            <div className="flex items-center gap-2">
              <div className="w-10 h-10 bg-gradient-to-br from-holo-purple-500 to-holo-magenta-500 rounded-full flex items-center justify-center overflow-hidden border-2 border-holo-purple-400/50">
                <img src="/kuroai.png" alt="Kuro AI" className="w-full h-full object-cover rounded-full" />
              </div>
              <div>
                <h2 className="font-orbitron text-xl font-bold text-holo-cyan-400">Kuro</h2>
                <p className="text-xs text-holo-cyan-400/60 font-rajdhani tracking-wider">AI ASSISTANT</p>
              </div>
            </div>
          )}
          
          <button
            onClick={onClose || (() => setIsCollapsed(!isCollapsed))}
            className="w-8 h-8 rounded-lg bg-holo-cyan-500/10 border border-holo-cyan-400/30 hover:bg-holo-cyan-500/20 transition-all duration-300 flex items-center justify-center"
          >
            {isCollapsed ? <Menu className="w-4 h-4 text-holo-cyan-400" /> : <X className="w-4 h-4 text-holo-cyan-400" />}
          </button>
        </div>

        {/* New Chat Button */}
        {!isCollapsed && (
          <div className="mt-4">
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
          </div>
        )}

        {isCollapsed && (
          <div className="mt-4">
            <HolographicButton
              onClick={onNewChat}
              variant="primary"
              className="w-full aspect-square"
            >
              <Plus className="w-5 h-5" />
            </HolographicButton>
          </div>
        )}
      </div>

      {/* Sessions List - Scrollable content with bottom padding for bottom section */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3 relative min-h-0" style={{ paddingBottom: '200px' }}>
        {!isCollapsed && (
          <h3 className="text-xs font-semibold text-holo-cyan-400/80 uppercase tracking-wider mb-4 font-orbitron">
            CHATS
          </h3>
        )}
        
        {sessions.map((session) => (
          <div key={session.session_id} className="group">
            <div
              className={cn(
                "glass-panel border-holo-cyan-500/20 cursor-pointer transition-all duration-300 hover:border-holo-cyan-400/40 hover:bg-holo-cyan-500/5",
                currentSessionId === session.session_id && "border-holo-cyan-400/50 bg-holo-cyan-500/10",
                isCollapsed && "flex justify-center"
              )}
              onClick={() => onSelectSession(session.session_id)}
            >
              <div className="flex items-center gap-3 p-3">
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
                        <p className="text-sm font-medium truncate text-holo-cyan-100 font-space">
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
                        <button
                          className="w-6 h-6 rounded-md bg-holo-cyan-500/10 border border-holo-cyan-400/20 hover:bg-holo-cyan-500/20 transition-all duration-300 flex items-center justify-center flex-shrink-0"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <MoreHorizontal className="w-3 h-3 text-holo-cyan-400" />
                        </button>
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
            </div>
          </div>
        ))}
      </div>

      {/* Bottom Section - Fixed at bottom with sponsor, user profile, and logout */}
      {user && (
        <div className="absolute bottom-0 left-0 right-0 bg-background/95 backdrop-blur-sm border-t border-holo-cyan-500/20">
          {!isCollapsed && (
            <>
              {/* Sponsor Button */}
              <div className="p-4 pb-2">
                <HolographicButton
                  variant="ghost"
                  size="sm"
                  className="w-full text-xs font-orbitron tracking-wide"
                  onClick={() => window.open('https://github.com/sponsors/Gaurav8302', '_blank')}
                >
                  <Brain className="w-3 h-3 mr-2" />
                  SPONSOR
                </HolographicButton>
              </div>
              
              {/* User Profile */}
              <div className="px-4 pb-2">
                <div className="flex items-center gap-3">
                  <Avatar className="w-10 h-10 border-2 border-holo-blue-400/50">
                    <AvatarImage src={user.avatar} alt={user.name} />
                    <AvatarFallback className="bg-gradient-to-br from-holo-blue-500 to-holo-cyan-500 text-white text-sm font-medium font-orbitron">
                      {user.name.split(' ').map(n => n[0]).join('')}
                    </AvatarFallback>
                  </Avatar>
                  
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate text-holo-cyan-100 font-space">{user.name}</p>
                    <p className="text-xs text-holo-cyan-400/60 truncate font-orbitron">{user.email}</p>
                  </div>
                </div>
              </div>
            </>
          )}
          
          {/* Logout Button */}
          <div className="p-4 pt-2">
            {!isCollapsed ? (
              <button
                onClick={onSignOut}
                className="w-full inline-flex items-center justify-center gap-2 px-3 h-10 rounded-lg bg-holo-magenta-500/10 border border-holo-magenta-400/30 hover:bg-holo-magenta-500/20 transition-all duration-300"
              >
                <LogOut className="w-4 h-4 text-holo-magenta-400" />
                <span className="text-sm font-orbitron text-holo-magenta-300 tracking-wide">LOG OUT</span>
              </button>
            ) : (
              <button
                onClick={onSignOut}
                className="w-full h-10 rounded-lg bg-holo-magenta-500/10 border border-holo-magenta-400/30 hover:bg-holo-magenta-500/20 transition-all duration-300 flex items-center justify-center"
              >
                <LogOut className="w-4 h-4 text-holo-magenta-400" />
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
});

// Full animated sidebar for desktop
const AnimatedSidebar: React.FC<OptimizedSidebarProps> = memo((props) => {
  const { animationDuration } = useOptimizedAnimations();
  
  return (
    <motion.div
      initial={{ x: -320, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ duration: animationDuration * 2, ease: 'easeOut' }}
    >
      <LightweightSidebar {...props} />
    </motion.div>
  );
});

export const OptimizedSidebar: React.FC<OptimizedSidebarProps> = (props) => {
  const isMobile = useIsMobile();
  const { shouldReduceAnimations } = useOptimizedAnimations();

  // Use lightweight sidebar on mobile or when animations should be reduced
  if (isMobile || shouldReduceAnimations) {
    return <LightweightSidebar {...props} />;
  }

  // Use animated sidebar on desktop
  return <AnimatedSidebar {...props} />;
};

export default OptimizedSidebar;