'use client';

import { useState, useEffect } from 'react';
import { systemApi } from '@/lib/api';
import { toast } from 'react-toastify';
import SystemStatusCard from '@/components/system/SystemStatusCard';
import ServiceCard from '@/components/system/ServiceCard';

interface ServiceStatus {
  name: string;
  status: 'running' | 'stopped' | 'error';
  message?: string;
  uptime?: number;
  version?: string;
}

interface SystemStatus {
  pipeline_status: 'running' | 'paused' | 'error';
  queue_size: number;
  active_jobs: number;
  failed_jobs: number;
  completed_jobs: number;
  services: ServiceStatus[];
}

interface SystemMetrics {
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  network_rx: number;
  network_tx: number;
}

export default function SystemPage() {
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);

  const fetchSystemData = async () => {
    const isInitialLoad = isLoading;
    if (!isInitialLoad) setIsRefreshing(true);
    
    try {
      // Fetch system status
      const statusResponse = await systemApi.getStatus();
      setSystemStatus(statusResponse.data);
      
      // Fetch system metrics
      const metricsResponse = await systemApi.getMetrics();
      setMetrics(metricsResponse.data);
    } catch (error) {
      console.error('Error fetching system data:', error);
      toast.error('Failed to load system data');
    } finally {
      setIsLoading(false);
      if (!isInitialLoad) setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchSystemData();
    
    // Poll for updates every 30 seconds
    const intervalId = setInterval(fetchSystemData, 30000);
    
    // Cleanup on unmount
    return () => clearInterval(intervalId);
  }, []);

  const handleRefresh = () => {
    fetchSystemData();
  };

  // Format memory size
  const formatMemorySize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center py-8">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">System Status</h1>
        <button
          onClick={handleRefresh}
          disabled={isRefreshing}
          className="py-2 px-4 bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50"
        >
          {isRefreshing ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>
      
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
          
          {/* System Metrics */}
          {metrics && (
            <div className="p-6 bg-white dark:bg-gray-800 rounded-lg shadow-md">
              <h2 className="text-xl font-semibold mb-4">System Metrics</h2>
              
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-sm text-gray-500 dark:text-gray-400">CPU Usage</span>
                    <span className="text-sm font-medium">{metrics.cpu_usage.toFixed(1)}%</span>
                  </div>
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5">
                    <div
                      className={`h-2.5 rounded-full ${
                        metrics.cpu_usage > 90
                          ? 'bg-red-600'
                          : metrics.cpu_usage > 70
                          ? 'bg-yellow-600'
                          : 'bg-green-600'
                      }`}
                      style={{ width: `${metrics.cpu_usage}%` }}
                    ></div>
                  </div>
                </div>
                
                <div>
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-sm text-gray-500 dark:text-gray-400">Memory Usage</span>
                    <span className="text-sm font-medium">{metrics.memory_usage.toFixed(1)}%</span>
                  </div>
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5">
                    <div
                      className={`h-2.5 rounded-full ${
                        metrics.memory_usage > 90
                          ? 'bg-red-600'
                          : metrics.memory_usage > 70
                          ? 'bg-yellow-600'
                          : 'bg-green-600'
                      }`}
                      style={{ width: `${metrics.memory_usage}%` }}
                    ></div>
                  </div>
                </div>
                
                <div>
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-sm text-gray-500 dark:text-gray-400">Disk Usage</span>
                    <span className="text-sm font-medium">{metrics.disk_usage.toFixed(1)}%</span>
                  </div>
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5">
                    <div
                      className={`h-2.5 rounded-full ${
                        metrics.disk_usage > 90
                          ? 'bg-red-600'
                          : metrics.disk_usage > 70
                          ? 'bg-yellow-600'
                          : 'bg-green-600'
                      }`}
                      style={{ width: `${metrics.disk_usage}%` }}
                    ></div>
                  </div>
                </div>
                
                <div className="grid grid-cols-2 gap-4 mt-4">
                  <div className="bg-gray-100 dark:bg-gray-700 p-3 rounded-lg">
                    <div className="text-gray-500 dark:text-gray-400 text-sm">Network RX</div>
                    <div className="font-bold text-xl">{formatMemorySize(metrics.network_rx)}/s</div>
                  </div>
                  <div className="bg-gray-100 dark:bg-gray-700 p-3 rounded-lg">
                    <div className="text-gray-500 dark:text-gray-400 text-sm">Network TX</div>
                    <div className="font-bold text-xl">{formatMemorySize(metrics.network_tx)}/s</div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
      
      {/* Services */}
      {systemStatus && (
        <div className="space-y-4">
          <h2 className="text-xl font-semibold">Services</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
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
      )}
    </div>
  );
}
