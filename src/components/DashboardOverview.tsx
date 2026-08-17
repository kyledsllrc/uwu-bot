import React, { useState } from 'react';
import {
  Server,
  Users,
  Coins,
  Trophy,
  Music,
  ShieldCheck,
  Zap,
  TrendingUp,
  Flame,
  Radio,
  ArrowUpRight,
  CheckCircle2,
  Film,
  Bot,
  RefreshCw,
  Database,
  Key,
  Info,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  AlertCircle
} from 'lucide-react';
import { BotStats, LiveAggregatedState } from '../types';

interface DashboardOverviewProps {
  stats: BotStats | null;
  liveData: LiveAggregatedState | null;
  onRefresh: () => Promise<void>;
  isSyncing: boolean;
  setActiveTab: (tab: string) => void;
}

export const DashboardOverview: React.FC<DashboardOverviewProps> = ({
  stats,
  liveData,
  onRefresh,
  isSyncing,
  setActiveTab
}) => {
  const [showConfigGuide, setShowConfigGuide] = useState(false);
  const [showGuildsList, setShowGuildsList] = useState(false);

  const formatUwuncy = (num: number) => {
    if (num >= 1e12) return `${(num / 1e12).toFixed(2)} Trillion`;
    if (num >= 1e9) return `${(num / 1e9).toFixed(2)} Billion`;
    if (num >= 1e6) return `${(num / 1e6).toFixed(2)} Million`;
    return num.toLocaleString();
  };

  const isDiscordLive = Boolean(stats?.discordConnected || liveData?.discord?.connected);
  const isFirebaseLive = Boolean(stats?.firebaseConnected || liveData?.firebase?.connected);
  const botUser = stats?.botUser || liveData?.discord?.botUser;
  const guilds = liveData?.discord?.guilds || [];

  return (
    <div className="space-y-8 animate-fadeIn">

      {/* Live Data Connection & Sync Monitor */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-4 sm:p-5 shadow-xl backdrop-blur-md">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          
          {/* Connection Status Indicators */}
          <div className="flex flex-wrap items-center gap-3">
            
            {/* Discord API Status */}
            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-xl border text-xs font-semibold ${
              isDiscordLive
                ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                : 'bg-amber-500/10 text-amber-300 border-amber-500/30'
            }`}>
              <Radio className={`w-3.5 h-3.5 ${isDiscordLive ? 'text-emerald-400 animate-pulse' : 'text-amber-400'}`} />
              <span>
                Discord Gateway: {isDiscordLive ? (botUser?.tag || 'Connected') : 'Awaiting Token'}
              </span>
              {isDiscordLive && (
                <span className="font-mono text-emerald-400 bg-emerald-500/20 px-1.5 py-0.2 rounded text-[10px]">
                  {stats?.pingMs || liveData?.discord?.pingMs || 0}ms
                </span>
              )}
            </div>

            {/* Firebase Database Status */}
            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-xl border text-xs font-semibold ${
              isFirebaseLive
                ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                : 'bg-amber-500/10 text-amber-300 border-amber-500/30'
            }`}>
              <Database className={`w-3.5 h-3.5 ${isFirebaseLive ? 'text-emerald-400' : 'text-amber-400'}`} />
              <span>
                Firebase Database: {isFirebaseLive ? `${liveData?.firebase?.totalUsers || stats?.totalUsers || 0} Synced Wallets` : 'Awaiting Credentials'}
              </span>
            </div>

            {/* Code Engine Sync */}
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-purple-500/10 text-purple-300 border border-purple-500/30 text-xs font-semibold">
              <Bot className="w-3.5 h-3.5 text-purple-400" />
              <span>Code Engine: {stats?.totalCommandsExtracted || 151} Live Commands</span>
            </div>

          </div>

          {/* Sync Trigger & Config Guide Buttons */}
          <div className="flex items-center gap-2 self-start md:self-auto">
            <button
              onClick={() => setShowConfigGuide(!showConfigGuide)}
              className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium border border-slate-700 transition flex items-center gap-1.5"
            >
              <Key className="w-3.5 h-3.5 text-pink-400" />
              <span>{(!isDiscordLive || !isFirebaseLive) ? 'Setup Live Tokens' : 'Connection Details'}</span>
              {showConfigGuide ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </button>

            <button
              onClick={onRefresh}
              disabled={isSyncing}
              className="px-3.5 py-1.5 rounded-xl bg-gradient-to-r from-pink-500 to-purple-600 hover:from-pink-400 hover:to-purple-500 text-white text-xs font-semibold shadow-md transition flex items-center gap-1.5 disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isSyncing ? 'animate-spin' : ''}`} />
              <span>{isSyncing ? 'Syncing...' : 'Sync Live Data'}</span>
            </button>
          </div>

        </div>

        {/* Expandable Configuration & Live Status Details */}
        {showConfigGuide && (
          <div className="mt-4 pt-4 border-t border-slate-800 space-y-4 text-xs">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              
              {/* Discord Token Setup Info */}
              <div className="bg-slate-950/80 p-4 rounded-xl border border-slate-800/80 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-white flex items-center gap-1.5">
                    <Radio className="w-3.5 h-3.5 text-pink-400" /> Discord Bot Integration
                  </span>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    isDiscordLive ? 'bg-emerald-500/20 text-emerald-300' : 'bg-amber-500/20 text-amber-300'
                  }`}>
                    {isDiscordLive ? 'ACTIVE' : 'TOKEN REQUIRED'}
                  </span>
                </div>
                <p className="text-slate-400 leading-relaxed">
                  {isDiscordLive ? (
                    <>Connected as <strong>{botUser?.tag}</strong> (ID: <code className="text-pink-300">{botUser?.id}</code>). Currently active in <strong>{stats?.totalServers || guilds.length} Discord servers</strong> with <strong>{stats?.totalUsers} approximate members</strong>.</>
                  ) : (
                    <>To fetch live server counts, real bot avatar, and gateway ping, add your <code className="text-pink-300 bg-pink-500/10 px-1 py-0.5 rounded">DISCORD_BOT_TOKEN</code> secret in AI Studio Settings.</>
                  )}
                </p>
                {guilds.length > 0 && (
                  <button
                    onClick={() => setShowGuildsList(!showGuildsList)}
                    className="text-pink-400 hover:text-pink-300 font-semibold underline pt-1 block"
                  >
                    {showGuildsList ? 'Hide Connected Servers' : `View ${guilds.length} Connected Guilds`}
                  </button>
                )}
              </div>

              {/* Firebase Database Setup Info */}
              <div className="bg-slate-950/80 p-4 rounded-xl border border-slate-800/80 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-white flex items-center gap-1.5">
                    <Database className="w-3.5 h-3.5 text-indigo-400" /> Firebase Realtime Database
                  </span>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    isFirebaseLive ? 'bg-emerald-500/20 text-emerald-300' : 'bg-amber-500/20 text-amber-300'
                  }`}>
                    {isFirebaseLive ? 'SYNCED' : 'CREDENTIALS REQUIRED'}
                  </span>
                </div>
                <p className="text-slate-400 leading-relaxed">
                  {isFirebaseLive ? (
                    <>Connected to <code className="text-indigo-300">{liveData?.firebase?.databaseUrl}</code>. Live balances, jackpot pool, crypto rates, and user ranks are synchronized directly with Discord interaction commands.</>
                  ) : (
                    <>To load real player wallets, crypto investments, and leaderboard from your bot database, add <code className="text-indigo-300 bg-indigo-500/10 px-1 py-0.5 rounded">FIREBASE_CREDENTIALS</code> in AI Studio Settings.</>
                  )}
                </p>
                <div className="text-[11px] text-slate-500">
                  Default Database: <code className="text-slate-400">https://uwu-bot-4cff1-default-rtdb.asia-southeast1.firebasedatabase.app</code>
                </div>
              </div>

            </div>

            {/* Guilds List Dropdown */}
            {showGuildsList && guilds.length > 0 && (
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800/80 space-y-3">
                <h4 className="font-bold text-white">Live Connected Discord Guilds ({guilds.length})</h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2 max-h-48 overflow-y-auto pr-1">
                  {guilds.map((g) => (
                    <div key={g.id} className="flex items-center gap-2 p-2 bg-slate-900 rounded-lg border border-slate-800">
                      {g.iconUrl ? (
                        <img src={g.iconUrl} alt={g.name} className="w-6 h-6 rounded-full" />
                      ) : (
                        <div className="w-6 h-6 rounded-full bg-slate-800 flex items-center justify-center font-bold text-[10px] text-pink-400">
                          {g.name.charAt(0)}
                        </div>
                      )}
                      <div className="truncate">
                        <div className="font-medium text-slate-200 truncate">{g.name}</div>
                        <div className="text-[10px] text-slate-500">{(g.approximate_member_count || 0).toLocaleString()} members</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="flex items-center justify-between text-slate-500 text-[11px]">
              <span>Last Synchronized: {stats?.syncedAt ? new Date(stats.syncedAt).toLocaleTimeString() : 'Just now'}</span>
              <span>Bot Codebase: {stats?.codeLineCount?.toLocaleString() || '24,000+'} Lines of Python (main.py)</span>
            </div>
          </div>
        )}
      </div>

      {/* Hero Banner with Anime Aesthetic */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-slate-900 via-purple-950/40 to-slate-900 border border-purple-500/20 p-6 sm:p-8 lg:p-10 shadow-2xl">
        <div className="absolute top-0 right-0 -mt-8 -mr-8 w-72 h-72 bg-pink-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 left-1/3 -mb-12 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
        
        <div className="relative z-10 grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
          <div className="lg:col-span-8 space-y-4">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-pink-500/10 border border-pink-500/30 text-pink-300 text-xs font-semibold uppercase tracking-wider">
              <SparklesIcon className="w-3.5 h-3.5 text-pink-400" />
              Official Discord Bot Control Center
            </div>
            
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-white tracking-tight leading-tight">
              {isDiscordLive && botUser ? botUser.username : 'UwU Bot'} — Economy, Casino, Music & Community
            </h1>
            
            <p className="text-slate-300 text-sm sm:text-base max-w-2xl leading-relaxed">
              Featuring dynamic crypto market investments, multiplayer arena lobbies, 24/7 Lavalink V4 music, 
              movie watch parties, community polls with up to 20 choices, and an empathetic AI emotional companion.
            </p>

            {/* Quick Action Badges */}
            <div className="flex flex-wrap items-center gap-3 pt-2">
              <button
                onClick={() => setActiveTab('commands')}
                className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-pink-500 to-purple-600 hover:from-pink-400 hover:to-purple-500 text-white text-sm font-semibold shadow-lg shadow-pink-500/25 transition transform active:scale-95 flex items-center gap-2"
              >
                <Bot className="w-4 h-4" />
                Browse Commands ({stats?.totalCommandsExtracted || 151})
              </button>
              
              <button
                onClick={() => setActiveTab('crypto')}
                className="px-5 py-2.5 rounded-xl bg-slate-800/80 hover:bg-slate-700 text-slate-200 text-sm font-semibold border border-slate-700 transition flex items-center gap-2"
              >
                <TrendingUp className="w-4 h-4 text-emerald-400" />
                Live Crypto Market
              </button>

              <button
                onClick={() => setActiveTab('showcase')}
                className="px-5 py-2.5 rounded-xl bg-slate-800/80 hover:bg-slate-700 text-slate-200 text-sm font-semibold border border-slate-700 transition flex items-center gap-2"
              >
                <Film className="w-4 h-4 text-pink-400" />
                Movie Night & Polls
              </button>
            </div>
          </div>

          {/* Real-time System Status Card */}
          <div className="lg:col-span-4 bg-slate-950/70 backdrop-blur-md rounded-2xl border border-slate-800/90 p-5 space-y-4 shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Bot Cluster Status</span>
              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-semibold">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
                {isDiscordLive ? 'Gateway Active' : 'Online & Ready'}
              </span>
            </div>

            <div className="space-y-2.5 text-xs">
              <div className="flex justify-between items-center py-1">
                <span className="text-slate-400 flex items-center gap-1.5">
                  <Radio className="w-3.5 h-3.5 text-pink-400" /> Discord Gateway
                </span>
                <span className="text-slate-200 font-mono font-medium">
                  {stats?.pingMs || 0}ms {isDiscordLive ? '(Live REST)' : '(Standby)'}
                </span>
              </div>
              <div className="flex justify-between items-center py-1">
                <span className="text-slate-400 flex items-center gap-1.5">
                  <Music className="w-3.5 h-3.5 text-indigo-400" /> Lavalink Cluster
                </span>
                <span className="text-slate-200 font-mono font-medium">{stats?.activeLavalinkNodes || 2} Live V4 Nodes</span>
              </div>
              <div className="flex justify-between items-center py-1">
                <span className="text-slate-400 flex items-center gap-1.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" /> Anti-Nuke Shield
                </span>
                <span className="text-emerald-300 font-semibold">{stats?.antiNukeStatus || 'Armed & Active'}</span>
              </div>
              <div className="flex justify-between items-center py-1">
                <span className="text-slate-400 flex items-center gap-1.5">
                  <Database className="w-3.5 h-3.5 text-amber-400" /> Database Link
                </span>
                <span className="text-slate-200 font-mono font-medium">
                  {isFirebaseLive ? 'RTDB Firebase' : 'Code Engine'}
                </span>
              </div>
            </div>

            <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
              <span>Default Prefix: <code className="text-pink-300 bg-pink-500/10 px-1.5 py-0.5 rounded font-mono font-bold">uwu</code></span>
              <span className="text-slate-500">v2.8.0</span>
            </div>
          </div>
        </div>
      </div>

      {/* Key Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        
        {/* Metric 1: Total Circulating Wealth */}
        <div className="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-5 relative overflow-hidden group hover:border-pink-500/40 transition">
          <div className="flex items-center justify-between text-slate-400 mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider">Total Wealth</span>
            <div className="p-2 bg-pink-500/10 text-pink-400 rounded-xl">
              <Coins className="w-5 h-5" />
            </div>
          </div>
          <div className="text-2xl font-black text-white tracking-tight">
            {stats && stats.totalUwuncyInCirculation > 0 ? (
              <>{formatUwuncy(stats.totalUwuncyInCirculation)} <span className="text-sm font-normal text-pink-400">uwuncy</span></>
            ) : (
              <span className="text-lg text-slate-300 font-semibold">
                {isFirebaseLive ? '0 uwuncy' : 'Synced on Connect'}
              </span>
            )}
          </div>
          <p className="text-xs text-slate-400 mt-1 flex items-center gap-1">
            <TrendingUp className="w-3.5 h-3.5 text-emerald-400" /> 
            {isFirebaseLive ? 'Live across all player accounts' : 'Requires Firebase credentials'}
          </p>
        </div>

        {/* Metric 2: Connected Servers */}
        <div className="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-5 relative overflow-hidden group hover:border-purple-500/40 transition">
          <div className="flex items-center justify-between text-slate-400 mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider">Discord Guilds</span>
            <div className="p-2 bg-purple-500/10 text-purple-400 rounded-xl">
              <Server className="w-5 h-5" />
            </div>
          </div>
          <div className="text-2xl font-black text-white tracking-tight">
            {stats?.totalServers !== undefined ? (
              <>{stats.totalServers} <span className="text-sm font-normal text-purple-400">Servers</span></>
            ) : (
              '0 Servers'
            )}
          </div>
          <p className="text-xs text-slate-400 mt-1 flex items-center gap-1">
            <Users className="w-3.5 h-3.5 text-slate-400" /> Serving {(stats?.totalUsers || 0).toLocaleString()} users
          </p>
        </div>

        {/* Metric 3: Jackpot Prize Pool */}
        <div className="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-5 relative overflow-hidden group hover:border-amber-500/40 transition">
          <div className="flex items-center justify-between text-slate-400 mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider">Jackpot Pool</span>
            <div className="p-2 bg-amber-500/10 text-amber-400 rounded-xl">
              <Trophy className="w-5 h-5" />
            </div>
          </div>
          <div className="text-2xl font-black text-amber-300 tracking-tight">
            {formatUwuncy(stats?.totalJackpotPool || 10000)} <span className="text-sm font-normal text-amber-400">uwuncy</span>
          </div>
          <p className="text-xs text-slate-400 mt-1 flex items-center gap-1">
            <Flame className="w-3.5 h-3.5 text-amber-400" /> Accumulates from slots & casino bets
          </p>
        </div>

        {/* Metric 4: Total Executions / Commands */}
        <div className="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-5 relative overflow-hidden group hover:border-indigo-500/40 transition">
          <div className="flex items-center justify-between text-slate-400 mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider">Bot Commands</span>
            <div className="p-2 bg-indigo-500/10 text-indigo-400 rounded-xl">
              <Zap className="w-5 h-5" />
            </div>
          </div>
          <div className="text-2xl font-black text-white tracking-tight">
            {stats?.totalCommandsExtracted || 151} <span className="text-sm font-normal text-indigo-400">Commands</span>
          </div>
          <p className="text-xs text-slate-400 mt-1 flex items-center gap-1">
            <CheckCircle2 className="w-3.5 h-3.5 text-indigo-400" /> Extracted directly from main.py
          </p>
        </div>

      </div>

      {/* Feature Pillars Showcase */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* Card 1: 20-Choice Polls & Watch Parties */}
        <div 
          onClick={() => setActiveTab('showcase')}
          className="cursor-pointer bg-slate-900/60 hover:bg-slate-900/90 border border-slate-800 hover:border-pink-500/40 rounded-2xl p-6 transition group shadow-lg flex flex-col justify-between"
        >
          <div className="space-y-3">
            <div className="w-12 h-12 rounded-xl bg-pink-500/10 border border-pink-500/20 flex items-center justify-center text-pink-400 text-xl group-hover:scale-110 transition transform">
              🎬
            </div>
            <h2 className="text-lg font-bold text-white group-hover:text-pink-300 transition flex items-center gap-1.5">
              Movie Streams & Polls
              <ArrowUpRight className="w-4 h-4 opacity-0 group-hover:opacity-100 transition" />
            </h2>
            <p className="text-slate-400 text-xs sm:text-sm leading-relaxed">
              Automatic movie lookups with poster art, RSVP buttons, and the new <strong>20-choice community poll system</strong> with real-time percentage progress bars.
            </p>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-pink-400 font-semibold">
            <span>Try Interactive Demo</span>
            <span>uwu poll / uwu movie →</span>
          </div>
        </div>

        {/* Card 2: AI Emotional Support Companion */}
        <div 
          onClick={() => setActiveTab('showcase')}
          className="cursor-pointer bg-slate-900/60 hover:bg-slate-900/90 border border-slate-800 hover:border-purple-500/40 rounded-2xl p-6 transition group shadow-lg flex flex-col justify-between"
        >
          <div className="space-y-3">
            <div className="w-12 h-12 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400 text-xl group-hover:scale-110 transition transform">
              💬
            </div>
            <h2 className="text-lg font-bold text-white group-hover:text-purple-300 transition flex items-center gap-1.5">
              AI Rant & Emotional Comfort
              <ArrowUpRight className="w-4 h-4 opacity-0 group-hover:opacity-100 transition" />
            </h2>
            <p className="text-slate-400 text-xs sm:text-sm leading-relaxed">
              Empathetic AI listener that recognizes sentiment and responds in natural Tagalog, English, Bisaya, Japanese, and more whenever users vent their feelings.
            </p>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-purple-400 font-semibold">
            <span>Explore AI Engine</span>
            <span>uwu rant / uwu vent →</span>
          </div>
        </div>

        {/* Card 3: Live Casino & Crypto Exchange */}
        <div 
          onClick={() => setActiveTab('crypto')}
          className="cursor-pointer bg-slate-900/60 hover:bg-slate-900/90 border border-slate-800 hover:border-emerald-500/40 rounded-2xl p-6 transition group shadow-lg flex flex-col justify-between"
        >
          <div className="space-y-3">
            <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 text-xl group-hover:scale-110 transition transform">
              📈
            </div>
            <h2 className="text-lg font-bold text-white group-hover:text-emerald-300 transition flex items-center gap-1.5">
              Crypto Exchange & Real Estate
              <ArrowUpRight className="w-4 h-4 opacity-0 group-hover:opacity-100 transition" />
            </h2>
            <p className="text-slate-400 text-xs sm:text-sm leading-relaxed">
              Trade 6 fluctuating cryptocurrencies, climb the global wealth leaderboard, purchase luxury estates for hourly income, and collect prestige badges.
            </p>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-emerald-400 font-semibold">
            <span>View Live Tickers</span>
            <span>uwu crypto / uwu properties →</span>
          </div>
        </div>

      </div>

    </div>
  );
};

function SparklesIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z" />
      <path d="M5 3v4" />
      <path d="M19 17v4" />
      <path d="M3 5h4" />
      <path d="M17 19h4" />
    </svg>
  );
}
