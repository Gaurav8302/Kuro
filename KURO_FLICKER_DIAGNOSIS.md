# Kuro Flicker Diagnosis

Date: 2026-09-21  
Scope: Diagnose chat UI flicker/jump after response completion. **No code changes.**

Recording referenced: `C:\Users\wanna\Videos\Screen Recordings\Screen Recording 2026-09-21 112525.mp4` (~11.7s, 1918×918).  
Frame-sampled at 2 fps for visual confirmation (see Observed Behavior).

---

## Observed Behavior

From the recording (frame sequence at ~2 fps):

1. User sends “i want to learn DSA”; typing pill **KURO IS PROCESSING…** is visible; input shows **Kuro is responding…** (frames ~10–11).
2. Typing pill unmounts; assistant reply appears locally; input **still** shows responding + spinner (frames ~12–13) — local `setMessages` before `finally` clears loading.
3. Next frames: same reply content, but **timestamps change** from local **11:25 AM** → server **05:55 AM** (user + assistant), older history scroll/content shifts, input flips to **Type a message…** (frame ~14).

That timestamp flip is direct visual proof of the post-completion history replace remounting the list — not mid-stream jitter (there is no streaming).

---

## Reproduction

1. Open Kuro chat with an existing session that already has messages (flicker is more obvious with prior history).
2. Send a normal message.
3. Wait until the assistant reply appears.
4. Watch the message list at the moment loading ends: bubbles briefly re-appear / shift, and the viewport may jump.

Harder to notice on an empty first-turn chat (few messages, less remount animation).

---

## Timeline

Kuro does **not** stream. `POST /chat` returns one full JSON body. Lifecycle in `frontend/src/hooks/use-chat-panel.ts` → `sendMessage`:

```text
T0  setIsLoading(true); setIsTyping(true)
T1  setMessages([...prev, optimisticUser])     // local user bubble
    scrollToBottom()                           // explicit
T1b useEffect([messages]) → scrollToBottom     // second scroll
T1c useEffect([isTyping]) → scrollToBottom     // third scroll (typing on)

    … wait for POST /chat …

T2  setMessages([...prev, localAssistant])     // local assistant bubble
    setIsTyping(false)                         // typing indicator unmounts
    scrollToBottom()                           // explicit again
T2b useEffect([messages]) → scrollToBottom
T2c useEffect([isTyping]) may run (typing off; no scroll because isTyping false)

T3  GET /chat/{session_id}                     // history refresh
    setMessages(mappedMessages)                // FULL LIST REPLACE
T3b useEffect([messages]) → scrollToBottom     // scroll again
    // MessageList keys change → remount → fade-in-up restarts on every bubble

T4  finally: setIsLoading(false)               // input sending/placeholder flip
    // optional auto-rename → onSessionsChanged (sidebar title), not the main jump
```

There is no temporary streaming token buffer. There **is** a temporary local assistant message followed by a full session reload.

---

## Root Cause

### Confirmed (primary)

**After painting the assistant reply locally, the UI fetches the full session history and replaces `messages` wholesale.**

Evidence (`use-chat-panel.ts`):

```374:399:frontend/src/hooks/use-chat-panel.ts
        // Add AI response
        setMessages((prev) => [
          ...prev,
          {
            message: response.reply,
            ...
          },
        ]);
        setIsTyping(false);
        scrollToBottom();

        // Refresh from backend to ensure sync
        const data = await clerkApiRequest<{ history: any[] }>(
          `/chat/${sessionToUse.session_id}`,
          'get'
        );
        const mappedMessages = mapHistory(data.history);
        setMessages(mappedMessages);
```

That is exactly the anti-pattern called out in the brief:

```text
Response → Update UI → Persist (server) → Fetch entire session → Replace UI state
```

### Confirmed (why the replace is visible)

**Message React keys are unstable across the local → server transition.**

```93:93:frontend/src/components/MessageList.tsx
        <React.Fragment key={message.timestamp + idx}>
```

* Local messages use `new Date().toISOString()` (client clock, ISO string).
* History reload uses Mongo `timestamp` from the API (different value/format for the same turn).
* `mapHistory` also splits each DB turn into separate user/assistant rows that **share** the server timestamp, while local user/assistant rows had **different** client timestamps.

So after `setMessages(mappedMessages)`, every key changes. React tears down and remounts the message items.

### Confirmed (why remount looks like flicker)

Remounted items always run enter animation:

```35:41:frontend/src/components/MessageList.tsx
  <div
    className="transform-gpu animate-fade-in-up"
    ...
    style={{
      animationDelay: shouldReduceAnimations ? '0ms' : `${Math.min(index * 30, 150)}ms`,
      animationFillMode: 'both'
    }}
```

`animate-fade-in-up` starts at `opacity: 0` + `translateY(10px)` (`frontend/src/styles/global.css`). Remounting the whole list makes the conversation briefly blank/shift and animate back — a classic flicker.

