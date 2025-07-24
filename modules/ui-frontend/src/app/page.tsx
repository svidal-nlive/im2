import AppLayout from '@/components/layout/AppLayout';
import Link from 'next/link';

export default function Home() {
  return (
    <AppLayout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="py-10">
          <header>
            <h1 className="text-3xl font-bold leading-tight text-gray-900 dark:text-white">
              IM2 - Ironclad Modular Audio Processing Stack
            </h1>
          </header>
          
          <div className="mt-10">
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
              {/* Dashboard Cards */}
              <Link href="/upload">
                <div className="group bg-white dark:bg-gray-800 p-6 rounded-lg shadow-md hover:shadow-lg transition-all cursor-pointer">
                  <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                    Upload Files
                  </h2>
                  <p className="text-gray-600 dark:text-gray-300">
                    Upload audio files for stem separation.
                  </p>
                </div>
              </Link>
              
              <Link href="/jobs">
                <div className="group bg-white dark:bg-gray-800 p-6 rounded-lg shadow-md hover:shadow-lg transition-all cursor-pointer">
                  <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                    Monitor Jobs
                  </h2>
                  <p className="text-gray-600 dark:text-gray-300">
                    Track job progress and status in real time.
                  </p>
                </div>
              </Link>
              
              <Link href="/files">
                <div className="group bg-white dark:bg-gray-800 p-6 rounded-lg shadow-md hover:shadow-lg transition-all cursor-pointer">
                  <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                    Job History
                  </h2>
                  <p className="text-gray-600 dark:text-gray-300">
                    Browse your past jobs and download results.
                  </p>
                </div>
              </Link>
              
              <Link href="/system">
                <div className="group bg-white dark:bg-gray-800 p-6 rounded-lg shadow-md hover:shadow-lg transition-all cursor-pointer">
                  <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                    System Status
                  </h2>
                  <p className="text-gray-600 dark:text-gray-300">
                    View health and status of pipeline components.
                  </p>
                </div>
              </Link>
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
