# 🎨 AI Chat - Artistic Frontend

> **A vibrant, creative AI chatbot interface built with React, TypeScript, and lots of personality!**

This is a complete frontend-first implementation of a personalized AI chatbot with artistic design, ready for backend integration.

![AI Chat Interface](./src/assets/hero-ai.jpg)

## ✨ Features

### 🎭 **Artistic Design System**
- Vibrant color palette with gradients and animations
- Handwriting fonts (Caveat) mixed with clean typography (Inter)
- Framer Motion animations throughout
- Fun, creative UI elements - not corporate!

### 🤖 **Complete Chat Interface**
- Real-time message bubbles with animations
- Typing indicators and loading states
- Session management with rename/delete
- Responsive sidebar with chat history
- Beautiful chat input with auto-resize

### 🔐 **Authentication Ready**
- Sign In / Sign Up pages designed for Clerk integration
- Protected routes and user profile management
- Clean authentication flow

### 📱 **Responsive Design**
- Mobile-first approach
- Smooth animations and transitions
- Touch-friendly interface

## 🚀 Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

## 🔧 Backend Integration Guide

All API endpoints are clearly marked with `TODO` comments. Here's what you need to connect:

### **Chat Endpoints**
```typescript
// TODO: Replace with fetch('/api/chat', { method: 'POST', body: JSON.stringify({ message, sessionId }) })
// Hooks into backend route: POST /chat
mockApiCalls.sendMessage(message, sessionId)

// TODO: Replace with fetch(`/api/sessions/${userId}`)
// Hooks into backend route: GET /sessions/:user_id
mockApiCalls.getUserSessions(userId)

// TODO: Replace with fetch(`/api/sessions/${sessionId}`)
// Hooks into backend route: GET /chat/:session_id
mockApiCalls.getSession(sessionId)
```

### **Session Management**
```typescript
// TODO: Replace with fetch('/api/sessions', { method: 'POST' })
// Hooks into backend route: POST /session/create
mockApiCalls.createSession(title, userId)

// TODO: Replace with fetch(`/api/sessions/${sessionId}`, { method: 'PUT' })
// Hooks into backend route: PUT /session/:session_id (rename)
mockApiCalls.renameSession(sessionId, newTitle)

// TODO: Replace with fetch(`/api/sessions/${sessionId}`, { method: 'DELETE' })
// Hooks into backend route: DELETE /session/:session_id
mockApiCalls.deleteSession(sessionId)
```

### **Memory & Context**
```typescript
// TODO: Replace with fetch('/api/memory/store', { method: 'POST' })
// Hooks into backend route: POST /store-memory
mockApiCalls.storeMemory(context, sessionId)

// TODO: Replace with fetch('/api/memory/retrieve', { method: 'POST' })
// Hooks into backend route: POST /retrieve-memory
mockApiCalls.retrieveMemory(query)

// TODO: Replace with fetch(`/api/sessions/${sessionId}/summarize`, { method: 'POST' })
// Hooks into backend route: POST /session/summarize/:session_id
mockApiCalls.summarizeSession(sessionId)
```

## 🔐 Clerk Authentication Setup

