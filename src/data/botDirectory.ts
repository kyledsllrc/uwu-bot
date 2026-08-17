import { BotCommand, PropertyItem, CollectibleItem, FlowerItem, CryptoCoin, BoosterShopItem } from '../types';

export const BOT_COMMANDS: BotCommand[] = [
  // Booster Commands
  { name: 'booster', category: 'booster', usage: 'uwu booster', description: 'Claim daily 5T uwuncy reward & view booster multipliers', permissions: 'Server Booster', example: 'uwu booster', aliases: ['boost', 'serverbooster'] },
  { name: 'boosters', category: 'booster', usage: 'uwu boosters', description: 'View active server boosters & server boost tier level', permissions: 'Server Booster', example: 'uwu boosters', aliases: ['boostlist'] },
  { name: 'booster count', category: 'booster', usage: 'uwu booster count <amount>', description: 'Set or update active boost count', permissions: 'Server Booster', example: 'uwu booster count 2', aliases: [] },
  { name: 'setboostcount', category: 'booster', usage: 'uwu setboostcount <@user> <amount>', description: 'Admin/booster sync user boost count', permissions: 'Administrator', example: 'uwu setboostcount @User 3', aliases: [] },
  { name: 'setbooster', category: 'booster', usage: 'uwu setbooster @user <count>', description: 'Set user booster count & status', permissions: 'Administrator', example: 'uwu setbooster @User 2', aliases: [] },
  { name: 'booster shop', category: 'booster', usage: 'uwu booster shop', description: 'Browse exclusive booster items & passes catalog', permissions: 'Server Booster', example: 'uwu booster shop', aliases: ['boostershop'] },
  { name: 'booster buy', category: 'booster', usage: 'uwu booster buy <item_id>', description: 'Purchase booster items with uwuncy', permissions: 'Server Booster', example: 'uwu booster buy 2x_earnings_pass', aliases: [] },

  // Economy Commands
  { name: 'claim', category: 'economy', usage: 'uwu claim', description: 'Claim hourly uwuncy reward (500B uwuncy)', example: 'uwu claim', aliases: ['hourly'] },
  { name: 'daily', category: 'economy', usage: 'uwu daily', description: 'Claim daily uwuncy streak rewards', example: 'uwu daily', aliases: ['streak'] },
  { name: 'money', category: 'economy', usage: 'uwu money [@user]', description: 'Check wallet & bank balance', example: 'uwu bal', aliases: ['bal', 'balance', 'wallet'] },
  { name: 'hidebank', category: 'economy', usage: 'uwu hidebank', description: 'Hide bank details in uwu bal', example: 'uwu hidebank', aliases: [] },
  { name: 'showbank', category: 'economy', usage: 'uwu showbank', description: 'Show bank details in uwu bal', example: 'uwu showbank', aliases: [] },
  { name: 'info', category: 'economy', usage: 'uwu info [@user]', description: 'Check user profile & stats', example: 'uwu info', aliases: ['userinfo', 'profile'] },
  { name: 'deposit', category: 'economy', usage: 'uwu deposit <amount|all>', description: 'Deposit into safe bank vault', example: 'uwu dep 500b', aliases: ['dep'] },
  { name: 'withdraw', category: 'economy', usage: 'uwu withdraw <amount|all>', description: 'Withdraw from bank to wallet', example: 'uwu with 100b', aliases: ['with'] },
  { name: 'give', category: 'economy', usage: 'uwu give @user <amount>', description: 'Transfer uwuncy to another member', example: 'uwu give @User 10b', aliases: ['pay'] },
  { name: 'history', category: 'economy', usage: 'uwu history', description: 'View transaction & gambling history', example: 'uwu history', aliases: ['bets', 'recent'] },
  { name: 'achievements', category: 'economy', usage: 'uwu achievements', description: 'View unlocked badges & achievements', example: 'uwu ach', aliases: ['ach', 'badges'] },
  { name: 'quests', category: 'economy', usage: 'uwu quests', description: 'View daily & weekly quests', example: 'uwu quests', aliases: ['quest', 'missions'] },
  { name: 'jackpot', category: 'economy', usage: 'uwu jackpot', description: 'View server jackpot pool & entries', example: 'uwu jackpot', aliases: [] },
  { name: 'hunt', category: 'economy', usage: 'uwu hunt', description: 'Hunt for wild animals & rewards', example: 'uwu hunt', aliases: [] },
  { name: 'huntinfo', category: 'economy', usage: 'uwu huntinfo', description: 'View hunting level & equipment stats', example: 'uwu huntinfo', aliases: ['huntlevel', 'huntstats'] },
  { name: 'leaderboard', category: 'economy', usage: 'uwu leaderboard', description: 'View global wealth rankings', example: 'uwu lb', aliases: ['lb', 'top'] },
  { name: 'crypwuncy', category: 'economy', usage: 'uwu crypwuncy', description: 'Check live crypto prices & sparkline trends', example: 'uwu crypto', aliases: ['crypto', 'market'] },
  { name: 'invest', category: 'economy', usage: 'uwu invest <coin> <amount>', description: 'Invest in crypto coins (bitwuncy, eterwuncy, etc.)', example: 'uwu invest bitwuncy 10b', aliases: ['buycrypto'] },
  { name: 'sell', category: 'economy', usage: 'uwu sell <coin> <amount|all>', description: 'Sell crypto investments back to wallet', example: 'uwu sell bitwuncy all', aliases: ['cashout', 'sellcrypto'] },
  { name: 'withdrawcrypto', category: 'economy', usage: 'uwu withdrawcrypto <coin> <amount>', description: 'Withdraw crypto holdings to wallet', example: 'uwu withdrawcrypto bitwuncy 5', aliases: ['cryptowithdraw'] },
  { name: 'investments', category: 'economy', usage: 'uwu investments', description: 'View your crypto portfolio & PnL', example: 'uwu investments', aliases: ['portfolio', 'invested'] },
  { name: 'shop', category: 'economy', usage: 'uwu shop', description: 'View global shop catalog', example: 'uwu shop', aliases: ['store'] },
  { name: 'buy', category: 'economy', usage: 'uwu buy <item_id>', description: 'Buy item or flower from shop', example: 'uwu buy tulip', aliases: [] },
  { name: 'inventory', category: 'economy', usage: 'uwu inventory', description: 'View owned items & flowers', example: 'uwu inv', aliases: ['inv'] },
  { name: 'properties', category: 'economy', usage: 'uwu properties', description: 'Browse real estate properties catalog', example: 'uwu properties', aliases: ['property'] },
  { name: 'buyproperty', category: 'economy', usage: 'uwu buyproperty <id>', description: 'Buy real estate property (Penthouse, Mansion, Moonbase)', example: 'uwu buyproperty penthouse', aliases: [] },
  { name: 'myproperty', category: 'economy', usage: 'uwu myproperty', description: 'View owned real estate properties', example: 'uwu myproperty', aliases: ['myproperties'] },
  { name: 'prestige', category: 'economy', usage: 'uwu prestige', description: 'Reset wallet wealth for permanent prestige multiplier', example: 'uwu prestige', aliases: [] },
  { name: 'collection', category: 'economy', usage: 'uwu collection', description: 'View owned items & rare collectibles', example: 'uwu collection', aliases: ['collectibles', 'museum'] },
  { name: 'buycollectible', category: 'economy', usage: 'uwu buycollectible <id>', description: 'Buy rare collectible item (Jackpot Crown, Arena Trophy, Diamond Paw)', example: 'uwu buycollectible jackpotcrown', aliases: [] },
  { name: 'season', category: 'economy', usage: 'uwu season', description: 'View current season stats, level & rewards', example: 'uwu season', aliases: [] },
  { name: 'seasonclaim', category: 'economy', usage: 'uwu seasonclaim', description: 'Claim seasonal level tier rewards', example: 'uwu seasonclaim', aliases: [] },
  { name: 'seasonrank', category: 'economy', usage: 'uwu seasonrank', description: 'View seasonal leaderboard rankings', example: 'uwu seasonrank', aliases: [] },

  // Gambling & Minigames
  { name: 'coinflip', category: 'gambling', usage: 'uwu coinflip <amount|all> <heads|tails>', description: 'Flip a coin with customizable odds and house edge', example: 'uwu cf 500m heads', aliases: ['cf'] },
  { name: 'slots', category: 'gambling', usage: 'uwu slots <amount|all>', description: 'Spin the 3-reel slot machine for jackpot multipliers up to 50x', example: 'uwu slot 1b', aliases: ['slot'] },
  { name: 'blackjack', category: 'gambling', usage: 'uwu blackjack <amount|all>', description: 'Play blackjack against the dealer (hit/stand/double)', example: 'uwu bj 2b', aliases: ['bj'] },
  { name: 'roulette', category: 'gambling', usage: 'uwu roulette <amount> <red|black|green|number>', description: 'European roulette wheel spin', example: 'uwu rr 500m red', aliases: ['rr'] },
  { name: 'crash', category: 'gambling', usage: 'uwu crash <amount>', description: 'Rocket crash multiplier game with interactive cashout button', example: 'uwu crash 1b', aliases: ['rocket'] },
  { name: 'dice', category: 'gambling', usage: 'uwu dice <amount> [guess]', description: 'Roll 6-sided dice with 6x max payout', example: 'uwu dice 500m 6', aliases: ['roll'] },
  { name: 'mines', category: 'gambling', usage: 'uwu mines <amount> [mines_count]', description: 'Grid minesweeper with escalating cashout multipliers', example: 'uwu mines 1b 3', aliases: ['m'] },
  { name: 'colorgame', category: 'gambling', usage: 'uwu colorgame <amount> <color>', description: 'Classic 3-dice perya color game', example: 'uwu cg 500m yellow', aliases: ['cg'] },
  { name: 'highlow', category: 'gambling', usage: 'uwu highlow <amount>', description: 'Predict higher or lower card', example: 'uwu hl 500m', aliases: ['hl'] },
  { name: 'tower', category: 'gambling', usage: 'uwu tower <amount>', description: 'Climb 8 floors without triggering trap doors', example: 'uwu tower 500m', aliases: ['climb'] },
  { name: 'wheel', category: 'gambling', usage: 'uwu wheel <amount>', description: 'Spin wheel of fortune with up to 10x multiplier', example: 'uwu wheel 1b', aliases: ['spin'] },
  { name: 'horse', category: 'gambling', usage: 'uwu horse <amount> <1-5>', description: 'Place bet on live horse derby race', example: 'uwu horse 500m 3', aliases: ['derby', 'race'] },
  { name: 'scratch', category: 'gambling', usage: 'uwu scratch <amount>', description: 'Scratch 3 matching symbols ticket', example: 'uwu scratch 200m', aliases: ['card'] },
  { name: 'baccarat', category: 'gambling', usage: 'uwu baccarat <amount> <player|banker|tie>', description: 'Punto Banco baccarat betting', example: 'uwu baccarat 1b player', aliases: ['bac'] },
  { name: 'keno', category: 'gambling', usage: 'uwu keno <amount> <num1,num2...>', description: 'Pick 1 to 5 numbers out of 20 lottery balls', example: 'uwu keno 500m 3,7,12', aliases: [] },
  { name: 'plinko', category: 'gambling', usage: 'uwu plinko <amount>', description: 'Drop peg ball down physics triangle for multipliers', example: 'uwu plinko 1b', aliases: [] },

  // Social & Community Commands
  { name: 'poll', category: 'social', usage: 'uwu poll <choice1, choice2...> | [duration]', description: 'Create interactive real-time community poll with up to 20 choices and live progress bars', example: 'uwu poll What game to play? | Valorant, Roblox, Minecraft | 30m', aliases: ['vote', 'surveypoll'] },
  { name: 'rant', category: 'social', usage: 'uwu rant [on|off|text]', description: 'Talk to empathetic AI companion in English, Tagalog, or Bisaya', example: 'uwu rant I had an exhausting day...', aliases: ['vent', 'comfort'] },
  { name: 'movie', category: 'moderation', usage: 'uwu movie <title> [schedule]', description: 'Search movie info, IMDb rating, and announce watch party with RSVP buttons', example: 'uwu movie Inception tonight at 8 PM', permissions: 'Manage Server / Moderator', aliases: ['movienight', 'watchparty'] },
  { name: 'marry', category: 'social', usage: 'uwu marry @user', description: 'Propose marriage to another member with flower bouquet requirement', example: 'uwu marry @User', aliases: ['propose'] },
  { name: 'divorce', category: 'social', usage: 'uwu divorce', description: 'End marriage and split mutual gifts', example: 'uwu divorce', aliases: [] },
  { name: 'rep', category: 'social', usage: 'uwu rep @user', description: 'Give reputation point to a helpful member (daily reset)', example: 'uwu rep @User', aliases: ['+rep', 'reputation'] },
  { name: 'hug', category: 'social', usage: 'uwu hug @user', description: 'Give a warm anime GIF hug to someone', example: 'uwu hug @User', aliases: [] },
  { name: 'kiss', category: 'social', usage: 'uwu kiss @user', description: 'Send a romantic anime kiss GIF', example: 'uwu kiss @User', aliases: [] },
  { name: 'pat', category: 'social', usage: 'uwu pat @user', description: 'Gently pat someone on the head with wholesome GIF', example: 'uwu pat @User', aliases: ['headpat'] },
  { name: 'slap', category: 'social', usage: 'uwu slap @user', description: 'Playfully slap someone with anime GIF', example: 'uwu slap @User', aliases: [] },
  { name: 'cuddle', category: 'social', usage: 'uwu cuddle @user', description: 'Cuddle closely with someone', example: 'uwu cuddle @User', aliases: [] },
  { name: 'feed', category: 'social', usage: 'uwu feed @user', description: 'Feed delicious anime snacks to someone', example: 'uwu feed @User', aliases: [] },

  // Music Commands
  { name: 'play', category: 'music', usage: 'uwu play <song name or URL>', description: 'Play music in your voice channel with Lavalink V4 SSL', example: 'uwu play Bohemian Rhapsody', aliases: ['p'] },
  { name: 'skip', category: 'music', usage: 'uwu skip', description: 'Skip current playing track in queue', example: 'uwu skip', aliases: ['s'] },
  { name: 'queue', category: 'music', usage: 'uwu queue', description: 'View current music queue and upcoming tracks', example: 'uwu queue', aliases: ['q'] },
  { name: 'pause', category: 'music', usage: 'uwu pause', description: 'Pause current song playback', example: 'uwu pause', aliases: [] },
  { name: 'resume', category: 'music', usage: 'uwu resume', description: 'Resume paused music playback', example: 'uwu resume', aliases: ['unpause'] },
  { name: 'stop', category: 'music', usage: 'uwu stop', description: 'Stop playback, clear queue, and leave voice channel', example: 'uwu stop', aliases: ['disconnect', 'leave'] },
  { name: 'nowplaying', category: 'music', usage: 'uwu nowplaying', description: 'Display current playing song track progress & artist', example: 'uwu np', aliases: ['np'] },
  { name: 'volume', category: 'music', usage: 'uwu volume <1-150>', description: 'Adjust music playback volume percentage', example: 'uwu volume 80', aliases: ['vol'] },
  { name: 'loop', category: 'music', usage: 'uwu loop <track|queue|off>', description: 'Toggle repeat loop mode for track or queue', example: 'uwu loop track', aliases: ['repeat'] },

  // Moderation & Admin Commands
  { name: 'antinuke', category: 'admin', usage: 'uwu antinuke <enable|disable|status>', description: 'Configure zero-tolerance anti-nuke defense shield', permissions: 'Administrator', example: 'uwu antinuke enable', aliases: ['shield'] },
  { name: 'ban', category: 'moderation', usage: 'uwu ban @user [reason]', description: 'Ban a member from the Discord server', permissions: 'Manage Server / Moderator', example: 'uwu ban @User Spamming', aliases: [] },
  { name: 'kick', category: 'moderation', usage: 'uwu kick @user [reason]', description: 'Kick a member from the Discord server', permissions: 'Manage Server / Moderator', example: 'uwu kick @User Breaking rules', aliases: [] },
  { name: 'mute', category: 'moderation', usage: 'uwu mute @user <duration> [reason]', description: 'Timeout/mute a member for specified duration', permissions: 'Manage Server / Moderator', example: 'uwu mute @User 1h Toxicity', aliases: ['timeout'] },
  { name: 'unmute', category: 'moderation', usage: 'uwu unmute @user', description: 'Remove timeout/mute from a member', permissions: 'Manage Server / Moderator', example: 'uwu unmute @User', aliases: ['untimeout'] },
  { name: 'purge', category: 'moderation', usage: 'uwu purge <amount>', description: 'Bulk delete specified number of messages (1-100)', permissions: 'Manage Server / Moderator', example: 'uwu purge 25', aliases: ['clear'] },
  { name: 'setodds', category: 'admin', usage: 'uwu setodds <game> <win_chance_percent>', description: 'Configure house edge / game win chance in Firebase', permissions: 'Administrator', example: 'uwu setodds slots 45', aliases: ['odds'] },
  { name: 'economystats', category: 'admin', usage: 'uwu economystats', description: 'View total server wealth distribution and circulation stats', permissions: 'Administrator', example: 'uwu economystats', aliases: ['econ', 'economy'] },
  { name: 'setprefix', category: 'admin', usage: 'uwu setprefix <new_prefix>', description: 'Change custom bot prefix for current server', permissions: 'Administrator', example: 'uwu setprefix !', aliases: ['prefix'] },
];

