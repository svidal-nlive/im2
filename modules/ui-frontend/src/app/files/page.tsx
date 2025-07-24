'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { filesApi } from '@/lib/api';
import { toast } from 'react-toastify';
import { formatDistanceToNow, format } from 'date-fns';

interface File {
  id: string;
  filename: string;
  path: string;
  size: number;
  created_at: string;
  updated_at: string;
  file_type: string;
  status: string;
}

interface FilesResponse {
  items: File[];
  total: number;
}

export default function FilesPage() {
  const router = useRouter();
  const [files, setFiles] = useState<File[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [page, setPage] = useState<number>(1);
  const [hasMore, setHasMore] = useState<boolean>(true);
  const [currentPath, setCurrentPath] = useState<string>('/');
  const limit = 20;

  const fetchFiles = async (page: number, path: string) => {
    setIsLoading(true);
    try {
      const params = {
        limit,
        offset: (page - 1) * limit,
        path
      };

      const response = await filesApi.getFiles(params);
      const data: FilesResponse = response.data;
      
      // If first page, replace all files, otherwise append
      if (page === 1) {
        setFiles(data.items);
      } else {
        setFiles(prev => [...prev, ...data.items]);
      }
      
      // Check if we have more pages
      setHasMore(data.items.length === limit && data.total > page * limit);
    } catch (error) {
      console.error('Error fetching files:', error);
      toast.error('Failed to load files');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    // Reset page when path changes
    setPage(1);
    fetchFiles(1, currentPath);
  }, [currentPath]);

  const handleLoadMore = () => {
    const nextPage = page + 1;
    setPage(nextPage);
    fetchFiles(nextPage, currentPath);
  };

  const handleFileClick = (file: File) => {
    // If it's a directory, navigate to it
    if (file.file_type === 'directory') {
      setCurrentPath(file.path);
    } else {
      // Otherwise, download the file
      handleDownload(file);
    }
  };

  const handleDownload = async (file: File) => {
    try {
      const response = await filesApi.downloadFile(file.id);
      
      // Create a download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', file.filename);
      document.body.appendChild(link);
      link.click();
      
      // Cleanup
      link.parentNode?.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast.success('File downloaded successfully');
    } catch (error) {
      console.error('Error downloading file:', error);
      toast.error('Failed to download file');
    }
  };

  const navigateUp = () => {
    if (currentPath === '/') return;
    
    // Get parent path
    const parts = currentPath.split('/').filter(Boolean);
    parts.pop();
    const parentPath = parts.length === 0 ? '/' : `/${parts.join('/')}/`;
    
    setCurrentPath(parentPath);
  };

  // Format file size
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Files</h1>
        
        <button
          onClick={() => router.push('/upload')}
          className="py-2 px-4 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
        >
          Upload File
        </button>
      </div>
      
      {/* Path navigation */}
      <div className="flex items-center bg-gray-100 dark:bg-gray-800 rounded-lg p-2">
        <button
          onClick={navigateUp}
          disabled={currentPath === '/'}
          className="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-700 mr-2 disabled:opacity-50"
          title="Go up"
        >
          <svg
            className="h-5 w-5 text-gray-600 dark:text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              d="M15 19l-7-7 7-7"
            ></path>
          </svg>
        </button>
        
        <div className="font-mono text-sm overflow-x-auto whitespace-nowrap">
          {currentPath}
        </div>
      </div>
      
      {isLoading && page === 1 ? (
        <div className="flex justify-center items-center py-8">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
        </div>
      ) : files.length === 0 ? (
        <div className="text-center py-8">
          <p className="text-gray-500 dark:text-gray-400">No files found in this location.</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className="bg-gray-100 dark:bg-gray-800">
              <tr>
                <th
                  scope="col"
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
                >
                  Name
                </th>
                <th
                  scope="col"
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
                >
                  Type
                </th>
                <th
                  scope="col"
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
                >
                  Size
                </th>
                <th
                  scope="col"
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
                >
                  Modified
                </th>
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-800">
              {files.map((file) => (
                <tr
                  key={file.id}
                  className="hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer"
                  onClick={() => handleFileClick(file)}
                >
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      {file.file_type === 'directory' ? (
                        <svg
                          className="h-5 w-5 text-yellow-500 mr-2"
                          fill="currentColor"
                          viewBox="0 0 20 20"
                          xmlns="http://www.w3.org/2000/svg"
                        >
                          <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z"></path>
                        </svg>
                      ) : (
                        <svg
                          className="h-5 w-5 text-gray-500 mr-2"
                          fill="currentColor"
                          viewBox="0 0 20 20"
                          xmlns="http://www.w3.org/2000/svg"
                        >
                          <path
                            fillRule="evenodd"
                            d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z"
                            clipRule="evenodd"
                          ></path>
                        </svg>
                      )}
                      <span className="truncate max-w-xs" title={file.filename}>
                        {file.filename}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                    {file.file_type === 'directory' ? 'Folder' : file.file_type.toUpperCase()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                    {file.file_type === 'directory' ? '-' : formatFileSize(file.size)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400" title={format(new Date(file.updated_at), 'PPpp')}>
                    {formatDistanceToNow(new Date(file.updated_at), { addSuffix: true })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          
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
