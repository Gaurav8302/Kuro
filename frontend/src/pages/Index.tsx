import { useState, useEffect } from 'react';
import KuroIntro from '@/components/KuroIntro';

const Index = () => {
  const [showIntro, setShowIntro] = useState(true);

  useEffect(() => {
    const t = setTimeout(() => setShowIntro(false), 5200); // a little longer than 3 cycles
    return () => clearTimeout(t);
  }, []);

  return (
    <div className="min-h-screen bg-background relative">
      {showIntro && <KuroIntro />}
      <main className="relative z-10 flex min-h-screen items-center justify-center p-6">
        <div className="text-center max-w-xl">
          <h1 className="text-4xl md:text-6xl font-bold mb-6 tracking-tight bg-gradient-to-r from-purple-400 via-fuchsia-400 to-indigo-400 bg-clip-text text-transparent">Welcome to Kuro</h1>
          <p className="text-lg md:text-xl text-muted-foreground leading-relaxed">Your creative runtime for rapid ideation, exploration and intelligent problem solving. Dive in and start a new chat to build, learn or experiment.</p>
        </div>
      </main>
    </div>
  );
};

export default Index;