export const FLOWERS_CATALOG: FlowerItem[] = [
  { id: 'tulip', name: '🌷 Tulip', price: 5_000_000, charisma: 50, description: 'A sweet tulip. Grants +50 Charisma EXP.', icon: '🌷' },
  { id: 'rose', name: '🌹 Red Rose', price: 10_000_000, charisma: 110, description: 'A classic romantic rose. Grants +110 Charisma EXP.', icon: '🌹' },
  { id: 'sunflower', name: '🌻 Sunflower', price: 25_000_000, charisma: 300, description: 'A bright sunflower. Grants +300 Charisma EXP.', icon: '🌻' },
  { id: 'lily', name: '🌸 Lily', price: 50_000_000, charisma: 650, description: 'An elegant lily. Grants +650 Charisma EXP.', icon: '🌸' },
  { id: 'golden_orchid', name: '✨ Golden Orchid', price: 100_000_000, charisma: 1500, description: 'A prestigious shimmering golden orchid. Grants +1,500 Charisma EXP.', icon: '✨' },
  { id: 'eternal_bloom', name: '👑 Eternal Bloom', price: 500_000_000, charisma: 8000, description: 'The pinnacle of floral luxury. Grants +8,000 Charisma EXP.', icon: '👑' },
];

export const PROPERTIES_CATALOG: PropertyItem[] = [
  { id: 'penthouse', name: 'Uwuncy Penthouse', price: 100_000_000_000, yieldPerHour: 250_000_000, tier: 'Luxury', description: 'A permanent luxury profile badge.', icon: '🏙️' },
  { id: 'mansion', name: 'Golden Mansion', price: 500_000_000_000, yieldPerHour: 1_500_000_000, tier: 'Elite', description: 'A permanent elite property title.', icon: '🏰' },
  { id: 'moonbase', name: 'Moonbase', price: 2_000_000_000_000, yieldPerHour: 8_000_000_000, tier: 'Legendary', description: 'A rare endgame property collectible.', icon: '🛸' },
];