1. **Get your Clerk keys** from [https://go.clerk.com/lovable](https://go.clerk.com/lovable)

2. **Replace the authentication placeholders** in:
   - `src/pages/SignIn.tsx`
   - `src/pages/SignUp.tsx`
   - `src/pages/Chat.tsx`

3. **Example Clerk integration**:
```typescript
// In SignIn.tsx
import { useSignIn } from "@clerk/clerk-react";

const { signIn, setActive } = useSignIn();

const result = await signIn.create({
  identifier: formData.email,
  password: formData.password,
});

if (result.status === "complete") {
  await setActive({ session: result.createdSessionId });
  navigate('/chat');
}
```

4. **Wrap your app** with ClerkProvider in `src/main.tsx`:
```typescript
import { ClerkProvider } from "@clerk/clerk-react";

const PUBLISHABLE_KEY = "pk_test_..."; // Your Clerk key

ReactDOM.createRoot(document.getElementById("root")!).render(
  <ClerkProvider publishableKey={PUBLISHABLE_KEY}>
    <App />
  </ClerkProvider>
);
```

## 🎨 Design System

### **Colors & Gradients**
- Primary: Purple/Magenta gradients
- Secondary: Coral/Orange tones  
- Accent: Cyan/Turquoise highlights
- Rainbow gradients for special elements

### **Typography**
- **Headings**: Caveat (handwriting font)
- **Body**: Inter (clean sans-serif)
- **Code**: Monospace

### **Animations**
- Framer Motion for page transitions
- CSS animations for micro-interactions
- Hover effects and loading states
- Typing indicators

## 📁 Project Structure

```
src/
├── assets/               # Images and static files
├── components/          
│   ├── ui/              # shadcn components (enhanced)
│   ├── ChatBubble.tsx   # Message display component
│   ├── ChatInput.tsx    # Message input with animations
│   └── Sidebar.tsx      # Session management sidebar
├── data/
│   └── mockData.ts      # Mock data & API placeholders
├── pages/
│   ├── Landing.tsx      # Artistic landing page
│   ├── Chat.tsx         # Main chat interface
│   ├── SignIn.tsx       # Authentication pages
│   ├── SignUp.tsx       
│   └── NotFound.tsx     # 404 page
├── types/
│   └── index.ts         # TypeScript definitions
├── hooks/               # Custom hooks
├── lib/                 # Utilities
└── index.css           # Design system & animations
```

## 🔄 Switching from Mock to Real Data

1. **Find all `TODO` comments** in the codebase
2. **Replace `mockApiCalls`** with actual `fetch()` calls
3. **Update the data shapes** in `src/types/index.ts` if needed
4. **Test each endpoint** individually
5. **Update error handling** for your specific API responses

## 🎯 Key Features Ready for Backend

- ✅ **Message streaming** (just connect WebSocket)
- ✅ **Session persistence** (replace localStorage with DB)
- ✅ **User management** (integrate with Clerk)
- ✅ **Memory context** (connect to vector DB)
- ✅ **File uploads** (add endpoint + UI)
- ✅ **Export/sharing** (add backend generation)

## 🚀 Deployment

Built for modern deployment platforms:

```bash
# Production build
npm run build

# Preview build
npm run preview
```

Deploy to Vercel, Netlify, or any static hosting platform. The build output will be in `dist/`.

## 🎨 Customization

### **Changing Colors**
Edit `src/index.css` CSS variables:
```css
:root {
  --primary: 285 85% 58%;        /* Purple */
  --secondary: 25 95% 68%;       /* Coral */
  --accent: 185 85% 58%;         /* Cyan */
  /* Add your brand colors here */
}
```

### **Adding New Animations**
Add to `tailwind.config.ts`:
```typescript
animation: {
  'your-animation': 'your-keyframes 2s ease-in-out infinite'
}
```

### **Custom Components**
Follow the established patterns in `src/components/` - all components use:
- Framer Motion for animations
- Design system colors/tokens
- TypeScript for type safety
- Responsive design principles

---

## 💡 Pro Tips

1. **API Integration**: Start with one endpoint at a time
2. **Error Handling**: Update toast messages for your API errors  
3. **Performance**: The app uses React Query for caching
4. **Accessibility**: All components follow WAI-ARIA guidelines
5. **SEO**: Add meta tags in `index.html` for your domain

**Built with ❤️ and lots of ✨ for creative AI experiences!**

---

### Technologies Used

- **React 18** + **TypeScript** 
- **Vite** for blazing-fast development
- **Tailwind CSS** + **Custom Design System**
- **Framer Motion** for animations
- **shadcn/ui** components (heavily customized)
- **React Router** for navigation
- **Clerk** ready for authentication
- **Lucide React** for beautiful icons
