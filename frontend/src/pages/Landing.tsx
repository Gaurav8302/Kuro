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
  Heart,
  Star,
  Palette
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import heroImage from '@/assets/hero-ai.jpg';

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
      title: "Smart Conversations",
      description: "AI that remembers and learns from our chats",
      color: "text-primary"
    },
    {
      icon: Heart,
      title: "Personal Touch",
      description: "Tailored responses that understand your style",
      color: "text-secondary"
    },
    {
      icon: Zap,
      title: "Lightning Fast",
      description: "Quick responses with thoughtful insights",
      color: "text-accent"
    },
    {
      icon: Palette,
      title: "Smart Conversations",
      description: "Brainstorm ideas and explore possibilities",
      color: "text-primary"
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
      <div className="min-h-screen bg-gradient-hero flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-white/30 border-t-white rounded-full animate-spin mx-auto mb-4" />
          <p className="text-white/80">Loading Kuro AI...</p>
        </div>
      </div>
    );
  }

  return (
  <div className="min-h-screen bg-gradient-hero overflow-hidden relative">
      {/* Animated background elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <motion.div
          className="absolute top-20 left-10 w-20 h-20 bg-gradient-secondary rounded-full opacity-20"
          animate={{ 
            y: [0, -20, 0],
            rotate: [0, 360]
          }}
          transition={{ 
            duration: 8,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        />
        <motion.div
          className="absolute top-40 right-20 w-16 h-16 bg-gradient-accent rounded-full opacity-20"
          animate={{ 
            y: [0, 20, 0],
            x: [0, -10, 0]
          }}
          transition={{ 
            duration: 6,
            repeat: Infinity,
            ease: "easeInOut",
            delay: 1
          }}
        />
        <motion.div
          className="absolute bottom-20 left-1/4 w-12 h-12 bg-gradient-primary rounded-full opacity-20"
          animate={{ 
            scale: [1, 1.2, 1],
            rotate: [0, -360]
          }}
          transition={{ 
            duration: 10,
            repeat: Infinity,
            ease: "easeInOut",
            delay: 2
          }}
        />
      </div>

  <div className="relative z-10">
        {/* Header */}
        <motion.header 
          className="p-6"
          initial={{ y: -50, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.6 }}
        >
          <div className="max-w-7xl mx-auto flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-white/20 backdrop-blur-sm rounded-full flex items-center justify-center overflow-hidden">
                <img src="/kuroai.png" alt="Kuro AI" className="w-full h-full object-cover rounded-full" />
              </div>
              <div>
                <h1 className="font-handwriting text-2xl font-bold text-white">
                  Kuro
                </h1>
                <p className="text-white/80 text-sm">Your AI Assistant</p>
              </div>
            </div>

            {/* Auth buttons or Go to Chat based on Clerk state */}
            {isLoaded && !isSignedIn && (
              <div className="flex flex-col sm:flex-row gap-2 sm:gap-3">
                <div className="flex gap-2 sm:gap-3">
                  <Button 
                    variant="outline" 
                    className="bg-white/10 border-white/20 text-white hover:bg-white/20"
                    onClick={() => navigate('/auth/signin')}
                  >
                    Sign In
                  </Button>
                  <Button 
                    variant="outline" 
                    className="bg-white/10 border-white/20 text-white hover:bg-white/20"
                    onClick={() => navigate('/auth/signup')}
                  >
                    Sign Up
                  </Button>
                </div>
                <Button 
                  variant="outline" 
                  className="bg-white/10 border-white/20 text-white hover:bg-white/20 w-full sm:w-auto"
                  onClick={() => window.open('https://github.com/sponsors/Gaurav8302', '_blank')}
                >
                  <Heart className="w-4 h-4 mr-2" />
                  Donate
                </Button>
              </div>
            )}
            {isLoaded && isSignedIn && (
              <div className="flex flex-col sm:flex-row gap-2 sm:gap-3">
                <Button 
                  variant="secondary"
                  onClick={() => navigate('/chat')}
                  className="w-full sm:w-auto"
                >
                  <MessageSquare className="w-4 h-4 mr-2" />
                  Go to Chat
                </Button>
                <Button 
                  variant="default"
                  onClick={() => navigate('/workspace')}
                  className="w-full sm:w-auto bg-primary/90 hover:bg-primary"
                >
                  <Sparkles className="w-4 h-4 mr-2" />
                  Workspace
                </Button>
                <Button 
                  variant="outline" 
                  className="bg-white/10 border-white/20 text-white hover:bg-white/20 w-full sm:w-auto"
                  onClick={() => window.open('https://github.com/sponsors/Gaurav8302', '_blank')}
                >
                  <Heart className="w-4 h-4 mr-2" />
                  Donate
                </Button>
              </div>
            )}
          </div>
        </motion.header>

        {/* Hero Section */}
        <main className="max-w-7xl mx-auto px-6 py-16">
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            {/* Content */}
            <motion.div
              initial={{ x: -100, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              transition={{ duration: 0.8, delay: 0.2 }}
              className="text-center lg:text-left"
            >
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ duration: 0.5, delay: 0.4 }}
                className="inline-flex items-center gap-2 bg-white/10 backdrop-blur-sm px-4 py-2 rounded-full text-white mb-6"
              >
                <Sparkles className="w-4 h-4" />
                <span className="text-sm font-medium">Powered by Groq LLaMA 3 70B</span>
                <Star className="w-4 h-4" />
              </motion.div>

              <h1 className="text-6xl lg:text-7xl font-bold text-white mb-6 leading-tight">
                Meet Your
                <span className="block font-handwriting text-gradient-rainbow bg-white">
                  AI Assistant
                </span>
                <span className="block">Companion</span>
              </h1>

              <p className="text-xl text-white/90 mb-8 leading-relaxed">
                Chat with Kuro, an AI powered by Groq's ultra-fast LLaMA 3 70B model. 
                Experience lightning-fast responses with advanced reasoning capabilities.
                <span className="font-handwriting text-2xl text-white"> ✨ Open source & free!</span>
              </p>

              <motion.div
                className="flex flex-col sm:flex-row gap-4 justify-center lg:justify-start"
                initial={{ y: 50, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ duration: 0.6, delay: 0.6 }}
              >
                <Button
                  variant="hero"
                  size="xl"
                  onClick={handleStartChat}
                  className="group"
                >
                  <MessageSquare className="w-5 h-5 mr-2 group-hover:animate-wiggle" />
                  Start Chatting
                  <ArrowRight className="w-5 h-5 ml-2 group-hover:translate-x-1 transition-transform" />
                </Button>
                
                <Button
                  variant="outline"
                  size="xl"
                  className="bg-white/10 border-white/20 text-white hover:bg-white/20"
                  onClick={() => document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' })}
                >
                  Learn More
                  <Sparkles className="w-5 h-5 ml-2" />
                </Button>
              </motion.div>
            </motion.div>

            {/* Hero Image */}
            <motion.div
              initial={{ x: 100, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              transition={{ duration: 0.8, delay: 0.4 }}
              className="relative"
            >
              <div className="relative overflow-hidden rounded-3xl shadow-glow">
                <img 
                  src={heroImage} 
                  alt="Kuro AI Assistant" 
                  className="w-full h-auto animate-float"
                />
                {/* Overlay for extra visual interest */}
                <div className="absolute inset-0 bg-gradient-to-t from-primary/20 to-transparent" />
              </div>
              
              {/* Floating elements around the image */}
              <motion.div
                className="absolute -top-4 -right-4 w-16 h-16 bg-gradient-secondary rounded-full flex items-center justify-center"
                animate={{ rotate: 360 }}
                transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
              >
                <Sparkles className="w-8 h-8 text-white" />
              </motion.div>
              
              <motion.div
                className="absolute -bottom-4 -left-4 w-12 h-12 bg-gradient-accent rounded-full flex items-center justify-center"
                animate={{ scale: [1, 1.2, 1] }}
                transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
              >
                <Heart className="w-6 h-6 text-white" />
              </motion.div>
            </motion.div>
          </div>
        </main>

        {/* Features Section */}
        <section id="features" className="max-w-7xl mx-auto px-6 py-20">
          <motion.div
            initial={{ y: 50, opacity: 0 }}
            whileInView={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.6 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl font-bold text-white mb-4">
              Why You'll <span className="font-handwriting text-5xl">Love</span> This AI
            </h2>
            <p className="text-xl text-white/80">
              More than just a chatbot – it's your AI assistant
            </p>
          </motion.div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
            {features.map((feature, index) => (
              <motion.div
                key={feature.title}
                initial={{ y: 50, opacity: 0 }}
                whileInView={{ y: 0, opacity: 1 }}
                transition={{ duration: 0.6, delay: index * 0.1 }}
                viewport={{ once: true }}
                whileHover={{ y: -10, scale: 1.05 }}
                className="group"
              >
                <Card className="p-6 bg-white/10 backdrop-blur-sm border-white/20 hover:shadow-glow transition-all duration-300 h-full">
                  <div className={`w-12 h-12 rounded-xl bg-gradient-primary flex items-center justify-center mb-4 group-hover:animate-bounce-in`}>
                    <feature.icon className="w-6 h-6 text-white" />
                  </div>
                  <h3 className="text-xl font-semibold text-white mb-2">
                    {feature.title}
                  </h3>
                  <p className="text-white/80">
                    {feature.description}
                  </p>
                </Card>
              </motion.div>
            ))}
          </div>
        </section>

        {/* Tech & Open Source Section */}
        <motion.section
          initial={{ y: 50, opacity: 0 }}
          whileInView={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.6 }}
          viewport={{ once: true }}
          className="max-w-6xl mx-auto px-6 py-20"
        >
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-white mb-4">
              Built with Free & Open Source Tools
            </h2>
            <p className="text-xl text-white/80 max-w-3xl mx-auto">
              Kuro is completely free and open-source, built using only free resources to keep it accessible to everyone.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-6 border border-white/20">
              <div className="w-12 h-12 bg-gradient-to-br from-purple-600 to-purple-700 rounded-lg flex items-center justify-center mb-4">
                <Brain className="w-6 h-6 text-white" />
              </div>
              <h3 className="text-xl font-bold text-white mb-2">Groq LLaMA 3 70B</h3>
              <p className="text-white/70">
                Powered by Groq's ultra-fast inference engine. Experience lightning-fast AI with advanced reasoning.
              </p>
            </div>

            <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-6 border border-white/20">
              <div className="w-12 h-12 bg-gradient-to-br from-purple-600 to-purple-700 rounded-lg flex items-center justify-center mb-4">
                <Zap className="w-6 h-6 text-white" />
              </div>
              <h3 className="text-xl font-bold text-white mb-2">Vercel Hosting</h3>
              <p className="text-white/70">
                Frontend hosted on Vercel's free tier for lightning-fast global delivery.
              </p>
            </div>

            <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-6 border border-white/20">
              <div className="w-12 h-12 bg-gradient-to-br from-purple-600 to-purple-700 rounded-lg flex items-center justify-center mb-4">
                <MessageSquare className="w-6 h-6 text-white" />
              </div>
              <h3 className="text-xl font-bold text-white mb-2">Render Backend</h3>
              <p className="text-white/70">
                Backend services running on Render's free tier with MongoDB Atlas.
              </p>
            </div>
          </div>

          <div className="text-center mt-12">
            <p className="text-white/80 mb-6">
              Want to help make Kuro smarter with premium AI models? Consider supporting the project!
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Button
                variant="outline"
                size="lg"
                className="bg-white/10 border-white/20 text-white hover:bg-white/20"
                onClick={() => window.open('https://github.com/Gaurav8302/Kuro', '_blank')}
              >
                <Star className="w-5 h-5 mr-2" />
                View on GitHub
              </Button>
              <Button
                variant="hero"
                size="lg"
                onClick={() => window.open('https://github.com/sponsors/Gaurav8302', '_blank')}
              >
                <Heart className="w-5 h-5 mr-2" />
                Support Development
              </Button>
            </div>
          </div>
        </motion.section>

        {/* CTA Section */}
        <motion.section
          initial={{ y: 50, opacity: 0 }}
          whileInView={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.6 }}
          viewport={{ once: true }}
          className="max-w-4xl mx-auto px-6 py-20 text-center"
        >
          <div className="bg-white/10 backdrop-blur-sm rounded-3xl p-12 border border-white/20">
            <h2 className="text-4xl font-bold text-white mb-4">
              Ready to Chat with Kuro?
            </h2>
            <p className="text-xl text-white/80 mb-8">
              Start chatting with our lightning-fast AI assistant powered by Groq LLaMA 3!
            </p>
            <Button
              variant="hero"
              size="xl"
              onClick={handleStartChat}
              className="animate-pulse-glow"
            >
              <Brain className="w-5 h-5 mr-2" />
              Start Chatting with Kuro
              <ArrowRight className="w-5 h-5 ml-2" />
            </Button>
          </div>
        </motion.section>
      </div>
    </div>
  );
};

export default Landing;