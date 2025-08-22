import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { useUser } from '@clerk/clerk-react';
import { 
  ArrowRight, 
  Sparkles, 
  MessageSquare, 
  Brain, 
  Zap,
  Star,
  Shield,
  Cpu,
  Network,
  Github
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { ThemeToggle } from '@/components/ui/theme-toggle';
import { PerformanceOptimizedBackground } from '@/components/PerformanceOptimizedBackground';

const Landing = () => {
  const navigate = useNavigate();
  const { isSignedIn, isLoaded } = useUser();

  // Optionally, redirect signed-in users to /chat automatically
  useEffect(() => {
    if (isLoaded && isSignedIn) {
      navigate('/chat');
    }
  }, [isLoaded, isSignedIn, navigate]);

  const features = [
    {
  icon: Brain,
  title: "Smart Reasoning",
  description: "Groq LLaMA 3 70B for intelligent conversations"
    },
    {
      icon: Shield,
  title: "Privacy & Security",
  description: "Secure authentication and protected APIs"
    },
    {
      icon: Zap,
  title: "Fast Responses",
  description: "Optimized for speed and performance"
    },
    {
      icon: Network,
  title: "Memory & Context",
  description: "Persistent conversation memory"
    }
  ];

  const handleStartChat = () => {
    // Check authentication status before navigating
    if (isLoaded && isSignedIn) {
      // User is signed in, go to chat
      navigate('/chat');
    } else {
      // User is not signed in, redirect to sign-in page
      navigate('/auth/signin');
    }
  };

  // Show loading state while Clerk initializes
  if (!isLoaded) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center relative z-10">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
            className="w-12 h-12 mx-auto mb-4"
          >
            <div className="w-full h-full rounded-full border-2 border-primary border-t-transparent" />
          </motion.div>
          <p className="text-muted-foreground">Loading Kuro AI...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background relative">
      <PerformanceOptimizedBackground variant="standard" />

      <div className="relative z-10">
        {/* Header */}
        <motion.header 
          className="p-4 md:p-6"
          initial={{ y: -50, opacity: 0, filter: 'blur(10px)' }}
          animate={{ y: 0, opacity: 1, filter: 'blur(0px)' }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
        >
          <div className="max-w-7xl mx-auto flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 md:w-12 md:h-12 bg-primary/10 rounded-full flex items-center justify-center">
                <img src="/kuroai.png" alt="Kuro AI" className="w-full h-full object-cover rounded-full" />
              </div>
              <div>
                <h1 className="text-xl md:text-2xl font-bold text-foreground">
                  Kuro
                </h1>
                <p className="text-xs text-muted-foreground">AI Assistant</p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <ThemeToggle />
            {isLoaded && !isSignedIn && (
              <div className="flex gap-2">
                <Button variant="ghost" onClick={() => navigate('/auth/signin')}>
                  Sign In
                </Button>
                <Button onClick={() => navigate('/auth/signup')}>
                  Sign Up
                </Button>
              </div>
            )}
            {isLoaded && isSignedIn && (
              <Button onClick={() => navigate('/chat')}>
                Open Chat
              </Button>
            )}
            </div>
          </div>
        </motion.header>

        {/* Hero Section */}
        <main className="max-w-7xl mx-auto px-4 md:px-6 py-12 md:py-20">
          <div className="grid lg:grid-cols-2 gap-12 lg:gap-20 items-center">
            {/* Content */}
            <motion.div
              initial={{ x: -100, opacity: 0, filter: 'blur(10px)' }}
              animate={{ x: 0, opacity: 1, filter: 'blur(0px)' }}
              transition={{ duration: 1, delay: 0.3, ease: 'easeOut' }}
              className="text-center lg:text-left"
            >
              <motion.h1 
                className="text-4xl md:text-5xl lg:text-6xl font-bold mb-6 leading-tight"
                initial={{ opacity: 0, y: 50 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, delay: 0.7 }}
              >
                <span className="block text-foreground">Smart AI</span>
                <span className="block text-primary">Assistant</span>
              </motion.h1>

              <motion.div
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, delay: 0.9 }}
              >
                <p className="text-lg md:text-xl text-muted-foreground mb-6 leading-relaxed">
                  Kuro is a production-ready AI chatbot using <strong>Groq LLaMA 3 70B</strong> for intelligent conversation and <strong>Google Gemini embeddings</strong> for semantic memory.
                </p>
              </motion.div>

              <motion.div
                className="flex flex-col sm:flex-row gap-3 justify-center lg:justify-start"
                initial={{ y: 50, opacity: 0, scale: 0.8 }}
                animate={{ y: 0, opacity: 1, scale: 1 }}
                transition={{ duration: 0.8, delay: 1.1, ease: 'backOut' }}
              >
                <Button
                  size="lg"
                  onClick={handleStartChat}
                  className="group"
                >
                  <MessageSquare className="w-5 h-5 mr-2" />
                  Start Chat
                  <motion.div
                    className="ml-2"
                    animate={{ x: [0, 5, 0] }}
                    transition={{ duration: 1.5, repeat: Infinity }}
                  >
                    <ArrowRight className="w-5 h-5" />
                  </motion.div>
                </Button>
                
                <Button
                  variant="ghost"
                  size="lg"
                  onClick={() => document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' })}
                >
                  Learn More
                  <Sparkles className="w-4 h-4 ml-2" />
                </Button>
              </motion.div>
            </motion.div>

            {/* Hero Image */}
            <motion.div
              initial={{ x: 100, opacity: 0, filter: 'blur(10px)' }}
              animate={{ x: 0, opacity: 1, filter: 'blur(0px)' }}
              transition={{ duration: 1, delay: 0.5, ease: 'easeOut' }}
              className="relative hidden lg:block"
            >
              <Card className="overflow-hidden">
                <CardContent className="p-8">
                  <motion.div
                    className="w-48 h-48 mx-auto relative bg-primary/5 rounded-full flex items-center justify-center"
                    animate={{ 
                      scale: [1, 1.05, 1]
                    }}
                    transition={{ 
                      scale: { duration: 4, repeat: Infinity }
                    }}
                  >
                    <Brain className="w-16 h-16 text-primary" />
                  </motion.div>
                </CardContent>
              </Card>
            </motion.div>
          </div>
        </main>

        {/* Features Section */}
        <section id="features" className="max-w-7xl mx-auto px-4 md:px-6 py-12 md:py-20">
          <motion.div
            initial={{ y: 50, opacity: 0, filter: 'blur(10px)' }}
            whileInView={{ y: 0, opacity: 1, filter: 'blur(0px)' }}
            transition={{ duration: 0.8, ease: 'easeOut' }}
            viewport={{ once: true }}
            className="text-center mb-12"
          >
            <h2 className="text-3xl md:text-4xl font-bold text-foreground mb-4">
              Advanced Capabilities
            </h2>
            <p className="text-lg text-muted-foreground">
              Powered by cutting-edge AI technology
            </p>
          </motion.div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {features.map((feature, index) => (
              <motion.div
                key={feature.title}
                initial={{ y: 50, opacity: 0, scale: 0.8 }}
                whileInView={{ y: 0, opacity: 1, scale: 1 }}
                transition={{ duration: 0.6, delay: index * 0.15, ease: 'easeOut' }}
                viewport={{ once: true }}
              >
                <Card className="p-6 h-full hover:shadow-lg transition-all duration-300">
                  <CardContent className="p-0">
                    <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center mb-4">
                    <feature.icon className="w-7 h-7 text-white" />
                    </div>
                    <h3 className="text-lg font-semibold text-foreground mb-3">
                    {feature.title}
                  </h3>
                    <p className="text-muted-foreground leading-relaxed">
                    {feature.description}
                  </p>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </section>


        {/* CTA Section */}
        <motion.section
          initial={{ y: 50, opacity: 0, scale: 0.9 }}
          whileInView={{ y: 0, opacity: 1, scale: 1 }}
          transition={{ duration: 0.8 }}
          viewport={{ once: true }}
          className="max-w-4xl mx-auto px-4 md:px-6 py-12 md:py-20 text-center"
        >
          <Card className="p-8 md:p-12">
            <CardContent className="p-0">
              <h2 className="text-3xl md:text-4xl font-bold text-foreground mb-4">
                Ready to Chat?
              </h2>
              <p className="text-lg text-muted-foreground mb-8">
                Start a conversation with Kuro AI today.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Button size="lg" onClick={handleStartChat} className="group">
                  <Brain className="w-5 h-5 mr-2" />
                  Start Chat
                  <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
                </Button>
                <Button 
                  variant="outline" 
                  size="lg"
                  onClick={() => window.open('https://github.com/Gaurav8302/Kuro', '_blank')}
                >
                  <Github className="w-4 h-4 mr-2" />
                  View Source
                </Button>
              </div>
            </CardContent>
          </Card>
        </motion.section>
      </div>
    </div>
  );
};

export default Landing;