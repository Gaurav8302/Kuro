import { motion } from 'framer-motion';
import { Clock, AlertTriangle, Server, Shield, RefreshCw, Zap } from 'lucide-react';
import { HolographicCard } from '@/components/HolographicCard';
import { HolographicButton } from '@/components/HolographicButton';
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
        return <Clock className="w-5 h-5 text-holo-cyan-400" />;
      case 'error':
        return <AlertTriangle className="w-5 h-5 text-holo-magenta-400" />;
      case 'warning':
        return <Server className="w-5 h-5 text-holo-blue-400" />;
      default:
        return <Shield className="w-5 h-5 text-holo-green-400" />;
    }
  };

  const getMessageStyle = () => {
    switch (messageType) {
      case 'rate_limit':
        return {
          border: 'border-holo-cyan-400/30',
          bg: 'bg-holo-cyan-500/10',
          icon: 'text-holo-cyan-400',
          title: 'text-holo-cyan-200'
        };
      case 'error':
        return {
          border: 'border-holo-magenta-400/30',
          bg: 'bg-holo-magenta-500/10',
          icon: 'text-holo-magenta-400',
          title: 'text-holo-magenta-200'
        };
      case 'warning':
        return {
          border: 'border-holo-blue-400/30',
          bg: 'bg-holo-blue-500/10',
          icon: 'text-holo-blue-400',
          title: 'text-holo-blue-200'
        };
      default:
        return {
          border: 'border-holo-green-400/30',
          bg: 'bg-holo-green-500/10',
          icon: 'text-holo-green-400',
          title: 'text-holo-green-200'
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
      initial={{ opacity: 0, y: 30, scale: 0.8, filter: 'blur(10px)' }}
      animate={{ opacity: 1, y: 0, scale: 1, filter: 'blur(0px)' }}
      exit={{ opacity: 0, y: -20, scale: 0.8, filter: 'blur(5px)' }}
      transition={{ duration: 0.5, ease: 'easeOut' }}
      className="flex justify-center"
    >
      <HolographicCard
        variant="glow"
        scanLine={true}
        className={cn(
          "max-w-md mx-4 relative overflow-hidden",
          styles.border,
          styles.bg
        )}
      >
        <div className="p-4 relative">
          {/* Animated background pattern */}
          <div className="absolute inset-0 opacity-20">
            <motion.div
              className="absolute inset-0 bg-gradient-to-r from-transparent via-current to-transparent"
              animate={{ x: ['-100%', '100%'] }}
              transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
            />
          </div>
          
          <div className="flex items-start gap-3">
            <motion.div 
              className={cn("mt-0.5 relative", styles.icon)}
              animate={{ rotate: [0, 5, -5, 0] }}
              transition={{ duration: 2, repeat: Infinity }}
            >
              {getMessageIcon()}
            </motion.div>
            
            <div className="flex-1 min-w-0">
              <div className={cn("text-sm leading-relaxed font-space", styles.title)}>
                {/* Render message with basic markdown-like formatting */}
                {message.split('\n').map((line, idx) => {
                  if (line.startsWith('**') && line.endsWith('**')) {
                    return (
                      <div key={idx} className="font-semibold mb-2 text-holo-glow font-orbitron tracking-wide">
                        {line.replace(/\*\*/g, '')}
                      </div>
                    );
                  } else if (line.startsWith('•')) {
                    return (
                      <div key={idx} className="ml-2 mb-1 text-holo-cyan-400/70 font-rajdhani">
                        {line}
                      </div>
                    );
                  } else if (line.trim()) {
                    return (
                      <div key={idx} className="mb-1 font-space">
                        {line}
                      </div>
                    );
                  }
                  return <div key={idx} className="h-2" />;
                })}
              </div>
              
              {showRetryButton && onRetry && (
                <div className="mt-3 flex gap-2">
                  <HolographicButton
                    variant="accent"
                    size="sm"
                    onClick={onRetry}
                    className="text-xs font-orbitron tracking-wide"
                  >
                    <Zap className="w-3 h-3 mr-1" />
                    RETRY TRANSMISSION
                  </HolographicButton>
                </div>
              )}
              
              <div className="text-xs text-holo-cyan-400/50 mt-2 font-orbitron">
                {new Date(timestamp).toLocaleTimeString([], { 
                  hour: '2-digit', 
                  minute: '2-digit' 
                })}
              </div>
            </div>
          </div>
        </div>
      </HolographicCard>
    </motion.div>
  );
};
