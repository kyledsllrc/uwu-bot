import React, { useState } from 'react';
import {
  BookOpen,
  Search,
  Copy,
  Check,
  Tag,
  Shield,
  Sparkles,
  Zap,
  Radio,
  Coins,
  Gamepad2,
  Heart,
  Music,
  Lock,
  Film,
  Bot
} from 'lucide-react';
import { BOT_COMMANDS } from '../data/botDirectory';
import { BotCommand } from '../types';

interface CommandsDirectoryProps {
  commands?: BotCommand[];
}

export const CommandsDirectory: React.FC<CommandsDirectoryProps> = ({
  commands: propCommands
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [copiedCmd, setCopiedCmd] = useState<string | null>(null);

  const commandList = (propCommands && propCommands.length > 0) ? propCommands : BOT_COMMANDS;

  const categories = [
    { id: 'all', label: 'All Commands', icon: Sparkles },
    { id: 'booster', label: 'Server Booster', icon: Zap },
    { id: 'economy', label: 'Economy', icon: Coins },
    { id: 'gambling', label: 'Gambling & Games', icon: Gamepad2 },
    { id: 'social', label: 'Social & Polls', icon: Heart },
    { id: 'music', label: 'Music & Voice', icon: Music },
    { id: 'moderation', label: 'Moderation & Movie', icon: Film },
    { id: 'admin', label: 'Admin & Config', icon: Shield },
  ];

  const filteredCommands = commandList.filter((cmd) => {
    const matchesCategory = selectedCategory === 'all' || cmd.category.toLowerCase() === selectedCategory.toLowerCase();
    const term = searchTerm.toLowerCase().trim();
    if (!term) return matchesCategory;

    const matchesSearch =
      cmd.name.toLowerCase().includes(term) ||
      cmd.description.toLowerCase().includes(term) ||
      cmd.usage.toLowerCase().includes(term) ||
      (cmd.aliases && cmd.aliases.some((a) => a.toLowerCase().includes(term))) ||
      (cmd.permissions && cmd.permissions.toLowerCase().includes(term));
    return matchesCategory && matchesSearch;
  });

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedCmd(text);
    setTimeout(() => setCopiedCmd(null), 2000);
  };

  return (
    <div className="space-y-8 animate-fadeIn">
      
      {/* Header with Search & Filter */}
      <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-6 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
              <BookOpen className="w-5 h-5 text-pink-400" />
              Complete Bot Commands Directory ({commandList.length} Commands)
            </h2>
            <p className="text-xs sm:text-sm text-slate-400 mt-1">
              Extracted directly from <code className="text-pink-300">HELP_CATEGORIES</code> in <code className="text-pink-300">main.py</code>.
            </p>
          </div>

          <div className="relative w-full sm:w-80">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search command, alias, or syntax..."
              className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-10 pr-4 py-2 text-sm text-white focus:outline-none focus:border-pink-500 transition"
            />
          </div>
        </div>

        {/* Category Filter Pills */}
        <div className="flex flex-wrap gap-2 pt-2 border-t border-slate-800/80">
          {categories.map((cat) => {
            const Icon = cat.icon;
            const isSelected = selectedCategory === cat.id;
            const count = cat.id === 'all'
              ? commandList.length
              : commandList.filter((c) => c.category.toLowerCase() === cat.id.toLowerCase()).length;

            return (
              <button
                key={cat.id}
                onClick={() => setSelectedCategory(cat.id)}
                className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold transition ${
                  isSelected
                    ? 'bg-pink-500 text-white shadow-md shadow-pink-500/20'
                    : 'bg-slate-800/80 text-slate-300 hover:bg-slate-800 hover:text-white border border-slate-700/60'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{cat.label}</span>
                <span className={`px-1.5 py-0.2 rounded-full text-[10px] ${
                  isSelected ? 'bg-white/20 text-white' : 'bg-slate-900 text-slate-400'
                }`}>
                  {count}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Commands Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredCommands.map((cmd, idx) => (
          <div
            key={`${cmd.name}-${idx}`}
            className="bg-slate-900/80 border border-slate-800 hover:border-pink-500/40 rounded-2xl p-5 space-y-4 transition flex flex-col justify-between group shadow-lg"
          >
            <div className="space-y-3">
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-xl bg-pink-500/10 border border-pink-500/20 flex items-center justify-center text-pink-400 font-mono font-bold text-xs">
                    uwu
                  </div>
                  <h3 className="font-bold text-white text-base font-mono group-hover:text-pink-300 transition">
                    {cmd.name}
                  </h3>
                </div>

                <span className="px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-400 text-[10px] font-bold uppercase tracking-wider">
                  {cmd.category}
                </span>
              </div>

              <p className="text-xs text-slate-300 leading-relaxed">
                {cmd.description}
              </p>

              {/* Aliases & Permissions */}
              <div className="flex flex-wrap items-center gap-1.5 pt-1">
                {cmd.permissions && (
                  <span className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20 text-[10px] font-semibold flex items-center gap-1">
                    <Shield className="w-3 h-3" /> {cmd.permissions}
                  </span>
                )}
                {cmd.aliases && cmd.aliases.map((alias) => (
                  <span
                    key={alias}
                    className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 text-[10px] font-mono"
                  >
                    {alias}
                  </span>
                ))}
              </div>
            </div>

            {/* Usage Syntax Box with One-Click Copy */}
            <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between gap-2">
              <code className="text-xs text-pink-300 font-mono bg-slate-950 px-2.5 py-1.5 rounded-lg border border-slate-800/80 truncate flex-1">
                {cmd.usage}
              </code>

              <button
                onClick={() => handleCopy(cmd.usage)}
                title="Copy usage"
                className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition flex-shrink-0"
              >
                {copiedCmd === cmd.usage ? (
                  <Check className="w-4 h-4 text-emerald-400" />
                ) : (
                  <Copy className="w-4 h-4" />
                )}
              </button>
            </div>
          </div>
        ))}
      </div>

      {filteredCommands.length === 0 && (
        <div className="text-center py-12 bg-slate-900/50 rounded-2xl border border-slate-800 text-slate-400">
          <BookOpen className="w-8 h-8 mx-auto text-slate-500 mb-2" />
          <p className="text-sm font-medium">No commands found matching "{searchTerm}"</p>
          <p className="text-xs text-slate-500 mt-1">Try searching for a different keyword or category.</p>
        </div>
      )}

    </div>
  );
};