export const COLLECTIBLES_CATALOG: CollectibleItem[] = [
  { id: 'jackpotcrown', name: 'Jackpot Crown', price: 250_000_000_000, rarity: 'Mythic', description: 'A prestigious crown for the richest gamblers.', icon: '👑' },
  { id: 'arena-trophy', name: 'Arena Trophy', price: 100_000_000_000, rarity: 'Legendary', description: 'A trophy commemorating arena champions.', icon: '🏆' },
  { id: 'diamond-paw', name: 'Diamond Paw', price: 750_000_000_000, rarity: 'Godly', description: 'A limited-looking collectible badge.', icon: '💎' },
];

export const BOOSTER_ITEMS_CATALOG: BoosterShopItem[] = [
  { id: '2x_earnings_pass', name: '2× Earnings Pass', category: 'Economy & Multipliers', price: 15_000_000_000_000, description: 'Doubles ALL money you earn for 7 days', icon: '📈' },
  { id: 'tax_exemption_token', name: 'Tax Exemption Token', category: 'Economy & Multipliers', price: 8_000_000_000_000, description: 'Pay 0% tax on all transactions for 30 days', icon: '📜' },
  { id: 'cooldown_skip', name: 'Cooldown Skip', category: 'Economy & Multipliers', price: 5_000_000_000_000, description: 'Skip any active cooldown immediately', icon: '⚡' },
  { id: 'daily_cap_bypass', name: 'Daily Cap Bypass', category: 'Economy & Multipliers', price: 10_000_000_000_000, description: 'Double your max daily earnings cap for 14 days', icon: '🔓' },
  { id: 'permanent_1_5x_boost', name: 'Permanent 1.5× Boost', category: 'Economy & Multipliers', price: 150_000_000_000_000, description: 'Permanent 1.5× multiplier on all income', icon: '🌟' },
  { id: 'lump_sum_bonus', name: 'Lump Sum Bonus', category: 'Economy & Multipliers', price: 3_000_000_000_000, description: 'Instantly receive 10T uwuncy bonus', icon: '💰' },
  { id: 'priority_queue', name: 'Priority Queue', category: 'Command & Utility Perks', price: 20_000_000_000_000, description: 'Priority music queueing and instant track bypass', icon: '🎵' },
  { id: 'extra_storage_slot', name: 'Extra Storage Slot', category: 'Command & Utility Perks', price: 15_000_000_000_000, description: '+10 extra inventory capacity slots', icon: '🎒' },
  { id: 'exclusive_command_pack', name: 'Exclusive Command Pack', category: 'Command & Utility Perks', price: 30_000_000_000_000, description: 'Access to special vanity commands and particle effects', icon: '✨' },
  { id: 'stealth_mode', name: 'Stealth Mode', category: 'Command & Utility Perks', price: 12_000_000_000_000, description: 'Hide your profile from public leaderboard searches', icon: '🥷' },
  { id: 'auto_claim_pass', name: 'Auto-Claim Pass', category: 'Command & Utility Perks', price: 25_000_000_000_000, description: 'Auto-claims hourly uwuncy for 7 days', icon: '🤖' },
  { id: 'permanent_shop_access', name: 'Permanent Shop Access', category: 'Limited & Rare', price: 80_000_000_000_000, description: 'Access Booster Shop even if boost expires', icon: '🏛️' },
  { id: 'lucky_enchant', name: 'Lucky Enchant', category: 'Limited & Rare', price: 45_000_000_000_000, description: '+5% permanent win chance on minigames', icon: '🍀' },
  { id: 'boost_count_multiplier', name: 'Boost Count Multiplier', category: 'Limited & Rare', price: 60_000_000_000_000, description: 'Multiplies your daily booster payout by 2x', icon: '🚀' },
];

