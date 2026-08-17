import React, { useState, useEffect, useCallback } from 'react';
import { Navbar } from './components/Navbar';
import { DashboardOverview } from './components/DashboardOverview';
import { CommandsDirectory } from './components/CommandsDirectory';
import { CryptoMarketView } from './components/CryptoMarketView';
import { CasinoPlayground } from './components/CasinoPlayground';
import { FeaturesShowcase } from './components/FeaturesShowcase';
import { EconomyAndShopView } from './components/EconomyAndShopView';
import { GitSyncModal } from './components/GitSyncModal';
import { BotStats, LiveAggregatedState, BotCommand, ShopsCatalogResponse } from './types';
import { BOT_COMMANDS } from './data/botDirectory';
import {
  Github,
  ExternalLink,
} from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState<string>('dashboard');
  const [stats, setStats] = useState<BotStats | null>(null);
  const [liveData, setLiveData] = useState<LiveAggregatedState | null>(null);
  const [commands, setCommands] = useState<BotCommand[]>(BOT_COMMANDS);
  const [shopsData, setShopsData] = useState<ShopsCatalogResponse | null>(null);
  const [gitModalOpen, setGitModalOpen] = useState<boolean>(false);
  const [isSyncing, setIsSyncing] = useState<boolean>(false);

  // Fetch all live data endpoints
  const fetchAllData = useCallback(async () => {
    setIsSyncing(true);
    try {
      const [statsRes, liveRes, cmdRes, shopRes] = await Promise.allSettled([
        fetch('/api/bot/stats'),
        fetch('/api/bot/live-data'),
        fetch('/api/bot/commands'),
        fetch('/api/bot/shops')
      ]);

      if (statsRes.status === 'fulfilled' && statsRes.value.ok) {
        const data = await statsRes.value.json();
        setStats(data);
      }

      if (liveRes.status === 'fulfilled' && liveRes.value.ok) {
        const data = await liveRes.value.json();
        setLiveData(data);
      }

      if (cmdRes.status === 'fulfilled' && cmdRes.value.ok) {
        const data = await cmdRes.value.json();
        if (data.commands && data.commands.length > 0) {
          setCommands(data.commands);
        }
      }

      if (shopRes.status === 'fulfilled' && shopRes.value.ok) {
        const data = await shopRes.value.json();
        setShopsData(data);
      }
    } catch (err) {
      console.error('Failed to sync live data:', err);
    } finally {
      setIsSyncing(false);
    }
  }, []);

  useEffect(() => {
    fetchAllData();
    const interval = setInterval(fetchAllData, 15000);
    return () => clearInterval(interval);
  }, [fetchAllData]);

  return (
    <div className="min-h-screen bg-[#0b0f19] text-slate-100 flex flex-col selection:bg-pink-500 selection:text-white font-sans">
      
      {/* Top Navigation */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        stats={stats}
        onOpenGitModal={() => setGitModalOpen(true)}
      />

      {/* Main App Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'dashboard' && (
          <DashboardOverview
            stats={stats}
            liveData={liveData}
            onRefresh={fetchAllData}
            isSyncing={isSyncing}
            setActiveTab={setActiveTab}
          />
        )}
        {activeTab === 'commands' && <CommandsDirectory commands={commands} />}
        {activeTab === 'crypto' && <CryptoMarketView liveData={liveData} />}
        {activeTab === 'casino' && <CasinoPlayground />}
        {activeTab === 'showcase' && <FeaturesShowcase />}
        {activeTab === 'economy' && (
          <EconomyAndShopView liveData={liveData} shopsData={shopsData} />
        )}
      </main>

      {/* Git Sync Modal */}
      <GitSyncModal
        isOpen={gitModalOpen}
        onClose={() => setGitModalOpen(false)}
      />

      {/* Footer */}
      <footer className="bg-slate-950 border-t border-slate-800/80 py-8 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-400">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-pink-500 to-purple-600 flex items-center justify-center text-white font-bold text-xs">
              ✨
            </div>
            <span className="font-semibold text-slate-300">
              {stats?.botUser?.username || 'UwU Bot'} Official Portal
            </span>
            <span>• Live synced with Discord API & Firebase RTDB</span>
          </div>

          <div className="flex items-center gap-6">
            <button
              onClick={() => setGitModalOpen(true)}
              className="hover:text-pink-400 transition flex items-center gap-1"
            >
              <Github className="w-3.5 h-3.5" /> Sync Repository
            </button>
            <a
              href="https://discord.com"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-pink-400 transition flex items-center gap-1"
            >
              <ExternalLink className="w-3.5 h-3.5" /> Discord Gateway
            </a>
            <span className="text-slate-600">|</span>
            <span className="text-emerald-400 flex items-center gap-1 font-mono">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              {stats?.discordConnected ? 'Live Connection' : 'Ready'}
            </span>
          </div>
        </div>
      </footer>

    </div>
  );
}