### Strongly suspected (amplifiers, not the root)

1. **Multiple `scrollIntoView({ behavior: 'smooth' })` calls** around the same completion (`scrollToBottom` + `useEffect([messages])`). Smooth scroll competing with remount/layout can add a secondary jump.
2. **Typing indicator unmount** (`TypingIndicator` returns `null` when `!isTyping`) removes a sizable “KURO IS PROCESSING…” card at the same moment the assistant bubble appears — a one-frame height change at the bottom.
3. **Input `sending` / placeholder flip** when `isLoading`/`isTyping` clear — small footer text change; unlikely the main jump.

### Confirmed from recording

* Timestamp labels jump from client-local **11:25 AM** to server **05:55 AM** in the same turn — matches `setMessages(mappedMessages)` after GET history.
* Typing indicator gone before input leaves “responding” — matches `setIsTyping(false)` before `finally { setIsLoading(false) }`.
* Sidebar (“Buddy”) stable; jump is in the message list / scroll area, not a full-app remount.

### Unconfirmed / secondary

* Whether scrollbar gutter width contributes (possible but secondary).
* Whether auto-title rename’s `onSessionsChanged` coincides visually (sidebar only; not visible in this clip).

---

## Contributing Factors

| Factor | Role |
| --- | --- |
| Full history replace after local paint | Primary cause of duplicate final state |
| `key={timestamp + index}` | Forces remount when timestamps change |
| `animate-fade-in-up` on every MessageItem | Makes remounts visible as flicker |
| Explicit + effect-driven smooth scrolls | Extra viewport motion after remount |
| Typing indicator height vs reply height | Bottom layout shift at completion |
| No stable message IDs from API | Encourages timestamp/index keys |

Not causes:

* Streaming token replacement (no streaming).
* React Strict Mode double-mount (`main.tsx` does not wrap in `<StrictMode>`).
* Entire app remount / route change.
* CSS `overflow: hidden` hacks (none required to explain this).

---

## Relevant Files

| File | Role |
| --- | --- |
| `frontend/src/hooks/use-chat-panel.ts` | Local append → history refetch → `setMessages` replace; scroll effects |
| `frontend/src/components/MessageList.tsx` | Unstable keys; fade-in-up on every item |
| `frontend/src/components/TypingIndicator.tsx` | Mount/unmount at completion |
| `frontend/src/components/ChatPanel.tsx` | Wires hook → content + input sending state |
| `frontend/src/components/kuro/KuroChatContent.tsx` | Uses `MessageList` (not `KuroMessageList`) |
| `frontend/src/styles/global.css` | `fade-in-up` keyframes (opacity 0 → 1) |
| `backend/memory/chat_database.py` | Persist + history timestamps used on refetch |

`KuroMessageList.tsx` has a similar key pattern and Framer `layout`/`AnimatePresence`, but the live panel path uses `MessageList` via `KuroChatContent`.

---

## Recommended Fix

Smallest clean fix (do **not** implement in this phase):

### 1. Stop replacing the list after a successful send (primary)

After `POST /chat` succeeds and local assistant state is set:

* Persist is already done server-side inside `/chat`.
* **Do not** immediately `GET /chat/{session}` and `setMessages(mappedMessages)`.

Keep the optimistic/local messages as the UI source of truth for that turn. Refresh history only on session switch / explicit reload.

### 2. If a sync is still desired, merge — don’t remount

* Give messages stable ids (client uuid, or backend message `_id` / sequence).
* Key by that id: `key={message.id}`.
* Update the existing assistant row in place; never rebuild the whole array from a refetch for the same turn.

### 3. Animate only new messages

* Do not put enter animation on every remounted row.
* Gate animation to first mount of a given id (or only the newest index).

### 4. Collapse scroll triggers

* Prefer one scroll path (either the `messages` effect **or** explicit `scrollToBottom` in `sendMessage`, not both).
* Prefer `behavior: 'auto'` for the post-completion sync scroll if any remain.

Do **not** “fix” this with delays, forced `min-height`, or global animation disables.

---

## Development vs Production

**Affects production.**  

Strict Mode is not enabled. The refetch + key remount + CSS enter animation path runs whenever `sendMessage` completes successfully in any build.

---

## Diagnosis Conclusion

| Question | Answer |
| --- | --- |
| Exact root cause | Local assistant paint followed by full history `setMessages` replace; unstable timestamp keys remount the list and restart `fade-in-up`. |
| Matches recording? | Yes — post-completion jump; frame ~14 shows 11:25→05:55 timestamp swap from history replace. |
| Streaming? | No. |
| Dev-only? | No. |
| Minimal fix | Remove post-send history replace (or merge by stable id); stable keys; don’t re-run enter animation on remount; reduce duplicate scrolls. |

Diagnosis-only phase complete. No UI/code fix applied.
