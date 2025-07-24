'use client';

import { useState, useRef, ChangeEvent, FormEvent } from 'react';
import { filesApi } from '@/lib/api';
import { toast } from 'react-toastify';

export default function UploadPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      
      // Check if the file is an audio file
      if (!file.type.startsWith('audio/')) {
        toast.error('Please select an audio file');
        return;
      }
      
      setSelectedFile(file);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      
      // Check if the file is an audio file
      if (!file.type.startsWith('audio/')) {
        toast.error('Please select an audio file');
        return;
      }
      
      setSelectedFile(file);
    }
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    
    if (!selectedFile) {
      toast.error('Please select a file to upload');
      return;
    }
    
    setIsUploading(true);
    setUploadProgress(0);
    
    try {
      const response = await filesApi.uploadFile(selectedFile, (progressEvent) => {
        const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        setUploadProgress(progress);
      });
      
      toast.success('File uploaded successfully!');
      
      // Reset form
      setSelectedFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      
      // Redirect to the file page or job page
      // router.push(`/jobs/${response.data.job_id}`);
    } catch (error) {
      console.error('Upload error:', error);
      toast.error('Failed to upload file');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Upload Audio File</h1>
      
      <form onSubmit={handleSubmit} className="space-y-6">
        <div
          className="border-2 border-dashed border-gray-300 dark:border-gray-700 rounded-lg p-6 flex flex-col items-center justify-center cursor-pointer"
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <svg
            className="h-12 w-12 text-gray-400 dark:text-gray-500 mb-3"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            ></path>
          </svg>
          
          <p className="mb-2 text-sm text-gray-600 dark:text-gray-400">
            <span className="font-medium">Click to upload</span> or drag and drop
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-500">
            WAV, MP3, FLAC, or other audio files
          </p>
          
          <input
            type="file"
            className="hidden"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept="audio/*"
          />
        </div>
        
        {selectedFile && (
          <div className="bg-gray-100 dark:bg-gray-800 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <svg
                  className="h-6 w-6 text-primary-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3"
                  ></path>
                </svg>
                <span className="font-medium">{selectedFile.name}</span>
              </div>
              <button
                type="button"
                className="text-red-600 hover:text-red-800"
                onClick={() => setSelectedFile(null)}
                disabled={isUploading}
              >
                Remove
              </button>
            </div>
            
            {isUploading && (
              <div className="mt-2">
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5">
                  <div
                    className="bg-primary-600 h-2.5 rounded-full"
                    style={{ width: `${uploadProgress}%` }}
                  ></div>
                </div>
                <div className="text-right text-xs mt-1">
                  {uploadProgress}% uploaded
                </div>
              </div>
            )}
          </div>
        )}
        
        <button
          type="submit"
          disabled={!selectedFile || isUploading}
          className="w-full py-2 px-4 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50"
        >
          {isUploading ? 'Uploading...' : 'Upload File'}
        </button>
      </form>
    </div>
  );
}
