export interface DiscordBotIdentity {
  id: string;
  username: string;
  discriminator: string;
  avatar: string | null;
  avatarUrl: string;
  tag: string;
  bot: boolean;
}

export interface DiscordGuildInfo {
  id: string;
  name: string;
  icon: string | null;
  iconUrl: string | null;
  approximate_member_count?: number;
  owner?: boolean;
}

export interface BotStats {
  status: 'online' | 'synced_db' | 'standby' | 'offline';
  discordConnected?: boolean;
  discordReason?: string;
  firebaseConnected?: boolean;
  firebaseReason?: string;
  botUser?: DiscordBotIdentity | null;
  pingMs: number;
  totalServers: number;
  totalUsers: number;
  totalUwuncyInCirculation: number;
  totalJackpotPool: number;
  totalCommandsRun: number;
  activeLavalinkNodes: number;
  lavalinkHealth: string;
  antiNukeStatus: string;
  version: string;
  uptimePercent?: number;
  lastRestart?: string;
  syncedAt?: string;
  codeLineCount?: number;
  totalCommandsExtracted?: number;
}

export interface LiveUserData {
  id: string;
  username?: string;
  displayName?: string;
  wallet: number;
  bank: number;
  netWorth: number;
  rank?: string;
  prestige?: number;
  streak?: number;
  charisma_exp?: number;
  is_booster?: boolean;
  boost_count?: number;
}

export interface LiveAggregatedState {
  syncedAt: string;
  timestamp: number;
  discord: {
    connected: boolean;
    reason?: string;
    botUser: DiscordBotIdentity | null;
    guilds: DiscordGuildInfo[];
    totalGuilds: number;
    totalMembers: number;
    pingMs: number;
  };
  firebase: {
    connected: boolean;
    reason?: string;
    databaseUrl: string;
    totalUsers: number;
    totalCirculation: number;
    jackpotPool: number;
    leaderboard: LiveUserData[];
    cryptoMarket: any;
    economySettings: any;
    gameOdds: any;
  };
  codebase: {
    commands: BotCommand[];
    boosterItems: any[];
    flowerShop: FlowerItem[];
    propertyShop: PropertyItem[];
    collectibleShop: CollectibleItem[];
    cryptoCoins: any[];
    mainPyLineCount: number;
    totalCommandsExtracted: number;
  };
}

export interface CryptoCoin {
  symbol: string;
  displayName: string;
  price: number;
  change24h: number;
  volume24h?: number;
  high24h?: number;
  low24h?: number;
  trend: 'bullish' | 'bearish' | 'neutral';
  history: { time: string; price: number }[];
  frozen?: boolean;
}

export interface LeaderboardUser {
  rank: number;
  id?: string;
  username: string;
  avatar: string;
  wallet: number;
  bank: number;
  totalNetWorth: number;
  prestigeLevel: number;
  isBooster: boolean;
  boostCount?: number;
  clanTag?: string;
  marriedTo?: string;
  charismaExp?: number;
}

export interface ShopsCatalogResponse {
  flowers: FlowerItem[];
  properties: PropertyItem[];
  collectibles: CollectibleItem[];
  boosterItems: BoosterShopItem[];
  cryptoCoins: any[];
}

export interface PropertyItem {
  id: string;
  name: string;
  price: number;
  yieldPerHour?: number;
  passiveIncomePerHour?: number;
  tier?: string;
  category?: 'Luxury' | 'Elite' | 'Cosmic' | 'Legendary' | string;
  description: string;
  icon?: string;
}

export interface CollectibleItem {
  id: string;
  name: string;
  price: number;
  rarity: 'Common' | 'Rare' | 'Epic' | 'Mythic' | 'Divine' | 'Legendary' | 'Godly' | string;
  description: string;
  icon?: string;
}

export interface FlowerItem {
  id: string;
  name: string;
  price: number;
  charisma: number;
  charismaExp?: number;
  description: string;
  icon?: string;
}

export interface BoosterShopItem {
  id: string;
  name: string;
  category: string;
  price: number;
  description: string;
  icon: string;
}

export interface BotCommand {
  name: string;
  category: 'booster' | 'economy' | 'gambling' | 'social' | 'music' | 'moderation' | 'admin' | string;
  usage: string;
  description: string;
  aliases: string[];
  permissions?: string;
  example: string;
}

export interface RepoStatus {
  hasRepo: boolean;
  remoteUrl?: string;
  branch?: string;
  lastCommit?: string;
  changes?: string[];
  message?: string;
}
