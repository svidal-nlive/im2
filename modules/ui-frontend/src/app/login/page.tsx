'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import LoginForm from '@/components/auth/LoginForm';
import { useAuthStore } from '@/lib/auth-store';

export default function LoginPage() {
  const router = useRouter();
  const { isAuthenticated, checkAuth } = useAuthStore();

  useEffect(() => {
    // If already authenticated, redirect to dashboard
    const verifyAuth = async () => {
      if (isAuthenticated) {
        router.push('/');
      } else {
        // Try to verify token in case page was refreshed
        await checkAuth();
        if (isAuthenticated) {
          router.push('/');
        }
      }
    };
    
    verifyAuth();
  }, [isAuthenticated, checkAuth, router]);

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100 dark:bg-gray-900">
      <div className="max-w-md w-full p-8 bg-white dark:bg-gray-800 rounded-lg shadow-lg">
        <h1 className="text-2xl font-bold text-center mb-6 text-gray-900 dark:text-white">IM2 Audio Processing</h1>
        <LoginForm />
      </div>
    </div>
  );
}
