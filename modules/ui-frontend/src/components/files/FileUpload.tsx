'use client';

import { useDropzone } from 'react-dropzone';
import { useState, useCallback } from 'react';
import { filesApi } from '@/lib/api';
import { toast } from 'react-toastify';

export default function FileUpload() {
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState<Record<string, number>>({});
  const [acceptedTerms, setAcceptedTerms] = useState(false);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    setFiles((prev) => [...prev, ...acceptedFiles]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'audio/*': ['.mp3', '.flac', '.wav', '.aac', '.m4a', '.ogg'],
    },
    maxSize: 1024 * 1024 * 500, // 500MB
  });

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const uploadFiles = async () => {
    if (!acceptedTerms) {
      toast.error('Please accept the terms before uploading');
      return;
    }

    if (files.length === 0) {
      toast.error('Please add files to upload');
      return;
    }

    setUploading(true);

    try {
      for (const file of files) {
        const handleProgress = (progressPercent: number) => {
          setProgress((prev) => ({
            ...prev,
            [file.name]: progressPercent,
          }));
        };

        try {
          await filesApi.uploadFile(file, handleProgress);
          toast.success(`Uploaded ${file.name} successfully`);
        } catch (error) {
          console.error(`Error uploading ${file.name}:`, error);
          toast.error(`Failed to upload ${file.name}`);
        }
      }
    } finally {
      setUploading(false);
      setFiles([]);
      setProgress({});
    }
  };

  return (
    <div className="flex flex-col space-y-4">
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-lg p-8 flex flex-col items-center justify-center cursor-pointer transition-colors ${
          isDragActive
            ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
            : 'border-gray-300 hover:border-primary-500'
        }`}
      >
        <input {...getInputProps()} />
        <div className="text-center">
          <svg
            className="mx-auto h-12 w-12 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
            />
          </svg>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">
            {isDragActive
              ? 'Drop the files here...'
              : 'Drag and drop audio files here, or click to select files'}
          </p>
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            MP3, FLAC, WAV, AAC, M4A, OGG up to 500MB
          </p>
        </div>
      </div>

      {files.length > 0 && (
        <div className="mt-4">
          <h3 className="text-lg font-medium">Selected Files</h3>
          <ul className="mt-2 divide-y divide-gray-200 dark:divide-gray-700">
            {files.map((file, index) => (
              <li key={`${file.name}-${index}`} className="py-3 flex items-center justify-between">
                <div className="flex items-center">
                  <span className="ml-3 text-sm font-medium text-gray-900 dark:text-gray-100">
                    {file.name}
                  </span>
                  <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">
                    {(file.size / (1024 * 1024)).toFixed(2)} MB
                  </span>
                </div>
                <div className="flex items-center">
                  {progress[file.name] !== undefined && (
                    <div className="w-24 bg-gray-200 rounded-full h-2.5 mr-4 dark:bg-gray-700">
                      <div
                        className="bg-primary-600 h-2.5 rounded-full"
                        style={{ width: `${progress[file.name]}%` }}
                      ></div>
                    </div>
                  )}
                  <button
                    type="button"
                    onClick={() => removeFile(index)}
                    disabled={uploading}
                    className="text-red-500 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
                  >
                    <svg
                      className="h-5 w-5"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M6 18L18 6M6 6l12 12"
                      />
                    </svg>
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-4 flex items-start">
        <input
          id="terms"
          name="terms"
          type="checkbox"
          checked={acceptedTerms}
          onChange={(e) => setAcceptedTerms(e.target.checked)}
          className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
        />
        <label htmlFor="terms" className="ml-2 block text-sm text-gray-700 dark:text-gray-300">
          I accept the{' '}
          <a href="#" className="text-primary-600 hover:text-primary-500">
            Terms of Service
          </a>{' '}
          and confirm that I have the right to process these audio files
        </label>
      </div>

      <div className="mt-4 flex justify-end">
        <button
          type="button"
          onClick={uploadFiles}
          disabled={uploading || files.length === 0 || !acceptedTerms}
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {uploading ? 'Uploading...' : 'Upload Files'}
        </button>
      </div>
    </div>
  );
}
