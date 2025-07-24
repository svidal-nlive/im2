'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { jobsApi, filesApi } from '@/lib/api';
import { toast } from 'react-toastify';
import { formatDistanceToNow, format } from 'date-fns';

interface JobDetail {
  id: string;
  status: string;
  created_at: string;
  updated_at: string;
  completed_at?: string;
  filename: string;
  job_type: string;
  file_id: string;
  error_message?: string;
  metadata?: Record<string, any>;
}

export default function JobDetailPage() {
  const params = useParams();
  const router = useRouter();
  const [job, setJob] = useState<JobDetail | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [logs, setLogs] = useState<string>('');
  const [isLoadingLogs, setIsLoadingLogs] = useState<boolean>(false);
  const [isRetrying, setIsRetrying] = useState<boolean>(false);
  const [isCanceling, setIsCanceling] = useState<boolean>(false);
  const [isDownloading, setIsDownloading] = useState<boolean>(false);
  
  const jobId = params.id as string;

  const fetchJob = async () => {
    setIsLoading(true);
    try {
      const response = await jobsApi.getJob(jobId);
      setJob(response.data);
    } catch (error) {
      console.error('Error fetching job:', error);
      toast.error('Failed to load job details');
    } finally {
      setIsLoading(false);
    }
  };

  const fetchLogs = async () => {
    setIsLoadingLogs(true);
    try {
      const response = await jobsApi.getJobLogs(jobId);
      setLogs(response.data.logs || 'No logs available');
    } catch (error) {
      console.error('Error fetching logs:', error);
      setLogs('Failed to load logs');
    } finally {
      setIsLoadingLogs(false);
    }
  };

  useEffect(() => {
    fetchJob();
  }, [jobId]);

  const handleRetry = async () => {
    setIsRetrying(true);
    try {
      await jobsApi.retryJob(jobId);
      toast.success('Job retry initiated');
      fetchJob();
    } catch (error) {
      console.error('Error retrying job:', error);
      toast.error('Failed to retry job');
    } finally {
      setIsRetrying(false);
    }
  };

  const handleCancel = async () => {
    setIsCanceling(true);
    try {
      await jobsApi.cancelJob(jobId);
      toast.success('Job canceled successfully');
      fetchJob();
    } catch (error) {
      console.error('Error canceling job:', error);
      toast.error('Failed to cancel job');
    } finally {
      setIsCanceling(false);
    }
  };

  const handleDownload = async () => {
    if (!job) return;
    
    setIsDownloading(true);
    try {
      const response = await filesApi.downloadFile(job.file_id);
      
      // Create a download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', job.filename);
      document.body.appendChild(link);
      link.click();
      
      // Cleanup
      link.parentNode?.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast.success('File downloaded successfully');
    } catch (error) {
      console.error('Error downloading file:', error);
      toast.error('Failed to download file');
    } finally {
      setIsDownloading(false);
    }
  };

  // Get status color
  const getStatusColor = () => {
    if (!job) return '';
    
    switch (job.status.toLowerCase()) {
      case 'completed':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300';
      case 'failed':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300';
      case 'processing':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300';
      case 'queued':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300';
      case 'canceled':
        return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300';
    }
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center py-8">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="text-center py-8">
        <p className="text-gray-500 dark:text-gray-400">Job not found.</p>
        <button
          onClick={() => router.push('/jobs')}
          className="mt-4 py-2 px-4 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
        >
          Back to Jobs
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Job Details</h1>
        <button
          onClick={() => router.push('/jobs')}
          className="py-2 px-4 bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
        >
          Back to Jobs
        </button>
      </div>
      
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">{job.filename}</h2>
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor()}`}>
            {job.status}
          </span>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <div>
            <p className="text-sm text-gray-500 dark:text-gray-400">Job ID</p>
            <p className="font-medium">{job.id}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500 dark:text-gray-400">Job Type</p>
            <p className="font-medium">{job.job_type}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500 dark:text-gray-400">Created</p>
            <p className="font-medium" title={format(new Date(job.created_at), 'PPpp')}>
              {formatDistanceToNow(new Date(job.created_at), { addSuffix: true })}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500 dark:text-gray-400">Last Updated</p>
            <p className="font-medium" title={format(new Date(job.updated_at), 'PPpp')}>
              {formatDistanceToNow(new Date(job.updated_at), { addSuffix: true })}
            </p>
          </div>
          {job.completed_at && (
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Completed</p>
              <p className="font-medium" title={format(new Date(job.completed_at), 'PPpp')}>
                {formatDistanceToNow(new Date(job.completed_at), { addSuffix: true })}
              </p>
            </div>
          )}
        </div>
        
        {job.error_message && (
          <div className="mb-6">
            <p className="text-sm text-gray-500 dark:text-gray-400">Error</p>
            <div className="p-3 bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-300 rounded-lg mt-1">
              {job.error_message}
            </div>
          </div>
        )}
        
        {job.metadata && Object.keys(job.metadata).length > 0 && (
          <div className="mb-6">
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">Metadata</p>
            <div className="bg-gray-100 dark:bg-gray-700 p-3 rounded-lg">
              <pre className="text-xs overflow-auto">
                {JSON.stringify(job.metadata, null, 2)}
              </pre>
            </div>
          </div>
        )}
        
        <div className="flex space-x-3">
          {job.status === 'failed' && (
            <button
              onClick={handleRetry}
              disabled={isRetrying}
              className="py-2 px-4 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50"
            >
              {isRetrying ? 'Retrying...' : 'Retry Job'}
            </button>
          )}
          
          {(job.status === 'queued' || job.status === 'processing') && (
            <button
              onClick={handleCancel}
              disabled={isCanceling}
              className="py-2 px-4 bg-red-600 hover:bg-red-700 text-white font-medium rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500 disabled:opacity-50"
            >
              {isCanceling ? 'Canceling...' : 'Cancel Job'}
            </button>
          )}
          
          {job.status === 'completed' && (
            <button
              onClick={handleDownload}
              disabled={isDownloading}
              className="py-2 px-4 bg-green-600 hover:bg-green-700 text-white font-medium rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 disabled:opacity-50"
            >
              {isDownloading ? 'Downloading...' : 'Download Result'}
            </button>
          )}
        </div>
      </div>
      
      {/* Logs Section */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">Logs</h2>
          <button
            onClick={fetchLogs}
            disabled={isLoadingLogs}
            className="py-1 px-3 bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 text-sm rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50"
          >
            {isLoadingLogs ? 'Loading...' : 'Refresh Logs'}
          </button>
        </div>
        
        <div className="bg-gray-100 dark:bg-gray-900 p-3 rounded-lg max-h-96 overflow-y-auto">
          {logs ? (
            <pre className="text-xs whitespace-pre-wrap font-mono">{logs}</pre>
          ) : (
            <div className="text-center py-4">
              <button
                onClick={fetchLogs}
                disabled={isLoadingLogs}
                className="py-2 px-4 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50"
              >
                {isLoadingLogs ? 'Loading...' : 'Load Logs'}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
