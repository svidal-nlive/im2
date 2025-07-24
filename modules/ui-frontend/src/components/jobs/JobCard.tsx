'use client';

import Link from 'next/link';
import { formatDistanceToNow } from 'date-fns';

interface JobCardProps {
  id: string;
  status: string;
  createdAt: string;
  filename: string;
  jobType: string;
}

export default function JobCard({ id, status, createdAt, filename, jobType }: JobCardProps) {
  // Format the date
  const formattedDate = formatDistanceToNow(new Date(createdAt), { addSuffix: true });
  
  // Get status color
  const getStatusColor = () => {
    switch (status.toLowerCase()) {
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

  return (
    <Link href={`/jobs/${id}`}>
      <div className="p-4 bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 hover:shadow-md transition-shadow duration-200">
        <div className="flex justify-between items-center mb-2">
          <h3 className="font-medium truncate" title={filename}>
            {filename}
          </h3>
          <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor()}`}>
            {status}
          </span>
        </div>
        
        <div className="flex justify-between items-center text-sm text-gray-500 dark:text-gray-400">
          <div>
            <span className="inline-block bg-gray-200 dark:bg-gray-700 rounded px-2 py-1">
              {jobType}
            </span>
          </div>
          <div>{formattedDate}</div>
        </div>
      </div>
    </Link>
  );
}
