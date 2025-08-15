import React, { useMemo, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/atom-one-dark.css';
import hljs from 'highlight.js';
import { motion } from 'framer-motion';
import { Copy, Check, ChevronDown, ChevronUp } from 'lucide-react';
import { cn } from '@/lib/utils';

// Threshold (number of lines) beyond which code blocks become collapsible
const COLLAPSE_LINE_THRESHOLD = 14;

interface MarkdownMessageProps {
  // Content can be a string, object, or array (LLM tool responses, rich blocks, etc.)
  content: any;
}

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

export const MarkdownMessage: React.FC<MarkdownMessageProps> = ({ content }) => {
  const prepared = useMemo(() => {
    const normalized = coerceToMarkdown(content);
    return preprocess(normalized);
  }, [content]);

  return (
    <div className="markdown-body prose prose-invert max-w-none text-sm leading-relaxed font-space">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={{
          p: ({ node, ...props }: any) => <p className="mb-3 last:mb-0 text-holo-cyan-100" {...props} />,
          h1: (props: any) => <h1 className="mt-4 mb-2 text-2xl font-bold border-b border-holo-cyan-500/30 pb-1 text-holo-cyan-300 text-holo-glow font-orbitron" {...props} />,
          h2: (props: any) => <h2 className="mt-4 mb-2 text-xl font-bold text-holo-cyan-300 text-holo-glow font-orbitron" {...props} />,
          h3: (props: any) => <h3 className="mt-3 mb-2 text-lg font-semibold text-holo-cyan-300 font-rajdhani" {...props} />,
          ul: (props: any) => <ul className="list-disc ml-5 mb-3 space-y-1 marker:text-holo-cyan-400" {...props} />,
          ol: (props: any) => <ol className="list-decimal ml-5 mb-3 space-y-1 marker:text-holo-cyan-400" {...props} />,
          li: (props: any) => <li className="marker:text-holo-cyan-400/60 text-holo-cyan-100" {...props} />,
          strong: (props: any) => <strong className="font-semibold text-holo-cyan-200 text-holo-glow" {...props} />,
          code(codeProps: any) {
            const { inline, className = '', children, ...props } = codeProps;
            const raw = String(children).replace(/\n+$/, '');
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
            const lines = raw.split('\n');
            const isLong = lines.length > COLLAPSE_LINE_THRESHOLD;
            // local component state for collapse
            const [collapsed, setCollapsed] = useState(isLong);
            const visibleContent = collapsed ? lines.slice(0, COLLAPSE_LINE_THRESHOLD).join('\n') : raw;
            const hiddenCount = lines.length - COLLAPSE_LINE_THRESHOLD;

            const handleCopy = async () => {
              try {
                await navigator.clipboard.writeText(raw);
              } catch (e) {
                // Fallback
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

            const langMatch = /language-([a-z0-9]+)/i.exec(className);
            const language = langMatch?.[1];
            let highlighted: string;
            try {
              if (language && hljs.getLanguage(language)) {
                highlighted = hljs.highlight(raw, { language }).value;
              } else {
                highlighted = hljs.highlightAuto(raw).value;
              }
            } catch {
              highlighted = raw
                .replace(/&/g,'&amp;')
                .replace(/</g,'&lt;')
                .replace(/>/g,'&gt;');
            }

            const visibleHighlighted = (() => {
              const vRaw = collapsed ? lines.slice(0, COLLAPSE_LINE_THRESHOLD).join('\n') : raw;
              let vHighlighted: string;
              try {
                if (language && hljs.getLanguage(language)) {
                  vHighlighted = hljs.highlight(vRaw, { language }).value;
                } else {
                  vHighlighted = hljs.highlightAuto(vRaw).value;
                }
              } catch { vHighlighted = vRaw; }
              return vHighlighted;
            })();

            const visibleLines = visibleHighlighted.split('\n');
            const [copied, setCopied] = useState(false);

            return (
              <motion.div 
                className="group/code relative border border-holo-cyan-400/30 rounded-lg bg-black/40 backdrop-blur-md overflow-hidden"
                whileHover={{ scale: 1.01 }}
                transition={{ duration: 0.2 }}
              >
                {/* Code block header */}
                <div className="flex items-center justify-between px-3 py-2 bg-holo-cyan-500/10 border-b border-holo-cyan-400/20">
                  <span className="text-xs text-holo-cyan-400 font-orbitron tracking-wider">
                    {language ? language.toUpperCase() : 'CODE'}
                  </span>
                  <div className="flex gap-1 opacity-0 group-hover/code:opacity-100 transition-opacity">
                    <motion.button
                    type="button"
                    onClick={handleCopy}
                    className="px-2 h-6 text-[10px] rounded bg-holo-cyan-500/20 hover:bg-holo-cyan-500/30 text-holo-cyan-300 border border-holo-cyan-400/30 font-orbitron tracking-wide hover:shadow-holo-glow transition-all duration-300"
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
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
                  </motion.button>
                  {isLong && (
                    <motion.button
                      type="button"
                      onClick={() => setCollapsed(c => !c)}
                      className="px-2 h-6 text-[10px] rounded bg-holo-blue-500/20 hover:bg-holo-blue-500/30 text-holo-blue-300 border border-holo-blue-400/30 font-orbitron tracking-wide hover:shadow-holo-blue transition-all duration-300"
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
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
                    </motion.button>
                  )}
                  </div>
                </div>
                
                <pre className="p-4 overflow-auto max-h-[32rem] text-xs with-line-numbers bg-black/20 font-orbitron" aria-live="polite">
                  <code className={cn(className, "text-holo-cyan-300")} {...props}>
                    {visibleLines.map((l, i) => (
                      <motion.span 
                        key={i} 
                        className="code-line block hover:bg-holo-cyan-500/10 transition-colors duration-200" 
                        dangerouslySetInnerHTML={{ __html: l || ' ' }}
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: i * 0.02, duration: 0.3 }}
                      />
                    ))}
                  </code>
                </pre>
                {collapsed && (
                  <div className="text-[10px] px-4 pb-2 text-holo-cyan-400/50 font-orbitron tracking-wide bg-holo-cyan-500/5">
                    TRUNCATED ({hiddenCount} MORE LINE{hiddenCount === 1 ? '' : 'S'})
                  </div>
                )}
              </motion.div>
            );
          },
          blockquote: (p) => (
            <blockquote 
              className="border-l-4 border-holo-purple-400/50 pl-4 italic opacity-90 mb-3 bg-holo-purple-500/10 py-2 rounded-r-lg text-holo-purple-200" 
              {...p} 
            />
          ),
          hr: (p: any) => (
            <motion.hr 
              className="my-6 border-holo-cyan-500/30 border-t-2"
              initial={{ scaleX: 0 }}
              animate={{ scaleX: 1 }}
              transition={{ duration: 0.5 }}
              {...p} 
            />
          )
        }}
      >
        {prepared}
      </ReactMarkdown>
    </div>
  );
};

export default MarkdownMessage;
