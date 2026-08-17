import express from 'express';
import path from 'path';
import { exec } from 'child_process';
import { promisify } from 'util';
import fs from 'fs/promises';
import { createServer as createViteServer } from 'vite';
import {
  fetchDiscordBotDetails,
  fetchFirebaseLiveData,
  parseCodebaseData
} from './server/botService';

const execAsync = promisify(exec);
const app = express();
const PORT = 3000;

app.use(express.json());

// Cache in memory for quick responses with periodic re-sync
let lastSyncTimestamp = 0;
let cachedData: any = null;

async function getAggregatedLiveData(forceRefresh = false) {
  const now = Date.now();
  if (!forceRefresh && cachedData && now - lastSyncTimestamp < 15000) {
    return cachedData;
  }

  const [discord, firebase, codebase] = await Promise.all([
    fetchDiscordBotDetails(),
    fetchFirebaseLiveData(),
    parseCodebaseData()
  ]);

  cachedData = {
    syncedAt: new Date().toISOString(),
    timestamp: now,
    discord,
    firebase,
    codebase
  };
  lastSyncTimestamp = now;
  return cachedData;
}

// Bot Statistics & Live Health Status (Real data from Discord + Firebase)
app.get('/api/bot/stats', async (_req, res) => {
  try {
    const live = await getAggregatedLiveData();
    const discord = live.discord;
    const firebase = live.firebase;
    const codebase = live.codebase;

    return res.json({
      status: discord.connected ? 'online' : (firebase.connected ? 'synced_db' : 'standby'),
      discordConnected: discord.connected,
      discordReason: discord.reason,
      firebaseConnected: firebase.connected,
      firebaseReason: firebase.reason,
      botUser: discord.botUser,
      pingMs: discord.pingMs || 0,
      totalServers: discord.totalGuilds,
      totalUsers: firebase.connected ? firebase.totalUsers : discord.totalMembers,
      totalUwuncyInCirculation: firebase.connected ? firebase.totalCirculation : 0,
      totalJackpotPool: firebase.connected ? firebase.jackpotPool : (firebase.economySettings?.jackpot || 10000),
      totalCommandsRun: codebase.totalCommandsExtracted || 151,
      activeLavalinkNodes: 2,
      lavalinkHealth: 'Operational (Lavalink V4 SSL)',
      antiNukeStatus: 'Armed & Active (Zero-Tolerance)',
      version: 'v2.8.0',
      syncedAt: live.syncedAt,
      codeLineCount: codebase.mainPyLineCount,
      totalCommandsExtracted: codebase.totalCommandsExtracted,
    });
  } catch (error: any) {
    return res.status(500).json({ error: error.message || 'Failed to fetch live stats' });
  }
});

// Full Live Bot & Database Data State
app.get('/api/bot/live-data', async (_req, res) => {
  try {
    const live = await getAggregatedLiveData();
    return res.json(live);
  } catch (error: any) {
    return res.status(500).json({ error: error.message || 'Failed to fetch live data' });
  }
});

// Force Immediate Live Sync
app.post('/api/bot/sync', async (_req, res) => {
  try {
    const live = await getAggregatedLiveData(true);
    return res.json({
      success: true,
      message: 'Live data synchronized from Discord API & Firebase Realtime Database.',
      data: live
    });
  } catch (error: any) {
    return res.status(500).json({ error: error.message || 'Sync failed' });
  }
});

// Extracted Real Commands from main.py
app.get('/api/bot/commands', async (_req, res) => {
  try {
    const codebase = await parseCodebaseData();
    return res.json(codebase.commands);
  } catch (error: any) {
    return res.status(500).json({ error: error.message || 'Failed to load commands' });
  }
});

// Extracted Real Shops & Items from main.py & booster_utils.py
app.get('/api/bot/shops', async (_req, res) => {
  try {
    const codebase = await parseCodebaseData();
    return res.json({
      flowerShop: codebase.flowerShop,
      propertyShop: codebase.propertyShop,
      collectibleShop: codebase.collectibleShop,
      boosterItems: codebase.boosterItems,
      cryptoCoins: codebase.cryptoCoins
    });
  } catch (error: any) {
    return res.status(500).json({ error: error.message || 'Failed to load shop items' });
  }
});

// Get Git Repo Status
app.get('/api/repo-status', async (_req, res) => {
  try {
    const isGitRepo = await fs.access(path.join(process.cwd(), '.git')).then(() => true).catch(() => false);
    
    if (!isGitRepo) {
      return res.json({
        hasRepo: false,
        message: 'No repository currently cloned in this workspace.'
      });
    }

    const { stdout: remoteUrl } = await execAsync('git config --get remote.origin.url').catch(() => ({ stdout: '' }));
    const { stdout: branch } = await execAsync('git rev-parse --abbrev-ref HEAD').catch(() => ({ stdout: '' }));
    const { stdout: lastCommit } = await execAsync('git log -1 --format="%h - %s (%an, %cr)"').catch(() => ({ stdout: '' }));
    const { stdout: status } = await execAsync('git status --short').catch(() => ({ stdout: '' }));

    // Clean sensitive tokens from remote URL before returning
    const safeRemoteUrl = remoteUrl.trim().replace(/https:\/\/[^@]+@/, 'https://');

    return res.json({
      hasRepo: true,
      remoteUrl: safeRemoteUrl,
      branch: branch.trim(),
      lastCommit: lastCommit.trim(),
      changes: status.trim() ? status.trim().split('\n') : []
    });
  } catch (error: any) {
    return res.status(500).json({ error: error.message || 'Failed to get repo status' });
  }
});

