import React, { useState, useEffect } from 'react';
import {
  TrendingUp,
  TrendingDown,
  Coins,
  DollarSign,
  ArrowUpRight,
  ArrowDownRight,
  RefreshCw,
  Calculator,
  ShieldAlert,
  BarChart2,
  Database
} from 'lucide-react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip } from 'recharts';
import { INITIAL_CRYPTO_COINS } from '../data/botDirectory';
import { CryptoCoin, LiveAggregatedState } from '../types';

interface CryptoMarketViewProps {
  liveData?: LiveAggregatedState | null;
}

export const CryptoMarketView: React.FC<CryptoMarketViewProps> = ({ liveData }) => {
  const [coins, setCoins] = useState<CryptoCoin[]>(() => {
    if (liveData?.firebase?.cryptoMarket && liveData.firebase.cryptoMarket.length > 0) {
      return liveData.firebase.cryptoMarket;
    }
    return INITIAL_CRYPTO_COINS;
  });

  const [selectedCoin, setSelectedCoin] = useState<CryptoCoin>(coins[0]);
  const [calcAmount, setCalcAmount] = useState<string>('1000000000'); // 1B
  const [calcAction, setCalcAction] = useState<'buy' | 'sell'>('buy');
  const [isLiveUpdating, setIsLiveUpdating] = useState<boolean>(true);

  // Sync if liveData updates from server
  useEffect(() => {
    if (liveData?.firebase?.cryptoMarket && liveData.firebase.cryptoMarket.length > 0) {
      setCoins(liveData.firebase.cryptoMarket);
      const current = liveData.firebase.cryptoMarket.find((c) => c.symbol === selectedCoin.symbol);
      if (current) setSelectedCoin(current);
    }
  }, [liveData]);

  // Live simulation tick every 4 seconds if not currently locked to remote server
  useEffect(() => {
    if (!isLiveUpdating) return;

    const interval = setInterval(() => {
      setCoins((prevCoins) =>
        prevCoins.map((coin) => {
          // Slight random fluctuation between -1.5% and +1.8%
          const pctDelta = (Math.random() * 3.3 - 1.5) / 100;
          const newPrice = Math.max(0.01, +(coin.price * (1 + pctDelta)).toFixed(2));
          const newChange24h = +(coin.change24h + pctDelta * 10).toFixed(2);
          
          const nowStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
          const newHistory = [...coin.history.slice(1), { time: nowStr, price: newPrice }];

          const updated = {
            ...coin,
            price: newPrice,
            change24h: newChange24h,
            high24h: Math.max(coin.high24h, newPrice),
            low24h: Math.min(coin.low24h, newPrice),
            trend: (newChange24h >= 0 ? 'bullish' : 'bearish') as 'bullish' | 'bearish',
            history: newHistory
          };

          if (selectedCoin.symbol === coin.symbol) {
            setSelectedCoin(updated);
          }

          return updated;
        })
      );
    }, 4000);

    return () => clearInterval(interval);
  }, [isLiveUpdating, selectedCoin.symbol]);

  const parsedAmount = parseFloat(calcAmount) || 0;
  const estimatedTokens = parsedAmount > 0 && selectedCoin.price > 0 ? (parsedAmount / selectedCoin.price).toFixed(4) : '0';
  const estimatedUwuncyPayout = parsedAmount > 0 ? (parsedAmount * selectedCoin.price).toLocaleString() : '0';

  return (
    <div className="space-y-8 animate-fadeIn">
      
      {/* Header & Market Status */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-900/70 border border-slate-800 rounded-2xl p-6">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
              <Coins className="w-5 h-5 text-emerald-400" />
              Live Crypwuncy Exchange Market
            </h2>
            <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 text-xs font-semibold border border-emerald-500/30 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              LIVE TICKER
            </span>
          </div>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Real-time cryptocurrency trading engine with 6 volatile assets synced with <code className="text-pink-300">main.py</code>.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsLiveUpdating(!isLiveUpdating)}
            className={`px-3 py-1.5 rounded-xl text-xs font-medium border transition flex items-center gap-1.5 ${
              isLiveUpdating
                ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30 hover:bg-emerald-500/20'
                : 'bg-slate-800 text-slate-400 border-slate-700 hover:text-white'
            }`}
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLiveUpdating ? 'animate-spin' : ''}`} />
            {isLiveUpdating ? 'Live Ticker: ON' : 'Live Ticker: PAUSED'}
          </button>
        </div>
      </div>

      {/* Crypto Assets Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {coins.map((coin) => {
          const isSelected = selectedCoin.symbol === coin.symbol;
          const isPositive = coin.change24h >= 0;

          return (
            <div
              key={coin.symbol}
              onClick={() => setSelectedCoin(coin)}
              className={`cursor-pointer rounded-2xl p-5 border transition-all duration-200 ${
                isSelected
                  ? 'bg-slate-900 border-pink-500/60 shadow-lg shadow-pink-500/10'
                  : 'bg-slate-900/60 border-slate-800 hover:border-slate-700 hover:bg-slate-900/90'
              }`}
            >
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-bold text-white text-base">{coin.displayName}</h3>
                  <span className="text-xs text-slate-400 font-mono">uwu {coin.symbol}</span>
                </div>

                <div className={`flex items-center gap-1 text-xs font-bold px-2 py-0.5 rounded-md ${
                  isPositive ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'
                }`}>
                  {isPositive ? <ArrowUpRight className="w-3.5 h-3.5" /> : <ArrowDownRight className="w-3.5 h-3.5" />}
                  {isPositive ? `+${coin.change24h}%` : `${coin.change24h}%`}
                </div>
              </div>

              <div className="mt-4 flex items-baseline justify-between">
                <div>
                  <div className="text-2xl font-extrabold text-white font-mono">
                    {coin.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </div>
                  <span className="text-[10px] text-slate-400 uppercase tracking-wider">uwuncy / coin</span>
                </div>

                <div className="text-right text-[11px] text-slate-400 space-y-0.5">
                  <div>H: {coin.high24h.toLocaleString()}</div>
                  <div>L: {coin.low24h.toLocaleString()}</div>
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
                <span className="capitalize flex items-center gap-1">
                  Trend: <strong className={isPositive ? 'text-emerald-400' : 'text-rose-400'}>{coin.trend}</strong>
                </span>
                <span className="text-pink-400 font-medium">Trade Asset →</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Selected Asset Interactive Chart & Quick Calculator */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Chart Column (8 cols) */}
        <div className="lg:col-span-8 bg-slate-900/70 border border-slate-800 rounded-2xl p-6 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-4">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-lg font-bold text-white">{selectedCoin.displayName} Live Chart</h3>
                <span className="text-xs font-mono px-2 py-0.5 bg-slate-800 text-pink-300 rounded">
                  uwu invest {selectedCoin.symbol} &lt;amount&gt;
                </span>
              </div>
              <p className="text-xs text-slate-400">Live price history synchronized with bot market ticks</p>
            </div>

            <div className="text-right">
              <div className="text-xl font-mono font-bold text-emerald-400">
                {selectedCoin.price.toLocaleString()} uwuncy
              </div>
              <span className="text-[10px] text-slate-400 uppercase tracking-wider">Current Market Price</span>
            </div>
          </div>

          {/* Area Chart Container */}
          <div className="h-64 w-full pt-4">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={selectedCoin.history}>
                <defs>
                  <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ec4899" stopOpacity={0.4}/>
                    <stop offset="95%" stopColor="#ec4899" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <XAxis dataKey="time" stroke="#64748b" fontSize={11} tickLine={false} />
                <YAxis stroke="#64748b" fontSize={11} tickLine={false} domain={['auto', 'auto']} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.75rem' }}
                  labelStyle={{ color: '#94a3b8', fontSize: '11px' }}
                  itemStyle={{ color: '#f472b6', fontWeight: 'bold' }}
                />
                <Area type="monotone" dataKey="price" stroke="#ec4899" strokeWidth={2.5} fillOpacity={1} fill="url(#colorPrice)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Investment Calculator Column (4 cols) */}
        <div className="lg:col-span-4 bg-slate-900/70 border border-slate-800 rounded-2xl p-6 flex flex-col justify-between space-y-4">
          <div className="space-y-4">
            <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
              <Calculator className="w-5 h-5 text-pink-400" />
              <h3 className="font-bold text-white text-base">Trade Estimator</h3>
            </div>

            {/* Buy / Sell Tabs */}
            <div className="grid grid-cols-2 gap-2 bg-slate-950 p-1 rounded-xl border border-slate-800">
              <button
                onClick={() => setCalcAction('buy')}
                className={`py-1.5 rounded-lg text-xs font-bold transition ${
                  calcAction === 'buy' ? 'bg-emerald-500 text-white' : 'text-slate-400 hover:text-white'
                }`}
              >
                Buy (Invest)
              </button>
              <button
                onClick={() => setCalcAction('sell')}
                className={`py-1.5 rounded-lg text-xs font-bold transition ${
                  calcAction === 'sell' ? 'bg-rose-500 text-white' : 'text-slate-400 hover:text-white'
                }`}
              >
                Sell (Cash Out)
              </button>
            </div>

            {/* Input Amount */}
            <div className="space-y-1.5">
              <label className="text-xs text-slate-400 font-medium">
                {calcAction === 'buy' ? 'Uwuncy Investment Amount' : 'Coins to Sell'}
              </label>
              <input
                type="number"
                value={calcAmount}
                onChange={(e) => setCalcAmount(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-sm text-white font-mono focus:outline-none focus:border-pink-500"
              />
            </div>

            {/* Result Breakdown Box */}
            <div className="bg-slate-950/80 rounded-xl p-3.5 border border-slate-800/80 space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-400">Target Coin:</span>
                <span className="text-white font-semibold">{selectedCoin.displayName}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Unit Price:</span>
                <span className="text-emerald-400 font-mono font-semibold">{selectedCoin.price.toLocaleString()} uwuncy</span>
              </div>
              <div className="pt-2 border-t border-slate-800 flex justify-between items-center text-sm font-bold">
                <span className="text-slate-300">{calcAction === 'buy' ? 'You Receive:' : 'Payout:'}</span>
                <span className="text-pink-400 font-mono">
                  {calcAction === 'buy' ? `${estimatedTokens} Coins` : `${estimatedUwuncyPayout} uwuncy`}
                </span>
              </div>
            </div>
          </div>

          {/* Bot Command to execute in Discord */}
          <div className="bg-pink-500/10 border border-pink-500/20 rounded-xl p-3 text-xs space-y-1">
            <span className="text-pink-300 font-semibold block">Discord Command:</span>
            <code className="text-slate-200 font-mono block">
              {calcAction === 'buy'
                ? `uwu invest ${selectedCoin.symbol} ${calcAmount}`
                : `uwu sell ${selectedCoin.symbol} ${calcAmount}`}
            </code>
          </div>
        </div>

      </div>

    </div>
  );
};
