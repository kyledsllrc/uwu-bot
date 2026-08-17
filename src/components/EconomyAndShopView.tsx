import React, { useState } from 'react';
import {
  Trophy,
  Crown,
  Building2,
  Sparkles,
  Heart,
  Zap,
  Coins,
  Shield,
  Clock,
  ArrowUpRight,
  Database,
  Tag,
  CheckCircle2,
  Gift
} from 'lucide-react';
import {
  PROPERTIES_CATALOG,
  COLLECTIBLES_CATALOG,
  FLOWERS_CATALOG,
  BOOSTER_ITEMS_CATALOG
} from '../data/botDirectory';
import { LiveAggregatedState, ShopsCatalogResponse, LeaderboardUser } from '../types';

interface EconomyAndShopViewProps {
  liveData: LiveAggregatedState | null;
  shopsData: ShopsCatalogResponse | null;
}

export const EconomyAndShopView: React.FC<EconomyAndShopViewProps> = ({
  liveData,
  shopsData
}) => {
  const [shopTab, setShopTab] = useState<'leaderboard' | 'properties' | 'collectibles' | 'flowers' | 'booster' | 'economy_rules'>('leaderboard');
  const [selectedBoosterCategory, setSelectedBoosterCategory] = useState<string>('All');

  const formatUwuncy = (num: number) => {
    if (num >= 1e12) return `${(num / 1e12).toFixed(2)}T`;
    if (num >= 1e9) return `${(num / 1e9).toFixed(2)}B`;
    if (num >= 1e6) return `${(num / 1e6).toFixed(2)}M`;
    return num.toLocaleString();
  };

  // Extract catalogs from live server or default fallback
  const flowers = shopsData?.flowers || FLOWERS_CATALOG;
  const properties = shopsData?.properties || PROPERTIES_CATALOG;
  const collectibles = shopsData?.collectibles || COLLECTIBLES_CATALOG;
  const boosterItems = shopsData?.boosterItems || BOOSTER_ITEMS_CATALOG;
  const leaderboard: LeaderboardUser[] = liveData?.firebase?.leaderboard || [];

  const boosterCategories = ['All', 'Economy & Multipliers', 'Command & Utility Perks', 'Limited & Rare'];
  const filteredBoosterItems = selectedBoosterCategory === 'All'
    ? boosterItems
    : boosterItems.filter((i) => i.category === selectedBoosterCategory);

  return (
    <div className="space-y-8 animate-fadeIn">
      
      {/* Header & Sub-Navigation Tabs */}
      <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-6 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-pink-400" />
              Economy Store, Real Estate & Global Rankings
            </h2>
            <p className="text-xs sm:text-sm text-slate-400 mt-1">
              Live items and wealth rankings synced directly with <code className="text-pink-300">main.py</code> and <code className="text-pink-300">booster_utils.py</code>.
            </p>
          </div>

          <div className="flex items-center gap-2 text-xs">
            <span className="px-3 py-1 rounded-xl bg-purple-500/10 text-purple-300 border border-purple-500/30 flex items-center gap-1.5 font-medium">
              <Coins className="w-3.5 h-3.5" /> Hourly Claim: 500B uwuncy
            </span>
            <span className="px-3 py-1 rounded-xl bg-pink-500/10 text-pink-300 border border-pink-500/30 flex items-center gap-1.5 font-medium">
              <Zap className="w-3.5 h-3.5" /> Booster Daily: 5T uwuncy
            </span>
          </div>
        </div>

        {/* Store Tabs */}
        <div className="flex flex-wrap gap-2 pt-2 border-t border-slate-800/80">
          {[
            { id: 'leaderboard', label: '🏆 Wealth Leaderboard', count: leaderboard.length },
            { id: 'booster', label: '💎 Booster Shop', count: boosterItems.length },
            { id: 'properties', label: '🏙️ Real Estate', count: properties.length },
            { id: 'collectibles', label: '👑 Collectibles', count: collectibles.length },
            { id: 'flowers', label: '🌸 Flowers & Charisma', count: flowers.length },
            { id: 'economy_rules', label: '📜 Economy Configuration' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setShopTab(tab.id as any)}
              className={`px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-1.5 ${
                shopTab === tab.id
                  ? 'bg-pink-500 text-white shadow-md shadow-pink-500/20'
                  : 'bg-slate-800 text-slate-300 hover:bg-slate-700 hover:text-white'
              }`}
            >
              <span>{tab.label}</span>
              {tab.count !== undefined && (
                <span className={`px-1.5 py-0.2 rounded-full text-[10px] ${
                  shopTab === tab.id ? 'bg-white/20 text-white' : 'bg-slate-900 text-slate-400'
                }`}>
                  {tab.count}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* 1. Global Wealth Leaderboard */}
      {shopTab === 'leaderboard' && (
        <div className="bg-slate-900/70 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
          <div className="p-5 bg-slate-950/60 border-b border-slate-800 flex items-center justify-between">
            <h3 className="font-bold text-white text-base flex items-center gap-2">
              <Crown className="w-4 h-4 text-amber-400" />
              Global Net Worth Rankings ({leaderboard.length} Ranked Players)
            </h3>
            <span className="text-xs text-slate-400 font-mono">uwu lb • Firebase Synced</span>
          </div>

          {leaderboard.length > 0 ? (
            <div className="divide-y divide-slate-800/80">
              {leaderboard.map((user) => (
                <div
                  key={user.rank}
                  className="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-slate-800/40 transition"
                >
                  <div className="flex items-center gap-4">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center font-black text-xs ${
                      user.rank === 1
                        ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                        : user.rank === 2
                        ? 'bg-slate-300/20 text-slate-200 border border-slate-300/40'
                        : user.rank === 3
                        ? 'bg-amber-700/20 text-amber-500 border border-amber-700/40'
                        : 'bg-slate-800 text-slate-400'
                    }`}>
                      #{user.rank}
                    </div>

                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-lg">
                        {user.avatar || '👤'}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-white text-sm">{user.username}</span>
                          {user.isBooster && (
                            <span className="px-1.5 py-0.5 rounded bg-pink-500/20 text-pink-300 border border-pink-500/30 text-[10px] font-bold">
                              BOOSTER
                            </span>
                          )}
                          {user.prestigeLevel > 0 && (
                            <span className="px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 text-[10px] font-bold">
                              P{user.prestigeLevel}
                            </span>
                          )}
                        </div>
                        <div className="text-xs text-slate-400 flex items-center gap-2 mt-0.5">
                          {user.clanTag && <span className="text-purple-400 font-mono">[{user.clanTag}]</span>}
                          {user.marriedTo && <span>💍 Married to {user.marriedTo}</span>}
                          {user.charismaExp > 0 && <span>✨ {user.charismaExp.toLocaleString()} Charisma</span>}
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-6 self-end sm:self-auto text-right">
                    <div>
                      <div className="text-xs text-slate-400">Total Net Worth</div>
                      <div className="text-base font-extrabold text-pink-400 font-mono">
                        {formatUwuncy(user.totalNetWorth)} <span className="text-xs">uwuncy</span>
                      </div>
                    </div>
                    <div className="hidden sm:block text-xs text-slate-500">
                      <div>Wallet: {formatUwuncy(user.wallet)}</div>
                      <div>Bank: {formatUwuncy(user.bank)}</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-8 text-center text-slate-400 space-y-3">
              <Database className="w-8 h-8 text-slate-500 mx-auto" />
              <p className="text-sm font-medium">No player accounts synced from Firebase yet.</p>
              <p className="text-xs text-slate-500 max-w-md mx-auto">
                Once users run <code className="text-pink-300">uwu claim</code> or gamble on your Discord server, their balances and net worth will appear here automatically.
              </p>
            </div>
          )}
        </div>
      )}

      {/* 2. Booster Shop (16 Real Items from booster_utils.py) */}
      {shopTab === 'booster' && (
        <div className="space-y-6">
          <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div>
              <h3 className="font-bold text-white text-lg flex items-center gap-2">
                <Zap className="w-5 h-5 text-pink-400" />
                Exclusive Server Booster Shop (16 Items)
              </h3>
              <p className="text-xs sm:text-sm text-slate-400 mt-1">
                Purchase prestige badges, multipliers, and perks using <code className="text-pink-300">uwu booster buy &lt;id&gt;</code>.
              </p>
            </div>

            <div className="flex flex-wrap gap-1.5 bg-slate-950 p-1 rounded-xl border border-slate-800">
              {boosterCategories.map((cat) => (
                <button
                  key={cat}
                  onClick={() => setSelectedBoosterCategory(cat)}
                  className={`px-3 py-1 rounded-lg text-xs font-semibold transition ${
                    selectedBoosterCategory === cat
                      ? 'bg-pink-500 text-white'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredBoosterItems.map((item) => (
              <div
                key={item.id}
                className="bg-slate-900/80 border border-slate-800 hover:border-pink-500/40 rounded-2xl p-5 space-y-4 transition flex flex-col justify-between"
              >
                <div className="space-y-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="w-12 h-12 rounded-xl bg-pink-500/10 border border-pink-500/20 flex items-center justify-center text-2xl">
                      {item.icon || '💎'}
                    </div>
                    <span className="px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-400 text-[10px] font-bold uppercase tracking-wider">
                      {item.category}
                    </span>
                  </div>

                  <div>
                    <h4 className="font-bold text-white text-base">{item.name}</h4>
                    <p className="text-xs text-slate-400 mt-1 leading-relaxed">{item.description}</p>
                  </div>
                </div>

                <div className="pt-3 border-t border-slate-800 flex items-center justify-between">
                  <div>
                    <div className="text-[10px] uppercase text-slate-500 font-semibold">Cost</div>
                    <div className="text-sm font-extrabold text-pink-400 font-mono">
                      {formatUwuncy(item.price)} uwuncy
                    </div>
                  </div>
                  <code className="text-[11px] bg-slate-950 px-2 py-1 rounded border border-slate-800 text-pink-300 font-mono">
                    uwu booster buy {item.id}
                  </code>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 3. Real Estate Properties */}
      {shopTab === 'properties' && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {properties.map((prop) => (
            <div
              key={prop.id}
              className="bg-slate-900/80 border border-slate-800 hover:border-purple-500/40 rounded-2xl p-6 space-y-4 transition flex flex-col justify-between"
            >
              <div className="space-y-3">
                <div className="flex items-start justify-between">
                  <div className="w-12 h-12 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-2xl">
                    {prop.icon || '🏙️'}
                  </div>
                  <span className="px-2.5 py-0.5 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30 text-xs font-bold">
                    {prop.tier} Tier
                  </span>
                </div>

                <div>
                  <h4 className="font-bold text-white text-lg">{prop.name}</h4>
                  <p className="text-xs text-slate-400 mt-1">{prop.description}</p>
                </div>

                <div className="bg-slate-950/80 p-3 rounded-xl border border-slate-800 space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-400">Yield per Hour:</span>
                    <span className="text-emerald-400 font-mono font-bold">+{formatUwuncy(prop.yieldPerHour)} / hr</span>
                  </div>
                </div>
              </div>

              <div className="pt-3 border-t border-slate-800 flex items-center justify-between">
                <div>
                  <div className="text-[10px] uppercase text-slate-500 font-semibold">Purchase Price</div>
                  <div className="text-sm font-extrabold text-pink-400 font-mono">
                    {formatUwuncy(prop.price)} uwuncy
                  </div>
                </div>
                <code className="text-[11px] bg-slate-950 px-2 py-1 rounded border border-slate-800 text-pink-300 font-mono">
                  uwu buyproperty {prop.id}
                </code>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 4. Rare Collectibles */}
      {shopTab === 'collectibles' && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {collectibles.map((item) => (
            <div
              key={item.id}
              className="bg-slate-900/80 border border-slate-800 hover:border-amber-500/40 rounded-2xl p-6 space-y-4 transition flex flex-col justify-between"
            >
              <div className="space-y-3">
                <div className="flex items-start justify-between">
                  <div className="w-12 h-12 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-2xl">
                    {item.icon || '👑'}
                  </div>
                  <span className="px-2.5 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30 text-xs font-bold">
                    {item.rarity}
                  </span>
                </div>

                <div>
                  <h4 className="font-bold text-white text-lg">{item.name}</h4>
                  <p className="text-xs text-slate-400 mt-1">{item.description}</p>
                </div>
              </div>

              <div className="pt-3 border-t border-slate-800 flex items-center justify-between">
                <div>
                  <div className="text-[10px] uppercase text-slate-500 font-semibold">Price</div>
                  <div className="text-sm font-extrabold text-amber-400 font-mono">
                    {formatUwuncy(item.price)} uwuncy
                  </div>
                </div>
                <code className="text-[11px] bg-slate-950 px-2 py-1 rounded border border-slate-800 text-amber-300 font-mono">
                  uwu buycollectible {item.id}
                </code>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 5. Flowers & Charisma */}
      {shopTab === 'flowers' && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {flowers.map((fl) => (
            <div
              key={fl.id}
              className="bg-slate-900/80 border border-slate-800 hover:border-pink-500/40 rounded-2xl p-6 space-y-4 transition flex flex-col justify-between"
            >
              <div className="space-y-3">
                <div className="flex items-start justify-between">
                  <div className="w-12 h-12 rounded-xl bg-pink-500/10 border border-pink-500/20 flex items-center justify-center text-2xl">
                    {fl.icon || '🌸'}
                  </div>
                  <span className="px-2.5 py-0.5 rounded-full bg-pink-500/20 text-pink-300 border border-pink-500/30 text-xs font-bold flex items-center gap-1">
                    ✨ +{fl.charisma || fl.charismaExp || 50} Charisma
                  </span>
                </div>

                <div>
                  <h4 className="font-bold text-white text-lg">{fl.name}</h4>
                  <p className="text-xs text-slate-400 mt-1">{fl.description}</p>
                </div>
              </div>

              <div className="pt-3 border-t border-slate-800 flex items-center justify-between">
                <div>
                  <div className="text-[10px] uppercase text-slate-500 font-semibold">Price</div>
                  <div className="text-sm font-extrabold text-pink-400 font-mono">
                    {formatUwuncy(fl.price)} uwuncy
                  </div>
                </div>
                <code className="text-[11px] bg-slate-950 px-2 py-1 rounded border border-slate-800 text-pink-300 font-mono">
                  uwu buy {fl.id}
                </code>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 6. Economy Configuration Reference */}
      {shopTab === 'economy_rules' && (
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 space-y-6">
          <div>
            <h3 className="font-bold text-white text-lg flex items-center gap-2">
              <Shield className="w-5 h-5 text-indigo-400" />
              Bot Economy Rules & Multipliers
            </h3>
            <p className="text-xs text-slate-400 mt-1">
              Configuration constants parsed from <code className="text-pink-300">main.py</code>.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-1">
              <div className="text-xs text-slate-400 font-semibold">Hourly Reward (uwu claim)</div>
              <div className="text-lg font-bold text-white font-mono">500,000,000,000 uwuncy (500B)</div>
              <p className="text-[11px] text-slate-500">Cooldown: 1 hour (3600 seconds)</p>
            </div>

            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-1">
              <div className="text-xs text-slate-400 font-semibold">Server Booster Reward (uwu booster)</div>
              <div className="text-lg font-bold text-pink-400 font-mono">5,000,000,000,000 uwuncy (5T)</div>
              <p className="text-[11px] text-slate-500">Cooldown: 24 hours per boost count</p>
            </div>

            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-1">
              <div className="text-xs text-slate-400 font-semibold">Initial Jackpot Pool</div>
              <div className="text-lg font-bold text-amber-400 font-mono">10,000 uwuncy</div>
              <p className="text-[11px] text-slate-500">Tax contribution: +5% on casino bets</p>
            </div>

            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-1">
              <div className="text-xs text-slate-400 font-semibold">Transfer / Give Tax</div>
              <div className="text-lg font-bold text-emerald-400 font-mono">5% Standard Tax</div>
              <p className="text-[11px] text-slate-500">Exempt with Booster Tax Exemption Token</p>
            </div>

            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-1">
              <div className="text-xs text-slate-400 font-semibold">Prestige Wealth Requirement</div>
              <div className="text-lg font-bold text-purple-400 font-mono">100 Trillion uwuncy</div>
              <p className="text-[11px] text-slate-500">Permanent +10% earnings multiplier per prestige tier</p>
            </div>

            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-1">
              <div className="text-xs text-slate-400 font-semibold">Max Poll Choices Limit</div>
              <div className="text-lg font-bold text-pink-300 font-mono">20 Choices Max</div>
              <p className="text-[11px] text-slate-500">Command: uwu poll &lt;choices&gt; | [time]</p>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
