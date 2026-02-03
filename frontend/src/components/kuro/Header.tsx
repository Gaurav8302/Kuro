import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { SignedIn, SignedOut, UserButton } from "@clerk/clerk-react";
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
          <div className="w-8 h-8 rounded-lg overflow-hidden shadow-lg shadow-primary/20">
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

        {/* Auth Section */}
        <div className="flex items-center gap-3">
          <SignedOut>
            <Button variant="ghost" size="sm" asChild>
              <Link to="/sign-in">Sign in</Link>
            </Button>
            <Button variant="hero" size="sm" asChild>
              <Link to="/sign-up">Get Started</Link>
            </Button>
          </SignedOut>
          <SignedIn>
            <Button variant="hero" size="sm" asChild>
              <Link to="/chat">Open Chat</Link>
            </Button>
            <UserButton 
              afterSignOutUrl="/"
              appearance={{
                elements: {
                  avatarBox: "w-8 h-8",
                  userButtonPopoverCard: "bg-card border border-border shadow-xl",
                  userButtonPopoverActionButton: "hover:bg-secondary",
                  userButtonPopoverFooter: "hidden"
                }
              }}
            />
          </SignedIn>
        </div>
      </div>
    </motion.header>
  );
};

export default Header;
