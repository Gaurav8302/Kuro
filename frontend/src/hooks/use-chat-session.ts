import { useClerkApi } from '@/lib/api';
import { useState } from 'react';
import { useToast } from '@/hooks/use-toast';

export const useChatSession = () => {
  const clerkApiRequest = useClerkApi();
  const { toast } = useToast();
  const [isSummarizing, setIsSummarizing] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  const summarizeSession = async (sessionId: string, userId: string) => {
    setIsSummarizing(true);
    try {
      const result = await clerkApiRequest<{ summary: string }>(
        `/session/summarize/${sessionId}`,
        'post',
        { user_id: userId }
      );
      
      toast({
        title: "Session Summarized",
        description: "Chat session has been summarized successfully.",
      });
      
      return result.summary;
    } catch (err: any) {
      toast({ 
        title: 'Error', 
        description: 'Failed to summarize session: ' + err.message, 
        variant: 'destructive' 
      });
    } finally {
      setIsSummarizing(false);
    }
  };

  const exportChatHistory = async (sessionId: string) => {
    setIsExporting(true);
    try {
      const history = await clerkApiRequest<{ history: any[] }>(
        `/chat/${sessionId}`,
        'get'
      );

      // Format chat history for export
      const formattedHistory = history.history.map((msg: any) => ({
        timestamp: new Date(msg.timestamp).toLocaleString(),
        user: msg.user,
        assistant: msg.assistant
      }));

      // Create and download file
      const blob = new Blob(
        [JSON.stringify(formattedHistory, null, 2)], 
        { type: 'application/json' }
      );
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `chat-history-${sessionId}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      toast({
        title: "Chat Exported",
        description: "Chat history has been downloaded successfully.",
      });
    } catch (err: any) {
      toast({ 
        title: 'Error', 
        description: 'Failed to export chat: ' + err.message, 
        variant: 'destructive' 
      });
    } finally {
      setIsExporting(false);
    }
  };

  return {
    summarizeSession,
    exportChatHistory,
    isSummarizing,
    isExporting
  };
};
