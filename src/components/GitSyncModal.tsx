import React, { useState, useEffect } from 'react';
import {
  Github,
  GitBranch,
  GitCommit,
  RefreshCw,
  X,
  CheckCircle2,
  AlertCircle,
  DownloadCloud
} from 'lucide-react';
import { RepoStatus } from '../types';

interface GitSyncModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const GitSyncModal: React.FC<GitSyncModalProps> = ({ isOpen, onClose }) => {
  const [repoStatus, setRepoStatus] = useState<RepoStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [pulling, setPulling] = useState<boolean>(false);
  const [actionMessage, setActionMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  const fetchRepoStatus = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/repo-status');
      const data = await res.json();
      setRepoStatus(data);
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchRepoStatus();
    }
  }, [isOpen]);

  const handleGitPull = async () => {
    setPulling(true);
    setActionMessage(null);
    try {
      const res = await fetch('/api/pull', { method: 'POST' });
      const data = await res.json();
      if (res.ok) {
        setActionMessage({ text: data.message || 'Successfully pulled latest changes!', type: 'success' });
        fetchRepoStatus();
      } else {
        setActionMessage({ text: data.error || 'Failed to pull changes', type: 'error' });
      }
    } catch (err: any) {
      setActionMessage({ text: err.message || 'Network error while pulling', type: 'error' });
    } finally {
      setPulling(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fadeIn">
      <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-lg w-full p-6 space-y-6 shadow-2xl relative">
        
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-slate-800 text-white">
              <Github className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">GitHub Repository Sync</h3>
              <p className="text-xs text-slate-400">Workspace Git status & remote tracking</p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg bg-slate-800 text-slate-400 hover:text-white transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Status Content */}
        {loading ? (
          <div className="py-8 text-center text-xs text-slate-400 flex items-center justify-center gap-2">
            <RefreshCw className="w-4 h-4 animate-spin text-pink-400" />
            Loading repository details...
          </div>
        ) : repoStatus?.hasRepo ? (
          <div className="space-y-4 text-xs font-mono">
            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
              <div className="flex items-center justify-between text-slate-300">
                <span className="text-slate-500">Remote:</span>
                <span className="text-pink-300 font-bold truncate max-w-[280px]">{repoStatus.remoteUrl}</span>
              </div>
              <div className="flex items-center justify-between text-slate-300">
                <span className="text-slate-500">Branch:</span>
                <span className="text-emerald-400 font-bold flex items-center gap-1">
                  <GitBranch className="w-3.5 h-3.5" />
                  {repoStatus.branch}
                </span>
              </div>
              <div className="flex items-center justify-between text-slate-300">
                <span className="text-slate-500">Last Commit:</span>
                <span className="text-slate-200 truncate max-w-[280px]">{repoStatus.lastCommit}</span>
              </div>
            </div>

            {actionMessage && (
              <div
                className={`p-3 rounded-xl flex items-center gap-2 text-xs ${
                  actionMessage.type === 'success'
                    ? 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/30'
                    : 'bg-rose-500/10 text-rose-300 border border-rose-500/30'
                }`}
              >
                {actionMessage.type === 'success' ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                ) : (
                  <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />
                )}
                <span>{actionMessage.text}</span>
              </div>
            )}

            <div className="pt-2 flex gap-3">
              <button
                onClick={handleGitPull}
                disabled={pulling}
                className="flex-1 py-2.5 bg-gradient-to-r from-pink-500 to-purple-600 hover:from-pink-400 hover:to-purple-500 text-white font-bold rounded-xl text-xs transition flex items-center justify-center gap-1.5 shadow-lg shadow-pink-500/20 disabled:opacity-50"
              >
                <DownloadCloud className={`w-4 h-4 ${pulling ? 'animate-bounce' : ''}`} />
                {pulling ? 'Pulling changes...' : 'Pull Latest Commits'}
              </button>

              <button
                onClick={fetchRepoStatus}
                className="px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs transition"
              >
                Refresh
              </button>
            </div>
          </div>
        ) : (
          <div className="text-center py-6 text-slate-400 text-xs">
            No local git repository cloned yet.
          </div>
        )}

      </div>
    </div>
  );
};
