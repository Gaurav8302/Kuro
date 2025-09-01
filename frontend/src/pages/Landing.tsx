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
import { OptimizedHolographicCard } from '@/components/OptimizedHolographicCard';
import { OptimizedHolographicBackground } from '@/components/OptimizedHolographicBackground';
import { SuspendedHolographicParticles } from '@/components/LazyComponents';
import { HoloBrainIcon, HoloSparklesIcon } from '@/components/HolographicIcons';
import { useOptimizedAnimations } from '@/hooks/use-performance';

const Landing = () => {
  const navigate = useNavigate();
  const { isSignedIn, isLoaded } = useUser();
  const { shouldReduceAnimations, animationDuration } = useOptimizedAnimations();

  // Optionally, redirect signed-in users to /chat automatically
  useEffect(() => {
    if (isLoaded && isSignedIn) {
      navigate('/chat');
    }
  }, [isLoaded, isSignedIn, navigate]);

  const features = [
    {
  icon: Brain,
  title: "SMART ROUTING",
  description: "Dynamic model selection from Groq & OpenRouter",
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
  title: "SEMANTIC MEMORY",
  description: "Gemini embeddings + Pinecone for contextual recall",
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
        <OptimizedHolographicBackground variant="subtle" />
        <div className="text-center">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ 
              duration: shouldReduceAnimations ? 1 : 2, 
              repeat: Infinity, 
              ease: 'linear' 
            }}
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
  <div className="min-app-screen bg-background overflow-hidden relative flex flex-col">
      <OptimizedHolographicBackground variant="default" />
      
      {/* Animated background elements */}
      <SuspendedHolographicParticles count={shouldReduceAnimations ? 15 : 40} size="md" className="opacity-40" />

      <div className="relative z-10">
        {/* Header */}
        <motion.header 
          className="p-6"
          initial={{ y: -50, opacity: 0, filter: 'blur(10px)' }}
          animate={{ y: 0, opacity: 1, filter: 'blur(0px)' }}
          transition={{ duration: animationDuration * 1.6, ease: 'easeOut' }}
        >
          <div className="max-w-7xl mx-auto flex items-center justify-between relative">
            {/* Header scan line */}
            {!shouldReduceAnimations && <motion.div
              className="absolute bottom-0 left-0 w-full h-0.5 bg-gradient-to-r from-transparent via-holo-cyan-400 to-transparent"
              animate={{ opacity: [0.3, 0.8, 0.3] }}
              transition={{ duration: 3, repeat: Infinity }}
            />}
            
            <div className="flex items-center gap-3">
              <motion.div 
                className="w-14 h-14 glass-panel border-holo-cyan-400/50 rounded-full flex items-center justify-center overflow-hidden shadow-holo-glow"
                whileHover={shouldReduceAnimations ? undefined : { scale: 1.1, rotate: 5 }}
                transition={{ duration: animationDuration }}
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
  <main className="max-w-7xl mx-auto px-6 py-16 md:py-20 flex-1 flex flex-col">
          <div className="grid lg:grid-cols-2 gap-12 md:gap-20 items-center">
            {/* Content */}
            <motion.div
              initial={{ x: -100, opacity: 0, filter: 'blur(10px)' }}
              animate={{ x: 0, opacity: 1, filter: 'blur(0px)' }}
              transition={{ 
                duration: shouldReduceAnimations ? 0.3 : 1, 
                delay: shouldReduceAnimations ? 0.1 : 0.3, 
                ease: 'easeOut' 
              }}
              className="text-center lg:text-left"
            >
              <motion.div
                initial={{ scale: 0, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ 
                  duration: shouldReduceAnimations ? 0.2 : 0.6, 
                  delay: shouldReduceAnimations ? 0.1 : 0.5, 
                  ease: 'backOut' 
                }}
                className="inline-flex items-center gap-3 glass-panel border-holo-cyan-400/30 px-6 py-3 rounded-full text-holo-cyan-300 mb-8 shadow-holo-glow"
              >
                {!shouldReduceAnimations && <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
                >
                  <HoloSparklesIcon size={16} />
                </motion.div>}
                {shouldReduceAnimations && <HoloSparklesIcon size={16} />}
                <span className="text-sm font-medium font-orbitron tracking-wide">MULTI‑MODEL: GROQ + GEMINI</span>
                {!shouldReduceAnimations && <motion.div
                  animate={{ scale: [1, 1.2, 1] }}
                  transition={{ duration: 2, repeat: Infinity }}
                >
                  <Star className="w-4 h-4 text-holo-cyan-400" />
                </motion.div>}
                {shouldReduceAnimations && <Star className="w-4 h-4 text-holo-cyan-400" />}
              </motion.div>

              <motion.h1 
                className="text-4xl sm:text-5xl lg:text-7xl font-bold mb-6 sm:mb-8 leading-tight"
                initial={{ opacity: 0, y: 50 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ 
                  duration: shouldReduceAnimations ? 0.3 : 0.8, 
                  delay: shouldReduceAnimations ? 0.2 : 0.7 
                }}
              >
                <span className="block text-holo-cyan-300 font-orbitron tracking-wide">SMART</span>
                <motion.span 
                  className="block hero-gradient-word font-orbitron text-holo-glow"
                  animate={shouldReduceAnimations ? {} : { 
                    textShadow: [
                      '0 0 20px #00e6d6',
                      '0 0 40px #8c1aff',
                      '0 0 20px #1a8cff',
                      '0 0 20px #00e6d6'
                    ]
                  }}
                  transition={{ 
                    duration: shouldReduceAnimations ? 0 : 4, 
                    repeat: shouldReduceAnimations ? 0 : Infinity 
                  }}
                >
                  ASSISTANT
                </motion.span>
                <span className="block text-holo-cyan-200 font-space font-light">CHAT</span>
              </motion.h1>

              <motion.div
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ 
                  duration: shouldReduceAnimations ? 0.3 : 0.8, 
                  delay: shouldReduceAnimations ? 0.2 : 0.9 
                }}
              >
                <p className="text-lg sm:text-xl text-holo-cyan-100 mb-4 sm:mb-6 leading-relaxed font-space">
                  Kuro is a production-ready AI chatbot using an advanced multi-model architecture: <strong>Groq & OpenRouter models</strong> for intelligent conversation routing and <strong>Google Gemini embeddings</strong> for semantic memory retrieval.
                </p>
                <p className="text-base sm:text-lg text-holo-cyan-200 mb-4 font-space">
                  Built with <strong>FastAPI</strong>, <strong>React</strong>, <strong>TypeScript</strong>, <strong>Pinecone vector database</strong>, and <strong>MongoDB</strong>. Features real-time chat, persistent memory, session management, and comprehensive observability.
                </p>
                <p className="text-sm sm:text-base text-holo-cyan-300 mb-6 sm:mb-8 font-space italic">
                  ⭐ Full-stack application demonstrating modern AI/ML integration, cloud deployment, and production-grade architecture patterns.
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
                transition={{ 
                  duration: shouldReduceAnimations ? 0.3 : 0.8, 
                  delay: shouldReduceAnimations ? 0.3 : 1.1, 
                  ease: 'backOut' 
                }}
              >
                <HolographicButton
                  variant="primary"
                  size="xl"
                  onClick={handleStartChat}
                  className="group font-orbitron tracking-wide"
                >
                  <MessageSquare className="w-5 h-5 mr-2" />
                  START CHAT
                  {!shouldReduceAnimations && <motion.div
                    className="ml-2"
                    animate={{ x: [0, 5, 0] }}
                    transition={{ duration: 1.5, repeat: Infinity }}
                  >
                    <ArrowRight className="w-5 h-5" />
                  </motion.div>}
                  {shouldReduceAnimations && <ArrowRight className="w-5 h-5 ml-2" />}
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
              transition={{ 
                duration: shouldReduceAnimations ? 0.3 : 1, 
                delay: shouldReduceAnimations ? 0.1 : 0.5, 
                ease: 'easeOut' 
              }}
              className="relative mt-12 lg:mt-0"
            >
              <OptimizedHolographicCard variant="intense" className="overflow-hidden">
                <div className="relative p-6 sm:p-8">
                  {/* Central holographic display */}
                  <motion.div
                    className="w-64 h-64 mx-auto relative"
                    animate={shouldReduceAnimations ? {} : { 
                      rotateY: [0, 360],
                      scale: [1, 1.05, 1]
                    }}
                    transition={{ 
                      rotateY: { 
                        duration: shouldReduceAnimations ? 0 : 10, 
                        repeat: shouldReduceAnimations ? 0 : Infinity, 
                        ease: 'linear' 
                      },
                      scale: { 
                        duration: shouldReduceAnimations ? 0 : 4, 
                        repeat: shouldReduceAnimations ? 0 : Infinity 
                      }
                    }}
                  >
                    {/* Holographic brain visualization */}
                    <div className="absolute inset-0 rounded-full border-4 border-holo-cyan-400/30 shadow-holo-glow">
                      <div className="absolute inset-4 rounded-full border-2 border-holo-purple-400/40 shadow-holo-purple">
                        <div className="absolute inset-4 rounded-full border border-holo-blue-400/50 shadow-holo-blue flex items-center justify-center">
                          <motion.div
                            animate={shouldReduceAnimations ? {} : { 
                              rotate: 360, 
                              scale: [1, 1.2, 1] 
                            }}
                            transition={{ 
                              duration: shouldReduceAnimations ? 0 : 3, 
                              repeat: shouldReduceAnimations ? 0 : Infinity, 
                              ease: 'linear' 
                            }}
                          >
                            <HoloBrainIcon size={64} className="text-holo-cyan-400" />
                          </motion.div>
                        </div>
                      </div>
                    </div>
                    
                    {/* Orbiting particles */}
                    {!shouldReduceAnimations && [0, 1, 2, 3].map(i => (
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
              </OptimizedHolographicCard>
              
              {/* Floating elements around the image */}
              {!shouldReduceAnimations && <motion.div
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
              </motion.div>}
              
              {!shouldReduceAnimations && <motion.div
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
              </motion.div>}
            </motion.div>
          </div>
        </main>

        {/* Features Section */}
        <section id="features" className="max-w-7xl mx-auto px-6 py-20">
          <motion.div
            initial={{ y: 50, opacity: 0, filter: 'blur(10px)' }}
            whileInView={{ y: 0, opacity: 1, filter: 'blur(0px)' }}
            transition={{ duration: animationDuration * 1.6, ease: 'easeOut' }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl font-bold text-holo-cyan-300 mb-6 font-orbitron tracking-wide text-holo-glow">
              ADVANCED <span className="hero-gradient-word text-6xl">CAPABILITIES</span>
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
                transition={{ 
                  duration: animationDuration * 1.2, 
                  delay: shouldReduceAnimations ? 0 : index * 0.15, 
                  ease: 'easeOut' 
                }}
                viewport={{ once: true }}
                whileHover={shouldReduceAnimations ? undefined : { 
                  y: -10, 
                  scale: 1.05, 
                  rotateY: 5 
                }}
                className="group"
              >
                <OptimizedHolographicCard 
                  variant="default" 
                  hover={true} 
                  scanLine={!shouldReduceAnimations}
                  className="p-6 h-full group-hover:shadow-holo-glow transition-all duration-500"
                >
                  <motion.div 
                    className={`w-14 h-14 rounded-xl bg-gradient-to-br from-holo-${feature.color}-500 to-holo-${feature.color}-600 flex items-center justify-center mb-6 shadow-holo-${feature.color} border border-holo-${feature.color}-400/30`}
                    whileHover={shouldReduceAnimations ? undefined : { 
                      scale: 1.1, 
                      rotate: 10,
                      boxShadow: `0 0 30px rgba(0, 230, 214, 0.6)`
                    }}
                    transition={{ duration: animationDuration }}
                  >
                    <feature.icon className="w-7 h-7 text-white" />
                  </motion.div>
                  <h3 className="text-lg font-semibold text-holo-cyan-200 mb-3 font-orbitron tracking-wide">
                    {feature.title}
                  </h3>
                  <p className="text-holo-cyan-100/80 font-space leading-relaxed">
                    {feature.description}
                  </p>
                </OptimizedHolographicCard>
              </motion.div>
            ))}
          </div>
        </section>

        {/* Tech Specifications Section */}
        <motion.section
          initial={{ y: 50, opacity: 0 }}
          whileInView={{ y: 0, opacity: 1 }}
          transition={{ duration: animationDuration * 1.6 }}
          viewport={{ once: true }}
          className="max-w-6xl mx-auto px-6 py-20"
        >
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-holo-cyan-300 mb-6 font-orbitron tracking-wide text-holo-glow">
              TECHNICAL ARCHITECTURE
            </h2>
            <p className="text-xl text-holo-cyan-100 max-w-4xl mx-auto font-space">
              Production-grade full-stack application showcasing modern AI/ML integration, cloud deployment, and enterprise architecture patterns.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {[
              {
                icon: Brain,
                title: "AI/ML STACK",
                description: "Groq LLaMA 3 70B (chat), Google Gemini (embeddings), Pinecone vector DB, LangChain orchestration",
                color: "holo-purple"
              },
              {
                icon: Cpu,
                title: "BACKEND TECH",
                description: "FastAPI, Python, MongoDB Atlas, Uvicorn ASGI, async/await patterns, RESTful APIs",
                color: "holo-blue"
              },
              {
                icon: Palette,
                title: "FRONTEND TECH",
                description: "React 18, TypeScript, Vite, TailwindCSS, Framer Motion, Clerk Auth, Axios",
                color: "holo-cyan"
              },
              {
                icon: Shield,
                title: "DEPLOYMENT",
                description: "Vercel (frontend), Render (backend), MongoDB Atlas (database), environment-based config",
                color: "holo-green"
              },
              {
                icon: Network,
                title: "ARCHITECTURE",
                description: "Microservices design, CORS handling, session management, memory persistence, observability",
                color: "holo-magenta"
              },
              {
                icon: Zap,
                title: "FEATURES",
                description: "Real-time chat, conversation memory, user auth, responsive UI, production monitoring",
                color: "holo-orange"
              }
            ].map((spec, index) => (
              <motion.div
                key={spec.title}
                initial={{ opacity: 0, y: 30, scale: 0.8 }}
                whileInView={{ opacity: 1, y: 0, scale: 1 }}
                transition={{ 
                  duration: animationDuration * 1.2, 
                  delay: shouldReduceAnimations ? 0 : index * 0.2 
                }}
                viewport={{ once: true }}
                whileHover={shouldReduceAnimations ? undefined : { scale: 1.05, rotateY: 5 }}
              >
                <OptimizedHolographicCard variant="glow" hover={true} className="p-6 h-full">
                  <motion.div 
                    className={`w-12 h-12 bg-gradient-to-br from-${spec.color}-500 to-${spec.color}-600 rounded-lg flex items-center justify-center mb-4 shadow-${spec.color} border border-${spec.color}-400/30`}
                    whileHover={shouldReduceAnimations ? undefined : { rotate: 10, scale: 1.1 }}
                    transition={{ duration: animationDuration }}
                  >
                    <spec.icon className="w-6 h-6 text-white" />
                  </motion.div>
                  <h3 className="text-lg font-bold text-holo-cyan-200 mb-3 font-orbitron tracking-wide">{spec.title}</h3>
                  <p className="text-holo-cyan-100/70 font-space leading-relaxed">
                    {spec.description}
                  </p>
                </OptimizedHolographicCard>
              </motion.div>
            ))}
          </div>

          <motion.div 
            className="text-center mt-16"
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ 
              duration: animationDuration * 1.6, 
              delay: shouldReduceAnimations ? 0.1 : 0.3 
            }}
            viewport={{ once: true }}
          >
            <div className="glass-panel border-holo-cyan-400/30 p-8 rounded-xl mb-8">
              <h3 className="text-2xl font-bold text-holo-cyan-300 mb-4 font-orbitron">🚀 FOR RECRUITERS & DEVELOPERS</h3>
              <p className="text-holo-cyan-100 mb-4 font-space text-lg">
                This is a <strong>production-ready, full-stack AI application</strong> demonstrating:
              </p>
              <ul className="text-holo-cyan-200 text-left max-w-2xl mx-auto font-space space-y-2">
                <li>✨ <strong>Modern AI/ML Integration:</strong> Multi-model architecture with vector databases</li>
                <li>🏗️ <strong>Scalable Architecture:</strong> Microservices, async processing, cloud deployment</li>
                <li>🔒 <strong>Enterprise Patterns:</strong> Authentication, session management, observability</li>
                <li>⚡ <strong>Performance Optimization:</strong> Caching, connection pooling, efficient data structures</li>
                <li>🎨 <strong>Modern Frontend:</strong> TypeScript, responsive design, real-time UI updates</li>
              </ul>
            </div>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <HolographicButton
                variant="primary"
                size="lg"
                className="font-orbitron tracking-wide"
                onClick={() => window.open('https://github.com/Gaurav8302/Kuro', '_blank')}
              >
                <Star className="w-5 h-5 mr-2" />
                VIEW SOURCE CODE
              </HolographicButton>
              <HolographicButton
                variant="secondary"
                size="lg"
                className="font-orbitron tracking-wide"
                onClick={() => window.open('https://github.com/Gaurav8302', '_blank')}
              >
                <Brain className="w-5 h-5 mr-2" />
                DEVELOPER PROFILE
              </HolographicButton>
            </div>
          </motion.div>
        </motion.section>

        {/* CTA Section */}
        <motion.section
          initial={{ y: 50, opacity: 0, scale: 0.9 }}
          whileInView={{ y: 0, opacity: 1, scale: 1 }}
          transition={{ duration: animationDuration * 1.6 }}
          viewport={{ once: true }}
          className="max-w-4xl mx-auto px-6 py-20 text-center"
        >
          <OptimizedHolographicCard variant="intense" className="p-12 relative overflow-hidden">
            {/* Animated background pattern */}
            {!shouldReduceAnimations && <div className="absolute inset-0 opacity-20">
              <motion.div
                className="absolute inset-0 bg-gradient-to-r from-holo-cyan-500/20 via-holo-purple-500/20 to-holo-blue-500/20"
                animate={{ 
                  backgroundPosition: ['0% 50%', '100% 50%', '0% 50%']
                }}
                transition={{ duration: 8, repeat: Infinity }}
                style={{ backgroundSize: '200% 200%' }}
              />
            </div>}
            
            <div className="relative z-10">
              <motion.h2 
                className="text-4xl font-bold text-holo-cyan-300 mb-6 font-orbitron tracking-wide text-holo-glow"
                animate={shouldReduceAnimations ? {} : { 
                  textShadow: [
                    '0 0 20px #00e6d6',
                    '0 0 40px #8c1aff',
                    '0 0 20px #00e6d6'
                  ]
                }}
                transition={{ 
                  duration: shouldReduceAnimations ? 0 : 3, 
                  repeat: shouldReduceAnimations ? 0 : Infinity 
                }}
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
              {!shouldReduceAnimations && <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
                className="mr-3"
              >
                <HoloBrainIcon size={20} />
              </motion.div>}
              {shouldReduceAnimations && <HoloBrainIcon size={20} className="mr-3" />}
              START CHAT
              {!shouldReduceAnimations && <motion.div
                className="ml-3"
                animate={{ x: [0, 5, 0] }}
                transition={{ duration: 1.5, repeat: Infinity }}
              >
                <ArrowRight className="w-5 h-5" />
              </motion.div>}
              {shouldReduceAnimations && <ArrowRight className="w-5 h-5 ml-3" />}
            </HolographicButton>
            </div>
          </OptimizedHolographicCard>
        </motion.section>
      </div>
    </div>
  );
};

export default Landing;