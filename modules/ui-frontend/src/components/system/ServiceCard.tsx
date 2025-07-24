'use client';

import { useState } from 'react';
import { systemApi } from '@/lib/api';
import { toast } from 'react-toastify';

interface ServiceCardProps {
  name: string;
  status: 'running' | 'stopped' | 'error';
  message?: string;
}

export default function ServiceCard({ name, status, message }: ServiceCardProps) {
  const [isRestarting, setIsRestarting] = useState(false);

  const handleRestartService = async () => {
    setIsRestarting(true);
    try {
      await systemApi.restartService(name);
      toast.success(`${name} service restarted successfully`);
    } catch (error) {
      console.error(`Error restarting ${name} service:`, error);
      toast.error(`Failed to restart ${name} service`);
    } finally {
      setIsRestarting(false);
    }
  };

  // Determine status colors
  const getStatusColor = () => {
    switch (status) {
      case 'running':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300';
      case 'stopped':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300';
      case 'error':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300';
    }
  };

  return (
    <div className="p-4 bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
      <div className="flex justify-between items-center mb-2">
        <h3 className="font-medium">{name}</h3>
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor()}`}>
          {status}
        </span>
      </div>
      
      {message && (
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-3 truncate" title={message}>
          {message}
        </p>
      )}
      
      <button
        onClick={handleRestartService}
        disabled={isRestarting}
        className="w-full py-1 px-2 text-sm bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 rounded focus:outline-none focus:ring-1 focus:ring-primary-500 disabled:opacity-50"
      >
        {isRestarting ? 'Restarting...' : 'Restart'}
      </button>
    </div>
  );
}
