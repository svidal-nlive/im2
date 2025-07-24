'use client';

import { useEffect, useState } from 'react';
import { systemApi, jobsApi } from '@/lib/api';
import { useAuthStore } from '@/lib/auth-store';
import { toast } from 'react-toastify';
import JobCard from '@/components/jobs/JobCard';
import SystemStatusCard from '@/components/system/SystemStatusCard';
import ServiceCard from '@/components/system/ServiceCard';

interface JobSummary {
  id: string;
  status: string;
  created_at: string;
  filename: string;
  job_type: string;
}

interface ServiceStatus {
  name: string;
  status: 'running' | 'stopped' | 'error';
  message?: string;
}

interface SystemStatus {
  pipeline_status: 'running' | 'paused' | 'error';
  queue_size: number;
  active_jobs: number;
  failed_jobs: number;
  completed_jobs: number;
  services: ServiceStatus[];
}

export default function DashboardPage() {
  const { isAuthenticated, checkAuth } = useAuthStore();
  const [recentJobs, setRecentJobs] = useState<JobSummary[]>([]);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    // Verify authentication
    const verifyAuth = async () => {
      if (!isAuthenticated) {
        await checkAuth();
      }
    };
    verifyAuth();
  }, [isAuthenticated, checkAuth]);

  useEffect(() => {
    // Fetch dashboard data
    const fetchDashboardData = async () => {
      setIsLoading(true);
      try {
        // Fetch recent jobs
        const jobsResponse = await jobsApi.getJobs({ limit: 5 });
        setRecentJobs(jobsResponse.data.items);

        // Fetch system status
        const statusResponse = await systemApi.getStatus();
        setSystemStatus(statusResponse.data);
      } catch (error) {
        console.error('Error fetching dashboard data:', error);
        toast.error('Failed to load dashboard data');
      } finally {
        setIsLoading(false);
      }
    };

    if (isAuthenticated) {
      fetchDashboardData();
    }
  }, [isAuthenticated]);

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>
      
      {/* System Status */}
      {systemStatus && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <SystemStatusCard
            status={systemStatus.pipeline_status}
            queueSize={systemStatus.queue_size}
            activeJobs={systemStatus.active_jobs}
            failedJobs={systemStatus.failed_jobs}
            completedJobs={systemStatus.completed_jobs}
          />
          
          <div className="space-y-4">
            <h2 className="text-xl font-semibold">Services</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {systemStatus.services.map((service) => (
                <ServiceCard
                  key={service.name}
                  name={service.name}
                  status={service.status}
                  message={service.message}
                />
              ))}
            </div>
          </div>
        </div>
      )}
      
      {/* Recent Jobs */}
      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <h2 className="text-xl font-semibold">Recent Jobs</h2>
          <a href="/jobs" className="text-primary-600 hover:text-primary-800 dark:text-primary-400 dark:hover:text-primary-300">
            View all jobs →
          </a>
        </div>
        
        <div className="space-y-4">
          {recentJobs.length > 0 ? (
            recentJobs.map((job) => (
              <JobCard
                key={job.id}
                id={job.id}
                status={job.status}
                createdAt={job.created_at}
                filename={job.filename}
                jobType={job.job_type}
              />
            ))
          ) : (
            <p className="text-gray-500 dark:text-gray-400">No recent jobs found.</p>
          )}
        </div>
      </div>
    </div>
  );
}
