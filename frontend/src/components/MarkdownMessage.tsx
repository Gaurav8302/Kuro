import React, { useMemo, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github-dark.css';
import hljs from 'highlight.js';

// Threshold (number of lines) beyond which code blocks become collapsible
const COLLAPSE_LINE_THRESHOLD = 14;

interface MarkdownMessageProps {
  content: string;
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
  const prepared = useMemo(() => preprocess(content), [content]);

  return (
    <div className="markdown-body prose prose-invert max-w-none text-sm leading-relaxed">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={{
          p: ({ node, ...props }) => <p className="mb-3 last:mb-0" {...props} />,
          h1: (p) => <h1 className="mt-4 mb-2 text-2xl font-bold border-b border-border pb-1" {...p} />,
          h2: (p) => <h2 className="mt-4 mb-2 text-xl font-bold" {...p} />,
          h3: (p) => <h3 className="mt-3 mb-2 text-lg font-semibold" {...p} />,
          ul: (p) => <ul className="list-disc ml-5 mb-3 space-y-1" {...p} />,
          ol: (p) => <ol className="list-decimal ml-5 mb-3 space-y-1" {...p} />,
          li: (p) => <li className="marker:text-muted-foreground" {...p} />,
          strong: (p) => <strong className="font-semibold text-foreground" {...p} />,
          code(codeProps: any) {
            const { inline, className = '', children, ...props } = codeProps;
            const raw = String(children).replace(/\n+$/, '');
            if (inline) {
              return <code className="px-1 py-0.5 rounded bg-muted text-primary font-mono" {...props}>{raw}</code>;
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
              <div className="group/code relative border border-border rounded-md bg-[#0f1115]">
                <div className="absolute top-1 right-1 flex gap-1 opacity-0 group-hover/code:opacity-100 transition-opacity">
                  <button
                    type="button"
                    onClick={handleCopy}
                    className="px-2 h-7 text-[10px] rounded bg-muted/60 hover:bg-muted text-foreground border border-border/40"
                  >{copied ? 'Copied' : 'Copy'}</button>
                  {isLong && (
                    <button
                      type="button"
                      onClick={() => setCollapsed(c => !c)}
                      className="px-2 h-7 text-[10px] rounded bg-muted/60 hover:bg-muted text-foreground border border-border/40"
                    >{collapsed ? `Expand (${hiddenCount} more)` : 'Collapse'}</button>
                  )}
                </div>
                <pre className="p-3 overflow-auto max-h-[32rem] text-xs rounded-md with-line-numbers" aria-live="polite">
                  <code className={className} {...props}>
                    {visibleLines.map((l, i) => (
                      <span key={i} className="code-line" dangerouslySetInnerHTML={{ __html: l || ' ' }} />
                    ))}
                  </code>
                </pre>
                {collapsed && (
                  <div className="text-[10px] px-3 pb-2 -mt-2 text-muted-foreground">
                    …truncated ({hiddenCount} more line{hiddenCount === 1 ? '' : 's'})
                  </div>
                )}
              </div>
            );
          },
          blockquote: (p) => <blockquote className="border-l-4 border-border pl-3 italic opacity-90 mb-3" {...p} />,
          hr: (p) => <hr className="my-6 border-border/60" {...p} />
        }}
      >
        {prepared}
      </ReactMarkdown>
    </div>
  );
};

export default MarkdownMessage;
