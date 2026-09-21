import React, { memo, useCallback, useEffect, useMemo, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { useDraggable } from '@dnd-kit/core';
import { CSS } from '@dnd-kit/utilities';
import { GripVertical } from 'lucide-react';
import { cn } from '@/lib/utils';
import { ChatSession } from '@/types';
import { useExperience } from '../ExperienceContext';
import { DUR, EASE } from '../motion';
import type { ClerkApiRequestFn } from '@/hooks/use-chat-panel';
import type { StoredMemory } from '@/lib/api';

/**
 * KuroNav — the system, opened from the Core.
 *
 *   CONVERSATIONS   what you and Kuro have talked about
 *   MEMORY          what Kuro remembers about you   (GET via /retrieve-memory)
 *   PROJECTS        contextual worlds — visual architecture only; not connected
 *   SETTINGS        name (/user/{id}/set-name), account, motion, sign out
 *
 * One panel, four views. It sits under the Core/wordmark/Menu controls (z-30)
 * so those stay reachable while it is open.
 */

export type NavView = 'conversations' | 'memory' | 'projects' | 'settings';

interface KuroNavProps {
  sessions: ChatSession[];
  currentSessionId?: string | null;
  userEmail?: string;
  clerkApiRequest: ClerkApiRequestFn;
  onNewChat: () => void;
  onSelectSession: (id: string) => void;
  onRenameSession: (id: string, title: string) => void;
  onDeleteSession: (id: string) => void;
  onSignOut: () => void;
}

const VIEWS: Array<{ id: NavView; label: string }> = [
  { id: 'conversations', label: 'Conversations' },
  { id: 'memory', label: 'Memory' },
  { id: 'projects', label: 'Projects' },
  { id: 'settings', label: 'Settings' },
];

/* ------------------------------------------------------------------ */
/* Conversations                                                       */
/* ------------------------------------------------------------------ */

const SessionRow: React.FC<{
  session: ChatSession;
  active: boolean;
  onSelect: () => void;
  onRename: (t: string) => void;
  onDelete: () => void;
}> = ({ session, active, onSelect, onRename, onDelete }) => {
  const [mode, setMode] = useState<'view' | 'edit' | 'confirm'>('view');
  const [value, setValue] = useState(session.title || '');
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: `session-${session.session_id}`,
    data: { sessionId: session.session_id, title: session.title },
  });

  const style = transform ? { transform: CSS.Translate.toString(transform), zIndex: isDragging ? 50 : undefined } : undefined;

  useEffect(() => {
    if (mode !== 'edit') setValue(session.title || '');
  }, [session.title, mode]);

  const save = () => {
    const t = value.trim();
    if (t && t !== session.title) onRename(t);
    setMode('view');
  };

  return (
    <li ref={setNodeRef} style={style} className={cn('group relative -mx-2 rounded px-2', isDragging && 'opacity-40')}>
      {mode === 'edit' ? (
        <input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onBlur={save}
          onKeyDown={(e) => {
            if (e.key === 'Enter') save();
            if (e.key === 'Escape') setMode('view');
          }}
          autoFocus
          aria-label="Rename conversation"
          className="k-field w-full border-b border-foreground/30 bg-transparent py-1.5 text-[13px] text-foreground outline-none"
        />
      ) : mode === 'confirm' ? (
        <div className="flex items-center justify-between py-1.5">
          <span className="text-[13px] text-muted-foreground">Delete this conversation?</span>
          <div className="flex gap-4">
            <button type="button" className="k-quiet !text-destructive" onClick={onDelete}>
              Delete
            </button>
            <button type="button" className="k-quiet" onClick={() => setMode('view')}>
              Keep
            </button>
          </div>
        </div>
      ) : (
        <div className="flex items-center gap-2 py-1.5">
          <span className="inline-block w-3 text-[9px] text-primary">{active ? '●' : ''}</span>
          <button
            type="button"
            onClick={onSelect}
            className={cn(
              'min-w-0 flex-1 truncate text-left text-[13px] transition-colors [transition-duration:180ms]',
              active ? 'text-foreground' : 'text-foreground/70 hover:text-foreground'
            )}
          >
            {session.title || 'Untitled'}
          </button>
          <div className="flex items-center gap-3 opacity-0 transition-opacity [transition-duration:180ms] group-hover:opacity-100 focus-within:opacity-100">
            <button type="button" className="k-quiet !text-[10px]" onClick={() => setMode('edit')}>
              Rename
            </button>
            <button type="button" className="k-quiet !text-[10px]" onClick={() => setMode('confirm')}>
              Delete
            </button>
            <span
              {...listeners}
              {...attributes}
              className="cursor-grab touch-none text-muted-foreground/50 active:cursor-grabbing"
              title="Drag into the conversation to open side by side"
              aria-label="Drag to open in split view"
            >
              <GripVertical className="h-3.5 w-3.5" />
            </span>
          </div>
        </div>
      )}
    </li>
  );
};

