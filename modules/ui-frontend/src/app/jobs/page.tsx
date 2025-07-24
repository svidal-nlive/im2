'use client';

import { useState, useEffect } from 'react';
import { jobsApi } from '@/lib/api';
import { toast } from 'react-toastify';
import JobCard from '@/components/jobs/JobCard';

interface Job {
  id: string;
  status: string;
  created_at: string;
  filename: string;
  job_type: string;
}

interface JobsResponse {
  items: Job[];
  total: number;
}

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [page, setPage] = useState<number>(1);
  const [hasMore, setHasMore] = useState<boolean>(true);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const limit = 10;

  const fetchJobs = async (page: number, status?: string) => {
    setIsLoading(true);
    try {
      const params: { status?: string, limit: number, offset: number } = {
        limit,
        offset: (page - 1) * limit
      };

      if (status && status !== 'all') {
        params.status = status;
      }

      const response = await jobsApi.getJobs(params);
      const data: JobsResponse = response.data;
      
      // If first page, replace all jobs, otherwise append
      if (page === 1) {
        setJobs(data.items);
      } else {
        setJobs(prev => [...prev, ...data.items]);
      }
      
      // Check if we have more pages
      setHasMore(data.items.length === limit && data.total > page * limit);
    } catch (error) {
      console.error('Error fetching jobs:', error);
      toast.error('Failed to load jobs');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    // Reset page when status filter changes
    setPage(1);
    fetchJobs(1, statusFilter);
  }, [statusFilter]);

  const handleLoadMore = () => {
    const nextPage = page + 1;
    setPage(nextPage);
    fetchJobs(nextPage, statusFilter);
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Jobs</h1>
        
        <div className="flex space-x-2">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-lg border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm focus:ring-primary-500 focus:border-primary-500"
          >
            <option value="all">All Status</option>
            <option value="queued">Queued</option>
            <option value="processing">Processing</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
            <option value="canceled">Canceled</option>
          </select>
        </div>
      </div>
      
      {isLoading && page === 1 ? (
        <div className="flex justify-center items-center py-8">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
        </div>
      ) : jobs.length === 0 ? (
        <div className="text-center py-8">
          <p className="text-gray-500 dark:text-gray-400">No jobs found.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {jobs.map((job) => (
            <JobCard
              key={job.id}
              id={job.id}
              status={job.status}
              createdAt={job.created_at}
              filename={job.filename}
              jobType={job.job_type}
            />
          ))}
          
          {hasMore && (
            <div className="flex justify-center mt-6">
              <button
                onClick={handleLoadMore}
                disabled={isLoading}
                className="py-2 px-4 bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50"
              >
                {isLoading ? 'Loading...' : 'Load More'}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
