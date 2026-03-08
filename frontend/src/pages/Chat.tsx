import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  DragStartEvent,
  DragEndEvent,
} from '@dnd-kit/core';
import { KuroSidebar } from '@/components/kuro/KuroSidebar';
import { KuroIntro } from '@/components/kuro/KuroIntro';
import { KuroBackground } from '@/components/kuro/KuroBackground';
import { ChatLayout } from '@/components/ChatLayout';
import { ChatPanel } from '@/components/ChatPanel';
import { SplitViewDropZone } from '@/components/SplitViewDropZone';
import NameSetupModal from '@/components/NameSetupModal';
import { ResizablePanelGroup, ResizablePanel, ResizableHandle } from '@/components/ui/resizable';
import {
  AlertTriangle,
  X,
  MessageSquare,
} from 'lucide-react';
import { ChatSession, DropZone } from '@/types';
import { useToast } from '@/hooks/use-toast';
import { cn } from '@/lib/utils';
import { useClerkApi, setUserName, getUserName, checkUserHasName, getIntroShown, setIntroShown } from '@/lib/api';
import { useAuth, useUser } from '@clerk/clerk-react';
import { useIsMobile } from '@/hooks/use-mobile';
import { KuroCard } from '@/components/kuro';
import { useOptimizedAnimations } from '@/hooks/use-performance';
import { SplitViewProvider, useSplitView } from '@/contexts/SplitViewContext';

/**
 * ChatInner - The main chat orchestrator component.
 * Must be wrapped in SplitViewProvider and DndContext.
 */
