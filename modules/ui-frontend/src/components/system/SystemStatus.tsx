'use client';

import { useState, useEffect } from 'react';
import { systemApi } from '@/lib/api';
import { toast } from 'react-toastify';

interface Service {
  name: string;
  status: 'running' | 'stopped' | 'error';
  health: 'healthy' | 'unhealthy' | 'unknown';
  uptime: string;
}

export default function SystemStatus() {
  const [services, setServices] = useState<Service[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRestarting, setIsRestarting] = useState<Record<string, boolean>>({});

  useEffect(() => {
    const fetchServices = async () => {
      try {
        const response = await systemApi.getServices();
        setServices(response.data);
      } catch (error) {
        console.error('Error fetching services:', error);
        toast.error('Failed to load system status');
      } finally {
        setIsLoading(false);
      }
    };

    fetchServices();
    
    // Poll for updates
    const intervalId = setInterval(fetchServices, 30000);
    
    return () => clearInterval(intervalId);
  }, []);

  const restartService = async (serviceName: string) => {
    setIsRestarting((prev) => ({ ...prev, [serviceName]: true }));
    
    try {
      await systemApi.restartService(serviceName);
      toast.success(`Service ${serviceName} is restarting`);
      
      // Wait for a bit and then refresh the status
      setTimeout(async () => {
        try {
          const response = await systemApi.getServices();
          setServices(response.data);
        } catch (error) {
          console.error('Error refreshing services:', error);
        } finally {
          setIsRestarting((prev) => ({ ...prev, [serviceName]: false }));
        }
      }, 5000);
    } catch (error) {
      console.error(`Error restarting ${serviceName}:`, error);
      toast.error(`Failed to restart ${serviceName}`);
      setIsRestarting((prev) => ({ ...prev, [serviceName]: false }));
    }
  };

  const getStatusColor = (status: string) => {
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

  const getHealthColor = (health: string) => {
    switch (health) {
      case 'healthy':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300';
      case 'unhealthy':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300';
      case 'unknown':
        return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300';
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
      <h2 className="text-xl font-semibold mb-4">System Status</h2>
      
      <div className="bg-white dark:bg-gray-800 shadow overflow-hidden sm:rounded-md">
        <ul className="divide-y divide-gray-200 dark:divide-gray-700">
          {services.map((service) => (
            <li key={service.name}>
              <div className="px-4 py-4 sm:px-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <p className="text-sm font-medium text-primary-600">{service.name}</p>
                    <span
                      className={`ml-2 px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusColor(
                        service.status
                      )}`}
                    >
                      {service.status}
                    </span>
                    <span
                      className={`ml-2 px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getHealthColor(
                        service.health
                      )}`}
                    >
                      {service.health}
                    </span>
                  </div>
                  <div>
                    <button
                      onClick={() => restartService(service.name)}
                      disabled={isRestarting[service.name]}
                      className="inline-flex items-center px-2.5 py-1.5 border border-transparent text-xs font-medium rounded text-primary-700 bg-primary-100 hover:bg-primary-200 dark:bg-primary-900 dark:text-primary-100 dark:hover:bg-primary-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {isRestarting[service.name] ? 'Restarting...' : 'Restart'}
                    </button>
                  </div>
                </div>
                <div className="mt-2">
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Uptime: {service.uptime}
                  </p>
                </div>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
