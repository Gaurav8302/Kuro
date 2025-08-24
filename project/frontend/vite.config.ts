import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { componentTagger } from "lovable-tagger";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
  server: {
    host: "::",
    port: 8080,
  },
  preview: {
    host: "0.0.0.0",
    port: 3000,
  },
  build: {
    outDir: "dist",
    sourcemap: mode === "development",
    minify: mode === "production",
    target: 'es2015', // Better browser compatibility
    cssCodeSplit: true, // Enable CSS code splitting
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          ui: ['@radix-ui/react-dialog', '@radix-ui/react-dropdown-menu'],
          clerk: ['@clerk/clerk-react'],
          router: ['react-router-dom'],
          query: ['@tanstack/react-query'],
          icons: ['lucide-react'],
          motion: ['framer-motion'],
          markdown: ['react-markdown', 'remark-gfm', 'rehype-highlight'],
          performance: ['@/hooks/use-performance', '@/utils/lazyLoader']
        }
      },
      // Optimize chunk sizes
      external: (id) => {
        // Don't bundle these in production for better caching
        if (mode === 'production') {
          return ['react', 'react-dom'].includes(id);
        }
        return false;
      }
    }
  },
  optimizeDeps: {
    include: [
      'react',
      'react-dom',
      'framer-motion',
      '@clerk/clerk-react',
      'react-router-dom'
    ],
    exclude: ['@/components/LazyComponents']
  },
  plugins: [
    react(),
    mode === 'development' && componentTagger(),
  ].filter(Boolean),
  resolve: {
    alias: {
      "@": path.resolve(process.cwd(), "./src"),
    },
  },
  // Performance optimizations
  esbuild: {
    // Remove console logs in production
    drop: mode === 'production' ? ['console', 'debugger'] : [],
  },
  // CSS optimizations
  css: {
    devSourcemap: mode === 'development',
    preprocessorOptions: {
      // Optimize CSS processing
    }
  }
}));
