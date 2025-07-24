'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuthStore } from '@/lib/auth-store';
import { useState, useEffect } from 'react';

interface NavItem {
  name: string;
  href: string;
  icon: string;
}

const navigation: NavItem[] = [
  { name: 'Dashboard', href: '/', icon: 'home' },
  { name: 'Upload', href: '/upload', icon: 'upload' },
  { name: 'Jobs', href: '/jobs', icon: 'briefcase' },
  { name: 'Files', href: '/files', icon: 'folder' },
  { name: 'System', href: '/system', icon: 'server' },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { isAuthenticated, logout, user } = useAuthStore();
  const [isOpen, setIsOpen] = useState(false);

  // Close the sidebar when clicking outside
  useEffect(() => {
    const handleOutsideClick = (event: MouseEvent) => {
      if (isOpen && (event.target as HTMLElement).closest('[data-sidebar]') === null) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleOutsideClick);
    return () => {
      document.removeEventListener('mousedown', handleOutsideClick);
    };
  }, [isOpen]);

  // Close the sidebar when the route changes
  useEffect(() => {
    setIsOpen(false);
  }, [pathname]);

  return (
    <>
      {/* Mobile sidebar toggle */}
      <button
        type="button"
        className="lg:hidden fixed top-4 left-4 z-50 p-2 rounded-md text-gray-400 hover:text-white hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-white"
        onClick={() => setIsOpen(!isOpen)}
      >
        <span className="sr-only">Open sidebar</span>
        <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor" aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
        </svg>
      </button>

      {/* Sidebar */}
      <div
        data-sidebar
        className={`fixed inset-y-0 left-0 z-40 w-64 bg-gray-800 transform ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        } lg:translate-x-0 transition-transform duration-300 ease-in-out`}
      >
        <div className="flex h-full flex-col">
          {/* Sidebar header */}
          <div className="flex h-16 shrink-0 items-center border-b border-gray-700 px-6">
            <h1 className="text-white text-xl font-bold">IM2</h1>
          </div>

          {/* Navigation */}
          <nav className="flex-1 overflow-y-auto py-4">
            <ul className="space-y-1 px-2">
              {navigation.map((item) => (
                <li key={item.name}>
                  <Link
                    href={item.href}
                    className={`group flex items-center rounded-md px-3 py-2 text-sm font-medium ${
                      pathname === item.href
                        ? 'bg-gray-900 text-white'
                        : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                    }`}
                  >
                    <span className="mr-3 h-6 w-6 flex-shrink-0">{/* Icon would go here */}</span>
                    {item.name}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>

          {/* User section */}
          {isAuthenticated ? (
            <div className="border-t border-gray-700 p-4">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <div className="h-8 w-8 rounded-full bg-gray-500 flex items-center justify-center text-white">
                    {user?.username?.[0]?.toUpperCase() || 'U'}
                  </div>
                </div>
                <div className="ml-3">
                  <p className="text-sm font-medium text-white">{user?.username || 'User'}</p>
                  <button
                    onClick={logout}
                    className="text-xs font-medium text-gray-300 hover:text-white"
                  >
                    Logout
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="border-t border-gray-700 p-4">
              <Link
                href="/login"
                className="flex items-center rounded-md px-3 py-2 text-sm font-medium text-gray-300 hover:bg-gray-700 hover:text-white"
              >
                Login
              </Link>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
