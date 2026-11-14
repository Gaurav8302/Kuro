import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  TouchSensor,
  useSensor,
  useSensors,
  DragStartEvent,
  DragEndEvent,
  closestCenter,
  rectIntersection,
} from '@dnd-kit/core';
import { ChatLayout } from '@/components/ChatLayout';
import { ChatPanel } from '@/components/ChatPanel';
import { SplitViewDropZone } from '@/components/SplitViewDropZone';
import { EditableTitle } from '@/components/kuro/KuroChatHeader';
import { ResizablePanelGroup, ResizablePanel, ResizableHandle } from '@/components/ui/resizable';
import { ChatSession, DropZone } from '@/types';
import { useToast } from '@/hooks/use-toast';
import { useClerkApi } from '@/lib/api';
import { useAuth, useUser } from '@clerk/clerk-react';
import { useIsMobile } from '@/hooks/use-mobile';
import { SplitViewProvider, useSplitView } from '@/contexts/SplitViewContext';
import { useExperience, useStage } from '@/experience/ExperienceContext';
import { KuroNav } from '@/experience/chat/KuroNav';

/**
 * ChatInner — the CHAT stage.
 *
 * The environment (background, Core, wordmark) is already on screen from the
 * previous stage; this component only adds the conversation and the system
 * navigation. Name setup and the first-time intro moved to the Awakening, so
 * there is no modal, no intro overlay, and no loading screen here.
 */
