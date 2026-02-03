import { motion } from "framer-motion";
import { Link, useNavigate } from "react-router-dom";
import { useEffect } from "react";
import { useUser, useAuth, SignedIn, SignedOut, UserButton } from "@clerk/clerk-react";
import { ArrowRight, Sparkles, Zap, Shield } from "lucide-react";
import KuroBot3D from "@/components/kuro/KuroBot3D";
import { Button } from "@/components/ui/button";

const Header = () => {
  return (
    <motion.header
      className="fixed top-0 left-0 right-0 z-50 glass"
      initial={{ y: -100, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
    >
      <div className="container mx-auto px-6 h-16 flex items-center justify-between">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2 group">
          <div className="w-8 h-8 rounded-lg overflow-hidden">
            <img src="/kuroai.png" alt="Kuro" className="w-full h-full object-cover" />
          </div>
          <span className="text-lg font-semibold text-foreground group-hover:text-primary transition-colors">
            Kuro
          </span>
        </Link>

        {/* Navigation */}
        <nav className="hidden md:flex items-center gap-8">
          <Link
            to="/"
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            Home
          </Link>
          <Link
            to="/chat"
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            Chat
          </Link>
        </nav>

        {/* Auth CTA */}
        <div className="flex items-center gap-3">
          <SignedOut>
            <Button variant="ghost" size="sm" asChild>
              <Link to="/auth/signin">Sign in</Link>
            </Button>
            <Button variant="hero" size="sm" asChild>
              <Link to="/auth/signup">Get Started</Link>
            </Button>
          </SignedOut>
          <SignedIn>
            <Button variant="hero" size="sm" asChild>
              <Link to="/chat">Open Chat</Link>
            </Button>
            <UserButton afterSignOutUrl="/" />
          </SignedIn>
        </div>
      </div>
    </motion.header>
  );
};

const Landing = () => {
  const navigate = useNavigate();
  const { isSignedIn, isLoaded } = useUser();

  // Redirect signed-in users to chat
  useEffect(() => {
    if (isLoaded && isSignedIn) {
      navigate("/chat");
    }
  }, [isLoaded, isSignedIn, navigate]);

  return (
    <div className="min-h-screen bg-background kuro-gradient noise-overlay">
      <Header />

      {/* Hero Section */}
      <section className="relative min-h-screen flex flex-col items-center justify-center px-6 pt-16 overflow-hidden">
        {/* Background grid pattern */}
        <div
          className="absolute inset-0 opacity-[0.02]"
          style={{
            backgroundImage: `
              linear-gradient(to right, hsl(var(--foreground)) 1px, transparent 1px),
              linear-gradient(to bottom, hsl(var(--foreground)) 1px, transparent 1px)
            `,
            backgroundSize: "60px 60px",
          }}
        />

        {/* Kuro 3D Bot */}
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 1, ease: "easeOut" }}
          className="relative z-10 mb-8"
        >
          <KuroBot3D className="w-80 h-80 md:w-96 md:h-96" />
        </motion.div>

        {/* Hero Content */}
        <motion.div
          className="relative z-10 text-center max-w-3xl mx-auto"
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.3 }}
        >
          <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6">
            <span className="text-foreground">Kuro.</span>
            <br />
            <span className="text-muted-foreground">Your personal AI interface.</span>
          </h1>

          <p className="text-lg md:text-xl text-muted-foreground mb-10 max-w-xl mx-auto leading-relaxed">
            A calm, powerful assistant designed for meaningful conversations. 
            No noise. Just clarity.
          </p>

          {/* CTAs */}
          <motion.div
            className="flex flex-col sm:flex-row items-center justify-center gap-4"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.6 }}
          >
            <Button variant="hero" size="xl" asChild>
              <Link to="/chat">
                Start Chat
                <ArrowRight className="ml-2 h-5 w-5" />
              </Link>
            </Button>
            <Button variant="hero-secondary" size="xl" asChild>
              <Link to="#features">
                Learn more
              </Link>
            </Button>
          </motion.div>
        </motion.div>

        {/* Scroll indicator */}
        <motion.div
          className="absolute bottom-8 left-1/2 -translate-x-1/2"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.5 }}
        >
          <motion.div
            className="w-6 h-10 rounded-full border-2 border-muted-foreground/30 flex justify-center pt-2"
            animate={{ y: [0, 5, 0] }}
            transition={{ duration: 2, repeat: Infinity }}
          >
            <div className="w-1 h-2 rounded-full bg-muted-foreground/50" />
          </motion.div>
        </motion.div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-32 px-6">
        <div className="container mx-auto max-w-6xl">
          <motion.div
            className="text-center mb-20"
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
          >
            <h2 className="text-3xl md:text-4xl font-bold text-foreground mb-4">
              Designed for depth
            </h2>
            <p className="text-muted-foreground text-lg max-w-xl mx-auto">
              Every interaction is crafted to feel natural, powerful, and purposeful.
            </p>
          </motion.div>

          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                icon: Sparkles,
                title: "Intelligent Responses",
                description:
                  "Context-aware conversations that understand nuance and deliver meaningful insights.",
              },
              {
                icon: Zap,
                title: "Instant Clarity",
                description:
                  "Fast, focused answers without the clutter. Get to what matters, quickly.",
              },
              {
                icon: Shield,
                title: "Private by Design",
                description:
                  "Your conversations stay yours. Built with privacy as a foundation, not an afterthought.",
              },
            ].map((feature, index) => (
              <motion.div
                key={feature.title}
                className="group p-8 rounded-2xl glass hover-glow cursor-default"
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
              >
                <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center mb-6 group-hover:bg-primary/20 transition-colors">
                  <feature.icon className="w-6 h-6 text-primary" />
                </div>
                <h3 className="text-xl font-semibold text-foreground mb-3">
                  {feature.title}
                </h3>
                <p className="text-muted-foreground leading-relaxed">
                  {feature.description}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 px-6 border-t border-border">
        <div className="container mx-auto max-w-6xl">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-md overflow-hidden">
                <img src="/kuroai.png" alt="Kuro" className="w-full h-full object-cover" />
              </div>
              <span className="text-sm text-muted-foreground">
                Kuro — Your personal AI interface
              </span>
            </div>
            <div className="text-sm text-muted-foreground">
              © 2026 Kuro. All rights reserved.
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Landing;
