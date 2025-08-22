import React, { useMemo, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Copy, Check, ChevronDown, ChevronUp } from 'lucide-react';
import { cn } from '@/lib/utils';

interface OptimizedMarkdownProps {
  content: string;
  className?: string;
}

// Lightweight markdown parser for better performance
const parseMarkdown = (text: string) => {
  const lines = text.split('\n');
  const elements: Array<{ type: string; content: string; language?: string }> = [];
  let inCodeBlock = false;
  let codeLanguage = '';
  let codeContent: string[] = [];

  for (const line of lines) {
    if (line.startsWith('```')) {
      if (inCodeBlock) {
        // End code block
        elements.push({
          type: 'code',
          content: codeContent.join('\n'),
          language: codeLanguage
        });
        inCodeBlock = false;
        codeContent = [];
        codeLanguage = '';
      } else {
        // Start code block
        inCodeBlock = true;
        codeLanguage = line.slice(3).trim();
      }
      continue;
    }

    if (inCodeBlock) {
      codeContent.push(line);
      continue;
    }

    if (line.startsWith('# ')) {
      elements.push({ type: 'h1', content: line.slice(2) });
    } else if (line.startsWith('## ')) {
      elements.push({ type: 'h2', content: line.slice(3) });
    } else if (line.startsWith('### ')) {
      elements.push({ type: 'h3', content: line.slice(4) });
    } else if (line.startsWith('**') && line.endsWith('**')) {
      elements.push({ type: 'strong', content: line.slice(2, -2) });
    } else if (line.trim() === '') {
      elements.push({ type: 'br', content: '' });
    } else {
      elements.push({ type: 'p', content: line });
    }
  }

  return elements;
};

const CodeBlock = React.memo(({ content, language }: { content: string; language?: string }) => {
  const [copied, setCopied] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);
  
  const lines = content.split('\n');
  const shouldCollapse = lines.length > 15;
  const displayContent = isCollapsed ? lines.slice(0, 10).join('\n') : content;

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      // Fallback for older browsers
      const textarea = document.createElement('textarea');
      textarea.value = content;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [content]);

  return (
    <div className="group relative my-4 rounded-lg border border-border bg-muted/30 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 bg-muted/50 border-b border-border">
        <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
          {language || 'Code'}
        </span>
        <div className="flex items-center gap-1">
          {shouldCollapse && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsCollapsed(!isCollapsed)}
              className="h-6 px-2 text-xs"
            >
              {isCollapsed ? (
                <>
                  <ChevronDown className="h-3 w-3 mr-1" />
                  Show All ({lines.length})
                </>
              ) : (
                <>
                  <ChevronUp className="h-3 w-3 mr-1" />
                  Collapse
                </>
              )}
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={handleCopy}
            className="h-6 px-2 text-xs"
          >
            {copied ? (
              <>
                <Check className="h-3 w-3 mr-1" />
                Copied
              </>
            ) : (
              <>
                <Copy className="h-3 w-3 mr-1" />
                Copy
              </>
            )}
          </Button>
        </div>
      </div>
      
      {/* Code content */}
      <pre className="p-4 overflow-x-auto text-sm">
        <code className="text-foreground font-mono">{displayContent}</code>
      </pre>
      
      {isCollapsed && (
        <div className="px-4 pb-2 text-xs text-muted-foreground">
          ... {lines.length - 10} more lines
        </div>
      )}
    </div>
  );
});

CodeBlock.displayName = 'CodeBlock';

export const OptimizedMarkdown: React.FC<OptimizedMarkdownProps> = ({
  content,
  className
}) => {
  const elements = useMemo(() => parseMarkdown(content), [content]);

  return (
    <div className={cn("prose prose-sm max-w-none", className)}>
      {elements.map((element, index) => {
        switch (element.type) {
          case 'h1':
            return (
              <motion.h1
                key={index}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.02 }}
                className="text-xl font-bold text-foreground mb-3 mt-6 first:mt-0"
              >
                {element.content}
              </motion.h1>
            );
          case 'h2':
            return (
              <motion.h2
                key={index}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.02 }}
                className="text-lg font-semibold text-foreground mb-2 mt-5 first:mt-0"
              >
                {element.content}
              </motion.h2>
            );
          case 'h3':
            return (
              <motion.h3
                key={index}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.02 }}
                className="text-base font-medium text-foreground mb-2 mt-4 first:mt-0"
              >
                {element.content}
              </motion.h3>
            );
          case 'strong':
            return (
              <motion.p
                key={index}
                initial={{ opacity: 0, y: 5 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.02 }}
                className="font-semibold text-foreground mb-2"
              >
                {element.content}
              </motion.p>
            );
          case 'code':
            return (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.02 }}
              >
                <CodeBlock content={element.content} language={element.language} />
              </motion.div>
            );
          case 'br':
            return <div key={index} className="h-2" />;
          case 'p':
            return (
              <motion.p
                key={index}
                initial={{ opacity: 0, y: 5 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.02 }}
                className="text-foreground mb-2 leading-relaxed"
              >
                {element.content}
              </motion.p>
            );
          default:
            return null;
        }
      })}
    </div>
  );
};

export default OptimizedMarkdown;