const Conversations: React.FC<Pick<KuroNavProps, 'sessions' | 'currentSessionId' | 'onNewChat' | 'onSelectSession' | 'onRenameSession' | 'onDeleteSession'>> = ({
  sessions,
  currentSessionId,
  onNewChat,
  onSelectSession,
  onRenameSession,
  onDeleteSession,
}) => (
  <div className="flex h-full flex-col">
    <button type="button" onClick={onNewChat} className="k-action mb-6 self-start !text-[11px]">
      New conversation
    </button>
    {sessions.length === 0 ? (
      <p className="text-[13px] text-muted-foreground">Nothing yet. Your first conversation will appear here.</p>
    ) : (
      <ul className="-mr-2 flex flex-col overflow-y-auto pr-2">
        {sessions.map((s) => (
          <SessionRow
            key={s.session_id}
            session={s}
            active={s.session_id === currentSessionId}
            onSelect={() => onSelectSession(s.session_id)}
            onRename={(t) => onRenameSession(s.session_id, t)}
            onDelete={() => onDeleteSession(s.session_id)}
          />
        ))}
      </ul>
    )}
    <p className="k-label mt-auto pt-6 !text-[10px] !text-muted-foreground/40">Drag a conversation into the view to open two side by side</p>
  </div>
);

/* ------------------------------------------------------------------ */
/* Memory                                                              */
/* ------------------------------------------------------------------ */

const CATEGORY_LABEL: Record<string, string> = {
  personal: 'About you',
  identity: 'About you',
  name: 'About you',
  project: 'What you are building',
  work: 'What you are building',
  building: 'What you are building',
  help: 'How Kuro helps',
  preference: 'Preferences',
  preferences: 'Preferences',
  learning: 'Learning',
  event: 'Moments',
  events: 'Moments',
  general: 'Context',
  memory: 'Context',
};

function labelFor(category: string) {
  return CATEGORY_LABEL[category?.toLowerCase()] ?? category?.replace(/[_-]/g, ' ').replace(/^\w/, (c) => c.toUpperCase()) ?? 'Context';
}

function when(ts: string) {
  if (!ts) return '';
  const d = new Date(ts);
  if (isNaN(d.getTime())) return '';
  return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
}