export const INITIAL_CRYPTO_COINS: CryptoCoin[] = [
  {
    symbol: 'bitwuncy',
    displayName: 'Bitwuncy (BIT)',
    price: 100.0,
    change24h: 0.0,
    volume24h: 0,
    high24h: 100.0,
    low24h: 100.0,
    trend: 'neutral',
    history: [
      { time: '00:00', price: 100 },
      { time: '04:00', price: 100 },
      { time: '08:00', price: 100 },
      { time: '12:00', price: 100 },
      { time: '16:00', price: 100 },
      { time: '20:00', price: 100 }
    ]
  },
  {
    symbol: 'eterwuncy',
    displayName: 'Eterwuncy (ETH)',
    price: 100.0,
    change24h: 0.0,
    volume24h: 0,
    high24h: 100.0,
    low24h: 100.0,
    trend: 'neutral',
    history: [
      { time: '00:00', price: 100 },
      { time: '04:00', price: 100 },
      { time: '08:00', price: 100 },
      { time: '12:00', price: 100 },
      { time: '16:00', price: 100 },
      { time: '20:00', price: 100 }
    ]
  },
  {
    symbol: 'golwuncy',
    displayName: 'Golwuncy (GLD)',
    price: 100.0,
    change24h: 0.0,
    volume24h: 0,
    high24h: 100.0,
    low24h: 100.0,
    trend: 'neutral',
    history: [
      { time: '00:00', price: 100 },
      { time: '04:00', price: 100 },
      { time: '08:00', price: 100 },
      { time: '12:00', price: 100 },
      { time: '16:00', price: 100 },
      { time: '20:00', price: 100 }
    ]
  },
  {
    symbol: 'algowuncy',
    displayName: 'Algowuncy (ALGO)',
    price: 100.0,
    change24h: 0.0,
    volume24h: 0,
    high24h: 100.0,
    low24h: 100.0,
    trend: 'neutral',
    history: [
      { time: '00:00', price: 100 },
      { time: '04:00', price: 100 },
      { time: '08:00', price: 100 },
      { time: '12:00', price: 100 },
      { time: '16:00', price: 100 },
      { time: '20:00', price: 100 }
    ]
  },
  {
    symbol: 'memwuncy',
    displayName: 'Memwuncy (MEME)',
    price: 100.0,
    change24h: 0.0,
    volume24h: 0,
    high24h: 100.0,
    low24h: 100.0,
    trend: 'neutral',
    history: [
      { time: '00:00', price: 100 },
      { time: '04:00', price: 100 },
      { time: '08:00', price: 100 },
      { time: '12:00', price: 100 },
      { time: '16:00', price: 100 },
      { time: '20:00', price: 100 }
    ]
  },
  {
    symbol: 'dogewuncy',
    displayName: 'Dogewuncy (DOGE)',
    price: 100.0,
    change24h: 0.0,
    volume24h: 0,
    high24h: 100.0,
    low24h: 100.0,
    trend: 'neutral',
    history: [
      { time: '00:00', price: 100 },
      { time: '04:00', price: 100 },
      { time: '08:00', price: 100 },
      { time: '12:00', price: 100 },
      { time: '16:00', price: 100 },
      { time: '20:00', price: 100 }
    ]
  }
];
