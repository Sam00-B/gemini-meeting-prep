import { useState, useEffect } from 'react';
import Markdown from 'react-markdown';
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

interface Briefing {
  title: string;
  time: string;
  attendees: string[];
  ai_briefing: string;
}

interface ApiResponse {
  message: string;
  briefings: Briefing[];
}

export default function App() {
  const [briefings, setBriefings] = useState<Briefing[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [hasFetched, setHasFetched] = useState<boolean>(false);
  const [isDarkMode, setIsDarkMode] = useState<boolean>(() => {
    return localStorage.getItem('theme') === 'dark';
  });

  useEffect(() => {
    const root = window.document.documentElement; 
    if (isDarkMode) {
      root.classList.add('dark')
      localStorage.setItem('theme', 'dark');
    } else {
      root.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  }, [isDarkMode]); 

  const generateBriefings = async () => {
      setIsLoading(true);
      setError(null);
      try {
        // 🚨 Added "?refresh=true" to the URL query string to bypass stale DB records
        const response = await fetch(`${API_BASE_URL}/api/briefings?refresh=true`, {
          method: 'GET',
          credentials: 'include' 
        });
        
        if (!response.ok) {
          if (response.status === 401) {
              throw new Error("Unauthorized: Please authenticate with Google first.");
          }
          throw new Error(`Server responded with a ${response.status} status.`);
        }
        const data: ApiResponse = await response.json();
        setBriefings(data.briefings)
        setHasFetched(true);
      } catch (err: any) {
        setError(err.message || "Failed to reach the backend service.");
      } finally {
        setIsLoading(false);
      }
    };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 dark:bg-slate-900 dark:text-slate-100 antialiased selection:bg-indigo-100 transition-colors duration-200">
      
      {/* Upper Navigation Bar */}
      <header className="sticky top-0 z-50 border-b border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md transition-colors duration-200">
        <div className="mx-auto flex max-w-7xl h-16 items-center justify-between px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">Executive Briefing Console</h1>
          </div>
        
        <div className="flex items-center gap-4">
          
          <button
            onClick={() => setIsDarkMode(!isDarkMode)}
            className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800 transition-colors text-lg"
            aria-label="Toggle theme"
          >
            {isDarkMode ? '☀️' : '🌙'}
          </button>

          {/* 🚨 NEW: Google Auth Button */}
          <button
            onClick={() => window.location.href = `${API_BASE_URL}/auth/login`}
            className="rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50 transition-all dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
          >
            Authenticate Google Workspace
          </button>

          <button
            onClick={generateBriefings}
            disabled={isLoading}
            className="inline-flex items-center justify-center rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            {isLoading ? (
              <span className="flex items-center gap-2">
                <svg className="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Syncing Pipelines...
              </span>
            ) : (
              'Sync & Compile Schedule'
            )}
          </button>
          </div>
        </div>
      </header>

      {/* Main Container Layout */}
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {error && (
          <div className="mb-6 rounded-lg border-l-4 border-red-500 bg-red-50 p-4 shadow-sm">
            <div className="flex">
              <span className="text-red-500 font-bold mr-2">⚠️ Execution Fault:</span>
              <p className="text-sm text-red-700">{error}</p>
            </div>
          </div>
        )}
        
        {/* Empty State Banner BEFORE fetch */}
        {briefings.length === 0 && !isLoading && !error && !hasFetched && (
          <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 p-12 text-center shadow-xs transition-colors duration-200">
            <div className="rounded-full bg-slate-100 dark:bg-slate-700 p-3 text-slate-500 dark:text-slate-400 text-3xl mb-4">📅</div>
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Workspace is Idle</h3>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400 max-w-sm">
              Authenticate first, then click "Sync & Compile Schedule".
            </p>
          </div>
        )}

        {/* Empty State AFTER fetch (No meetings) */}
        {briefings.length === 0 && !isLoading && !error && hasFetched && (
          <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 p-12 text-center shadow-xs transition-colors duration-200">
            <div className="rounded-full bg-slate-100 dark:bg-slate-700 p-3 text-slate-500 dark:text-slate-400 text-3xl mb-4">✨</div>
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">No meetings for today</h3>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400 max-w-sm">
              Your schedule is completely clear!
            </p>
          </div>
        )}

        {/* Loading State Skeleton Cards */}
        {isLoading && (
          <div className="space-y-8 animate-pulse">
            {[1, 2].map((i) => (
              <div key={i} className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-800 shadow-xs">
                <div className="border-b border-slate-100 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/50 px-6 py-5 sm:px-8">
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <div className="h-6 w-48 rounded bg-slate-200 dark:bg-slate-700"></div>
                    <div className="h-5 w-20 rounded bg-indigo-100 dark:bg-indigo-900/40"></div>
                  </div>
                  <div className="mt-4 flex gap-2">
                    <div className="h-4 w-16 rounded bg-slate-200 dark:bg-slate-700"></div>
                    <div className="h-4 w-24 rounded bg-slate-200 dark:bg-slate-700"></div>
                    <div className="h-4 w-28 rounded bg-slate-200 dark:bg-slate-700"></div>
                  </div>
                </div>
                <div className="px-6 py-6 sm:px-8 bg-white dark:bg-slate-800">
                  <div className="h-4 w-32 rounded bg-slate-200 dark:bg-slate-700 mb-6"></div>
                  <div className="space-y-3">
                    <div className="h-4 w-full rounded bg-slate-200 dark:bg-slate-700"></div>
                    <div className="h-4 w-5/6 rounded bg-slate-200 dark:bg-slate-700"></div>
                    <div className="h-4 w-4/5 rounded bg-slate-200 dark:bg-slate-700"></div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Dynamic Cards Grid */}
        <div className="space-y-8">
          {!isLoading && briefings.map((briefing, index) => (
            <article key={index} className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-800 shadow-xs transition-all hover:shadow-md">
              <div className="border-b border-slate-100 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/50 px-6 py-5 sm:px-8">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">{briefing.title}</h2>
                  <div className="inline-flex items-center rounded-md bg-indigo-50 dark:bg-indigo-950/50 px-2.5 py-1 text-xs font-medium text-indigo-700 dark:text-indigo-300 ring-1 ring-inset ring-indigo-700/10 dark:ring-indigo-500/20">
                    🕒 {(() => {
                          try {
                            const date = new Date(briefing.time);
                            return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + ' (' + date.toLocaleDateString([], { month: 'short', day: 'numeric' }) + ')';
                          } catch {
                            return briefing.time; 
                          }
                        })()}
                  </div>
                </div>
                <div className="mt-3 flex flex-wrap items-center gap-1.5 text-sm text-slate-500">
                  <span className="font-medium text-slate-700 dark:text-slate-300">Attendees:</span>
                  {briefing.attendees.length > 0 ? (
                    briefing.attendees.map((email, idx) => (
                      <span key={idx} className="inline-block rounded-sm bg-slate-100 dark:bg-slate-600 px-2 py-0.5 text-xs text-slate-600 dark:text-slate-300 font-mono">
                        {email}
                      </span>
                    ))
                  ) : (
                    <span className="italic text-slate-400">None declared</span>
                  )}
                </div>
              </div>
              <div className="px-6 py-6 sm:px-8 bg-white dark:bg-slate-800">
                <div className="flex items-center gap-2 mb-4 border-b border-slate-100 dark:border-slate-600 pb-2">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 dark:text-slate-400">Intelligence Briefing</h3>
                </div>
                <div className="text-slate-700 dark:text-slate-200 leading-relaxed max-w-none">
                  <Markdown
                      components={{
                        h1: ({ ...props }) => <h4 className="text-lg font-bold text-slate-900 dark:text-white mt-5 mb-2 border-b border-slate-100 dark:border-slate-700 pb-1" {...props} />,
                        h2: ({ ...props }) => <h5 className="text-base font-bold text-slate-900 dark:text-white mt-4 mb-2" {...props} />,
                        h3: ({ ...props }) => <h6 className="text-sm font-semibold text-slate-800 dark:text-slate-200 mt-3 mb-1" {...props} />,
                        p: ({ ...props }) => <p className="text-sm text-slate-600 dark:text-slate-300 mb-3" {...props} />,
                        ul: ({ ...props }) => <ul className="list-disc pl-5 mb-4 space-y-1.5 text-sm text-slate-600 dark:text-slate-300" {...props} />,
                        ol: ({ ...props }) => <ol className="list-decimal pl-5 mb-4 space-y-1.5 text-sm text-slate-600 dark:text-slate-300" {...props} />,
                        li: ({ ...props }) => <li className="text-sm leading-relaxed text-slate-600 dark:text-slate-300" {...props} />,
                        strong: ({ ...props }) => (
                          <strong 
                            className="font-bold bg-transparent bg-none text-indigo-600 dark:text-indigo-400 " 
                            style={{ backgroundColor: 'transparent', background: 'none' }} 
                            {...props} 
                          />
                        ),
                      }}
                    >
                    {briefing.ai_briefing}
                  </Markdown>
                </div>
              </div>
            </article>
          ))}
        </div>
      </main>
    </div>
  );
}