const ChatInner = () => {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const clerkApiRequest = useClerkApi();
  const { user } = useUser();
  const { signOut } = useAuth();
  const isMobile = useIsMobile();
  const splitView = useSplitView();
  const { setNavOpen, setCoreMode } = useExperience();
  useStage('chat', 'idle');

  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [sessionsLoaded, setSessionsLoaded] = useState(false);
  const [primaryTitle, setPrimaryTitle] = useState<{ title: string | null; id: string | null }>({ title: null, id: null });
  const autoCreated = useRef(false);

  const [draggedSession, setDraggedSession] = useState<{ sessionId: string; title: string } | null>(null);

  const isDev = import.meta.env.DEV;
  const showErrorToast = useCallback(
    (title: string, description: string) => {
      toast({
        title: isDev ? 'Maintenance' : title,
        description: isDev ? 'Maintenance in progress. Please try again later.' : description,
        variant: 'destructive',
      });
    },
    [toast, isDev]
  );

  // --- Sessions ---
  const fetchSessions = useCallback(async () => {
    if (!user) return;
    try {
      const data = await clerkApiRequest<{ sessions: ChatSession[] }>(`/sessions/${user.id}`, 'get');
      setSessions(data.sessions);
      setSessionsLoaded(true);
    } catch (err) {
      console.error('[kuro] sessions failed', err);
      setSessionsLoaded(true);
      showErrorToast('Connection issue', 'Having trouble loading conversations.');
    }
  }, [user, clerkApiRequest, showErrorToast]);

  useEffect(() => {
    if (user) fetchSessions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.id]);

  const handleNewChat = useCallback(async () => {
    if (!user) return;
    try {
      const data = await clerkApiRequest<{ session_id: string }>('/session/create', 'post', null, { user_id: user.id });
      await fetchSessions();
      navigate(`/chat/${data.session_id}`);
      setNavOpen(false);
    } catch (err) {
      showErrorToast('Error', err instanceof Error ? err.message : 'Could not start a conversation.');
    }
  }, [user, clerkApiRequest, fetchSessions, navigate, setNavOpen, showErrorToast]);

  // First visit with no conversations: open one (unchanged behaviour).
  useEffect(() => {
    if (!sessionsLoaded || sessionId || autoCreated.current) return;
    if (sessions.length === 0) {
      autoCreated.current = true;
      handleNewChat();
    }
  }, [sessionsLoaded, sessions.length, sessionId, handleNewChat]);

  // URL → primary panel
  useEffect(() => {
    if (!user || !sessionId || !sessionsLoaded) return;
    const exists = sessions.find((s) => s.session_id === sessionId);
    if (exists) {
      splitView.setPrimarySessionId(sessionId);
    } else if (sessions.length > 0) {
      toast({ title: 'Conversation not found', description: 'It may have been deleted.', variant: 'destructive' });
      navigate('/chat');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId, sessions, sessionsLoaded, user]);

  const handleDeleteSession = async (sid: string) => {
    try {
      await clerkApiRequest(`/session/${sid}`, 'delete');
      const panel = splitView.layout.panels.find((p) => p.sessionId === sid);
      if (panel) splitView.closePanel(panel.position);
      await fetchSessions();
      const primary = splitView.layout.panels[0]?.sessionId;
      if (primary === sid || !primary || sessionId === sid) navigate('/chat');
    } catch (err) {
      showErrorToast('Error', 'Could not delete: ' + (err instanceof Error ? err.message : ''));
    }
  };

  const handleRenameSession = async (sid: string, newTitle: string) => {
    try {
      await clerkApiRequest(`/session/${sid}`, 'put', { new_title: newTitle });
      await fetchSessions();
      if (primaryTitle.id === sid) setPrimaryTitle({ id: sid, title: newTitle });
    } catch (err) {
      showErrorToast('Error', 'Could not rename: ' + (err instanceof Error ? err.message : ''));
    }
  };

  const handleSignOut = async () => {
    setNavOpen(false);
    setCoreMode('idle');
    await signOut();
    navigate('/');
  };

  const handleSelectSession = (id: string) => {
    if (!user || !id) return;
    navigate(`/chat/${id}`);
    setNavOpen(false);
  };

  // --- DnD (split view) ---
  const handleDragStart = (event: DragStartEvent) => {
    const data = event.active.data.current;
    if (data?.sessionId) {
      setDraggedSession({ sessionId: data.sessionId, title: data.title || 'Conversation' });
      splitView.setIsDragging(true);
      setNavOpen(false);
    }
  };

  const handleDragEnd = (event: DragEndEvent) => {
    splitView.setIsDragging(false);
    setDraggedSession(null);
    const { active, over } = event;
    if (!over || !active.data.current?.sessionId) return;
    const dropped = active.data.current.sessionId as string;
    const zoneId = over.id as string;
    const map: Record<string, DropZone> = {
      'drop-left': 'left',
      'drop-right': 'right',
      'drop-center': 'center',
      'drop-top': 'top',
      'drop-bottom': 'bottom',
    };
    const zone = map[zoneId];
    if (!zone) return;
    splitView.openSessionInPanel(dropped, zone);
    if (zone === 'center' || zone === 'left' || zone === 'top') navigate(`/chat/${dropped}`);
  };

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: 150, tolerance: 8 } })
  );

  // --- Layout ---
  const { layout } = splitView;
  const primarySessionId = sessionId || layout.panels[0]?.sessionId || null;
  const secondarySessionId = layout.mode === 'split' ? layout.panels[1]?.sessionId || null : null;
  const isSplit = layout.mode === 'split' && !!secondarySessionId;

  const onPrimaryTitle = useCallback((title: string | null, id: string | null) => setPrimaryTitle({ title, id }), []);

  const mainContent = isSplit ? (
    <ResizablePanelGroup direction={isMobile ? 'vertical' : 'horizontal'} onLayout={(sizes: number[]) => splitView.updatePanelSizes(sizes)}>
      <ResizablePanel defaultSize={layout.panelSizes?.[0] ?? 50} minSize={20}>
        <ChatPanel
          sessionId={primarySessionId}
          sessions={sessions}
          userId={user?.id}
          userAvatar={user?.imageUrl || ''}
          clerkApiRequest={clerkApiRequest}
          panelPosition={isMobile ? 'top' : 'left'}
          isSplitMode
          onSessionsChanged={fetchSessions}
          onSessionTitle={onPrimaryTitle}
        />
      </ResizablePanel>
      <ResizableHandle className="bg-border/60" />
      <ResizablePanel defaultSize={layout.panelSizes?.[1] ?? 50} minSize={20}>
        <ChatPanel
          sessionId={secondarySessionId}
          sessions={sessions}
          userId={user?.id}
          userAvatar={user?.imageUrl || ''}
          clerkApiRequest={clerkApiRequest}
          panelPosition={isMobile ? 'bottom' : 'right'}
          isSplitMode
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
      onSessionTitle={onPrimaryTitle}
    />
  );

  // Top strip: [Core][KURO][Menu] come from the environment/rail (left ~190px).
  // The conversation title sits in the centre; nothing else.
  const topBar = (
    <div className="flex h-full items-center">
      <div className={isMobile ? 'w-[190px] flex-shrink-0' : 'w-[220px] flex-shrink-0'} />
      <div className="flex min-w-0 flex-1 items-center justify-center px-4">
        {!isSplit && primaryTitle.id && primaryTitle.title && (
          <EditableTitle
            title={primaryTitle.title}
            onRename={(t) => primaryTitle.id && handleRenameSession(primaryTitle.id, t)}
            align="center"
            className="max-w-[min(60vw,520px)]"
          />
        )}
      </div>
      <div className={isMobile ? 'w-4 flex-shrink-0' : 'w-[220px] flex-shrink-0'} />
    </div>
  );

  return (
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
      <ChatLayout
        topBar={topBar}
        mainContent={mainContent}
        dropZoneOverlay={<SplitViewDropZone isVisible={splitView.isDragging} currentMode={layout.mode} />}
        overlays={
          <KuroNav
            sessions={sessions}
            currentSessionId={primarySessionId}
            userEmail={user?.emailAddresses?.[0]?.emailAddress}
            clerkApiRequest={clerkApiRequest}
            onNewChat={handleNewChat}
            onSelectSession={handleSelectSession}
            onRenameSession={handleRenameSession}
            onDeleteSession={handleDeleteSession}
            onSignOut={handleSignOut}
          />
        }
      />
      <DragOverlay zIndex={70}>
        {draggedSession && (
          <div className="k-surface px-4 py-2 text-[13px] text-foreground">{draggedSession.title}</div>
        )}
      </DragOverlay>
    </DndContext>
  );
};

const Chat = () => (
  <SplitViewProvider>
    <ChatInner />
  </SplitViewProvider>
);

export default Chat;