const ChatInner = () => {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const clerkApiRequest = useClerkApi();
  const { user, isLoaded } = useUser();
  const { signOut } = useAuth();
  const isMobile = useIsMobile();
  const { shouldReduceAnimations, animationDuration } = useOptimizedAnimations();
  const splitView = useSplitView();

  // --- Global state (not per-panel) ---
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [hasAutoCreatedSession, setHasAutoCreatedSession] = useState(false);
  const [showNameModal, setShowNameModal] = useState(false);
  const [hasCheckedName, setHasCheckedName] = useState(false);
  const [isInitializing, setIsInitializing] = useState(true);
  const [showFirstTimeIntro, setShowFirstTimeIntro] = useState(false);
  const [introChecking, setIntroChecking] = useState(true);
  const [displayedName, setDisplayedName] = useState(user?.fullName || user?.username || '');
  const [globalError, setGlobalError] = useState<string | null>(null);

  // DnD state
  const [draggedSession, setDraggedSession] = useState<{
    sessionId: string;
    title: string;
  } | null>(null);

  const isDev = import.meta.env.DEV;
  const maintenanceMessage = 'Maintenance in progress. Please try again later.';

  const showErrorToast = useCallback(
    (fallbackTitle: string, fallbackDescription: string) => {
      toast({
        title: isDev ? 'Maintenance' : fallbackTitle,
        description: isDev ? maintenanceMessage : fallbackDescription,
        variant: 'destructive',
      });
    },
    [toast, isDev]
  );

  // --- Sync displayed name with Clerk user ---
  useEffect(() => {
    setDisplayedName(user?.fullName || user?.username || '');
  }, [user]);

  // --- Sidebar open/close based on viewport ---
  useEffect(() => {
    if (isMobile) {
      setIsSidebarOpen(false);
    } else {
      setIsSidebarOpen(true);
    }
  }, [isMobile]);

  // --- Dynamic viewport height for mobile ---
  useEffect(() => {
    const setAppHeight = () => {
      const vh = window.innerHeight * 0.01;
      document.documentElement.style.setProperty('--app-height', `${vh * 100}px`);
    };
    setAppHeight();
    window.addEventListener('resize', setAppHeight);
    window.addEventListener('orientationchange', setAppHeight);
    return () => {
      window.removeEventListener('resize', setAppHeight);
      window.removeEventListener('orientationchange', setAppHeight);
    };
  }, []);

  // --- First-time intro logic ---
  useEffect(() => {
    const checkIntro = async () => {
      if (!user || !isLoaded) return;
      if (!hasCheckedName) return;
      if (showNameModal) return;

      try {
        const { intro_shown } = await getIntroShown(user.id);
        if (!intro_shown) {
          setShowFirstTimeIntro(true);
          await setIntroShown(user.id);
          setTimeout(() => setShowFirstTimeIntro(false), 7000);
        }
      } catch (e) {
        console.error('Error checking intro status:', e);
        const fallbackKey = `kuro_intro_shown_${user.id}`;
        if (!localStorage.getItem(fallbackKey)) {
          localStorage.setItem(fallbackKey, '1');
          setShowFirstTimeIntro(true);
          setTimeout(() => setShowFirstTimeIntro(false), 7000);
        }
      } finally {
        setIntroChecking(false);
      }
    };
    checkIntro();
  }, [user, isLoaded, hasCheckedName, showNameModal]);

  // --- Check if user needs name setup ---
  useEffect(() => {
    const checkUserName = async () => {
      if (!user || hasCheckedName) return;
      try {
        const { has_name } = await checkUserHasName(user.id);
        if (!has_name) {
          setShowNameModal(true);
        } else {
          try {
            const { name } = await getUserName(user.id);
            if (name) setDisplayedName(name);
          } catch {
            // Use fallback from Clerk
          }
        }
      } catch {
        setShowNameModal(true);
      } finally {
        setHasCheckedName(true);
      }
    };
    if (user) checkUserName();
  }, [user, hasCheckedName]);

  // --- Name setup handlers ---
  const handleNameSetup = async (name: string) => {
    if (!user) return;
    try {
      await setUserName(user.id, name);
      setShowNameModal(false);
      setDisplayedName(name);
      toast({ title: 'Welcome!', description: `Nice to meet you, ${name}!` });
      setTimeout(() => {
        if (!showFirstTimeIntro) {
          setShowFirstTimeIntro(true);
          setTimeout(() => setShowFirstTimeIntro(false), 7000);
        }
      }, 500);
    } catch {
      setShowNameModal(false);
      toast({ title: 'Welcome!', description: "Let's start chatting!" });
    }
  };

  const handleNameSkip = () => {
    setShowNameModal(false);
    toast({ title: 'Welcome!', description: "Let's start chatting!" });
    setTimeout(() => {
      if (!showFirstTimeIntro) {
        setShowFirstTimeIntro(true);
        setTimeout(() => setShowFirstTimeIntro(false), 7000);
      }
    }, 500);
  };

  // --- Session management ---
  const fetchSessions = useCallback(async () => {
    if (!user) return;
    try {
      const data = await clerkApiRequest<{ sessions: ChatSession[] }>(
        `/sessions/${user.id}`,
        'get'
      );
      setSessions(data.sessions);

      if (data.sessions.length === 0 && !sessionId && !hasAutoCreatedSession) {
        setHasAutoCreatedSession(true);
        await handleNewChat();
        return;
      }

      // Sync primary panel with URL sessionId
      if (sessionId && data.sessions.length > 0) {
        const session = data.sessions.find((s) => s.session_id === sessionId);
        if (session) {
          splitView.setPrimarySessionId(sessionId);
        } else {
          navigate('/chat');
        }
      }
    } catch (err: any) {
      console.error('Error fetching sessions:', err);
      showErrorToast('Connection Issue', 'Having trouble loading sessions.');
    } finally {
      setIsInitializing(false);
    }
  }, [user, sessionId, hasAutoCreatedSession, clerkApiRequest, showErrorToast]);

  // Fetch sessions on mount
  useEffect(() => {
    if (user) {
      fetchSessions();
    } else {
      setIsInitializing(false);
    }
    const timeout = setTimeout(() => setIsInitializing(false), 10000);
    return () => clearTimeout(timeout);
  }, [user]);

  // Sync URL sessionId → primary panel
  useEffect(() => {
    if (!user || !sessionId || sessions.length === 0) return;
    const session = sessions.find((s) => s.session_id === sessionId);
    if (session) {
      splitView.setPrimarySessionId(sessionId);
    } else {
      toast({
        title: 'Session Not Found',
        description: 'The requested session could not be found.',
        variant: 'destructive',
      });
      navigate('/chat');
    }
  }, [sessionId, sessions, user]);

  const handleNewChat = async () => {
    try {
      if (!user) return;
      const data = await clerkApiRequest<{ session_id: string }>(
        '/session/create',
        'post',
        null,
        { user_id: user.id }
      );
      await fetchSessions();
      navigate(`/chat/${data.session_id}`);
      if (isMobile) setIsSidebarOpen(false);
    } catch (err: any) {
      showErrorToast('Error', err.message);
    }
  };

  const handleDeleteSession = async (sid: string) => {
    try {
      await clerkApiRequest(`/session/${sid}`, 'delete');
      toast({
        title: 'Session deleted',
        description: 'The chat session has been deleted successfully.',
      });

      // Close panel if this session is open in split view
      const panel = splitView.layout.panels.find((p) => p.sessionId === sid);
      if (panel) {
        splitView.closePanel(panel.position);
      }

      await fetchSessions();

      // If primary panel session was deleted, navigate to /chat
      const primarySessionId = splitView.layout.panels[0]?.sessionId;
      if (primarySessionId === sid || !primarySessionId) {
        navigate('/chat');
      }
    } catch (err: any) {
      showErrorToast('Error', 'Failed to delete session: ' + err.message);
    }
  };

  const handleRenameSession = async (sid: string, newTitle: string) => {
    try {
      await clerkApiRequest(`/session/${sid}`, 'put', { new_title: newTitle });
      await fetchSessions();
      toast({
        title: 'Session renamed',
        description: 'Chat session title has been updated successfully.',
      });
    } catch (err: any) {
      showErrorToast('Error', 'Failed to rename session: ' + err.message);
    }
  };

  const handleSignOut = async () => {
    await signOut();
    navigate('/');
    toast({ title: 'Signed out', description: 'Come back soon!' });
  };

  const handleSelectSession = async (id: string) => {
    if (!user || !id) return;
    navigate(`/chat/${id}`);
    if (isMobile) setIsSidebarOpen(false);
  };

  const toggleSidebar = () => setIsSidebarOpen(!isSidebarOpen);

  // --- DnD handlers ---
  const handleDragStart = (event: DragStartEvent) => {
    const data = event.active.data.current;
    if (data?.sessionId) {
      setDraggedSession({
        sessionId: data.sessionId,
        title: data.title || 'Chat Session',
      });
      splitView.setIsDragging(true);
    }
  };

  const handleDragEnd = (event: DragEndEvent) => {
    splitView.setIsDragging(false);
    setDraggedSession(null);

    const { active, over } = event;
    if (!over || !active.data.current?.sessionId) return;

    const droppedSessionId = active.data.current.sessionId as string;
    const dropZoneId = over.id as string;

    let dropZone: DropZone;
    if (dropZoneId === 'drop-left') dropZone = 'left';
    else if (dropZoneId === 'drop-right') dropZone = 'right';
    else if (dropZoneId === 'drop-center') dropZone = 'center';
    else if (dropZoneId === 'drop-top') dropZone = 'top';
    else if (dropZoneId === 'drop-bottom') dropZone = 'bottom';
    else return;

    splitView.openSessionInPanel(droppedSessionId, dropZone);

    // If center drop in single mode, navigate to the new session
    if (dropZone === 'center') {
      navigate(`/chat/${droppedSessionId}`);
    }
    // If split mode and this was dropped on left/top (primary), update URL
    else if (dropZone === 'left' || dropZone === 'top') {
      navigate(`/chat/${droppedSessionId}`);
    }
  };

  // Configure DnD sensors - distance threshold prevents clicks from triggering drag
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 8 },
    })
  );

  // --- Loading screen ---
  if (!isLoaded || !user || (isInitializing && user)) {
    return (
      <div className="h-screen flex items-center justify-center bg-background relative overflow-hidden">
        <KuroBackground variant="subtle" />
        <div className="text-center relative z-10">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{
              duration: shouldReduceAnimations ? 1 : 2,
              repeat: Infinity,
              ease: 'linear',
            }}
            className="w-16 h-16 mx-auto mb-6"
          >
            <div className="w-full h-full rounded-full border-4 border-primary/30 border-t-primary" />
          </motion.div>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: shouldReduceAnimations ? 0.1 : 0.3 }}
          >
            <h3 className="text-xl font-semibold text-foreground mb-2">Initializing</h3>
            <p className="text-muted-foreground text-sm">
              {!isLoaded ? 'Loading...' : !user ? 'Loading chat...' : 'Setting up your session...'}
            </p>
            {isInitializing && (
              <p className="text-xs text-muted-foreground/60 mt-4">
                Having trouble?{' '}
                <button
                  onClick={() => setIsInitializing(false)}
                  className="text-primary underline hover:text-primary/80 transition-colors"
                >
                  Skip and continue
                </button>
              </p>
            )}
          </motion.div>
        </div>
      </div>
    );
  }

  // --- Determine panel layout ---
  const { layout } = splitView;
  const primarySessionId = layout.panels[0]?.sessionId || sessionId || null;
  const secondarySessionId = layout.mode === 'split' ? layout.panels[1]?.sessionId || null : null;

  // --- Build main content ---
  const mainContent =
    layout.mode === 'split' && secondarySessionId ? (
      <ResizablePanelGroup
        direction={isMobile ? 'vertical' : 'horizontal'}
        onLayout={(sizes: number[]) => splitView.updatePanelSizes(sizes)}
      >
        <ResizablePanel defaultSize={layout.panelSizes?.[0] ?? 50} minSize={20}>
          <ChatPanel
            sessionId={primarySessionId}
            sessions={sessions}
            userId={user?.id}
            userAvatar={user?.imageUrl || ''}
            clerkApiRequest={clerkApiRequest}
            panelPosition={isMobile ? 'top' : 'left'}
            isSplitMode={true}
            onSessionsChanged={fetchSessions}
            onToggleSidebar={toggleSidebar}
          />
        </ResizablePanel>
        <ResizableHandle withHandle />
        <ResizablePanel defaultSize={layout.panelSizes?.[1] ?? 50} minSize={20}>
          <ChatPanel
            sessionId={secondarySessionId}
            sessions={sessions}
            userId={user?.id}
            userAvatar={user?.imageUrl || ''}
            clerkApiRequest={clerkApiRequest}
            panelPosition={isMobile ? 'bottom' : 'right'}
            isSplitMode={true}
            onSessionsChanged={fetchSessions}
          />
        </ResizablePanel>
      </ResizablePanelGroup>
    ) : (
      <ChatPanel
        sessionId={primarySessionId}
        sessions={sessions}
        userId={user?.id}
        userAvatar={user?.imageUrl || ''}
        clerkApiRequest={clerkApiRequest}
        panelPosition={isMobile ? 'top' : 'left'}
        isSplitMode={false}
        onSessionsChanged={fetchSessions}
        onToggleSidebar={toggleSidebar}
      />
    );

  // --- Sidebar ---
  const sidebarContent = (
    <KuroSidebar
      sessions={sessions}
      currentSessionId={primarySessionId || undefined}
      user={
        user
          ? {
              id: user.id,
              name: displayedName || 'User',
              email: user.emailAddresses?.[0]?.emailAddress || '',
              avatar: user.imageUrl,
            }
          : undefined
      }
      onNewChat={handleNewChat}
      onSelectSession={handleSelectSession}
      onRenameSession={handleRenameSession}
      onDeleteSession={handleDeleteSession}
      onSignOut={handleSignOut}
      onClose={() => setIsSidebarOpen(false)}
    />
  );

  // --- Overlays ---
  const overlayContent = (
    <>
      <AnimatePresence>
        {showFirstTimeIntro && !showNameModal && (
          <motion.div
            key="intro-overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: animationDuration }}
            className="fixed inset-0 z-[9998]"
          >
            <KuroIntro
              phrases={[
                displayedName ? `Welcome, ${displayedName}` : 'Welcome',
                "Let's Imagine",
                "Let's Build",
                'Kuro AI',
              ]}
              cycleMs={1600}
              fullscreen
              onFinish={() => {}}
            />
            <motion.button
              onClick={() => setShowFirstTimeIntro(false)}
              className="absolute top-6 right-6 z-[10000] px-6 py-3 rounded-full glass border border-white/10 text-muted-foreground hover:text-foreground hover:border-primary/50 text-sm font-medium tracking-wide transition-all duration-300"
              whileHover={shouldReduceAnimations ? undefined : { scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              Skip
            </motion.button>
          </motion.div>
        )}
      </AnimatePresence>

      <NameSetupModal
        isOpen={showNameModal}
        onComplete={handleNameSetup}
        onSkip={handleNameSkip}
      />

      <AnimatePresence>
        {globalError && (
          <motion.div
            className="fixed top-4 right-4 z-50 max-w-md"
            initial={{ opacity: 0, y: -30, scale: 0.8 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -30, scale: 0.8 }}
            transition={{ duration: animationDuration, ease: 'easeOut' }}
          >
            <KuroCard variant="elevated" className="bg-red-500/10 border-red-500/30">
              <div className="px-4 py-3 flex items-center gap-3">
                <AlertTriangle className="h-5 w-5 text-red-400" />
                <p className="text-sm text-red-200">{globalError}</p>
                <motion.button
                  className="ml-auto w-6 h-6 rounded bg-red-500/20 hover:bg-red-500/30 border border-red-500/30 flex items-center justify-center transition-all duration-300"
                  onClick={() => setGlobalError(null)}
                  whileHover={shouldReduceAnimations ? undefined : { scale: 1.1 }}
                  whileTap={{ scale: 0.9 }}
                >
                  <X className="h-3 w-3 text-red-400" />
                </motion.button>
              </div>
            </KuroCard>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );

  // --- Drag overlay (floating card during drag) ---
  const dragOverlayContent = (
    <DragOverlay>
      {draggedSession && (
        <div className="flex items-center gap-3 px-4 py-3 rounded-xl glass border border-primary/30 bg-background/95 shadow-xl min-w-[200px]">
          <div className="p-1.5 rounded-lg bg-secondary">
            <MessageSquare className="h-3.5 w-3.5 text-primary" />
          </div>
          <span className="text-sm font-medium text-foreground truncate">
            {draggedSession.title}
          </span>
        </div>
      )}
    </DragOverlay>
  );

  // --- Drop zone overlay ---
  const dropZoneOverlay = (
    <SplitViewDropZone
      isVisible={splitView.isDragging}
      currentMode={layout.mode}
    />
  );

  return (
    <DndContext
      sensors={sensors}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <ChatLayout
        sidebar={sidebarContent}
        sidebarOpen={isSidebarOpen}
        mainContent={mainContent}
        overlays={overlayContent}
        background={<KuroBackground variant="subtle" />}
        onMobileOverlayClick={() => setIsSidebarOpen(false)}
        dropZoneOverlay={dropZoneOverlay}
      />
      {dragOverlayContent}
    </DndContext>
  );
};

/**
 * Chat - Top-level page component.
 * Wraps everything in SplitViewProvider.
 */
const Chat = () => {
  return (
    <SplitViewProvider>
      <ChatInner />
    </SplitViewProvider>
  );
};

export default Chat;
