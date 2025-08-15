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
  Palette,
  Shield,
  Cpu,
  Network
} from 'lucide-react';
import { HolographicButton } from '@/components/HolographicButton';
import { HolographicCard } from '@/components/HolographicCard';
import { HolographicBackground } from '@/components/HolographicBackground';
import HolographicParticles from '@/components/HolographicParticles';
import { HoloBrainIcon, HoloSparklesIcon } from '@/components/HolographicIcons';

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
  title: "SMART REASONING",
  description: "Groq LLaMA 3 70B for clear, helpful answers",
      color: "holo-cyan"
    },
    {
      icon: Shield,
  title: "PRIVACY & SECURITY",
  description: "Secure auth with Clerk and protected APIs",
      color: "holo-blue"
    },
    {
      icon: Zap,
  title: "FAST RESPONSES",
  description: "Low-latency chat on modern cloud infra",
      color: "holo-purple"
    },
    {
      icon: Network,
  title: "MEMORY & CONTEXT",
  description: "Gemini embeddings + Pinecone for recall",
      color: "holo-magenta"
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
      <div className="min-h-screen bg-background flex items-center justify-center relative overflow-hidden">
        <HolographicBackground variant="subtle" />
        <div className="text-center">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
            className="w-16 h-16 mx-auto mb-6"
          >
            <div className="w-full h-full rounded-full border-4 border-holo-cyan-400/30 border-t-holo-cyan-400 shadow-holo-glow" />
          </motion.div>
          <p className="text-holo-cyan-400 font-orbitron tracking-wide">INITIALIZING KURO AI...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background overflow-hidden relative">
      <HolographicBackground variant="default" />
      
      {/* Animated background elements */}
      <HolographicParticles count={40} size="md" className="opacity-40" />

      <div className="relative z-10">
        {/* Header */}
        <motion.header 
          className="p-6"
          initial={{ y: -50, opacity: 0, filter: 'blur(10px)' }}
          animate={{ y: 0, opacity: 1, filter: 'blur(0px)' }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
        >
          <div className="max-w-7xl mx-auto flex items-center justify-between relative">
            {/* Header scan line */}
            <motion.div
              className="absolute bottom-0 left-0 w-full h-0.5 bg-gradient-to-r from-transparent via-holo-cyan-400 to-transparent"
              animate={{ opacity: [0.3, 0.8, 0.3] }}
              transition={{ duration: 3, repeat: Infinity }}
            />
            
            <div className="flex items-center gap-3">
              <motion.div 
                className="w-14 h-14 glass-panel border-holo-cyan-400/50 rounded-full flex items-center justify-center overflow-hidden shadow-holo-glow"
                whileHover={{ scale: 1.1, rotate: 5 }}
                transition={{ duration: 0.3 }}
              >
                <img src="/kuroai.png" alt="Kuro AI" className="w-full h-full object-cover rounded-full" />
              </motion.div>
              <div>
                <h1 className="font-orbitron text-3xl font-bold text-holo-cyan-400 text-holo-glow">
                  Kuro
                </h1>
                <p className="text-holo-cyan-400/70 text-sm font-rajdhani tracking-wider">AI ASSISTANT</p>
              </div>
            </div>

            {/* Auth buttons or Go to Chat based on Clerk state */}
            {isLoaded && !isSignedIn && (
              <div className="flex flex-col sm:flex-row gap-2 sm:gap-3">
                <div className="flex gap-2 sm:gap-3">
                  <HolographicButton
                    variant="ghost"
                    size="md"
                    onClick={() => navigate('/auth/signin')}
                  >
                      SIGN IN
                  </HolographicButton>
                  <HolographicButton
                    variant="accent"
                    size="md"
                    onClick={() => navigate('/auth/signup')}
                  >
                      SIGN UP
                  </HolographicButton>
                </div>
                <HolographicButton
                  variant="secondary"
                  size="md"
                  className="w-full sm:w-auto"
                  onClick={() => window.open('https://github.com/sponsors/Gaurav8302', '_blank')}
                >
                  <Brain className="w-4 h-4 mr-2" />
                    SPONSOR
                </HolographicButton>
              </div>
            )}
            {isLoaded && isSignedIn && (
              <div className="flex flex-col sm:flex-row gap-2 sm:gap-3">
                <HolographicButton
                  variant="primary"
                  size="md"
                  onClick={() => navigate('/chat')}
                  className="w-full sm:w-auto"
                >
                    OPEN CHAT
                </HolographicButton>
                <HolographicButton
                  variant="secondary"
                  size="md"
                  className="w-full sm:w-auto"
                  onClick={() => window.open('https://github.com/sponsors/Gaurav8302', '_blank')}
                >
                  <Brain className="w-4 h-4 mr-2" />
                    SPONSOR
                </HolographicButton>
              </div>
            )}
          </div>
        </motion.header>

        {/* Hero Section */}
        <main className="max-w-7xl mx-auto px-6 py-16">
          <div className="grid lg:grid-cols-2 gap-20 items-center">
            {/* Content */}
            <motion.div
              initial={{ x: -100, opacity: 0, filter: 'blur(10px)' }}
              animate={{ x: 0, opacity: 1, filter: 'blur(0px)' }}
              transition={{ duration: 1, delay: 0.3, ease: 'easeOut' }}
              className="text-center lg:text-left"
            >
              <motion.div
                initial={{ scale: 0, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ duration: 0.6, delay: 0.5, ease: 'backOut' }}
                className="inline-flex items-center gap-3 glass-panel border-holo-cyan-400/30 px-6 py-3 rounded-full text-holo-cyan-300 mb-8 shadow-holo-glow"
              >
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
                >
                  <HoloSparklesIcon size={16} />
                </motion.div>
                <span className="text-sm font-medium font-orbitron tracking-wide">MULTI‑MODEL: GROQ + GEMINI</span>
                <motion.div
                  animate={{ scale: [1, 1.2, 1] }}
                  transition={{ duration: 2, repeat: Infinity }}
                >
                  <Star className="w-4 h-4 text-holo-cyan-400" />
                </motion.div>
              </motion.div>

              <motion.h1 
                className="text-5xl lg:text-7xl font-bold mb-8 leading-tight"
                initial={{ opacity: 0, y: 50 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, delay: 0.7 }}
              >
                <span className="block text-holo-cyan-300 font-orbitron tracking-wide">SMART</span>
                <motion.span 
                  className="block holo-text font-orbitron text-holo-glow"
                  animate={{ 
                    textShadow: [
                      '0 0 20px #00e6d6',
                      '0 0 40px #8c1aff',
                      '0 0 20px #1a8cff',
                      '0 0 20px #00e6d6'
                    ]
                  }}
                  transition={{ duration: 4, repeat: Infinity }}
                >
                  ASSISTANT
                </motion.span>
                <span className="block text-holo-cyan-200 font-space font-light">CHAT</span>
              </motion.h1>

              <motion.div
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, delay: 0.9 }}
              >
                <p className="text-xl text-holo-cyan-100 mb-6 leading-relaxed font-space">
                  Kuro uses multiple models: Groq LLaMA 3 70B for chat and Gemini embeddings for semantic memory.
                </p>
                <p className="text-lg text-holo-cyan-200 mb-8 font-space">
                  Fast, helpful answers with context from your past conversations.
                </p>
                <motion.div
                  className="inline-flex items-center gap-2 glass-panel border-holo-green-400/30 px-4 py-2 rounded-full"
                  animate={{ scale: [1, 1.05, 1] }}
                  transition={{ duration: 2, repeat: Infinity }}
                >
                  <div className="w-2 h-2 bg-holo-green-400 rounded-full shadow-holo-green animate-holo-pulse" />
                  <span className="text-sm text-holo-green-300 font-orbitron tracking-wide">OPEN SOURCE</span>
                </motion.div>
              </motion.div>

              <motion.div
                className="flex flex-col sm:flex-row gap-4 justify-center lg:justify-start"
                initial={{ y: 50, opacity: 0, scale: 0.8 }}
                animate={{ y: 0, opacity: 1, scale: 1 }}
                transition={{ duration: 0.8, delay: 1.1, ease: 'backOut' }}
              >
                <HolographicButton
                  variant="primary"
                  size="xl"
                  onClick={handleStartChat}
                  className="group font-orbitron tracking-wide"
                >
                  <MessageSquare className="w-5 h-5 mr-2" />
                  START CHAT
                  <motion.div
                    className="ml-2"
                    animate={{ x: [0, 5, 0] }}
                    transition={{ duration: 1.5, repeat: Infinity }}
                  >
                    <ArrowRight className="w-5 h-5" />
                  </motion.div>
                </HolographicButton>
                
                <HolographicButton
                  variant="ghost"
                  size="xl"
                  className="font-orbitron tracking-wide"
                  onClick={() => document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' })}
                >
                  LEARN MORE
                  <HoloSparklesIcon size={20} className="ml-2" />
                </HolographicButton>
              </motion.div>
            </motion.div>

            {/* Hero Image */}
            <motion.div
              initial={{ x: 100, opacity: 0, filter: 'blur(10px)' }}
              animate={{ x: 0, opacity: 1, filter: 'blur(0px)' }}
              transition={{ duration: 1, delay: 0.5, ease: 'easeOut' }}
              className="relative"
            >
              <HolographicCard variant="intense" className="overflow-hidden">
                <div className="relative p-8">
                  {/* Central holographic display */}
                  <motion.div
                    className="w-64 h-64 mx-auto relative"
                    animate={{ 
                      rotateY: [0, 360],
                      scale: [1, 1.05, 1]
                    }}
                    transition={{ 
                      rotateY: { duration: 10, repeat: Infinity, ease: 'linear' },
                      scale: { duration: 4, repeat: Infinity }
                    }}
                  >
                    {/* Holographic brain visualization */}
                    <div className="absolute inset-0 rounded-full border-4 border-holo-cyan-400/30 shadow-holo-glow">
                      <div className="absolute inset-4 rounded-full border-2 border-holo-purple-400/40 shadow-holo-purple">
                        <div className="absolute inset-4 rounded-full border border-holo-blue-400/50 shadow-holo-blue flex items-center justify-center">
                          <motion.div
                            animate={{ rotate: 360, scale: [1, 1.2, 1] }}
                            transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
                          >
                            <HoloBrainIcon size={64} className="text-holo-cyan-400" />
                          </motion.div>
                        </div>
                      </div>
                    </div>
                    
                    {/* Orbiting particles */}
                    {[0, 1, 2, 3].map(i => (
                      <motion.div
                        key={i}
                        className="absolute w-3 h-3 bg-holo-cyan-400 rounded-full shadow-holo-glow"
                        style={{
                          top: '50%',
                          left: '50%',
                          transformOrigin: '0 0'
                        }}
                        animate={{
                          rotate: 360,
                          x: Math.cos(i * Math.PI / 2) * 120,
                          y: Math.sin(i * Math.PI / 2) * 120
                        }}
                        transition={{
                          duration: 4 + i,
                          repeat: Infinity,
                          ease: 'linear'
                        }}
                      />
                    ))}
                  </motion.div>
                </div>
              </HolographicCard>
              
              {/* Floating elements around the image */}
              <motion.div
                className="absolute -top-6 -right-6 w-16 h-16 glass-panel border-holo-purple-400/50 rounded-full flex items-center justify-center shadow-holo-purple"
                animate={{ 
                  rotate: 360,
                  scale: [1, 1.1, 1]
                }}
                transition={{ 
                  rotate: { duration: 20, repeat: Infinity, ease: "linear" },
                  scale: { duration: 3, repeat: Infinity }
                }}
              >
                <HoloSparklesIcon size={24} className="text-holo-purple-400" />
              </motion.div>
              
              <motion.div
                className="absolute -bottom-6 -left-6 w-12 h-12 glass-panel border-holo-blue-400/50 rounded-full flex items-center justify-center shadow-holo-blue"
                animate={{ 
                  scale: [1, 1.3, 1],
                  rotate: [0, 180, 360]
                }}
                transition={{ 
                  duration: 4, 
                  repeat: Infinity, 
                  ease: "easeInOut" 
                }}
              >
                <Cpu className="w-6 h-6 text-holo-blue-400" />
              </motion.div>
            </motion.div>
          </div>
        </main>

        {/* Features Section */}
        <section id="features" className="max-w-7xl mx-auto px-6 py-20">
          <motion.div
            initial={{ y: 50, opacity: 0, filter: 'blur(10px)' }}
            whileInView={{ y: 0, opacity: 1, filter: 'blur(0px)' }}
            transition={{ duration: 0.8, ease: 'easeOut' }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl font-bold text-holo-cyan-300 mb-6 font-orbitron tracking-wide text-holo-glow">
              ADVANCED <span className="holo-text text-6xl">CAPABILITIES</span>
            </h2>
            <p className="text-xl text-holo-cyan-100 font-space">
              Beyond conventional AI – this is your neural interface companion
            </p>
          </motion.div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
            {features.map((feature, index) => (
              <motion.div
                key={feature.title}
                initial={{ y: 50, opacity: 0, scale: 0.8 }}
                whileInView={{ y: 0, opacity: 1, scale: 1 }}
                transition={{ duration: 0.6, delay: index * 0.15, ease: 'easeOut' }}
                viewport={{ once: true }}
                whileHover={{ y: -10, scale: 1.05, rotateY: 5 }}
                className="group"
              >
                <HolographicCard 
                  variant="default" 
                  hover={true} 
                  scanLine={true}
                  className="p-6 h-full group-hover:shadow-holo-glow transition-all duration-500"
                >
                  <motion.div 
                    className={`w-14 h-14 rounded-xl bg-gradient-to-br from-holo-${feature.color}-500 to-holo-${feature.color}-600 flex items-center justify-center mb-6 shadow-holo-${feature.color} border border-holo-${feature.color}-400/30`}
                    whileHover={{ 
                      scale: 1.1, 
                      rotate: 10,
                      boxShadow: `0 0 30px rgba(0, 230, 214, 0.6)`
                    }}
                    transition={{ duration: 0.3 }}
                  >
                    <feature.icon className="w-7 h-7 text-white" />
                  </motion.div>
                  <h3 className="text-lg font-semibold text-holo-cyan-200 mb-3 font-orbitron tracking-wide">
                    {feature.title}
                  </h3>
                  <p className="text-holo-cyan-100/80 font-space leading-relaxed">
                    {feature.description}
                  </p>
                </HolographicCard>
              </motion.div>
            ))}
          </div>
        </section>

        {/* Tech Specifications Section */}
        <motion.section
          initial={{ y: 50, opacity: 0 }}
          whileInView={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.8 }}
          viewport={{ once: true }}
          className="max-w-6xl mx-auto px-6 py-20"
        >
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-holo-cyan-300 mb-6 font-orbitron tracking-wide text-holo-glow">
              SYSTEM SPECIFICATIONS
            </h2>
            <p className="text-xl text-holo-cyan-100 max-w-3xl mx-auto font-space">
              Built with a reliable, open-source stack for speed and accessibility.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {[
              {
                icon: Brain,
                title: "GROQ LLAMA 3 70B",
                description: "Fast, high-quality responses for chat (generation)",
                color: "holo-purple"
              },
              {
                icon: Zap,
                  title: "VERCEL FRONTEND",
                  description: "Global hosting for the React + Vite app",
                color: "holo-cyan"
              },
              {
                icon: Shield,
                  title: "RENDER BACKEND",
                  description: "FastAPI + MongoDB Atlas + Pinecone + Gemini embeddings",
                color: "holo-blue"
              }
            ].map((spec, index) => (
              <motion.div
                key={spec.title}
                initial={{ opacity: 0, y: 30, scale: 0.8 }}
                whileInView={{ opacity: 1, y: 0, scale: 1 }}
                transition={{ duration: 0.6, delay: index * 0.2 }}
                viewport={{ once: true }}
                whileHover={{ scale: 1.05, rotateY: 5 }}
              >
                <HolographicCard variant="glow" hover={true} className="p-6 h-full">
                  <motion.div 
                    className={`w-12 h-12 bg-gradient-to-br from-${spec.color}-500 to-${spec.color}-600 rounded-lg flex items-center justify-center mb-4 shadow-${spec.color} border border-${spec.color}-400/30`}
                    whileHover={{ rotate: 10, scale: 1.1 }}
                    transition={{ duration: 0.3 }}
                  >
                    <spec.icon className="w-6 h-6 text-white" />
                  </motion.div>
                  <h3 className="text-lg font-bold text-holo-cyan-200 mb-3 font-orbitron tracking-wide">{spec.title}</h3>
                  <p className="text-holo-cyan-100/70 font-space leading-relaxed">
                    {spec.description}
                  </p>
                </HolographicCard>
              </motion.div>
            ))}
          </div>

          <motion.div 
            className="text-center mt-16"
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.3 }}
            viewport={{ once: true }}
          >
            <p className="text-holo-cyan-100 mb-8 font-space text-lg">
              Like Kuro? Support development and new features.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <HolographicButton
                variant="ghost"
                size="lg"
                className="font-orbitron tracking-wide"
                onClick={() => window.open('https://github.com/Gaurav8302/Kuro', '_blank')}
              >
                <Star className="w-5 h-5 mr-2" />
                VIEW SOURCE
              </HolographicButton>
              <HolographicButton
                variant="secondary"
                size="lg"
                className="font-orbitron tracking-wide"
                onClick={() => window.open('https://github.com/sponsors/Gaurav8302', '_blank')}
              >
                <Brain className="w-5 h-5 mr-2" />
                SPONSOR
              </HolographicButton>
            </div>
          </motion.div>
        </motion.section>

        {/* CTA Section */}
        <motion.section
          initial={{ y: 50, opacity: 0, scale: 0.9 }}
          whileInView={{ y: 0, opacity: 1, scale: 1 }}
          transition={{ duration: 0.8 }}
          viewport={{ once: true }}
          className="max-w-4xl mx-auto px-6 py-20 text-center"
        >
          <HolographicCard variant="intense" className="p-12 relative overflow-hidden">
            {/* Animated background pattern */}
            <div className="absolute inset-0 opacity-20">
              <motion.div
                className="absolute inset-0 bg-gradient-to-r from-holo-cyan-500/20 via-holo-purple-500/20 to-holo-blue-500/20"
                animate={{ 
                  backgroundPosition: ['0% 50%', '100% 50%', '0% 50%']
                }}
                transition={{ duration: 8, repeat: Infinity }}
                style={{ backgroundSize: '200% 200%' }}
              />
            </div>
            
            <div className="relative z-10">
              <motion.h2 
                className="text-4xl font-bold text-holo-cyan-300 mb-6 font-orbitron tracking-wide text-holo-glow"
                animate={{ 
                  textShadow: [
                    '0 0 20px #00e6d6',
                    '0 0 40px #8c1aff',
                    '0 0 20px #00e6d6'
                  ]
                }}
                transition={{ duration: 3, repeat: Infinity }}
              >
                READY TO CHAT?
              </motion.h2>
              <p className="text-xl text-holo-cyan-100 mb-8 font-space">
                Start a conversation with Kuro.
              </p>
              <HolographicButton
                variant="primary"
              size="xl"
              onClick={handleStartChat}
              className="font-orbitron tracking-wide group"
            >
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
                className="mr-3"
              >
                <HoloBrainIcon size={20} />
              </motion.div>
              START CHAT
              <motion.div
                className="ml-3"
                animate={{ x: [0, 5, 0] }}
                transition={{ duration: 1.5, repeat: Infinity }}
              >
                <ArrowRight className="w-5 h-5" />
              </motion.div>
            </HolographicButton>
            </div>
          </HolographicCard>
        </motion.section>
      </div>
    </div>
  );
};

export default Landing;