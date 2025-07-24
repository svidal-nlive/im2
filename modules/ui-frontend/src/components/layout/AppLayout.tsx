'use client';

import { useState, useEffect } from 'react';
import { usePathname } from 'next/navigation';
import Sidebar from '@/components/layout/Sidebar';
import { useAuthStore } from '@/lib/auth-store';
import { useRouter } from 'next/navigation';
import { toast } from 'react-toastify';

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, checkAuth, isLoading } = useAuthStore();
  const router = useRouter();
  const pathname = usePathname();
  const [authChecked, setAuthChecked] = useState(false);

  // Protected routes
  const protectedRoutes = [
    '/jobs',
    '/upload',
    '/files',
    '/system',
  ];

  // Public routes
  const publicRoutes = [
    '/login',
    '/register',
    '/forgot-password',
  ];

  // Check authentication on mount
  useEffect(() => {
    const checkAuthentication = async () => {
      try {
        const isAuthed = await checkAuth();
        
        // Redirect logic
        const isProtectedRoute = protectedRoutes.some(route => 
          pathname === route || pathname.startsWith(`${route}/`)
        );
        
        const isPublicRoute = publicRoutes.some(route => 
          pathname === route || pathname.startsWith(`${route}/`)
        );
        
        if (!isAuthed && isProtectedRoute) {
          // Redirect to login if trying to access protected route
          toast.info('Please login to access this page');
          router.push('/login');
        } else if (isAuthed && isPublicRoute) {
          // Redirect to dashboard if already logged in and trying to access login/register
          router.push('/');
        }
      } catch (error) {
        console.error('Authentication check failed', error);
      } finally {
        setAuthChecked(true);
      }
    };

    checkAuthentication();
  }, [pathname]);

  // Show nothing while checking auth
  if (!authChecked) {
    return (
      <div className="flex h-screen w-screen items-center justify-center">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  // Determine if we should show the sidebar based on the route
  const showSidebar = !publicRoutes.some(route => 
    pathname === route || pathname.startsWith(`${route}/`)
  );

  return (
    <div className="flex h-screen">
      {showSidebar && <Sidebar />}
      
      <div className={`flex-1 ${showSidebar ? 'lg:ml-64' : ''} overflow-y-auto`}>
        <main className="p-4 md:p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
