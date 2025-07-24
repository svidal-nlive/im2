'use client';

import { useState } from 'react';
import { systemApi } from '@/lib/api';
import { toast } from 'react-toastify';

interface SystemStatusCardProps {
  status: 'running' | 'paused' | 'error';
  queueSize: number;
  activeJobs: number;
  failedJobs: number;
  completedJobs: number;
}

export default function SystemStatusCard({
  status,
  queueSize,
  activeJobs,
  failedJobs,
  completedJobs,
}: SystemStatusCardProps) {
  const [isLoading, setIsLoading] = useState(false);

  const handleTogglePipeline = async () => {
    setIsLoading(true);
    try {
      if (status === 'paused') {
        await systemApi.resumeQueue();
        toast.success('Pipeline resumed successfully');
      } else {
        await systemApi.pauseQueue();
        toast.success('Pipeline paused successfully');
      }
      // We'll let the parent component handle the refresh
    } catch (error) {
      console.error('Error toggling pipeline:', error);
      toast.error('Failed to toggle pipeline status');
    } finally {
      setIsLoading(false);
    }
  };

  // Determine status colors
  const getStatusColor = () => {
    switch (status) {
      case 'running':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300';
      case 'paused':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300';
      case 'error':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300';
    }
  };

  // Format status text
  const getStatusText = () => {
    switch (status) {
      case 'running':
        return 'Running';
      case 'paused':
        return 'Paused';
      case 'error':
        return 'Error';
      default:
        return 'Unknown';
    }
  };

  return (
    <div className="p-6 bg-white dark:bg-gray-800 rounded-lg shadow-md">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-semibold">System Status</h2>
        <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor()}`}>
          {getStatusText()}
        </span>
      </div>
      
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="bg-gray-100 dark:bg-gray-700 p-3 rounded-lg">
          <div className="text-gray-500 dark:text-gray-400 text-sm">Queue Size</div>
          <div className="font-bold text-xl">{queueSize}</div>
        </div>
        <div className="bg-gray-100 dark:bg-gray-700 p-3 rounded-lg">
          <div className="text-gray-500 dark:text-gray-400 text-sm">Active Jobs</div>
          <div className="font-bold text-xl">{activeJobs}</div>
        </div>
        <div className="bg-gray-100 dark:bg-gray-700 p-3 rounded-lg">
          <div className="text-gray-500 dark:text-gray-400 text-sm">Failed Jobs</div>
          <div className="font-bold text-xl">{failedJobs}</div>
        </div>
        <div className="bg-gray-100 dark:bg-gray-700 p-3 rounded-lg">
          <div className="text-gray-500 dark:text-gray-400 text-sm">Completed Jobs</div>
          <div className="font-bold text-xl">{completedJobs}</div>
        </div>
      </div>
      
      <button
        onClick={handleTogglePipeline}
        disabled={isLoading}
        className="w-full py-2 px-4 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50"
      >
        {isLoading
          ? 'Processing...'
          : status === 'paused'
          ? 'Resume Pipeline'
          : 'Pause Pipeline'}
      </button>
    </div>
  );
}
