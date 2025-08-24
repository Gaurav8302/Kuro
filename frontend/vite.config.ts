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
        manualChunks: (id) => {
          // Only create manual chunks in production
          if (mode === 'production') {
            if (id.includes('node_modules')) {
              if (id.includes('@radix-ui')) return 'ui';
              if (id.includes('@clerk')) return 'clerk';
              if (id.includes('framer-motion')) return 'motion';
              if (id.includes('react-router-dom')) return 'router';
              if (id.includes('@tanstack/react-query')) return 'query';
              if (id.includes('lucide-react')) return 'icons';
              if (id.includes('react-markdown') || id.includes('remark') || id.includes('rehype')) return 'markdown';
              // Group other vendor libraries
              return 'vendor';
            }
          }
        }
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
