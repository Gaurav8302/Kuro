import { motion } from 'framer-motion';
import { Clock, AlertTriangle, Server, Shield, RefreshCw } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface SystemMessageProps {
  message: string;
  messageType: 'rate_limit' | 'error' | 'warning' | 'normal';
  timestamp: string;
  onRetry?: () => void;
}

export const SystemMessage = ({ 
  message, 
  messageType, 
  timestamp,
  onRetry 
}: SystemMessageProps) => {
  const getMessageIcon = () => {
    switch (messageType) {
      case 'rate_limit':
        return <Clock className="w-5 h-5" />;
      case 'error':
        return <AlertTriangle className="w-5 h-5" />;
      case 'warning':
        return <Server className="w-5 h-5" />;
      default:
        return <Shield className="w-5 h-5" />;
    }
  };

  const getMessageStyle = () => {
    switch (messageType) {
      case 'rate_limit':
        return {
          border: 'border-amber-200/50 dark:border-amber-800/50',
          bg: 'bg-amber-50/50 dark:bg-amber-900/20',
          icon: 'text-amber-600 dark:text-amber-400',
          title: 'text-amber-800 dark:text-amber-200'
        };
      case 'error':
        return {
          border: 'border-red-200/50 dark:border-red-800/50',
          bg: 'bg-red-50/50 dark:bg-red-900/20',
          icon: 'text-red-600 dark:text-red-400',
          title: 'text-red-800 dark:text-red-200'
        };
      case 'warning':
        return {
          border: 'border-orange-200/50 dark:border-orange-800/50',
          bg: 'bg-orange-50/50 dark:bg-orange-900/20',
          icon: 'text-orange-600 dark:text-orange-400',
          title: 'text-orange-800 dark:text-orange-200'
        };
      default:
        return {
          border: 'border-blue-200/50 dark:border-blue-800/50',
          bg: 'bg-blue-50/50 dark:bg-blue-900/20',
          icon: 'text-blue-600 dark:text-blue-400',
          title: 'text-blue-800 dark:text-blue-200'
        };
    }
  };

  const detectRateLimitMessage = (msg: string) => {
    return msg.includes('Rate Limit') || 
           msg.includes('rate limit') || 
           msg.includes('⏰') ||
           msg.includes('Quota') ||
           msg.includes('quota');
  };

  const showRetryButton = messageType === 'rate_limit' || detectRateLimitMessage(message);
  const styles = getMessageStyle();

  return (
    <motion.div
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.3 }}
      className="flex justify-center"
    >
      <Card className={cn(
        "max-w-md mx-4 shadow-sm",
        styles.border,
        styles.bg
      )}>
        <CardContent className="p-4">
          <div className="flex items-start gap-3">
            <div className={cn("mt-0.5", styles.icon)}>
              {getMessageIcon()}
            </div>
            
            <div className="flex-1 min-w-0">
              <div className={cn("text-sm leading-relaxed", styles.title)}>
                {/* Render message with basic markdown-like formatting */}
                {message.split('\n').map((line, idx) => {
                  if (line.startsWith('**') && line.endsWith('**')) {
                    return (
                      <div key={idx} className="font-semibold mb-2">
                        {line.replace(/\*\*/g, '')}
                      </div>
                    );
                  } else if (line.startsWith('•')) {
                    return (
                      <div key={idx} className="ml-2 mb-1 text-muted-foreground">
                        {line}
                      </div>
                    );
                  } else if (line.trim()) {
                    return (
                      <div key={idx} className="mb-1">
                        {line}
                      </div>
                    );
                  }
                  return <div key={idx} className="h-2" />;
                })}
              </div>
              
              {showRetryButton && onRetry && (
                <div className="mt-3 flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={onRetry}
                    className="text-xs"
                  >
                    <RefreshCw className="w-3 h-3 mr-1" />
                    Try Again
                  </Button>
                </div>
              )}
              
              <div className="text-xs text-muted-foreground mt-2">
                {new Date(timestamp).toLocaleTimeString([], { 
                  hour: '2-digit', 
                  minute: '2-digit' 
                })}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
};
