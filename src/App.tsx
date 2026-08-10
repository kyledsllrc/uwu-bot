import React, { useState, useEffect } from 'react';
import {
  GitBranch,
  GitCommit,
  GitPullRequest,
  Github,
  Key,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  ArrowRight,
  Lock,
  Globe,
  Terminal,
  FolderGit2,
  ExternalLink,
  MessageSquare
} from 'lucide-react';

interface RepoStatus {
  hasRepo: boolean;
  remoteUrl?: string;
  branch?: string;
  lastCommit?: string;
  changes?: string[];
  message?: string;
}

export default function App() {
  const [repoUrl, setRepoUrl] = useState('');
  const [branch, setBranch] = useState('');
  const [token, setToken] = useState('');
  const [loading, setLoading] = useState(false);
  const [pulling, setPulling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [repoStatus, setRepoStatus] = useState<RepoStatus | null>(null);
  const [checkingStatus, setCheckingStatus] = useState(true);

  // Fetch current repo status on mount
  const fetchStatus = async () => {
    setCheckingStatus(true);
    try {
      const res = await fetch('/api/repo-status');
      const data = await res.json();
      setRepoStatus(data);
    } catch (err) {
      console.error('Failed to fetch status:', err);
    } finally {
      setCheckingStatus(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  const handleClone = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!repoUrl.trim()) {
      setError('Please enter a GitHub repository URL or user/repository string.');
      return;
    }

    setLoading(true);
    setError(null);
    setSuccessMsg(null);

    try {
      const res = await fetch('/api/clone', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          repoUrl: repoUrl.trim(),
          branch: branch.trim() || undefined,
          token: token.trim() || undefined,
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.details || data.error || 'Failed to pull repository');
      }

      setSuccessMsg(data.message || 'Repository successfully pulled into workspace!');
      setRepoUrl('');
      setToken('');
      fetchStatus();
    } catch (err: any) {
      setError(err.message || 'An unexpected error occurred while pulling repository.');
    } finally {
      setLoading(false);
    }
  };

  const handlePullLatest = async () => {
    setPulling(true);
    setError(null);
    setSuccessMsg(null);

    try {
      const res = await fetch('/api/pull', { method: 'POST' });
      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || 'Failed to pull changes');
      }

      setSuccessMsg(data.output || 'Latest changes pulled successfully!');
      fetchStatus();
    } catch (err: any) {
      setError(err.message || 'Failed to pull latest changes.');
    } finally {
      setPulling(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-indigo-500 selection:text-white">
      {/* Navigation Bar */}
      <header className="border-b border-slate-800 bg-slate-900/60 backdrop-blur-md px-6 py-4 sticky top-0 z-10">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-indigo-600/20 rounded-xl text-indigo-400 border border-indigo-500/30">
              <Github className="w-6 h-6" />
            </div>
            <div>
              <h1 className="font-semibold text-lg text-slate-100 tracking-tight">GitHub Repository Importer</h1>
              <p className="text-xs text-slate-400">Pull & Edit GitHub Repositories in AI Studio</p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={fetchStatus}
              disabled={checkingStatus}
              className="px-3 py-1.5 text-xs font-medium text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 rounded-lg border border-slate-700 transition flex items-center gap-1.5 disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${checkingStatus ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-5xl w-full mx-auto px-6 py-8 flex flex-col gap-8">
        
        {/* Active Repository Card (If Already Cloned) */}
        {repoStatus?.hasRepo && (
          <div className="bg-slate-900/80 border border-emerald-500/30 rounded-2xl p-6 shadow-xl relative overflow-hidden backdrop-blur-sm">
            <div className="absolute top-0 left-0 w-1 h-full bg-emerald-500"></div>
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Connected Workspace
                  </span>
                  {repoStatus.branch && (
                    <span className="px-2.5 py-0.5 rounded-full text-xs font-mono bg-slate-800 text-slate-300 border border-slate-700 flex items-center gap-1">
                      <GitBranch className="w-3.5 h-3.5 text-indigo-400" /> {repoStatus.branch}
                    </span>
                  )}
                </div>

                <h2 className="text-xl font-semibold text-white tracking-tight flex items-center gap-2">
                  <FolderGit2 className="w-5 h-5 text-indigo-400" />
                  {repoStatus.remoteUrl ? (
                    <a
                      href={repoStatus.remoteUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="hover:underline hover:text-indigo-300 flex items-center gap-1.5"
                    >
                      {repoStatus.remoteUrl.replace('https://github.com/', '')}
                      <ExternalLink className="w-4 h-4 text-slate-500" />
                    </a>
                  ) : (
                    'Active Local Repository'
                  )}
                </h2>

                {repoStatus.lastCommit && (
                  <p className="text-xs font-mono text-slate-400 flex items-center gap-1.5">
                    <GitCommit className="w-3.5 h-3.5 text-slate-500" />
                    {repoStatus.lastCommit}
                  </p>
                )}
              </div>

              <div className="flex items-center gap-3 self-start md:self-center">
                <button
                  onClick={handlePullLatest}
                  disabled={pulling}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-medium text-sm transition flex items-center gap-2 shadow-lg shadow-indigo-600/20 disabled:opacity-50"
                >
                  <GitPullRequest className={`w-4 h-4 ${pulling ? 'animate-spin' : ''}`} />
                  {pulling ? 'Pulling...' : 'Pull Latest Changes'}
                </button>
              </div>
            </div>

            {/* Changed Files */}
            {repoStatus.changes && repoStatus.changes.length > 0 && (
              <div className="mt-4 pt-4 border-t border-slate-800/80">
                <p className="text-xs font-semibold text-slate-400 mb-2 uppercase tracking-wider">Uncommitted Workspace Changes</p>
                <div className="bg-slate-950/60 rounded-xl p-3 border border-slate-800 max-h-36 overflow-y-auto font-mono text-xs text-slate-300 space-y-1">
                  {repoStatus.changes.map((change, idx) => (
                    <div key={idx} className="flex items-center gap-2">
                      <span className="text-amber-400 font-bold">{change.slice(0, 2)}</span>
                      <span>{change.slice(3)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Pull Repository Form Section */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Form Column */}
          <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">
            <div>
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <Github className="w-5 h-5 text-indigo-400" />
                Pull GitHub Repository
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                Enter your public repository URL or supply a Personal Access Token (PAT) for private repositories.
              </p>
            </div>

            {/* Alerts */}
            {error && (
              <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-xl text-red-300 text-sm flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <p className="font-semibold">Pull Failed</p>
                  <p className="text-xs text-red-300/90 leading-relaxed break-words">{error}</p>
                </div>
              </div>
            )}

            {successMsg && (
              <div className="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-300 text-sm flex items-start gap-3">
                <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <p className="font-semibold">Success</p>
                  <p className="text-xs text-emerald-300/90">{successMsg}</p>
                </div>
              </div>
            )}

            <form onSubmit={handleClone} className="space-y-5">
              {/* Repo URL Input */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                  Repository URL or Name <span className="text-indigo-400">*</span>
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                    <Globe className="w-4 h-4" />
                  </div>
                  <input
                    type="text"
                    required
                    value={repoUrl}
                    onChange={(e) => setRepoUrl(e.target.value)}
                    placeholder="https://github.com/username/repository or username/repo"
                    className="w-full pl-10 pr-4 py-3 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition font-mono"
                  />
                </div>
                <p className="text-[11px] text-slate-500 mt-1.5">
                  Examples: <code className="text-slate-400 bg-slate-800/80 px-1.5 py-0.5 rounded">https://github.com/facebook/react</code> or <code className="text-slate-400 bg-slate-800/80 px-1.5 py-0.5 rounded">owner/repo</code>
                </p>
              </div>

              {/* Branch Input */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                  Branch Name <span className="text-slate-500 font-normal">(Optional, defaults to main/master)</span>
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                    <GitBranch className="w-4 h-4" />
                  </div>
                  <input
                    type="text"
                    value={branch}
                    onChange={(e) => setBranch(e.target.value)}
                    placeholder="main, master, or feature-branch"
                    className="w-full pl-10 pr-4 py-3 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition font-mono"
                  />
                </div>
              </div>

              {/* Personal Access Token (PAT) for Private Repos */}
              <div className="pt-2 border-t border-slate-800/60">
                <div className="flex items-center justify-between mb-2">
                  <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                    <Lock className="w-3.5 h-3.5 text-amber-400" />
                    Personal Access Token (PAT)
                    <span className="text-slate-500 font-normal capitalize">(For private repositories)</span>
                  </label>
                  <a
                    href="https://github.com/settings/tokens"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[11px] text-indigo-400 hover:text-indigo-300 hover:underline flex items-center gap-1"
                  >
                    Generate Token <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                    <Key className="w-4 h-4" />
                  </div>
                  <input
                    type="password"
                    value={token}
                    onChange={(e) => setToken(e.target.value)}
                    placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
                    className="w-full pl-10 pr-4 py-3 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition font-mono"
                  />
                </div>
                <p className="text-[11px] text-slate-500 mt-1.5">
                  Required only if the repository is private. Uses read permissions to clone code.
                </p>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={loading}
                className="w-full py-3.5 px-6 bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 text-white rounded-xl font-semibold text-sm transition shadow-lg shadow-indigo-600/25 flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {loading ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Pulling Repository & Setting Up...
                  </>
                ) : (
                  <>
                    Pull Repository to Workspace
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>
          </div>

          {/* Right Info Column */}
          <div className="space-y-6">
            
            {/* Direct Chat Alternative */}
            <div className="bg-gradient-to-br from-indigo-900/30 to-slate-900 border border-indigo-500/30 rounded-2xl p-5 space-y-3">
              <div className="flex items-center gap-2 text-indigo-300 font-medium text-sm">
                <MessageSquare className="w-4 h-4 text-indigo-400" />
                Prefer Chat?
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                You can also type your GitHub repository URL directly in our chat response right here!
              </p>
              <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800 text-[11px] font-mono text-indigo-300">
                "Please pull https://github.com/myname/myrepo"
              </div>
            </div>

            {/* Quick Steps Guide */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4">
              <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                <Terminal className="w-4 h-4 text-indigo-400" />
                How it works
              </h3>

              <ol className="space-y-3 text-xs text-slate-400">
                <li className="flex gap-2.5">
                  <span className="flex shrink-0 w-5 h-5 rounded-full bg-slate-800 text-indigo-400 font-bold items-center justify-center text-[10px]">
                    1
                  </span>
                  <span>Enter your public repository link or <code className="text-slate-300">owner/repo</code> identifier.</span>
                </li>
                <li className="flex gap-2.5">
                  <span className="flex shrink-0 w-5 h-5 rounded-full bg-slate-800 text-indigo-400 font-bold items-center justify-center text-[10px]">
                    2
                  </span>
                  <span>For private repos, paste your GitHub Personal Access Token (PAT) with <code className="text-slate-300">repo</code> scope.</span>
                </li>
                <li className="flex gap-2.5">
                  <span className="flex shrink-0 w-5 h-5 rounded-full bg-slate-800 text-indigo-400 font-bold items-center justify-center text-[10px]">
                    3
                  </span>
                  <span>Click <strong>Pull Repository</strong> to download files and install dependencies automatically.</span>
                </li>
              </ol>
            </div>

            {/* Privacy & Security Note */}
            <div className="bg-slate-900/50 border border-slate-800/80 rounded-2xl p-4 text-xs text-slate-400 space-y-1">
              <p className="font-medium text-slate-300 flex items-center gap-1.5">
                <Lock className="w-3.5 h-3.5 text-emerald-400" />
                Secure Execution
              </p>
              <p className="text-[11px] leading-relaxed text-slate-400">
                Tokens are used strictly in-memory during the <code className="text-slate-300">git clone</code> process and are never logged or exposed.
              </p>
            </div>

          </div>

        </div>

      </main>
    </div>
  );
}
