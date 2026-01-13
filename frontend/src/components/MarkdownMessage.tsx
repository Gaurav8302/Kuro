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
    <div className="group/code relative border border-holo-cyan-400/30 rounded-lg bg-black/40 backdrop-blur-md overflow-hidden transform-gpu transition-transform duration-150 hover:scale-[1.005]">
      {/* Code block header */}
      <div className="flex items-center justify-between px-3 py-2 bg-holo-cyan-500/10 border-b border-holo-cyan-400/20">
        <span className="text-xs text-holo-cyan-400 font-orbitron tracking-wider">
          {language ? language.toUpperCase() : 'CODE'}
        </span>
        <div className="flex gap-1 opacity-0 group-hover/code:opacity-100 transition-opacity duration-150">
          <button
            type="button"
            onClick={handleCopy}
            className="px-2 h-6 text-[10px] rounded bg-holo-cyan-500/20 hover:bg-holo-cyan-500/30 text-holo-cyan-300 border border-holo-cyan-400/30 font-orbitron tracking-wide hover:shadow-holo-glow transition-all duration-150 transform-gpu hover:scale-105 active:scale-95"
          >
            {copied ? (
              <>
                <Check className="w-3 h-3 mr-1 inline" />
                COPIED
              </>
            ) : (
              <>
                <Copy className="w-3 h-3 mr-1 inline" />
                COPY
              </>
            )}
          </button>
          {isLong && (
            <button
              type="button"
              onClick={() => setCollapsed(c => !c)}
              className="px-2 h-6 text-[10px] rounded bg-holo-blue-500/20 hover:bg-holo-blue-500/30 text-holo-blue-300 border border-holo-blue-400/30 font-orbitron tracking-wide hover:shadow-holo-blue transition-all duration-150 transform-gpu hover:scale-105 active:scale-95"
            >
              {collapsed ? (
                <>
                  <ChevronDown className="w-3 h-3 mr-1 inline" />
                  EXPAND ({hiddenCount})
                </>
              ) : (
                <>
                  <ChevronUp className="w-3 h-3 mr-1 inline" />
                  COLLAPSE
                </>
              )}
            </button>
          )}
        </div>
      </div>
      
      <pre className="p-4 overflow-auto max-h-[32rem] text-xs with-line-numbers bg-black/20 font-orbitron" aria-live="polite">
        <code className={cn(className, "text-holo-cyan-300")}>
          {visibleLines.map((l, i) => (
            <span 
              key={i} 
              className="code-line block hover:bg-holo-cyan-500/10 transition-colors duration-150" 
              dangerouslySetInnerHTML={{ __html: l || ' ' }}
            />
          ))}
        </code>
      </pre>
      {collapsed && (
        <div className="text-[10px] px-4 pb-2 text-holo-cyan-400/50 font-orbitron tracking-wide bg-holo-cyan-500/5">
          TRUNCATED ({hiddenCount} MORE LINE{hiddenCount === 1 ? '' : 'S'})
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
    <div className="markdown-body prose prose-invert max-w-none text-sm leading-relaxed font-space">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
  // Note: we intentionally do NOT use rehype-highlight here because we
  // perform custom highlight.js rendering in our code component below.
  // Using both results in children becoming React elements instead of a
  // raw string, which leads to "[object Object]" appearing.
        components={{
          p: ({ node, ...props }: any) => <p className="mb-3 last:mb-0 text-holo-cyan-100 whitespace-pre-line" {...props} />,
          h1: (props: any) => <h1 className="mt-4 mb-2 text-2xl font-bold border-b border-holo-cyan-500/30 pb-1 text-holo-cyan-300 text-holo-glow font-orbitron" {...props} />,
          h2: (props: any) => <h2 className="mt-4 mb-2 text-xl font-bold text-holo-cyan-300 text-holo-glow font-orbitron" {...props} />,
          h3: (props: any) => <h3 className="mt-3 mb-2 text-lg font-semibold text-holo-cyan-300 font-rajdhani" {...props} />,
          ul: (props: any) => <ul className="list-disc ml-5 mb-3 space-y-1 marker:text-holo-cyan-400" {...props} />,
          ol: (props: any) => <ol className="list-decimal ml-5 mb-3 space-y-1 marker:text-holo-cyan-400" {...props} />,
          li: (props: any) => <li className="marker:text-holo-cyan-400/60 text-holo-cyan-100" {...props} />,
          strong: (props: any) => <strong className="font-semibold text-holo-cyan-200 text-holo-glow" {...props} />,
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
                <code 
                  className="px-2 py-1 rounded bg-holo-cyan-500/20 text-holo-cyan-300 font-orbitron border border-holo-cyan-400/30 text-holo-glow" 
                  {...props}
                >
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
          blockquote: (p) => (
            <blockquote 
              className="border-l-4 border-holo-purple-400/50 pl-4 italic opacity-90 mb-3 bg-holo-purple-500/10 py-2 rounded-r-lg text-holo-purple-200" 
              {...p} 
            />
          ),
          hr: (p: any) => (
            <hr 
              className="my-6 border-holo-cyan-500/30 border-t-2 animate-[shimmer_0.5s_ease-out]"
              {...p} 
            />
          )
        }}
      >
        {prepared}
      </ReactMarkdown>
    </div>
  );
});

MarkdownMessage.displayName = 'MarkdownMessage';

export default MarkdownMessage;
