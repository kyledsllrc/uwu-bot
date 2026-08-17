import React, { useState } from 'react';
import {
  Film,
  BarChart3,
  MessageCircleHeart,
  ShieldCheck,
  CheckCircle2,
  Clock,
  Sparkles,
  Users,
  Send,
  Calendar,
  Radio,
  Vote
} from 'lucide-react';

export const FeaturesShowcase: React.FC = () => {
  const [activeFeature, setActiveFeature] = useState<'poll' | 'movie' | 'ai' | 'antinuke'>('poll');

  // Interactive Poll State
  const [pollVotes, setPollVotes] = useState<{ [key: number]: number }>({
    0: 12,
    1: 24,
    2: 18,
    3: 9,
    4: 15,
  });
  const [userVotedIndex, setUserVotedIndex] = useState<number | null>(null);

  const pollOptions = [
    'Valorant 5v5 Custom Derby',
    'Roblox Anime Vanguards',
    'Minecraft Survival Realm',
    'Genshin Impact Co-op Bosses',
    'Movie Night Watch Party in VC'
  ];

  const handleVote = (index: number) => {
    setPollVotes((prev) => {
      const updated = { ...prev };
      if (userVotedIndex !== null) {
        updated[userVotedIndex] = Math.max(0, updated[userVotedIndex] - 1);
      }
      updated[index] = (updated[index] || 0) + 1;
      return updated;
    });
    setUserVotedIndex(index);
  };

  const totalPollVotes = (Object.values(pollVotes) as number[]).reduce((a, b) => a + b, 0);

  // Movie RSVP State
  const [rsvpCount, setRsvpCount] = useState<number>(14);
  const [hasRsvpd, setHasRsvpd] = useState<boolean>(false);

  // AI Rant State
  const [rantInput, setRantInput] = useState<string>('');
  const [rantHistory, setRantHistory] = useState<Array<{ sender: 'user' | 'bot'; text: string }>>([
    {
      sender: 'user',
      text: 'Pagod na pagod na ako sa trabaho at school kanina... parang gusto ko nalang humiga buong araw.'
    },
    {
      sender: 'bot',
      text: 'Naiintindihan kita sobra... 🫂 Grabe talaga yung bigat kapag sabay ang school at work. Valid na valid yang nararamdaman mo. Hinga ka muna nang malalim, uminom ka ng malamig na tubig, at wag mong kalimutang magpahinga. Nandito lang ako palagi para makinig sa\'yo, okay? ✨'
    }
  ]);
  const [isAiTyping, setIsAiTyping] = useState<boolean>(false);

  const handleSendRant = (e: React.FormEvent) => {
    e.preventDefault();
    if (!rantInput.trim()) return;

    const userMsg = rantInput.trim();
    setRantHistory((prev) => [...prev, { sender: 'user', text: userMsg }]);
    setRantInput('');
    setIsAiTyping(true);

    setTimeout(() => {
      setIsAiTyping(false);
      let reply = '';
      const lower = userMsg.toLowerCase();
      if (lower.includes('stress') || lower.includes('pagod') || lower.includes('tired')) {
        reply = 'Hugs with consent! 🤗 Ang tapang mo for getting through today. Take it one step at a time, grab your favorite comfort snack, at wag mong i-pressure sarili mo ngayong gabi.';
      } else if (lower.includes('sad') || lower.includes('lungkot') || lower.includes('cry')) {
        reply = 'It’s completely okay to not be okay right now. You don’t have to carry everything alone. Let it all out, I\'m here listening.';
      } else {
        reply = 'Thank you for sharing that with me! Always remember na you are doing your best, and your efforts matter. Laban lang palagi, I got your back! 💖';
      }
      setRantHistory((prev) => [...prev, { sender: 'bot', text: reply }]);
    }, 1000);
  };

  return (
    <div className="space-y-8 animate-fadeIn">
      
      {/* Feature Selector Tabs */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {[
          { id: 'poll', label: '20-Choice Poll System', icon: '📊', sub: 'uwu poll' },
          { id: 'movie', label: 'Movie Stream & RSVP', icon: '🎬', sub: 'uwu movie' },
          { id: 'ai', label: 'AI Rant & Comfort', icon: '💬', sub: 'uwu rant' },
          { id: 'antinuke', label: 'Anti-Nuke Defense', icon: '🛡️', sub: 'uwu antinuke' },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveFeature(tab.id as any)}
            className={`p-4 rounded-2xl border text-left transition-all duration-200 ${
              activeFeature === tab.id
                ? 'bg-slate-800 border-pink-500/60 shadow-lg shadow-pink-500/10 ring-1 ring-pink-500/30'
                : 'bg-slate-900/60 hover:bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
            }`}
          >
            <div className="text-2xl mb-1.5">{tab.icon}</div>
            <div className="font-bold text-sm text-white">{tab.label}</div>
            <div className="text-xs text-pink-400 font-mono mt-0.5">{tab.sub}</div>
          </button>
        ))}
      </div>

      {/* Feature Display Stage */}
      <div className="bg-slate-900/70 border border-slate-800 rounded-3xl p-6 sm:p-8 shadow-2xl">
        
        {/* 1. Poll Feature */}
        {activeFeature === 'poll' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
            <div className="lg:col-span-5 space-y-4">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-pink-500/10 border border-pink-500/30 text-pink-300 text-xs font-semibold">
                <Vote className="w-3.5 h-3.5" />
                Discord Interactive Poll Engine
              </div>
              <h2 className="text-2xl font-bold text-white tracking-tight">
                Real-Time Community Polls with up to 20 Choices
              </h2>
              <p className="text-slate-300 text-sm leading-relaxed">
                Empower server members to vote via Discord Select menus and buttons. 
                Features dynamic percentage bars, single-vote integrity, vote switching, and auto-ending timers.
              </p>
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 font-mono text-xs text-slate-300 space-y-1">
                <div className="text-slate-500">// Example Usage:</div>
                <div className="text-pink-300">uwu poll Game to play? | Valorant, Roblox, Minecraft | 30m</div>
              </div>
            </div>

            {/* Simulated Discord Embed for Poll */}
            <div className="lg:col-span-7 bg-[#2b2d31] rounded-2xl p-5 border-l-4 border-indigo-500 text-slate-100 shadow-2xl space-y-4 font-sans">
              <div className="flex items-center justify-between">
                <h3 className="font-bold text-white text-base flex items-center gap-2">
                  📊 COMMUNITY POLL • Weekend Server Game Night
                </h3>
                <span className="text-xs text-indigo-300 bg-indigo-500/20 px-2 py-0.5 rounded font-mono">
                  Ends: in 30 mins
                </span>
              </div>
              <p className="text-xs text-slate-300">
                Vote using the options below! Click any option to simulate live Discord voting.
              </p>

              {/* Poll Options List with Progress Bars */}
              <div className="space-y-3 pt-2">
                {pollOptions.map((option, idx) => {
                  const votes = pollVotes[idx] || 0;
                  const pct = totalPollVotes > 0 ? (votes / totalPollVotes) * 100 : 0;
                  const filledBlocks = Math.round((pct / 100) * 12);
                  const emptyBlocks = 12 - filledBlocks;
                  const bar = '█'.repeat(filledBlocks) + '░'.repeat(emptyBlocks);
                  const isUserPick = userVotedIndex === idx;

                  return (
                    <div
                      key={idx}
                      onClick={() => handleVote(idx)}
                      className={`cursor-pointer p-3 rounded-xl border transition ${
                        isUserPick
                          ? 'bg-[#35373c] border-indigo-500 ring-1 ring-indigo-500/50'
                          : 'bg-[#1e1f22] border-transparent hover:border-slate-600'
                      }`}
                    >
                      <div className="flex justify-between items-center text-xs font-semibold">
                        <span className="text-white flex items-center gap-1.5">
                          {idx + 1}️⃣ {option} {isUserPick && '✅ (Your Vote)'}
                        </span>
                        <span className="text-indigo-300 font-mono">{pct.toFixed(1)}% ({votes} votes)</span>
                      </div>
                      <div className="mt-1 font-mono text-[11px] text-indigo-400">
                        [{bar}]
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="pt-3 border-t border-slate-700/60 flex items-center justify-between text-xs text-slate-400">
                <span>👥 Total Votes Cast: <strong>{totalPollVotes}</strong></span>
                <span className="text-slate-500">UwU Bot Poll View</span>
              </div>
            </div>
          </div>
        )}

        {/* 2. Movie Watch Party Feature */}
        {activeFeature === 'movie' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
            <div className="lg:col-span-5 space-y-4">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-pink-500/10 border border-pink-500/30 text-pink-300 text-xs font-semibold">
                <Film className="w-3.5 h-3.5" />
                Server Owner Cinema System
              </div>
              <h2 className="text-2xl font-bold text-white tracking-tight">
                Movie Watch Party & Stream Announcements
              </h2>
              <p className="text-slate-300 text-sm leading-relaxed">
                Host movie nights effortlessly. The bot looks up high-resolution movie posters, IMDb ratings, runtime, directors, and embeds interactive RSVP buttons.
              </p>
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 font-mono text-xs text-slate-300 space-y-1">
                <div className="text-slate-500">// Example Usage:</div>
                <div className="text-pink-300">uwu movie Inception tonight at 8:00 PM</div>
              </div>
            </div>

            {/* Simulated Discord Embed for Movie */}
            <div className="lg:col-span-7 bg-[#2b2d31] rounded-2xl p-5 border-l-4 border-pink-500 text-slate-100 shadow-2xl space-y-4 font-sans">
              <div className="flex gap-4">
                <img
                  src="https://images.unsplash.com/photo-1536440136628-849c177e76a1?w=300&auto=format&fit=crop&q=80"
                  alt="Movie Poster"
                  className="w-24 h-36 rounded-xl object-cover border border-slate-700 shadow-lg"
                />
                <div className="flex-1 space-y-2">
                  <div className="flex items-center justify-between">
                    <h3 className="font-bold text-lg text-white">🎬 Inception (2010)</h3>
                    <span className="text-xs px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 font-bold">
                      ⭐ 8.8 / 10
                    </span>
                  </div>
                  <div className="text-xs text-slate-300 space-y-1">
                    <div>📅 <strong>Schedule:</strong> Tonight at 8:00 PM (Voice Lounge)</div>
                    <div>⏱️ <strong>Runtime:</strong> 2h 28m • Action, Sci-Fi</div>
                    <div>👤 <strong>Director:</strong> Christopher Nolan</div>
                  </div>
                  <p className="text-xs text-slate-400 line-clamp-2">
                    A thief who steals corporate secrets through the use of dream-sharing technology is given the inverse task of planting an idea.
                  </p>
                </div>
              </div>

              {/* Interactive RSVP Buttons */}
              <div className="pt-3 border-t border-slate-700/60 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => {
                      setHasRsvpd(!hasRsvpd);
                      setRsvpCount((c) => (hasRsvpd ? c - 1 : c + 1));
                    }}
                    className={`px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-1.5 ${
                      hasRsvpd
                        ? 'bg-emerald-500 text-slate-950 shadow-md shadow-emerald-500/20'
                        : 'bg-pink-600 hover:bg-pink-500 text-white'
                    }`}
                  >
                    <span>🍿</span>
                    <span>{hasRsvpd ? 'RSVP Confirmed!' : 'Count Me In / RSVP'}</span>
                  </button>

                  <button className="px-3 py-2 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded-xl text-xs font-semibold transition">
                    🔔 Remind Me
                  </button>
                </div>

                <div className="text-xs text-slate-300 font-semibold">
                  👥 <strong>{rsvpCount}</strong> attending
                </div>
              </div>
            </div>
          </div>
        )}

        {/* 3. AI Emotional Support Companion */}
        {activeFeature === 'ai' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
            <div className="lg:col-span-5 space-y-4">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-purple-500/10 border border-purple-500/30 text-purple-300 text-xs font-semibold">
                <MessageCircleHeart className="w-3.5 h-3.5" />
                Empathetic AI Companion
              </div>
              <h2 className="text-2xl font-bold text-white tracking-tight">
                Multilingual AI Emotional Comfort
              </h2>
              <p className="text-slate-300 text-sm leading-relaxed">
                When server members have a tough day, UwU Bot listens and responds with genuine empathy. 
                Supports English, Tagalog, Bisaya, Japanese, and casual conversational slang.
              </p>
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 font-mono text-xs text-slate-300 space-y-1">
                <div className="text-slate-500">// Example Usage:</div>
                <div className="text-purple-300">uwu rant Pagod na ako sa exams kanina...</div>
              </div>
            </div>

            {/* Interactive Chat Box */}
            <div className="lg:col-span-7 bg-[#2b2d31] rounded-2xl p-5 border border-purple-500/30 text-slate-100 shadow-2xl flex flex-col h-[340px] justify-between">
              <div className="space-y-3 overflow-y-auto pr-1">
                {rantHistory.map((msg, idx) => (
                  <div
                    key={idx}
                    className={`flex gap-3 text-xs ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    {msg.sender === 'bot' && (
                      <div className="w-7 h-7 rounded-full bg-purple-600 flex items-center justify-center flex-shrink-0 text-sm">
                        ✨
                      </div>
                    )}
                    <div
                      className={`p-3 rounded-2xl max-w-[80%] leading-relaxed ${
                        msg.sender === 'user'
                          ? 'bg-purple-600 text-white rounded-br-none'
                          : 'bg-[#1e1f22] text-slate-200 rounded-bl-none border border-slate-700'
                      }`}
                    >
                      {msg.text}
                    </div>
                  </div>
                ))}
                {isAiTyping && (
                  <div className="flex gap-2 items-center text-xs text-purple-300 italic">
                    <Sparkles className="w-3.5 h-3.5 animate-spin" /> UwU Bot is thinking of comforting words...
                  </div>
                )}
              </div>

              <form onSubmit={handleSendRant} className="pt-3 border-t border-slate-700 flex gap-2">
                <input
                  type="text"
                  value={rantInput}
                  onChange={(e) => setRantInput(e.target.value)}
                  placeholder="Vent or share what's on your mind..."
                  className="flex-1 bg-[#1e1f22] border border-slate-700 rounded-xl px-4 py-2 text-xs text-white focus:outline-none focus:border-purple-500"
                />
                <button
                  type="submit"
                  className="px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white font-bold rounded-xl text-xs transition flex items-center gap-1"
                >
                  <Send className="w-3.5 h-3.5" />
                </button>
              </form>
            </div>
          </div>
        )}

        {/* 4. Anti-Nuke Shield Feature */}
        {activeFeature === 'antinuke' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
            <div className="lg:col-span-5 space-y-4">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs font-semibold">
                <ShieldCheck className="w-3.5 h-3.5" />
                Zero-Tolerance Server Shield
              </div>
              <h2 className="text-2xl font-bold text-white tracking-tight">
                Anti-Nuke, Anti-Spam & Rollback Defense
              </h2>
              <p className="text-slate-300 text-sm leading-relaxed">
                Protects your server 24/7 against rogue admin accounts, mass bans, channel deletion bots, and raid waves with sub-second ban actions and full rollback restoration.
              </p>
            </div>

            <div className="lg:col-span-7 bg-slate-950 rounded-2xl p-6 border border-emerald-500/30 space-y-4 text-xs font-mono">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <span className="text-emerald-400 font-bold flex items-center gap-1.5">
                  <ShieldCheck className="w-4 h-4" /> Defense Matrix: ARMED & ACTIVE
                </span>
                <span className="text-slate-400">Audit Log Monitor: 0ms Hook</span>
              </div>

              <div className="space-y-2 text-slate-300">
                <div className="p-2.5 bg-emerald-950/30 border border-emerald-500/20 rounded-lg flex items-center justify-between">
                  <span>Mass Ban Threshold (&gt;3 bans/10s):</span>
                  <span className="text-emerald-400 font-bold">Auto-Stripped & Banned</span>
                </div>
                <div className="p-2.5 bg-emerald-950/30 border border-emerald-500/20 rounded-lg flex items-center justify-between">
                  <span>Channel Wipe Detection:</span>
                  <span className="text-emerald-400 font-bold">Instant Clone & Restore</span>
                </div>
                <div className="p-2.5 bg-emerald-950/30 border border-emerald-500/20 rounded-lg flex items-center justify-between">
                  <span>Anti-Raid / Alt Account Shield:</span>
                  <span className="text-emerald-400 font-bold">Auto-Quarantine Active</span>
                </div>
              </div>

              <div className="pt-2 text-slate-500 text-[11px]">
                Commands: <code className="text-emerald-300">uwu antinuke on</code> • <code className="text-emerald-300">uwu rollback</code> • <code className="text-emerald-300">uwu antiraid on</code>
              </div>
            </div>
          </div>
        )}

      </div>

    </div>
  );
};