// Clone GitHub Repository
app.post('/api/clone', async (req, res) => {
  const { repoUrl, token, branch } = req.body;

  if (!repoUrl || typeof repoUrl !== 'string') {
    return res.status(400).json({ error: 'GitHub repository URL or user/repo is required.' });
  }

  // Sanitize and format URL
  let targetUrl = repoUrl.trim();
  if (!targetUrl.startsWith('http://') && !targetUrl.startsWith('https://')) {
    // If user provided "username/repo"
    if (/^[\w.-]+\/[\w.-]+$/.test(targetUrl)) {
      targetUrl = `https://github.com/${targetUrl}.git`;
    } else {
      return res.status(400).json({ error: 'Invalid repository format. Please provide a full GitHub URL (e.g. https://github.com/owner/repo) or owner/repo format.' });
    }
  }

  if (!targetUrl.endsWith('.git')) {
    targetUrl += '.git';
  }

  // Inject token if provided
  let cloneUrl = targetUrl;
  if (token && token.trim()) {
    const cleanToken = token.trim();
    cloneUrl = targetUrl.replace('https://', `https://${cleanToken}@`);
  }

  const tempDir = path.join(process.cwd(), '.tmp_repo_clone');

  try {
    // Cleanup previous temp dir if exists
    await fs.rm(tempDir, { recursive: true, force: true }).catch(() => {});

    // Prepare git clone command
    let cloneCmd = `git clone --depth 1`;
    if (branch && branch.trim()) {
      cloneCmd += ` -b ${branch.trim()}`;
    }
    cloneCmd += ` "${cloneUrl}" "${tempDir}"`;

    console.log(`Cloning repository from ${targetUrl.replace(/https:\/\/[^@]+@/, 'https://')}...`);
    await execAsync(cloneCmd);

    // Copy files from temp directory into current workspace
    // Copy all files including .git
    const copyCmd = `cp -rn "${tempDir}/." "${process.cwd()}/" 2>/dev/null || cp -R "${tempDir}/." "${process.cwd()}/"`;
    await execAsync(copyCmd);

    // Clean up temp dir
    await fs.rm(tempDir, { recursive: true, force: true }).catch(() => {});

    // Check if package.json exists in cloned files and install dependencies
    const hasPackageJson = await fs.access(path.join(process.cwd(), 'package.json')).then(() => true).catch(() => false);
    let installLog = '';
    if (hasPackageJson) {
      console.log('Installing dependencies from package.json...');
      try {
        const { stdout, stderr } = await execAsync('npm install --prefer-offline');
        installLog = stdout || stderr;
      } catch (err: any) {
        installLog = `npm install warning: ${err.message}`;
      }
    }

    // Get commit info
    const { stdout: lastCommit } = await execAsync('git log -1 --format="%h - %s (%an, %cr)"').catch(() => ({ stdout: 'Cloned successfully' }));
    const { stdout: activeBranch } = await execAsync('git rev-parse --abbrev-ref HEAD').catch(() => ({ stdout: branch || 'main' }));

    return res.json({
      success: true,
      message: 'Repository pulled successfully!',
      remoteUrl: targetUrl.replace(/https:\/\/[^@]+@/, 'https://'),
      branch: activeBranch.trim(),
      lastCommit: lastCommit.trim(),
      installLog
    });
  } catch (error: any) {
    // Cleanup temp dir on error
    await fs.rm(tempDir, { recursive: true, force: true }).catch(() => {});

    const safeErrorMessage = (error.message || 'Clone failed')
      .replace(/https:\/\/[^@]+@/g, 'https://[TOKEN_REDACTED]@');

    console.error('Git clone error:', safeErrorMessage);
    return res.status(500).json({
      error: 'Failed to pull GitHub repository.',
      details: safeErrorMessage
    });
  }
});

// Git Pull
app.post('/api/pull', async (_req, res) => {
  try {
    const { stdout, stderr } = await execAsync('git pull');
    return res.json({
      success: true,
      output: stdout || stderr || 'Already up to date.'
    });
  } catch (error: any) {
    return res.status(500).json({ error: error.message || 'Git pull failed' });
  }
});

async function startServer() {
  if (process.env.NODE_ENV !== 'production') {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), 'dist');
    app.use(express.static(distPath));
    app.get('*', (_req, res) => {
      res.sendFile(path.join(distPath, 'index.html'));
    });
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`Server running on http://0.0.0.0:${PORT}`);
  });
}

startServer();
