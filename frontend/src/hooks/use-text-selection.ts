import { useState, useEffect, useCallback, useRef } from 'react';

export interface TextSelection {
  text: string;
  /** Surrounding context (~100 tokens worth) from the parent message */
  context: string;
  /** Position for anchoring the popup */
  x: number;
  y: number;
}

/**
 * Detects text selections inside a container and returns the selected text,
 * surrounding context, and cursor position for popup placement.
 *
 * The hook listens for `mouseup` and `touchend` events. When the selection
 * falls inside `containerRef`, a `TextSelection` is emitted. Clicking
 * elsewhere or collapsing the selection clears it.
 */
export function useTextSelection(containerRef: React.RefObject<HTMLElement | null>) {
  const [selection, setSelection] = useState<TextSelection | null>(null);
  // Track whether we're inside a mousedown so we can ignore stale events
  const isMouseDownRef = useRef(false);

  /**
   * Extract ~100 tokens (roughly 400 characters) of surrounding context
   * from the nearest message-level text node ancestor.
   */
  const getContext = useCallback((sel: Selection): string => {
    const anchor = sel.anchorNode;
    if (!anchor) return '';

    // Walk up to find the message bubble container (max 10 levels)
    let node: HTMLElement | null = anchor.nodeType === Node.TEXT_NODE
      ? anchor.parentElement
      : anchor as HTMLElement;

    for (let i = 0; i < 10 && node; i++) {
      // The message content wrapper typically has the markdown-body class
      if (node.classList?.contains('markdown-body')) break;
      node = node.parentElement;
    }

    const fullText = node?.textContent ?? '';
    const selectedText = sel.toString();
    const idx = fullText.indexOf(selectedText);
    if (idx === -1) return fullText.slice(0, 400);

    const start = Math.max(0, idx - 200);
    const end = Math.min(fullText.length, idx + selectedText.length + 200);
    return fullText.slice(start, end);
  }, []);

  const handleSelectionChange = useCallback(() => {
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed || !sel.toString().trim()) {
      // Don't clear immediately on mousedown — wait for mouseup
      if (!isMouseDownRef.current) {
        setSelection(null);
      }
      return;
    }

    // Selection must be inside our container
    const container = containerRef.current;
    if (!container) return;

    const anchorNode = sel.anchorNode;
    if (!anchorNode || !container.contains(anchorNode)) {
      return;
    }

    // Only trigger on assistant messages — check that the selection is inside
    // an element that renders AI replies (role !== 'user')
    let el: HTMLElement | null = anchorNode.nodeType === Node.TEXT_NODE
      ? anchorNode.parentElement
      : anchorNode as HTMLElement;
    let insideAssistant = false;
    while (el && el !== container) {
      // The message items rendered by MessageList don't have explicit role
      // markers, but assistant messages render through MarkdownMessage which
      // has the `markdown-body` class.
      if (el.classList?.contains('markdown-body')) {
        insideAssistant = true;
        break;
      }
      el = el.parentElement;
    }
    if (!insideAssistant) return;

    const text = sel.toString().trim();
    if (!text) return;

    const range = sel.getRangeAt(0);
    const rect = range.getBoundingClientRect();

    setSelection({
      text,
      context: getContext(sel),
      x: rect.left + rect.width / 2,
      y: rect.top,
    });
  }, [containerRef, getContext]);

  useEffect(() => {
    const onMouseDown = () => {
      isMouseDownRef.current = true;
    };
    const onMouseUp = () => {
      isMouseDownRef.current = false;
      // Small delay so the browser finalises the selection
      setTimeout(handleSelectionChange, 10);
    };
    const onTouchEnd = () => {
      isMouseDownRef.current = false;
      setTimeout(handleSelectionChange, 10);
    };

    document.addEventListener('mousedown', onMouseDown, true);
    document.addEventListener('mouseup', onMouseUp, true);
    document.addEventListener('touchend', onTouchEnd, true);

    return () => {
      document.removeEventListener('mousedown', onMouseDown, true);
      document.removeEventListener('mouseup', onMouseUp, true);
      document.removeEventListener('touchend', onTouchEnd, true);
    };
  }, [handleSelectionChange]);

  const clearSelection = useCallback(() => {
    setSelection(null);
    window.getSelection()?.removeAllRanges();
  }, []);

  return { selection, clearSelection };
}
