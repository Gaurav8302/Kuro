
import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface OptimizedMarkdownMessageProps {
  content: string;
}

const OptimizedMarkdownMessage: React.FC<OptimizedMarkdownMessageProps> = ({ content }) => {
  return (
    <ReactMarkdown remarkPlugins={[remarkGfm]}>
      {content}
    </ReactMarkdown>
  );
};

export default OptimizedMarkdownMessage;
