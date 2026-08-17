import React, { useState, useEffect } from 'react';
import {
  Gamepad2,
  Coins,
  Rocket,
  Sparkles,
  RefreshCw,
  Trophy,
  Dices,
  Flame,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';

export const CasinoPlayground: React.FC = () => {
  const [activeGame, setActiveGame] = useState<'cf' | 'crash' | 'slot' | 'dice'>('cf');
  const [bet, setBet] = useState<number>(50000000); // 50M
  const [balance, setBalance] = useState<number>(500000000); // 500M initial test balance
  const [log, setLog] = useState<string>('Welcome to the Casino Playground! Place a bet to test game mechanics.');

  // Coinflip State
  const [cfChoice, setCfChoice] = useState<'heads' | 'tails'>('heads');
  const [cfFlipping, setCfFlipping] = useState<boolean>(false);
  const [cfResult, setCfResult] = useState<'heads' | 'tails' | null>(null);

  // Crash Rocket State
  const [crashMultiplier, setCrashMultiplier] = useState<number>(1.0);
  const [crashState, setCrashState] = useState<'idle' | 'running' | 'crashed' | 'cashed'>('idle');
  const [cashoutMult, setCashoutMult] = useState<number>(0);

  // Slots State
  const [slotReels, setSlotReels] = useState<string[]>(['🍒', '💎', '7️⃣']);
  const [slotSpinning, setSlotSpinning] = useState<boolean>(false);

  // Dice State
  const [diceRoll, setDiceRoll] = useState<number>(50);
  const [diceTarget, setDiceTarget] = useState<number>(50);
  const [diceMode, setDiceMode] = useState<'over' | 'under'>('over');
  const [rollingDice, setRollingDice] = useState<boolean>(false);

  // Coinflip Handler
  const playCoinflip = () => {
    if (balance < bet) {
      setLog('❌ Insufficient test uwuncy! Reset balance to continue.');
      return;
    }
    setCfFlipping(true);
    setCfResult(null);
    setBalance((b) => b - bet);
    setLog(`🪙 Flipping coin for ${bet.toLocaleString()} uwuncy on ${cfChoice.toUpperCase()}...`);

    setTimeout(() => {
      const outcome: 'heads' | 'tails' = Math.random() < 0.5 ? 'heads' : 'tails';
      setCfResult(outcome);
      setCfFlipping(false);

      if (outcome === cfChoice) {
        const win = bet * 2;
        setBalance((b) => b + win);
        setLog(`🎉 WINNER! The coin landed on ${outcome.toUpperCase()}. You won ${win.toLocaleString()} uwuncy! (2.0x)`);
      } else {
        setLog(`💀 The coin landed on ${outcome.toUpperCase()}. You lost ${bet.toLocaleString()} uwuncy.`);
      }
    }, 1200);
  };

  // Crash Handler
  const startCrash = () => {
    if (balance < bet) {
      setLog('❌ Insufficient test balance.');
      return;
    }
    setBalance((b) => b - bet);
    setCrashState('running');
    setCrashMultiplier(1.0);
    setCashoutMult(0);
    setLog(`🚀 Rocket launched! Bet: ${bet.toLocaleString()} uwuncy. Cash out before explosion!`);

    // Determine crash point using provably fair exponential distribution
    const rand = Math.random();
    const targetCrash = Math.max(1.05, +(0.95 / (1 - rand)).toFixed(2));

    let current = 1.0;
    const interval = setInterval(() => {
      current += 0.05 + current * 0.02;
      const rounded = +current.toFixed(2);

      if (rounded >= targetCrash) {
        clearInterval(interval);
        setCrashMultiplier(targetCrash);
        setCrashState((prev) => (prev === 'running' ? 'crashed' : prev));
        if (crashState === 'running') {
          setLog(`💥 EXPLODED at ${targetCrash}x! You lost your bet.`);
        }
      } else {
        setCrashMultiplier(rounded);
      }
    }, 80);
  };

  const cashoutCrash = () => {
    if (crashState !== 'running') return;
    const winMult = crashMultiplier;
    setCashoutMult(winMult);
    setCrashState('cashed');
    const winAmount = Math.floor(bet * winMult);
    setBalance((b) => b + winAmount);
    setLog(`💰 CASHED OUT at ${winMult}x! You took home ${winAmount.toLocaleString()} uwuncy!`);
  };

  // Slot Handler
  const spinSlots = () => {
    if (balance < bet) {
      setLog('❌ Insufficient test balance.');
      return;
    }
    const icons = ['🍒', '🍋', '🍇', '💎', '7️⃣', '👑'];
    setSlotSpinning(true);
    setBalance((b) => b - bet);
    setLog(`🎰 Spinning slot reels for ${bet.toLocaleString()} uwuncy...`);

    let ticks = 0;
    const interval = setInterval(() => {
      setSlotReels([
        icons[Math.floor(Math.random() * icons.length)],
        icons[Math.floor(Math.random() * icons.length)],
        icons[Math.floor(Math.random() * icons.length)],
      ]);
      ticks++;
      if (ticks > 10) {
        clearInterval(interval);
        setSlotSpinning(false);
        const final = [
          icons[Math.floor(Math.random() * icons.length)],
          icons[Math.floor(Math.random() * icons.length)],
          icons[Math.floor(Math.random() * icons.length)],
        ];
        setSlotReels(final);

        if (final[0] === final[1] && final[1] === final[2]) {
          const mult = final[0] === '👑' ? 50 : final[0] === '7️⃣' ? 25 : final[0] === '💎' ? 15 : 5;
          const win = bet * mult;
          setBalance((b) => b + win);
          setLog(`🔥 JACKPOT! Triple ${final[0]}! Won ${win.toLocaleString()} uwuncy (${mult}x)!`);
        } else if (final[0] === final[1] || final[1] === final[2]) {
          const win = Math.floor(bet * 1.5);
          setBalance((b) => b + win);
          setLog(`✨ Double match! Won ${win.toLocaleString()} uwuncy (1.5x)!`);
        } else {
          setLog(`😢 No match. Better luck on the next spin!`);
        }
      }
    }, 100);
  };

  // Dice Handler
  const rollDiceGame = () => {
    if (balance < bet) {
      setLog('❌ Insufficient test balance.');
      return;
    }
    setRollingDice(true);
    setBalance((b) => b - bet);
    setLog(`🎲 Rolling 1-100 dice for ${diceMode.toUpperCase()} ${diceTarget}...`);

    setTimeout(() => {
      const outcome = Math.floor(Math.random() * 100) + 1;
      setDiceRoll(outcome);
      setRollingDice(false);

      const won = diceMode === 'over' ? outcome > diceTarget : outcome < diceTarget;
      if (won) {
        const winMult = diceMode === 'over' ? +(98 / (100 - diceTarget)).toFixed(2) : +(98 / diceTarget).toFixed(2);
        const win = Math.floor(bet * winMult);
        setBalance((b) => b + win);
        setLog(`🎉 Rolled ${outcome}! You won ${win.toLocaleString()} uwuncy (${winMult}x)!`);
      } else {
        setLog(`💀 Rolled ${outcome}. Did not hit target ${diceMode.toUpperCase()} ${diceTarget}.`);
      }
    }, 600);
  };

  return (
    <div className="space-y-8 animate-fadeIn">
      
      {/* Header & Wallet Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-900/70 border border-slate-800 rounded-2xl p-6">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <Gamepad2 className="w-5 h-5 text-pink-400" />
            Casino & Games Interactive Simulator
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Test and preview the exact math and payouts used in UwU Bot discord casino minigames.
          </p>
        </div>

        {/* Test Wallet Balance */}
        <div className="flex items-center gap-3 bg-slate-950 px-4 py-2.5 rounded-xl border border-slate-800">
          <div>
            <span className="text-xs text-slate-400 block font-medium">Simulator Balance:</span>
            <span className="text-lg font-black text-pink-400 font-mono">
              {balance.toLocaleString()} <span className="text-xs font-normal text-slate-400">uwuncy</span>
            </span>
          </div>
          <button
            onClick={() => {
              setBalance(500000000);
              setLog('🔄 Simulator test balance reset to 500M uwuncy.');
            }}
            title="Reset Test Balance"
            className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Game Selector Tabs */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { id: 'cf', label: 'Coinflip (uwu cf)', icon: '🪙' },
          { id: 'crash', label: 'Crash Rocket (uwu crash)', icon: '🚀' },
          { id: 'slot', label: 'Slots (uwu slot)', icon: '🎰' },
          { id: 'dice', label: 'Dice Roll (uwu dice)', icon: '🎲' },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveGame(tab.id as any)}
            className={`p-4 rounded-xl border font-semibold text-sm transition-all duration-200 flex items-center justify-center gap-2.5 ${
              activeGame === tab.id
                ? 'bg-slate-800 border-pink-500/50 text-white shadow-lg shadow-pink-500/10 ring-1 ring-pink-500/30'
                : 'bg-slate-900/60 hover:bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
            }`}
          >
            <span className="text-lg">{tab.icon}</span>
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      {/* Main Game Interface & Bet Settings */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Game Stage */}
        <div className="lg:col-span-8 bg-slate-900/70 border border-slate-800 rounded-2xl p-6 sm:p-8 flex flex-col justify-between min-h-[380px]">
          
          {/* Active Game Stage Component */}
          {activeGame === 'cf' && (
            <div className="flex-1 flex flex-col items-center justify-center space-y-6">
              <div className={`w-32 h-32 rounded-full border-4 flex items-center justify-center text-4xl shadow-2xl transition-all duration-500 ${
                cfFlipping
                  ? 'border-pink-500 animate-spin bg-slate-800'
                  : cfResult === 'heads'
                  ? 'border-amber-400 bg-amber-500/20 text-amber-300'
                  : cfResult === 'tails'
                  ? 'border-indigo-400 bg-indigo-500/20 text-indigo-300'
                  : 'border-slate-700 bg-slate-800 text-slate-400'
              }`}>
                {cfFlipping ? '✨' : cfResult ? (cfResult === 'heads' ? '👑' : '🦅') : '🪙'}
              </div>

              <div className="text-center">
                <div className="text-xl font-bold text-white">
                  {cfFlipping ? 'Flipping...' : cfResult ? `Landed on ${cfResult.toUpperCase()}!` : 'Choose Heads or Tails'}
                </div>
                <div className="text-xs text-slate-400 mt-1">2.0x Double-or-Nothing Payout</div>
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => setCfChoice('heads')}
                  className={`px-5 py-2.5 rounded-xl font-bold text-sm transition ${
                    cfChoice === 'heads'
                      ? 'bg-amber-500 text-slate-950 shadow-lg shadow-amber-500/20'
                      : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                  }`}
                >
                  👑 Heads (50%)
                </button>
                <button
                  onClick={() => setCfChoice('tails')}
                  className={`px-5 py-2.5 rounded-xl font-bold text-sm transition ${
                    cfChoice === 'tails'
                      ? 'bg-indigo-500 text-white shadow-lg shadow-indigo-500/20'
                      : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                  }`}
                >
                  🦅 Tails (50%)
                </button>
              </div>
            </div>
          )}

          {activeGame === 'crash' && (
            <div className="flex-1 flex flex-col items-center justify-center space-y-6">
              <div className="relative w-full max-w-sm h-36 bg-slate-950 rounded-2xl border border-slate-800 flex items-center justify-center overflow-hidden">
                <div className="text-center z-10">
                  <div className={`text-4xl sm:text-5xl font-black font-mono tracking-tight ${
                    crashState === 'crashed'
                      ? 'text-rose-500 animate-bounce'
                      : crashState === 'cashed'
                      ? 'text-emerald-400'
                      : crashState === 'running'
                      ? 'text-pink-400'
                      : 'text-slate-300'
                  }`}>
                    {crashMultiplier.toFixed(2)}x
                  </div>
                  <span className="text-xs text-slate-400 uppercase font-semibold">
                    {crashState === 'crashed' ? '💥 ROCKET CRASHED' : crashState === 'cashed' ? '✅ CASHED OUT' : crashState === 'running' ? '🚀 CLIMBING...' : 'READY FOR LAUNCH'}
                  </span>
                </div>
              </div>

              {crashState === 'running' ? (
                <button
                  onClick={cashoutCrash}
                  className="px-8 py-3.5 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-black rounded-xl text-base shadow-lg shadow-emerald-500/25 transition transform active:scale-95 animate-pulse"
                >
                  💰 CASH OUT (${(bet * crashMultiplier).toLocaleString()})
                </button>
              ) : (
                <div className="text-xs text-slate-400">Launch the rocket and cash out before the random explosion!</div>
              )}
            </div>
          )}

          {activeGame === 'slot' && (
            <div className="flex-1 flex flex-col items-center justify-center space-y-6">
              <div className="flex gap-4 p-6 bg-slate-950 rounded-3xl border-2 border-purple-500/30 shadow-2xl">
                {slotReels.map((reel, idx) => (
                  <div
                    key={idx}
                    className="w-20 h-24 sm:w-24 sm:h-28 bg-slate-900 border border-slate-800 rounded-2xl flex items-center justify-center text-4xl sm:text-5xl shadow-inner"
                  >
                    {reel}
                  </div>
                ))}
              </div>
              <div className="text-xs text-slate-400 text-center">
                Match 3 symbols for up to <strong>50x jackpot payout</strong> (👑 = 50x, 7️⃣ = 25x, 💎 = 15x)
              </div>
            </div>
          )}

          {activeGame === 'dice' && (
            <div className="flex-1 flex flex-col items-center justify-center space-y-6">
              <div className="w-28 h-28 bg-slate-950 border-2 border-indigo-500/40 rounded-3xl flex items-center justify-center text-4xl font-black font-mono text-indigo-300 shadow-xl">
                {rollingDice ? '🎲' : diceRoll}
              </div>

              <div className="flex items-center gap-4">
                <button
                  onClick={() => setDiceMode(diceMode === 'over' ? 'under' : 'over')}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold rounded-xl border border-slate-700"
                >
                  Roll {diceMode.toUpperCase()}
                </button>
                <input
                  type="range"
                  min="5"
                  max="95"
                  value={diceTarget}
                  onChange={(e) => setDiceTarget(Number(e.target.value))}
                  className="w-48 accent-indigo-500"
                />
                <span className="text-white font-mono font-bold text-sm">{diceTarget}</span>
              </div>
            </div>
          )}

          {/* Action Trigger Button */}
          <div className="mt-6 pt-4 border-t border-slate-800 flex justify-center">
            {activeGame === 'cf' && (
              <button
                onClick={playCoinflip}
                disabled={cfFlipping}
                className="px-8 py-3 bg-gradient-to-r from-pink-500 to-purple-600 hover:from-pink-400 hover:to-purple-500 text-white font-bold rounded-xl text-sm shadow-lg shadow-pink-500/25 transition disabled:opacity-50"
              >
                {cfFlipping ? 'Flipping...' : `Flip Coin (Bet ${bet.toLocaleString()})`}
              </button>
            )}
            {activeGame === 'crash' && crashState !== 'running' && (
              <button
                onClick={startCrash}
                className="px-8 py-3 bg-gradient-to-r from-pink-500 to-purple-600 hover:from-pink-400 hover:to-purple-500 text-white font-bold rounded-xl text-sm shadow-lg shadow-pink-500/25 transition"
              >
                Launch Rocket (Bet {bet.toLocaleString()})
              </button>
            )}
            {activeGame === 'slot' && (
              <button
                onClick={spinSlots}
                disabled={slotSpinning}
                className="px-8 py-3 bg-gradient-to-r from-pink-500 to-purple-600 hover:from-pink-400 hover:to-purple-500 text-white font-bold rounded-xl text-sm shadow-lg shadow-pink-500/25 transition disabled:opacity-50"
              >
                {slotSpinning ? 'Spinning...' : `Spin Slots (Bet ${bet.toLocaleString()})`}
              </button>
            )}
            {activeGame === 'dice' && (
              <button
                onClick={rollDiceGame}
                disabled={rollingDice}
                className="px-8 py-3 bg-gradient-to-r from-pink-500 to-purple-600 hover:from-pink-400 hover:to-purple-500 text-white font-bold rounded-xl text-sm shadow-lg shadow-pink-500/25 transition disabled:opacity-50"
              >
                {rollingDice ? 'Rolling...' : `Roll Dice (Bet ${bet.toLocaleString()})`}
              </button>
            )}
          </div>
        </div>

        {/* Bet Config & Game History Log */}
        <div className="lg:col-span-4 space-y-4">
          
          {/* Bet Amount Controls */}
          <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-5 space-y-4">
            <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
              <Coins className="w-4 h-4 text-pink-400" />
              Wager Amount
            </h3>

            <div className="space-y-2">
              <div className="flex justify-between text-xs text-slate-400 font-mono">
                <span>Current Bet:</span>
                <span className="text-white font-bold">{bet.toLocaleString()} uwuncy</span>
              </div>
              <div className="grid grid-cols-3 gap-1.5">
                {[10_000_000, 50_000_000, 100_000_000, 250_000_000, 500_000_000, balance].map((amt, idx) => (
                  <button
                    key={idx}
                    onClick={() => setBet(amt)}
                    className={`py-1.5 text-xs font-mono rounded-lg transition ${
                      bet === amt ? 'bg-pink-600 text-white font-bold' : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                    }`}
                  >
                    {amt >= 1e9 ? `${amt / 1e9}B` : amt === balance ? 'MAX' : `${amt / 1e6}M`}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Live Action Log */}
          <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-5 space-y-3">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Playground Output</h3>
            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 text-xs sm:text-sm font-mono text-slate-200 min-h-[90px] leading-relaxed flex items-center">
              {log}
            </div>
          </div>

        </div>

      </div>

    </div>
  );
};
