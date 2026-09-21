/**
 * The Kuro experience is one environment that changes state.
 *
 *   ORIGIN → (entering) → IDENTITY → (connecting) → AWAKENING → ONBOARDING → GENESIS → CHAT
 *
 * Returning users:  ORIGIN → (recognition) → CHAT
 *
 * Stages are explicit. There is no combination of booleans that can put the
 * environment in an impossible state.
 */
export type Stage =
  | 'origin'
  | 'entering'
  | 'identity'
  | 'connecting'
  | 'awakening'
  | 'onboarding'
  | 'genesis'
  | 'chat'
  | 'lost';

/**
 * How the Core is behaving right now. Modes are visually related to one
 * another; each one exists because something is happening.
 *
 *   idle        nothing is happening — nearly still
 *   attention   the user is present (pointer, focus, message received)
 *   thinking    Kuro is generating
 *   responding  a reply just arrived (one-shot settle)
 *   connecting  identity / session is being established
 *   genesis     memory is being formed
 */
export type CoreMode =
  | 'idle'
  | 'attention'
  | 'thinking'
  | 'responding'
  | 'connecting'
  | 'genesis';

export interface MemoryNode {
  id: string;
  label: string;
  /** 'name' | 'building' | 'help' | 'remember' | 'memory' */
  kind: string;
}

/**
 * Where the Core lives for each stage, in viewport-relative units.
 *   x, y  — 0..1 of viewport
 *   size  — CSS px on desktop; mobile applies a factor
 */
export interface CoreAnchor {
  x: number;
  y: number;
  size: number;
}

export const CORE_ANCHORS: Record<Stage, CoreAnchor> = {
  origin: { x: 0.5, y: 0.5, size: 264 },
  entering: { x: 0.5, y: 0.5, size: 360 },
  identity: { x: 0.5, y: 0.3, size: 132 },
  connecting: { x: 0.5, y: 0.5, size: 180 },
  awakening: { x: 0.5, y: 0.5, size: 200 },
  onboarding: { x: 0.5, y: 0.26, size: 112 },
  genesis: { x: 0.5, y: 0.5, size: 220 },
  chat: { x: 0, y: 0, size: 26 },
  lost: { x: 0.5, y: 0.42, size: 160 },
};

/** Fixed pixel offset for anchors expressed at (0,0): the chat header slot. */
export const CHAT_CORE_OFFSET = { x: 40, y: 30 };

export const STAGE_LABEL: Record<Stage, string> = {
  origin: 'ORIGIN',
  entering: 'ORIGIN',
  identity: 'IDENTITY',
  connecting: 'IDENTITY',
  awakening: 'AWAKENING',
  onboarding: 'AWAKENING',
  genesis: 'MEMORY',
  chat: 'KURO',
  lost: 'UNMAPPED',
};

/** The rail shows the journey as a sequence of five places. */
export const JOURNEY: Array<{ id: string; label: string; stages: Stage[] }> = [
  { id: 'origin', label: 'ORIGIN', stages: ['origin', 'entering'] },
  { id: 'identity', label: 'IDENTITY', stages: ['identity', 'connecting'] },
  { id: 'awakening', label: 'AWAKENING', stages: ['awakening', 'onboarding'] },
  { id: 'memory', label: 'MEMORY', stages: ['genesis'] },
  { id: 'kuro', label: 'KURO', stages: ['chat'] },
];
