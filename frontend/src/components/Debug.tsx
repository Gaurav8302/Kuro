// Debug component to check environment variables
import { useEffect } from 'react';

const Debug = () => {
  useEffect(() => {
    console.log('🔍 Environment Debug:');
    console.log('VITE_CLERK_PUBLISHABLE_KEY:', import.meta.env.VITE_CLERK_PUBLISHABLE_KEY ? '✅ Set' : '❌ Missing');
    console.log('VITE_API_URL:', import.meta.env.VITE_API_URL || '❌ Missing');
    console.log('Mode:', import.meta.env.MODE);
    console.log('Dev:', import.meta.env.DEV);
    console.log('Prod:', import.meta.env.PROD);
  }, []);

  return (
    <div style={{ 
      position: 'fixed', 
      top: 0, 
      left: 0, 
      background: 'black', 
      color: 'white', 
      padding: '10px',
      fontSize: '12px',
      zIndex: 9999 
    }}>
      <div>Debug Info (Check Console)</div>
      <div>Clerk Key: {import.meta.env.VITE_CLERK_PUBLISHABLE_KEY ? '✅' : '❌'}</div>
      <div>API URL: {import.meta.env.VITE_API_URL || 'Not Set'}</div>
    </div>
  );
};

export default Debug;