const Memory: React.FC<{ userId?: string; clerkApiRequest: ClerkApiRequestFn }> = ({ userId, clerkApiRequest }) => {
  const { memoryNodes, profile } = useExperience();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<StoredMemory[] | null>(null);
  const [status, setStatus] = useState<'idle' | 'loading' | 'error'>('idle');

  const search = useCallback(
    async (q: string) => {
      if (!userId) return;
      setStatus('loading');
      try {
        const res = await clerkApiRequest<{ query: string; results: StoredMemory[] }>('/retrieve-memory', 'post', {
          user_id: userId,
          query: q,
          top_k: 12,
        });
        setResults(res.results ?? []);
        setStatus('idle');
      } catch (e) {
        console.error('[kuro] retrieve-memory failed', e);
        setStatus('error');
      }
    },
    [userId, clerkApiRequest]
  );

  // Opening Memory asks Kuro what it knows about the person.
  useEffect(() => {
    if (results === null) search('who I am, what I am building, and what I asked Kuro to remember');
  }, [results, search]);

  const grouped = useMemo(() => {
    const map = new Map<string, StoredMemory[]>();
    (results ?? []).forEach((m) => {
      const k = labelFor(m.category);
      if (!map.has(k)) map.set(k, []);
      map.get(k)!.push(m);
    });
    return Array.from(map.entries());
  }, [results]);

  return (
    <div className="flex h-full flex-col">
      <p className="text-[13px] text-muted-foreground">
        {profile.name ? `What Kuro remembers about ${profile.name}.` : 'What Kuro remembers about you.'}
        {memoryNodes.length > 0 && ` ${memoryNodes.length} thing${memoryNodes.length === 1 ? '' : 's'} learned in this session.`}
      </p>

      <form
        className="mt-5"
        onSubmit={(e) => {
          e.preventDefault();
          if (query.trim()) search(query.trim());
        }}
      >
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask what Kuro remembers…"
          aria-label="Search memory"
          className="k-field w-full border-b border-foreground/20 bg-transparent py-2 text-[13px] text-foreground outline-none placeholder:text-muted-foreground/60 focus:border-foreground/50"
        />
      </form>

      <div className="-mr-2 mt-6 flex-1 overflow-y-auto pr-2">
        {status === 'loading' && results === null && <span className="k-label">Recalling</span>}
        {status === 'error' && <p className="text-[13px] text-muted-foreground">Memory is not reachable right now.</p>}
        {results !== null && results.length === 0 && status !== 'error' && (
          <p className="text-[13px] text-muted-foreground">
            Nothing here yet. Tell Kuro about yourself in conversation and it will hold on to what matters.
          </p>
        )}
        {grouped.map(([label, items]) => (
          <section key={label} className="mb-7">
            <h3 className="k-label mb-3 !text-[10px]">{label}</h3>
            <ul className="flex flex-col gap-3">
              {items.map((m, i) => (
                <li key={`${label}-${i}`} className="border-l border-foreground/15 pl-3">
                  <p className="text-[13px] leading-relaxed text-foreground/85">{m.text}</p>
                  {when(m.timestamp) && <span className="k-label !text-[10px] !text-muted-foreground/45">{when(m.timestamp)}</span>}
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </div>
  );
};

/* ------------------------------------------------------------------ */
/* Projects — honest                                                   */
/* ------------------------------------------------------------------ */

const Projects: React.FC = () => (
  <div className="flex h-full flex-col">
    <p className="text-[13px] text-muted-foreground">
      Projects will give Kuro a separate context for each thing you are building — its own memory, its own conversations.
    </p>
    <div className="mt-8 flex flex-col gap-3">
      <div className="flex items-center gap-3">
        <span className="inline-block h-1.5 w-1.5 rounded-full bg-primary/80" />
        <span className="text-[13px] text-foreground/85">Everything</span>
        <span className="k-label ml-auto !text-[10px] !text-muted-foreground/50">current</span>
      </div>
      <div className="ml-[3px] h-6 w-px k-hairline" />
      <p className="k-label !text-[10px] !text-muted-foreground/45">Not connected yet. For now Kuro keeps one shared memory across all conversations.</p>
    </div>
  </div>
);

/* ------------------------------------------------------------------ */
/* Settings                                                            */
/* ------------------------------------------------------------------ */

const Settings: React.FC<{ userEmail?: string; onSignOut: () => void }> = ({ userEmail, onSignOut }) => {
  const { profile, reducedMotion } = useExperience();
  const [name, setName] = useState(profile.name ?? '');
  const [saved, setSaved] = useState(false);

  useEffect(() => setName(profile.name ?? ''), [profile.name]);

  const save = async () => {
    const t = name.trim();
    if (!t || t === profile.name) return;
    await profile.saveName(t);
    setSaved(true);
    window.setTimeout(() => setSaved(false), 1400);
  };

  return (
    <div className="flex h-full flex-col gap-8">
      <div>
        <h3 className="k-label mb-3 !text-[10px]">What Kuro calls you</h3>
        <form
          className="flex items-baseline gap-4"
          onSubmit={(e) => {
            e.preventDefault();
            save();
          }}
        >
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            aria-label="Your name"
            className="k-field flex-1 border-b border-foreground/20 bg-transparent py-1.5 text-[14px] text-foreground outline-none focus:border-foreground/50"
          />
          <button type="submit" className="k-quiet" disabled={!name.trim() || name.trim() === profile.name}>
            {saved ? 'Saved' : 'Save'}
          </button>
        </form>
      </div>

      <div>
        <h3 className="k-label mb-3 !text-[10px]">Account</h3>
        <p className="text-[13px] text-foreground/80">{userEmail || '—'}</p>
      </div>

      <div>
        <h3 className="k-label mb-3 !text-[10px]">Motion</h3>
        <p className="text-[13px] text-muted-foreground">
          {reducedMotion ? 'Reduced — following your system preference.' : 'Full — following your system preference.'}
        </p>
      </div>

      <div className="mt-auto">
        <button type="button" onClick={onSignOut} className="k-quiet">
          Sign out
        </button>
      </div>
    </div>
  );
};

/* ------------------------------------------------------------------ */
/* Panel                                                               */
/* ------------------------------------------------------------------ */

export const KuroNav = memo<KuroNavProps>(function KuroNav(props) {
  const { navOpen, setNavOpen, reducedMotion, isMobile, profile } = useExperience();
  const [view, setView] = useState<NavView>('conversations');

  // Escape closes.
  useEffect(() => {
    if (!navOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setNavOpen(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [navOpen, setNavOpen]);

  const t = reducedMotion ? { duration: 0 } : { duration: DUR.interface, ease: EASE.out };
  const tExit = reducedMotion ? { duration: 0 } : { duration: DUR.interface * 0.7, ease: EASE.inOut };

  return (
    <AnimatePresence>
      {navOpen && (
        <React.Fragment key="nav">
          {/* Scrim: the conversation recedes, it does not disappear. */}
          <motion.div
            className="fixed inset-x-0 bottom-0 top-[60px] z-[24] bg-background/45"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, transition: tExit }}
            transition={t}
            onClick={() => setNavOpen(false)}
            aria-hidden="true"
          />
          <motion.aside
            // Opens beneath the top strip, so the Core / wordmark / Menu stay
            // where they are — the panel hangs from the system, it doesn't
            // replace it.
            className={cn(
              'fixed left-0 top-[60px] z-[25] flex h-[calc(100dvh-60px)] flex-col border-r border-border/60 bg-background/92 backdrop-blur-md',
              isMobile ? 'w-full border-r-0' : 'w-[360px]'
            )}
            initial={{ x: -18, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: -12, opacity: 0, transition: tExit }}
            transition={t}
            role="dialog"
            aria-label="Kuro navigation"
          >
            <div className="px-7 pt-4">
              <span className="k-label !text-[10px] !text-muted-foreground/60">{profile.name ? profile.name : 'You'}</span>
              <nav className="mt-5 flex flex-wrap gap-x-5 gap-y-2" aria-label="Sections">
                {VIEWS.map((v) => (
                  <button
                    key={v.id}
                    type="button"
                    onClick={() => setView(v.id)}
                    className={cn('k-quiet', view === v.id && '!text-foreground')}
                    aria-current={view === v.id ? 'page' : undefined}
                  >
                    {v.label}
                  </button>
                ))}
              </nav>
              <div className="k-hairline mt-5 h-px w-full" />
            </div>

            <div className="min-h-0 flex-1 px-7 pb-7 pt-6">
              <AnimatePresence mode="wait" initial={false}>
                <motion.div
                  key={view}
                  className="h-full"
                  initial={{ opacity: 0, y: reducedMotion ? 0 : 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: reducedMotion ? 0 : -3 }}
                  transition={reducedMotion ? { duration: 0 } : { duration: DUR.micro + 0.08, ease: EASE.out }}
                >
                  {view === 'conversations' && (
                    <Conversations
                      sessions={props.sessions}
                      currentSessionId={props.currentSessionId}
                      onNewChat={props.onNewChat}
                      onSelectSession={props.onSelectSession}
                      onRenameSession={props.onRenameSession}
                      onDeleteSession={props.onDeleteSession}
                    />
                  )}
                  {view === 'memory' && <Memory userId={profile.userId ?? undefined} clerkApiRequest={props.clerkApiRequest} />}
                  {view === 'projects' && <Projects />}
                  {view === 'settings' && <Settings userEmail={props.userEmail} onSignOut={props.onSignOut} />}
                </motion.div>
              </AnimatePresence>
            </div>
          </motion.aside>
        </React.Fragment>
      )}
    </AnimatePresence>
  );
});

export default KuroNav;
