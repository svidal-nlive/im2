'use client';

import { useState, useEffect } from 'react';
import { jobsApi } from '@/lib/api';
import { toast } from 'react-toastify';

interface Job {
  id: string;
  filename: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  created_at: string;
  updated_at: string;
  current_stage: string;
  progress: number;
  error_message?: string;
}

export default function JobList() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    const fetchJobs = async () => {
      try {
        const response = await jobsApi.getJobs({ status: filter !== 'all' ? filter : undefined });
        setJobs(response.data);
      } catch (error) {
        console.error('Error fetching jobs:', error);
        toast.error('Failed to load jobs');
      } finally {
        setIsLoading(false);
      }
    };

    fetchJobs();
    
    // Set up polling for active jobs
    const intervalId = setInterval(fetchJobs, 5000);
    
    return () => clearInterval(intervalId);
  }, [filter]);

  const cancelJob = async (jobId: string) => {
    try {
      await jobsApi.cancelJob(jobId);
      toast.success('Job cancelled successfully');
      // Refresh the job list
      const response = await jobsApi.getJobs({ status: filter !== 'all' ? filter : undefined });
      setJobs(response.data);
    } catch (error) {
      console.error('Error cancelling job:', error);
      toast.error('Failed to cancel job');
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300';
      case 'processing':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300';
      case 'completed':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300';
      case 'failed':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300';
    }
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary-500"></div>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-4 flex flex-wrap gap-2">
        <button
          onClick={() => setFilter('all')}
          className={`px-3 py-1 rounded-full text-sm font-medium ${
            filter === 'all'
              ? 'bg-primary-500 text-white'
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600'
          }`}
        >
          All
        </button>
        <button
          onClick={() => setFilter('pending')}
          className={`px-3 py-1 rounded-full text-sm font-medium ${
            filter === 'pending'
              ? 'bg-primary-500 text-white'
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600'
          }`}
        >
          Pending
        </button>
        <button
          onClick={() => setFilter('processing')}
          className={`px-3 py-1 rounded-full text-sm font-medium ${
            filter === 'processing'
              ? 'bg-primary-500 text-white'
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600'
          }`}
        >
          Processing
        </button>
        <button
          onClick={() => setFilter('completed')}
          className={`px-3 py-1 rounded-full text-sm font-medium ${
            filter === 'completed'
              ? 'bg-primary-500 text-white'
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600'
          }`}
        >
          Completed
        </button>
        <button
          onClick={() => setFilter('failed')}
          className={`px-3 py-1 rounded-full text-sm font-medium ${
            filter === 'failed'
              ? 'bg-primary-500 text-white'
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600'
          }`}
        >
          Failed
        </button>
      </div>

      {jobs.length === 0 ? (
        <div className="bg-white dark:bg-gray-800 shadow overflow-hidden sm:rounded-md p-6 text-center">
          <p className="text-gray-500 dark:text-gray-400">No jobs found</p>
        </div>
      ) : (
        <ul className="bg-white dark:bg-gray-800 shadow overflow-hidden sm:rounded-md">
          {jobs.map((job) => (
            <li key={job.id} className="border-b border-gray-200 dark:border-gray-700 last:border-b-0">
              <div className="px-4 py-4 sm:px-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <p className="text-sm font-medium text-primary-600 truncate">{job.filename}</p>
                    <span
                      className={`ml-2 px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusColor(
                        job.status
                      )}`}
                    >
                      {job.status}
                    </span>
                  </div>
                  <div className="flex space-x-2">
                    {(job.status === 'pending' || job.status === 'processing') && (
                      <button
                        onClick={() => cancelJob(job.id)}
                        className="inline-flex items-center px-2.5 py-1.5 border border-transparent text-xs font-medium rounded text-red-700 bg-red-100 hover:bg-red-200 dark:bg-red-900 dark:text-red-100 dark:hover:bg-red-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
                      >
                        Cancel
                      </button>
                    )}
                    {job.status === 'completed' && (
                      <button className="inline-flex items-center px-2.5 py-1.5 border border-transparent text-xs font-medium rounded text-green-700 bg-green-100 hover:bg-green-200 dark:bg-green-900 dark:text-green-100 dark:hover:bg-green-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500">
                        Download
                      </button>
                    )}
                    {job.status === 'failed' && (
                      <button className="inline-flex items-center px-2.5 py-1.5 border border-transparent text-xs font-medium rounded text-primary-700 bg-primary-100 hover:bg-primary-200 dark:bg-primary-900 dark:text-primary-100 dark:hover:bg-primary-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500">
                        Retry
                      </button>
                    )}
                  </div>
                </div>
                <div className="mt-2 sm:flex sm:justify-between">
                  <div className="sm:flex">
                    <p className="flex items-center text-sm text-gray-500 dark:text-gray-400">
                      Stage: {job.current_stage || 'Not started'}
                    </p>
                  </div>
                  <div className="mt-2 flex items-center text-sm text-gray-500 sm:mt-0 dark:text-gray-400">
                    <p>
                      Created: {new Date(job.created_at).toLocaleDateString()} {new Date(job.created_at).toLocaleTimeString()}
                    </p>
                  </div>
                </div>
                {(job.status === 'pending' || job.status === 'processing') && (
                  <div className="mt-2">
                    <div className="w-full bg-gray-200 rounded-full h-2.5 dark:bg-gray-700">
                      <div
                        className="bg-primary-600 h-2.5 rounded-full"
                        style={{ width: `${job.progress || 0}%` }}
                      ></div>
                    </div>
                    <p className="text-xs text-gray-500 mt-1 dark:text-gray-400">{job.progress || 0}% complete</p>
                  </div>
                )}
                {job.status === 'failed' && job.error_message && (
                  <div className="mt-2 text-sm text-red-600 dark:text-red-400">
                    <p>Error: {job.error_message}</p>
                  </div>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
