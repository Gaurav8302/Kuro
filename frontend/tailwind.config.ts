import type { Config } from "tailwindcss";
import tailwindcssAnimate from 'tailwindcss-animate';
import typography from '@tailwindcss/typography';

export default {
  darkMode: ["class"],
  content: [
    "./pages/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./app/**/*.{ts,tsx}",
    "./src/**/*.{ts,tsx}",
  ],
  prefix: "",
  theme: {
    container: {
      center: true,
      padding: '2rem',
      screens: {
        '2xl': '1400px'
      }
    },
    extend: {
      fontFamily: {
        orbitron: ['Orbitron', 'monospace'],
        space: ['Space Grotesk', 'sans-serif'],
        rajdhani: ['Rajdhani', 'sans-serif'],
        inter: ['Inter', 'sans-serif'],
      },
      colors: {
        // Base system colors
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        
        // Holographic color system
        holo: {
          cyan: {
            50: '#e0fffe',
            100: '#b3fffc',
            200: '#80fff9',
            300: '#4dfff6',
            400: '#1afff3',
            500: '#00e6d6',
            600: '#00b3a6',
            700: '#008075',
            800: '#004d45',
            900: '#001a16',
          },
          blue: {
            50: '#e6f3ff',
            100: '#b3d9ff',
            200: '#80bfff',
            300: '#4da6ff',
            400: '#1a8cff',
            500: '#0073e6',
            600: '#005ab3',
            700: '#004080',
            800: '#00264d',
            900: '#000d1a',
          },
          purple: {
            50: '#f3e6ff',
            100: '#d9b3ff',
            200: '#bf80ff',
            300: '#a64dff',
            400: '#8c1aff',
            500: '#7300e6',
            600: '#5a00b3',
            700: '#400080',
            800: '#26004d',
            900: '#0d001a',
          },
          magenta: {
            50: '#ffe6f7',
            100: '#ffb3e6',
            200: '#ff80d4',
            300: '#ff4dc3',
            400: '#ff1ab1',
            500: '#e6009f',
            600: '#b3007c',
            700: '#800059',
            800: '#4d0036',
            900: '#1a0013',
          },
          green: {
            50: '#e6ffe6',
            100: '#b3ffb3',
            200: '#80ff80',
            300: '#4dff4d',
            400: '#1aff1a',
            500: '#00e600',
            600: '#00b300',
            700: '#008000',
            800: '#004d00',
            900: '#001a00',
          },
        },
        
        // Theme colors
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))'
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))'
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))'
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))'
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))'
        },
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))'
        },
        sidebar: {
          DEFAULT: 'hsl(var(--sidebar-background))',
          foreground: 'hsl(var(--sidebar-foreground))',
          primary: 'hsl(var(--sidebar-primary))',
          'primary-foreground': 'hsl(var(--sidebar-primary-foreground))',
          accent: 'hsl(var(--sidebar-accent))',
          'accent-foreground': 'hsl(var(--sidebar-accent-foreground))',
          border: 'hsl(var(--sidebar-border))',
          ring: 'hsl(var(--sidebar-ring))'
        }
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)'
      },
      boxShadow: {
        'holo-glow': '0 0 12px rgba(0, 230, 214, 0.5), 0 0 24px rgba(0, 230, 214, 0.25)',
        'holo-blue': '0 0 12px rgba(26, 140, 255, 0.5), 0 0 24px rgba(26, 140, 255, 0.25)',
        'holo-purple': '0 0 12px rgba(140, 26, 255, 0.5), 0 0 24px rgba(140, 26, 255, 0.25)',
        'holo-magenta': '0 0 12px rgba(255, 26, 177, 0.5), 0 0 24px rgba(255, 26, 177, 0.25)',
        'holo-green': '0 0 12px rgba(26, 255, 26, 0.5), 0 0 24px rgba(26, 255, 26, 0.25)',
        'glass': '0 4px 16px 0 rgba(31, 38, 135, 0.25)',
        'glass-strong': '0 4px 20px 0 rgba(31, 38, 135, 0.4)',
      },
      backdropBlur: {
        'xs': '2px',
      },
      animation: {
        'accordion-down': 'accordion-down 0.15s ease-out',
        'accordion-up': 'accordion-up 0.15s ease-out',
        'holo-pulse': 'holo-pulse 1.5s ease-in-out infinite',
        'holo-scan': 'holo-scan 2s ease-in-out infinite',
        'holo-drift': 'holo-drift 6s ease-in-out infinite',
        'holo-glow': 'holo-glow 1.5s ease-in-out infinite alternate',
        'particle-float': 'particle-float 4s ease-in-out infinite',
        'gradient-shift': 'gradient-shift 6s ease-in-out infinite',
        'typing-dots': 'typing-dots 1s ease-in-out infinite',
        'shimmer': 'shimmer 1.5s linear infinite',
        'glitch': 'glitch 0.2s ease-in-out',
        'slide-in-holo': 'slide-in-holo 0.3s ease-out',
        'fade-in-up': 'fade-in-up 0.25s ease-out',
        'bounce-glow': 'bounce-glow 0.4s ease-out',
        'scan-line': 'scan-line 2s linear infinite',
      },
      keyframes: {
        'accordion-down': {
          from: { height: '0' },
          to: { height: 'var(--radix-accordion-content-height)' }
        },
        'accordion-up': {
          from: { height: 'var(--radix-accordion-content-height)' },
          to: { height: '0' }
        },
        'holo-pulse': {
          '0%, 100%': { 
            boxShadow: '0 0 20px rgba(0, 230, 214, 0.5), 0 0 40px rgba(0, 230, 214, 0.3)',
            transform: 'scale(1)'
          },
          '50%': { 
            boxShadow: '0 0 30px rgba(0, 230, 214, 0.8), 0 0 60px rgba(0, 230, 214, 0.5)',
            transform: 'scale(1.02)'
          }
        },
        'holo-scan': {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(100%)' }
        },
        'holo-drift': {
          '0%, 100%': { transform: 'translateY(0px) rotate(0deg)' },
          '33%': { transform: 'translateY(-10px) rotate(1deg)' },
          '66%': { transform: 'translateY(5px) rotate(-1deg)' }
        },
        'holo-glow': {
          '0%': { filter: 'brightness(1) hue-rotate(0deg)' },
          '100%': { filter: 'brightness(1.2) hue-rotate(10deg)' }
        },
        'particle-float': {
          '0%, 100%': { transform: 'translateY(0px) translateX(0px) scale(1)' },
          '25%': { transform: 'translateY(-20px) translateX(10px) scale(1.1)' },
          '50%': { transform: 'translateY(-10px) translateX(-5px) scale(0.9)' },
          '75%': { transform: 'translateY(-30px) translateX(15px) scale(1.05)' }
        },
        'gradient-shift': {
          '0%, 100%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' }
        },
        'typing-dots': {
          '0%, 60%, 100%': { transform: 'translateY(0)' },
          '30%': { transform: 'translateY(-10px)' }
        },
        'shimmer': {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(100%)' }
        },
        'glitch': {
          '0%, 100%': { transform: 'translate(0)' },
          '20%': { transform: 'translate(-2px, 2px)' },
          '40%': { transform: 'translate(-2px, -2px)' },
          '60%': { transform: 'translate(2px, 2px)' },
          '80%': { transform: 'translate(2px, -2px)' }
        },
        'slide-in-holo': {
          '0%': { 
            transform: 'translateX(-100%) scale(0.8)',
            opacity: '0',
            filter: 'blur(10px)'
          },
          '100%': { 
            transform: 'translateX(0) scale(1)',
            opacity: '1',
            filter: 'blur(0px)'
          }
        },
        'fade-in-up': {
          '0%': { 
            transform: 'translateY(12px)',
            opacity: '0'
          },
          '100%': { 
            transform: 'translateY(0)',
            opacity: '1'
          }
        },
        'bounce-glow': {
          '0%': { 
            transform: 'scale(1)',
            boxShadow: '0 0 20px rgba(0, 230, 214, 0.3)'
          },
          '50%': { 
            transform: 'scale(1.05)',
            boxShadow: '0 0 40px rgba(0, 230, 214, 0.6)'
          },
          '100%': { 
            transform: 'scale(1)',
            boxShadow: '0 0 20px rgba(0, 230, 214, 0.3)'
          }
        },
        'scan-line': {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100vh)' }
        }
      },
      backgroundImage: {
        'holo-grid': `
          linear-gradient(rgba(0, 230, 214, 0.1) 1px, transparent 1px),
          linear-gradient(90deg, rgba(0, 230, 214, 0.1) 1px, transparent 1px)
        `,
        'holo-mesh': `
          radial-gradient(circle at 25% 25%, rgba(0, 230, 214, 0.2) 0%, transparent 50%),
          radial-gradient(circle at 75% 75%, rgba(140, 26, 255, 0.2) 0%, transparent 50%),
          radial-gradient(circle at 50% 50%, rgba(26, 140, 255, 0.1) 0%, transparent 50%)
        `,
        'particle-field': `
          radial-gradient(2px 2px at 20px 30px, rgba(0, 230, 214, 0.3), transparent),
          radial-gradient(2px 2px at 40px 70px, rgba(140, 26, 255, 0.3), transparent),
          radial-gradient(1px 1px at 90px 40px, rgba(26, 140, 255, 0.3), transparent),
          radial-gradient(1px 1px at 130px 80px, rgba(255, 26, 177, 0.3), transparent),
          radial-gradient(2px 2px at 160px 30px, rgba(26, 255, 26, 0.3), transparent)
        `,
      },
      backgroundSize: {
        'holo-grid': '50px 50px',
        'particle-field': '200px 100px',
      }
    }
  },
  plugins: [
    tailwindcssAnimate, 
    typography,
    function({ addUtilities, theme }) {
      const newUtilities = {
        '.glass-panel': {
          background: 'rgba(255, 255, 255, 0.05)',
          backdropFilter: 'blur(10px)',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          boxShadow: '0 8px 32px 0 rgba(31, 38, 135, 0.37)',
        },
        '.glass-panel-dark': {
          background: 'rgba(0, 0, 0, 0.2)',
          backdropFilter: 'blur(15px)',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.5)',
        },
        '.holo-border': {
          border: '1px solid transparent',
          backgroundImage: 'linear-gradient(rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0.05)), linear-gradient(45deg, #00e6d6, #8c1aff, #1a8cff, #ff1ab1)',
          backgroundOrigin: 'border-box',
          backgroundClip: 'content-box, border-box',
        },
        '.scan-lines': {
          position: 'relative',
          '&::before': {
            content: '""',
            position: 'absolute',
            top: '0',
            left: '0',
            right: '0',
            bottom: '0',
            backgroundImage: 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0, 230, 214, 0.03) 2px, rgba(0, 230, 214, 0.03) 4px)',
            pointerEvents: 'none',
            zIndex: '1',
          }
        },
        '.text-holo-glow': {
          textShadow: '0 0 10px currentColor, 0 0 20px currentColor, 0 0 30px currentColor',
        },
        '.border-holo-glow': {
          borderColor: 'rgba(0, 230, 214, 0.5)',
          boxShadow: '0 0 10px rgba(0, 230, 214, 0.3), inset 0 0 10px rgba(0, 230, 214, 0.1)',
        }
      }
      addUtilities(newUtilities)
    }
  ],
} satisfies Config;