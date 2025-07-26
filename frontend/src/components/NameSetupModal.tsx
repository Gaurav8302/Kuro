import { useState } from 'react';
import { motion } from 'framer-motion';
import { X, User, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface NameSetupModalProps {
  isOpen: boolean;
  onComplete: (name: string) => void;
  onSkip: () => void;
}

const NameSetupModal = ({ isOpen, onComplete, onSkip }: NameSetupModalProps) => {
  const [name, setName] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    setIsSubmitting(true);
    try {
      await onComplete(name.trim());
    } catch (error) {
      console.error('Error setting name:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSkip = () => {
    onSkip();
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.3 }}
        className="w-full max-w-md"
      >
        <Card className="shadow-2xl border-0">
          <CardHeader className="text-center pb-4">
            <div className="flex justify-center mb-4">
              <div className="relative">
                <User className="w-12 h-12 text-indigo-600" />
                <Sparkles className="w-6 h-6 text-purple-500 absolute -top-1 -right-1" />
              </div>
            </div>
            <CardTitle className="text-2xl font-bold text-gray-900">
              Welcome to Kuro AI!
            </CardTitle>
            <p className="text-gray-600 text-sm">
              What would you like me to call you?
            </p>
          </CardHeader>
          
          <CardContent className="space-y-6">
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Enter your name"
                  className="text-center text-lg"
                  maxLength={50}
                  autoFocus
                />
              </div>

              <div className="flex flex-col gap-3">
                <Button 
                  type="submit" 
                  className="w-full bg-indigo-600 hover:bg-indigo-700"
                  disabled={!name.trim() || isSubmitting}
                >
                  {isSubmitting ? 'Setting up...' : 'Continue'}
                </Button>
                
                <Button 
                  type="button"
                  variant="ghost"
                  onClick={handleSkip}
                  className="w-full text-gray-600 hover:text-gray-800"
                  disabled={isSubmitting}
                >
                  Skip for now
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
};

export default NameSetupModal;
