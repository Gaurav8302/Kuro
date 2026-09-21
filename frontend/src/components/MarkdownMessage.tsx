import React, { useMemo, useState, memo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import 'highlight.js/styles/atom-one-dark.css';
import hljs from 'highlight.js';
import { Copy, Check, ChevronDown, ChevronUp } from 'lucide-react';
import { cn } from '@/lib/utils';

// Threshold (number of lines) beyond which code blocks become collapsible
const COLLAPSE_LINE_THRESHOLD = 14;

interface MarkdownMessageProps {
  // Content can be a string, object, or array (LLM tool responses, rich blocks, etc.)
  content: any;
}

// Extracted code block component to properly manage state (fixes React hooks violation)
interface CodeBlockProps {
  raw: string;
  language?: string;
  className?: string;
}

const CodeBlock = memo(({ raw, language, className = '' }: CodeBlockProps) => {
  const lines = useMemo(() => raw.split('\n'), [raw]);
  const isLong = lines.length > COLLAPSE_LINE_THRESHOLD;
  const [collapsed, setCollapsed] = useState(isLong);
  const [copied, setCopied] = useState(false);
  
  const hiddenCount = lines.length - COLLAPSE_LINE_THRESHOLD;

  const visibleHighlighted = useMemo(() => {
    const vRaw = collapsed ? lines.slice(0, COLLAPSE_LINE_THRESHOLD).join('\n') : raw;
    try {
      if (language && hljs.getLanguage(language)) {
        return hljs.highlight(vRaw, { language }).value;
      }
      return hljs.highlightAuto(vRaw).value;
    } catch {
      return vRaw.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    }
  }, [collapsed, lines, raw, language]);

  const visibleLines = useMemo(() => visibleHighlighted.split('\n'), [visibleHighlighted]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(raw);
    } catch {
      const textarea = document.createElement('textarea');
      textarea.value = raw;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="group/code relative my-3 overflow-hidden rounded-md border border-border bg-secondary/60">
      {/* Code block header */}
      <div className="flex items-center justify-between border-b border-border px-3 py-1.5">
        <span className="k-label !text-[10px]">{language ? language : 'code'}</span>
        <div className="flex gap-3 opacity-0 transition-opacity duration-150 group-hover/code:opacity-100 focus-within:opacity-100">
          <button type="button" onClick={handleCopy} className="k-quiet inline-flex items-center gap-1 !text-[10px]">
            {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
            {copied ? 'Copied' : 'Copy'}
          </button>
          {isLong && (
            <button type="button" onClick={() => setCollapsed((c) => !c)} className="k-quiet inline-flex items-center gap-1 !text-[10px]">
              {collapsed ? <ChevronDown className="h-3 w-3" /> : <ChevronUp className="h-3 w-3" />}
              {collapsed ? `Expand (${hiddenCount})` : 'Collapse'}
            </button>
          )}
        </div>
      </div>

      <pre className="max-h-[32rem] overflow-auto p-4 font-mono text-[12.5px] leading-relaxed" aria-live="polite">
        <code className={cn(className, 'text-foreground/90')}>
          {visibleLines.map((l, i) => (
            <span key={i} className="code-line block" dangerouslySetInnerHTML={{ __html: l || ' ' }} />
          ))}
        </code>
      </pre>
      {collapsed && (
        <div className="k-label px-4 pb-2 !text-[10px] !text-muted-foreground/60">
          {hiddenCount} more line{hiddenCount === 1 ? '' : 's'}
        </div>
      )}
    </div>
  );
});

CodeBlock.displayName = 'CodeBlock';

// Recursively coerce arbitrary content (string | object | array) into Markdown text.
// If we detect a code payload + language, we wrap with triple backticks.
function coerceToMarkdown(input: any): string {
  const fence = (code: string, lang?: string) => `\n\n\`\`\`${lang || ''}\n${code}\n\`\`\`\n\n`;

  const asString = (val: any): string => {
    if (val == null) return '';
    if (typeof val === 'string') return val;
    if (typeof val === 'number' || typeof val === 'boolean') return String(val);
    // If it looks like a code object
    if (typeof val === 'object') {
      const lang = (val.language || val.lang || val.programming_language || '').toString() || undefined;
      const code = val.code ?? val.text ?? val.value ?? val.content ?? val.body;
      if (typeof code === 'string') {
        // If it already contains backticks, return as-is
        if (/```/.test(code)) return code;
        return fence(code, lang);
      }
      if (Array.isArray(code)) {
        const joined = code.map(asString).filter(Boolean).join('\n');
        return fence(joined, lang);
      }
      // Other common shapes (e.g., OpenAI tool messages: { parts: [{text: ...}] })
      if (Array.isArray(val.parts)) {
        const joined = val.parts.map(asString).filter(Boolean).join('\n\n');
        return joined;
      }
      if (val.props && val.props.children) {
        return asString(val.props.children);
      }
      // Last resort: JSON dump in a code fence for debugging readability
      try { return fence(JSON.stringify(val, null, 2), 'json'); } catch { return String(val); }
    }
    // Arrays handled below
    return String(val);
  };

  if (typeof input === 'string') {
    return input;
  }
  if (Array.isArray(input)) {
    return input.map(asString).filter(Boolean).join('\n\n');
  }
  return asString(input);
}

// Convert standalone **Heading** lines to level-3 headings & collapse excessive blank lines
function preprocess(raw: string): string {
  return raw
    .split(/\r?\n/)
    .map(line => {
      const trimmed = line.trim();
      if (/^\*\*(.+?)\*\*$/.test(trimmed)) {
        return `### ${trimmed.replace(/^\*\*(.+)\*\*$/, '$1')}`;
      }
      return line;
    })
    .join('\n')
    .replace(/\n{3,}/g, '\n\n');
}

export const MarkdownMessage: React.FC<MarkdownMessageProps> = memo(({ content }) => {
  const prepared = useMemo(() => {
    const normalized = coerceToMarkdown(content);
    return preprocess(normalized);
  }, [content]);

  return (
    <div className="markdown-body max-w-none leading-relaxed">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
  // Note: we intentionally do NOT use rehype-highlight here because we
  // perform custom highlight.js rendering in our code component below.
  // Using both results in children becoming React elements instead of a
  // raw string, which leads to "[object Object]" appearing.
        components={{
          p: ({ node, ...props }: any) => <p className="whitespace-pre-line" {...props} />,
          strong: (props: any) => <strong className="font-medium text-foreground" {...props} />,
          code(codeProps: any) {
            const { inline, className = '', children, node, ...props } = codeProps;
            // Safely extract raw text from children which may be a string, array, or elements
            const extractRaw = (ch: any): string => {
              if (typeof ch === 'string') return ch;
              if (Array.isArray(ch)) {
                return ch
                  .map((c: any) =>
                    typeof c === 'string'
                      ? c
                      : c?.props?.children
                      ?? (typeof c === 'object' && c && 'value' in c ? c.value : '')
                  )
                  .join('');
              }
              if (node && Array.isArray((node as any).children)) {
                return (node as any).children.map((n: any) => n.value ?? '').join('');
              }
              try { return String(ch); } catch { return ''; }
            };

            const raw = extractRaw(children).replace(/\n+$/, '');
            if (inline) {
              return (
                <code className="rounded bg-secondary px-1.5 py-0.5 font-mono text-[0.88em] text-foreground/90" {...props}>
                  {raw}
                </code>
              );
            }
            
            // Extract language from className
            const langMatch = /language-([a-z0-9]+)/i.exec(className);
            const language = langMatch?.[1];
            
            // Use extracted CodeBlock component (properly manages useState)
            return <CodeBlock raw={raw} language={language} className={className} />;
          },
          blockquote: (p) => <blockquote className="my-3 border-l border-foreground/25 pl-4 text-muted-foreground" {...p} />,
          hr: (p: any) => <hr className="my-6 border-border" {...p} />,
        }}
      >
        {prepared}
      </ReactMarkdown>
    </div>
  );
});

MarkdownMessage.displayName = 'MarkdownMessage';

export default MarkdownMessage;
