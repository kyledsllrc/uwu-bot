# ==============================================
# KEEP-ALIVE FOR 24/7 REPLIT HOSTING
# ==============================================
from flask import Flask
import threading
app = Flask(__name__)
@app.route('/')
@app.route('/api')
@app.route('/api/')
def keep_alive(): return "UwU Bot is alive & running!", 200

# ==============================================
# BOT SETUP & IMPORTS
# ==============================================
import discord
from discord.ext import commands, tasks
import random, json, time, os, asyncio, socket, uuid, re, traceback, hashlib
import aiohttp
from html import unescape
import social_utils
import booster_utils
from typing import Union
from datetime import datetime, timezone, timedelta
from threading import Lock
from collections import deque
from urllib.parse import quote_plus
import urllib.request
import firebase_admin
from firebase_admin import credentials, db
from dotenv import load_dotenv

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

# Hosts that expose secrets as a .env file rather than real environment variables.
load_dotenv()

# --- BOT OWNER ID ---
BOT_OWNER_ID = "906461875221434428"

# --- PREFIX ---
DEFAULT_PREFIX = "uwu "
CURRENT_PREFIX = DEFAULT_PREFIX
PREFIX_VARIANTS = [
    "".join(letter.upper() if mask & (1 << index) else letter for index, letter in enumerate("uwu")) + " "
    for mask in range(8)
]

def get_prefix():
    return CURRENT_PREFIX

def get_prefixes():
    extra_prefixes = ["!", "uwu !", "Uwu !", "uWu !", "UWU !", "uwu!", "Uwu!", "uWu!", "UWU!"]
    return PREFIX_VARIANTS + extra_prefixes

# --- INTENTS ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
try:
    intents.invites = True
except AttributeError:
    pass
bot = commands.Bot(
    command_prefix=lambda b, m: get_prefixes(),
    intents=intents,
    case_insensitive=True,
    help_command=None
)

# --- OWNER CHECK ---
def is_owner(ctx):
    return str(ctx.author.id) == BOT_OWNER_ID

CATEGORY_ALIASES = {
    "social": "socials",
    "socials": "socials",
    "social-media": "socials",
    "gambling": "gambling",
    "casino": "gambling",
    "games": "gambling",
    "economy": "economy",
    "wallet": "economy",
    "wallets": "economy",
    "music": "music",
    "audio": "music",
    "mod": "moderation",
    "moderation": "moderation",
    "admin": "admin",
    "owner": "admin",
}

COMMAND_CATEGORY_MAP = {
    "ig": "socials",
    "tt": "socials",
    "fb": "socials",
    "coinflip": "gambling",
    "slots": "gambling",
    "blackjack": "gambling",
    "bj": "gambling",
    "mines": "gambling",
    "colorgame": "gambling",
    "dice": "gambling",
    "highlow": "gambling",
    "roulette": "gambling",
    "crash": "gambling",
    "tower": "gambling",
    "wheel": "gambling",
    "ladder": "gambling",
    "scratch": "gambling",
    "sabong": "gambling",
    "daily": "economy",
    "bal": "economy",
    "balance": "economy",
    "deposit": "economy",
    "withdraw": "economy",
    "give": "economy",
    "invest": "economy",
    "investments": "economy",
    "sell": "economy",
    "info": "economy",
    "profile": "economy",
    "ban": "moderation",
    "rollback": "moderation",
    "lock": "moderation",
    "unlock": "moderation",
    "modlog": "moderation",
    "whitelist": "moderation",
    "antinuke": "moderation",
    "antispam": "moderation",
    "antiraid": "moderation",
    "antibullying": "moderation",
    "anti-bullying": "moderation",
    "antibully": "moderation",
    "anti-bully": "moderation",
    "anti": "moderation",
    "setwelcome": "moderation",
    "set": "moderation",
    "welcomechannel": "moderation",
    "welcome": "moderation",
    "invites": "moderation",
    "invs": "moderation",
    "invite": "moderation",
    "inviter": "moderation",
    "invboard": "moderation",
    "topinvites": "moderation",
    "invleaderboard": "moderation",
    "syncinvites": "moderation",
    "invsync": "moderation",
    "addcoins": "admin",
    "economystats": "admin",
    "odds": "admin",
    "cryptocontrol": "admin",
    "userodds": "admin",
    "setgameodds": "admin",
    "setbetlimits": "admin",
    "marry": "socials",
    "divorce": "socials",
    "ship": "socials",
    "flowershop": "socials",
    "buyflower": "socials",
    "sendflower": "socials",
    "flower": "socials",
    "flowers": "socials",
    "flowergive": "socials",
    "flowersgive": "socials",
    "giveflower": "socials",
    "giveflowers": "socials",
    "charisma": "socials",
    "play": "music",
    "!play": "music",
    "pause": "music",
    "resume": "music",
    "skip": "music",
    "stop": "music",
    "volume": "music",
    "lyrics": "music",
    "save": "music",
}

# ==============================================
# ✅ FIREBASE PERSISTENCE
# ==============================================
DATA_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "data.json")
)
DATA_LOCK = Lock()

FIREBASE_DATABASE_URL = os.environ.get(
    "FIREBASE_DATABASE_URL",
    "https://uwu-bot-4cff1-default-rtdb.asia-southeast1.firebasedatabase.app",
)

def load_firebase_credentials():
    """Read the service account as inline JSON or as a path to a JSON file."""
    raw_credentials = os.environ.get("FIREBASE_CREDENTIALS", "").strip()
    if not raw_credentials:
        raise RuntimeError("FIREBASE_CREDENTIALS secret is not configured")
    # Hosting panels that cap environment variable length can point this at a file.
    if not raw_credentials.startswith("{"):
        with open(raw_credentials, "r", encoding="utf-8") as handle:
            return json.load(handle)
    return json.loads(raw_credentials)

def initialize_firebase():
    try:
        credential_data = load_firebase_credentials()
        firebase_credential = credentials.Certificate(credential_data)
        if not firebase_admin._apps:
            firebase_admin.initialize_app(
                firebase_credential,
                {"databaseURL": FIREBASE_DATABASE_URL},
            )
        return db.reference("users")
    except Exception as exc:
        raise RuntimeError(f"Firebase initialization failed: {exc}") from exc

db_ref = initialize_firebase()
GAME_ODDS_REF = db.reference("game_odds")
USER_GAME_ODDS_REF = db.reference("user_game_odds")
GAME_BET_LIMITS_REF = db.reference("game_bet_limits")
ECONOMY_REF = db.reference("economy_settings")
CRYPTO_REF = db.reference("crypto_market")
ARENAS_REF = db.reference("arenas")
ARENA_CHANNELS_REF = db.reference("arena_channels")
ARENA_CHANNEL_REDO_REF = db.reference("arena_channel_redo")
CLANS_REF = db.reference("clans")
SEASONS_REF = db.reference("seasons")
BOT_LOCK_REF = db.reference("bot_runtime_lock")
BOT_INSTANCE_ID = f"{socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex}"
BOT_LEASE_SECONDS = 45
BOT_HEARTBEAT_SECONDS = 15
bot_lease_stop = threading.Event()

FFMPEG_OPTIONS = {
    "before_options": (
        "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 "
        "-user_agent \"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36\""
    ),
    "options": "-vn -ar 48000 -ac 2 -loglevel error",
}
YTDL_OPTIONS = {
    "format": "bestaudio/best",
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch",
    "ignoreerrors": True,
    "playlistend": 100,
    "nocheckcertificate": True,
    "skip_download": True,
    "source_address": "0.0.0.0",
    "cachedir": False,
    "extractor_args": {
        "youtube": {
            "player_client": ["mweb", "ios", "android"]
        }
    }
}
MUSIC_STATES = {}
MUSIC_LOCKS = {}
MARRIAGES_KEY = "_marriages"

GAMBLING_GAME_NAMES = (
    "slots",
    "coinflip",
    "blackjack",
    "mines",
    "colorgame",
    "dice",
    "highlow",
    "roulette",
    "crash",
    "tower",
    "wheel",
    "ladder",
    "scratch",
    "sabong",
)

DEFAULT_GAME_WIN_CHANCES = {
    game: 40.0
    for game in GAMBLING_GAME_NAMES
}
# Sabong is player-versus-player, so its chance is not a house win rate: it is
# the chance the MERON rooster wins. 50% is an even fight.
DEFAULT_GAME_WIN_CHANCES["sabong"] = 50.0

GAME_ODDS_ALIASES = {
    "slot": "slots",
    "slots": "slots",
    "cf": "coinflip",
    "coinflip": "coinflip",
    "bj": "blackjack",
    "blackjack": "blackjack",
    "m": "mines",
    "mines": "mines",
    "cg": "colorgame",
    "colorgame": "colorgame",
    "dice": "dice",
    "roll": "dice",
    "hl": "highlow",
    "highlow": "highlow",
    "rr": "roulette",
    "roulette": "roulette",
    "crash": "crash",
    "rocket": "crash",
    "tower": "tower",
    "climb": "tower",
    "wheel": "wheel",
    "spin": "wheel",
    "ladder": "ladder",
    "chain": "ladder",
    "scratch": "scratch",
    "sc": "scratch",
    "sabong": "sabong",
    "cockfight": "sabong",
    "tari": "sabong",
}


def game_odds_meaning(game):
    """What a game's configured percentage actually controls."""
    # Sabong is bet between players, so there is no house win rate to set --
    # the percentage steers which rooster wins instead.
    return "chance MERON wins" if game == "sabong" else "win chance"

def load_game_win_chances():
    """Load developer-controlled win chances without losing safe defaults."""
    try:
        stored = GAME_ODDS_REF.get()
        chances = DEFAULT_GAME_WIN_CHANCES.copy()
        if isinstance(stored, dict):
            for game, default in chances.items():
                try:
                    value = float(stored.get(game, default))
                except (TypeError, ValueError):
                    value = default
                chances[game] = max(0.0, min(100.0, value))
        if not isinstance(stored, dict) or any(
            game not in stored for game in chances
        ):
            GAME_ODDS_REF.set(chances)
        return chances
    except Exception as exc:
        raise RuntimeError(f"Firebase game odds read failed: {exc}") from exc

def save_game_win_chances(chances):
    try:
        GAME_ODDS_REF.set(chances)
    except Exception as exc:
        raise RuntimeError(f"Firebase game odds write failed: {exc}") from exc

GAME_WIN_CHANCES = load_game_win_chances()


def load_user_game_odds():
    """Load owner-controlled per-user gambling odds overrides."""
    try:
        stored = USER_GAME_ODDS_REF.get()
        return stored if isinstance(stored, dict) else {}
    except Exception as exc:
        raise RuntimeError(f"Firebase user game odds read failed: {exc}") from exc


def save_user_game_odds():
    try:
        USER_GAME_ODDS_REF.set(USER_GAME_ODDS)
    except Exception as exc:
        raise RuntimeError(f"Firebase user game odds write failed: {exc}") from exc


USER_GAME_ODDS = load_user_game_odds()

DEFAULT_GAME_BET_LIMITS = {
    game: {"min": 1, "max": 0}
    for game in GAMBLING_GAME_NAMES
}


def load_game_bet_limits():
    """Load exact min/max bets for non-Arena gambling games."""
    try:
        stored = GAME_BET_LIMITS_REF.get()
        limits = {
            game: values.copy()
            for game, values in DEFAULT_GAME_BET_LIMITS.items()
        }
        if isinstance(stored, dict):
            for game in limits:
                record = stored.get(game)
                if not isinstance(record, dict):
                    continue
                try:
                    limits[game]["min"] = max(1, int(record.get("min", 1)))
                except (TypeError, ValueError):
                    pass
                try:
                    limits[game]["max"] = max(0, int(record.get("max", 0)))
                except (TypeError, ValueError):
                    pass
                if limits[game]["max"] and limits[game]["max"] < limits[game]["min"]:
                    limits[game]["max"] = limits[game]["min"]
        if not isinstance(stored, dict):
            GAME_BET_LIMITS_REF.set(limits)
        return limits
    except Exception as exc:
        raise RuntimeError(f"Firebase game bet limits read failed: {exc}") from exc


def save_game_bet_limits():
    try:
        GAME_BET_LIMITS_REF.set(GAME_BET_LIMITS)
    except Exception as exc:
        raise RuntimeError(f"Firebase game bet limits write failed: {exc}") from exc


GAME_BET_LIMITS = load_game_bet_limits()

DEFAULT_ECONOMY_SETTINGS = {
    "jackpot": 10_000,
    "max_bet_percent": 25.0,
    "bet_cap_enabled": True,
    "claim_reward": 500_000_000_000,
}

def load_economy_settings():
    """Load global economy settings while preserving safe defaults."""
    try:
        stored = ECONOMY_REF.get()
        settings = DEFAULT_ECONOMY_SETTINGS.copy()
        if isinstance(stored, dict):
            legacy_cap_settings = "bet_cap_enabled" not in stored
            try:
                settings["jackpot"] = max(0, int(stored.get("jackpot", settings["jackpot"])))
            except (TypeError, ValueError):
                pass
            try:
                settings["claim_reward"] = max(0, int(stored.get("claim_reward", settings["claim_reward"])))
            except (TypeError, ValueError):
                pass
            if legacy_cap_settings:
                settings["max_bet_percent"] = DEFAULT_ECONOMY_SETTINGS["max_bet_percent"]
                settings["bet_cap_enabled"] = True
            else:
                try:
                    settings["max_bet_percent"] = max(
                        0.0, min(100.0, float(stored.get("max_bet_percent", settings["max_bet_percent"])))
                    )
                except (TypeError, ValueError):
                    pass
                settings["bet_cap_enabled"] = bool(stored.get("bet_cap_enabled", True))
        else:
            ECONOMY_REF.set(settings)
        return settings
    except Exception as exc:
        raise RuntimeError(f"Firebase economy settings read failed: {exc}") from exc

def save_economy_settings():
    try:
        ECONOMY_REF.set(ECONOMY_SETTINGS)
    except Exception as exc:
        raise RuntimeError(f"Firebase economy settings write failed: {exc}") from exc

ECONOMY_SETTINGS = load_economy_settings()

CRYPTO_SYMBOLS = (
    "bitwuncy",
    "eterwuncy",
    "golwuncy",
    "algowuncy",
    "memwuncy",
    "dogewuncy",
)
CRYPTO_DISPLAY_NAMES = {
    "bitwuncy": "Bitwuncy",
    "eterwuncy": "Eterwuncy",
    "golwuncy": "Golwuncy",
    "algowuncy": "Algowuncy",
    "memwuncy": "Memwuncy",
    "dogewuncy": "Dogewuncy",
}
CRYPTO_ALIASES = {
    **{symbol: symbol for symbol in CRYPTO_SYMBOLS},
    "bit": "bitwuncy",
    "eter": "eterwuncy",
    "eth": "eterwuncy",
    "gol": "golwuncy",
    "algo": "algowuncy",
    "mem": "memwuncy",
    "doge": "dogewuncy",
}
CRYPTO_HISTORY_LENGTH = 30
CRYPTO_TICK_SECONDS = 30
CRYPTO_DEFAULT_TICK_PERCENT = 2.0
CRYPTO_LOCK = Lock()

def _default_crypto_market():
    return {
        "paused": False,
        "updated_at": time.time(),
        "symbols": {
            symbol: {
                "price": 100.0,
                "history": [100.0] * CRYPTO_HISTORY_LENGTH,
                "trend": "random",
                "tick_percent": CRYPTO_DEFAULT_TICK_PERCENT,
                "frozen": False,
            }
            for symbol in CRYPTO_SYMBOLS
        },
    }

def _normalize_crypto_market(stored):
    market = _default_crypto_market()
    if isinstance(stored, dict):
        market["paused"] = bool(stored.get("paused", False))
        try:
            market["updated_at"] = float(stored.get("updated_at", market["updated_at"]))
        except (TypeError, ValueError):
            pass
        for symbol in CRYPTO_SYMBOLS:
            old = stored.get("symbols", {}).get(symbol, {})
            if not isinstance(old, dict):
                continue
            try:
                price = max(1.0, float(old.get("price", 100.0)))
            except (TypeError, ValueError):
                price = 100.0
            try:
                tick_percent = max(
                    0.1, min(50.0, float(old.get("tick_percent", CRYPTO_DEFAULT_TICK_PERCENT)))
                )
            except (TypeError, ValueError):
                tick_percent = CRYPTO_DEFAULT_TICK_PERCENT
            history = old.get("history", [])
            if not isinstance(history, list):
                history = []
            clean_history = []
            for value in history[-CRYPTO_HISTORY_LENGTH:]:
                try:
                    clean_history.append(max(1.0, float(value)))
                except (TypeError, ValueError):
                    continue
            if not clean_history:
                clean_history = [price]
            market["symbols"][symbol] = {
                "price": price,
                "history": (clean_history + [price] * CRYPTO_HISTORY_LENGTH)[-CRYPTO_HISTORY_LENGTH:],
                "trend": old.get("trend", "random")
                if old.get("trend") in {"up", "down", "random"} else "random",
                "tick_percent": tick_percent,
                "frozen": bool(old.get("frozen", False)),
            }
    return market

def load_crypto_market():
    try:
        stored = CRYPTO_REF.get()
        market = _normalize_crypto_market(stored)
        if not isinstance(stored, dict) or stored != market:
            CRYPTO_REF.set(market)
        return market
    except Exception as exc:
        raise RuntimeError(f"Firebase crypto market read failed: {exc}") from exc

def save_crypto_market():
    try:
        CRYPTO_REF.set(CRYPTO_MARKET)
    except Exception as exc:
        raise RuntimeError(f"Firebase crypto market write failed: {exc}") from exc

CRYPTO_MARKET = load_crypto_market()

def resolve_crypto(value):
    return CRYPTO_ALIASES.get(str(value or "").casefold())

def crypto_price(symbol):
    return float(CRYPTO_MARKET["symbols"][symbol]["price"])

def crypto_sparkline(values):
    """Render a compact, readable price graph for a Discord embed."""
    blocks = "▁▂▃▄▅▆▇█"
    if not values:
        return "—"
    numbers = [float(value) for value in values]
    low, high = min(numbers), max(numbers)
    if high == low:
        return blocks[3] * len(numbers)
    return "".join(
        blocks[
            min(
                len(blocks) - 1,
                max(0, int((value - low) / (high - low) * (len(blocks) - 1))),
            )
        ]
        for value in numbers
    )

def crypto_change_percent(state):
    history = state.get("history", [])
    if not history or not history[0]:
        return 0.0
    return (float(state["price"]) - float(history[0])) / float(history[0]) * 100

def update_crypto_market():
    """Move the market one tick and persist the new graph points."""
    changed = False
    with CRYPTO_LOCK:
        if not CRYPTO_MARKET.get("paused", False):
            for state in CRYPTO_MARKET["symbols"].values():
                if state.get("frozen", False):
                    continue
                percent = max(0.1, min(50.0, float(state.get("tick_percent", 2.0))))
                trend = state.get("trend", "random")
                direction = 1 if trend == "up" else -1 if trend == "down" else random.choice((-1, 1))
                next_price = max(1.0, float(state["price"]) * (1 + direction * percent / 100))
                state["price"] = round(next_price, 4)
                state["history"] = (state.get("history", []) + [state["price"]])[-CRYPTO_HISTORY_LENGTH:]
                changed = True
            if changed:
                CRYPTO_MARKET["updated_at"] = time.time()
                save_crypto_market()
    return changed

@tasks.loop(seconds=CRYPTO_TICK_SECONDS)
async def crypto_market_loop():
    update_crypto_market()

def format_crypto_price(price):
    return f"{float(price):,.2f}"

def crypto_portfolio(user):
    """Return held positions marked to the current market price."""
    positions = user.get("crypto_positions", {})
    if not isinstance(positions, dict):
        positions = {}
    rows = []
    total_invested = 0.0
    total_value = 0.0
    for symbol in CRYPTO_SYMBOLS:
        position = positions.get(symbol)
        if not isinstance(position, dict):
            continue
        try:
            invested = max(0.0, float(position.get("invested", 0)))
            held_principal = max(
                0.0, float(position.get("held_principal", invested))
            )
            units = max(0.0, float(position.get("units", 0)))
        except (TypeError, ValueError):
            continue
        if invested <= 0 or units <= 0:
            continue
        value = units * crypto_price(symbol)
        profit = value - invested
        total_invested += invested
        total_value += value
        rows.append({
            "symbol": symbol,
            "invested": invested,
            "held_principal": held_principal,
            "units": units,
            "value": value,
            "profit": profit,
            "entry_price": invested / units,
            "price": crypto_price(symbol),
        })
    return rows, total_invested, total_value, total_value - total_invested

def crypto_position_value(user, symbol):
    position = user.get("crypto_positions", {}).get(symbol)
    if not isinstance(position, dict):
        return None
    try:
        invested = max(0.0, float(position.get("invested", 0)))
        units = max(0.0, float(position.get("units", 0)))
    except (TypeError, ValueError):
        return None
    if invested <= 0 or units <= 0:
        return None
    return position, invested, units, units * crypto_price(symbol)

def crypto_market_embed():
    embed = discord.Embed(
        title="📈 UWUCRYPTO — Live Market",
        description="Prices update automatically every 30 seconds.",
        color=discord.Color.green(),
    )
    for symbol in CRYPTO_SYMBOLS:
        state = CRYPTO_MARKET["symbols"][symbol]
        change = crypto_change_percent(state)
        arrow = "📈" if change > 0 else "📉" if change < 0 else "➖"
        trend = state.get("trend", "random").title()
        embed.add_field(
            name=f"{arrow} {CRYPTO_DISPLAY_NAMES[symbol]}",
            value=(
                f"Price: **{format_crypto_price(state['price'])} uwuncy**\n"
                f"{crypto_sparkline(state.get('history', []))}\n"
                f"Since graph start: **{change:+.2f}%** • Trend: `{trend}`"
            ),
            inline=False,
        )
    status = "PAUSED" if CRYPTO_MARKET.get("paused") else "LIVE"
    embed.set_footer(text=f"Market {status} • Use uwu invest <crypto> <amount>")
    return embed

def get_game_win_chance(game):
    return float(GAME_WIN_CHANCES.get(game, 40.0))

def get_user_game_win_chance(user_id, game):
    """Return a per-user win chance override, if one is configured."""
    record = USER_GAME_ODDS.get(str(user_id), {})
    if not isinstance(record, dict):
        return None
    setting = record.get(game)
    if not isinstance(setting, dict):
        return None
    try:
        percent = float(setting.get("percent"))
    except (TypeError, ValueError):
        return None

    # ✅ ADD HARD LOCKS HERE — CRUCIAL FOR YOUR COMMANDS!
    if setting.get("mode") == "win":
        if percent >= 100:
            return 100.0  # ✅ FORCE ALWAYS WIN
        if percent <= 0:
            return 0.0    # ❌ FORCE ALWAYS LOSE
        return max(0.0, min(100.0, percent))

    elif setting.get("mode") == "lose":
        if percent >= 100:
            return 0.0    # ❌ LOSE 100% = NEVER WIN
        if percent <= 0:
            return 100.0  # ✅ LOSE 0% = ALWAYS WIN
        percent = 100.0 - percent
        return max(0.0, min(100.0, percent))

def get_effective_game_win_chance(game, user_id=None):
    override = None
    if user_id is not None:
        override = get_user_game_win_chance(user_id, game)
    # ✅ USE OVERRIDE IF EXISTS, ELSE GLOBAL
    return get_game_win_chance(game) if override is None else override

def chance_roll(game, bonus=0.0, user_id=None):
    chance = max(0.0, min(100.0, get_effective_game_win_chance(game, user_id) + bonus))
    # ⚡ FORCE INSTANT RESULT — NO RANDOM CHANCE TO FAIL!
    if chance >= 100:
        return True
    if chance <= 0:
        return False
    return random.random() < (chance / 100.0)

# ==============================================
# 🎲 PAYOUT MATH FOR THE CASH-OUT GAMBLING GAMES
# ==============================================
# Every multiplier below is priced off BASELINE_WIN_CHANCE, never off the
# chance the owner has configured. That keeps `uwu odds` and `uwu userodds`
# working as economy controls: lowering a game's chance lowers the player's
# real return without silently inflating the payout table to compensate.
BASELINE_WIN_CHANCE = 40.0
HOUSE_EDGE = 0.10
# Average total return of a winning instant round, so a full round returns
# (1 - HOUSE_EDGE) of the stake on average at the baseline chance.
INSTANT_WIN_RETURN = (1.0 - HOUSE_EDGE) / (BASELINE_WIN_CHANCE / 100.0)

def scaled_step_survival(base_survival, win_chance):
    """Map a configured win chance onto one step's survival probability.

    Anchored so 0% always busts, the baseline chance keeps the game's natural
    survival rate, and 100% never busts.
    """
    chance = max(0.0, min(100.0, float(win_chance)))
    if chance <= BASELINE_WIN_CHANCE:
        return base_survival * (chance / BASELINE_WIN_CHANCE)
    climb = (chance - BASELINE_WIN_CHANCE) / (100.0 - BASELINE_WIN_CHANCE)
    return base_survival + (1.0 - base_survival) * climb

def survive_step(game, base_survival, user_id=None):
    """Roll one step of a cash-out game under the configured odds."""
    survival = scaled_step_survival(
        base_survival,
        get_effective_game_win_chance(game, user_id),
    )
    if survival >= 1.0:
        return True
    if survival <= 0.0:
        return False
    return random.random() < survival

def cashout_multiplier(base_survival, steps):
    """Total return (stake included) after surviving `steps` steps."""
    return (1.0 - HOUSE_EDGE) / (base_survival ** max(0, int(steps)))

def balance_payout_table(entries, target_mean=INSTANT_WIN_RETURN):
    """Retune a table's top prize so its weighted mean return hits the target."""
    table = [[float(multiplier), float(weight)] for multiplier, weight in entries]
    total_weight = sum(weight for _, weight in table)
    top_index = max(range(len(table)), key=lambda index: table[index][0])
    fixed_value = sum(
        multiplier * weight
        for index, (multiplier, weight) in enumerate(table)
        if index != top_index
    )
    table[top_index][0] = round(
        (target_mean * total_weight - fixed_value) / table[top_index][1],
        2,
    )
    return tuple((multiplier, weight) for multiplier, weight in table)

def draw_payout(table):
    """Pick one multiplier from a weighted payout table."""
    return random.choices(
        [multiplier for multiplier, _ in table],
        weights=[weight for _, weight in table],
        k=1,
    )[0]

def table_mean_return(table):
    return sum(
        multiplier * weight for multiplier, weight in table
    ) / sum(weight for _, weight in table)

# Every gambling game shares one configurable win chance, so they must also
# share one winning return — otherwise the cheapest game to win becomes a money
# printer. WIN_PROFIT is what a flat win credits on top of a stake that was
# never debited; INSTANT_WIN_RETURN is the same number for games that reserve
# the stake up front.
WIN_PROFIT = INSTANT_WIN_RETURN - 1.0
# A natural 21 keeps its traditional 3:2 premium over a normal blackjack win.
BLACKJACK_NATURAL_PROFIT = WIN_PROFIT * 1.5
# Colorgame's two-match consolation, kept below a full win.
COLORGAME_PAIR_RETURN = 1.5

SLOT_SYMBOLS = ("🍒", "🍋", "🍊", "🍇", "7️⃣", "💎")
# Total return per winning symbol; the top prize is retuned so the weighted
# mean lands exactly on INSTANT_WIN_RETURN.
SLOT_TABLE = balance_payout_table(
    ((1.7, 20), (1.7, 20), (1.7, 20), (1.7, 20), (3.0, 13), (6.0, 7))
)

def draw_slot_symbol():
    """Pick a winning reel symbol and its total return."""
    index = random.choices(
        range(len(SLOT_TABLE)),
        weights=[weight for _, weight in SLOT_TABLE],
        k=1,
    )[0]
    return SLOT_SYMBOLS[index], SLOT_TABLE[index][0]

def blackjack_score(hand):
    total = sum(card[1] for card in hand)
    aces = sum(card[0] == "A" for card in hand)
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total

def build_blackjack_round(target_win):
    """Deal a valid blackjack round whose resolved result matches the odds target."""
    cards = [
        ("A", 11), ("2", 2), ("3", 3), ("4", 4), ("5", 5),
        ("6", 6), ("7", 7), ("8", 8), ("9", 9), ("10", 10),
        ("J", 10), ("Q", 10), ("K", 10),
    ] * 4

    for _ in range(500):
        deck = cards.copy()
        random.shuffle(deck)
        player = [deck.pop(), deck.pop()]
        dealer = [deck.pop(), deck.pop()]

        while blackjack_score(player) < 17:
            player.append(deck.pop())
        while blackjack_score(dealer) < 17:
            dealer.append(deck.pop())

        player_score = blackjack_score(player)
        dealer_score = blackjack_score(dealer)
        resolved_win = (
            player_score == 21
            and len(player) == 2
            and not (dealer_score == 21 and len(dealer) == 2)
        ) or (
            player_score <= 21
            and (dealer_score > 21 or player_score > dealer_score)
        )
        resolved_loss = (
            player_score > 21
            or (
                player_score <= 21
                and dealer_score <= 21
                and player_score < dealer_score
            )
        )
        if (target_win and resolved_win) or (not target_win and resolved_loss):
            return player[:2], dealer[:2], player, dealer

    # A valid fallback is extremely unlikely to be needed, but keeps the
    # command safe if the random source behaves unexpectedly.
    player = [("10", 10), ("7", 7)]
    dealer = [("10", 10), ("6", 6)]
    if target_win:
        return player, dealer, player, dealer
    return [("10", 10), ("6", 6)], [("10", 10), ("7", 7)], [("10", 10), ("6", 6)], [("10", 10), ("7", 7)]

def _claim_or_keep_lease(current):
    now = time.time()
    if not current or current.get("expires_at", 0) <= now:
        return {
            "owner": BOT_INSTANCE_ID,
            "expires_at": now + BOT_LEASE_SECONDS,
        }
    if current.get("owner") == BOT_INSTANCE_ID:
        current["expires_at"] = now + BOT_LEASE_SECONDS
    return current

def acquire_bot_lease():
    """Claim the Firebase lease before opening the Discord gateway."""
    deadline = time.time() + BOT_LEASE_SECONDS * 2
    while time.time() < deadline:
        try:
            result = BOT_LOCK_REF.transaction(_claim_or_keep_lease)
            if result and result.get("owner") == BOT_INSTANCE_ID:
                print("✅ DISCORD LEASE ACQUIRED — SINGLE INSTANCE PROTECTION ACTIVE")
                return
        except Exception as exc:
            print(f"⚠️ Discord lease check failed: {exc}")
        time.sleep(2)
    raise RuntimeError(
        "Another bot instance owns the Discord lease; refusing to start a duplicate."
    )

def refresh_bot_lease():
    while not bot_lease_stop.wait(BOT_HEARTBEAT_SECONDS):
        try:
            result = BOT_LOCK_REF.transaction(_claim_or_keep_lease)
            if not result or result.get("owner") != BOT_INSTANCE_ID:
                print("❌ Discord lease lost; shutting down this bot instance.")
                bot_lease_stop.set()
                asyncio.run_coroutine_threadsafe(bot.close(), bot.loop)
                return
        except Exception as exc:
            print(f"⚠️ Discord lease heartbeat failed: {exc}")

def release_bot_lease():
    bot_lease_stop.set()
    try:
        def release(current):
            if current and current.get("owner") == BOT_INSTANCE_ID:
                return {}
            return current
        BOT_LOCK_REF.transaction(release)
    except Exception as exc:
        print(f"⚠️ Could not release Discord lease: {exc}")

def load_local_backup():
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}

def migrate_legacy_currency_fields(data):
    """Convert legacy balance fields into the canonical Firebase wallet field."""
    if not isinstance(data, dict):
        return False

    changed = False
    for record in data.values():
        if not isinstance(record, dict):
            continue

        # Prefer the current wallet value if both old and current fields exist.
        # This avoids double-counting an account that was partially migrated.
        if "wallet" not in record:
            for legacy_key in ("uwuncy", "coins"):
                if legacy_key not in record:
                    continue
                try:
                    record["wallet"] = max(0, int(record[legacy_key]))
                except (TypeError, ValueError):
                    record["wallet"] = 0
                changed = True
                break

        for legacy_key in ("coins", "uwuncy"):
            if legacy_key in record:
                del record[legacy_key]
                changed = True

    return changed

def migrate_unheld_crypto_positions(data):
    """Reserve principal for investments created before wallet holding existed."""
    if not isinstance(data, dict):
        return False

    changed = False
    for record in data.values():
        if not isinstance(record, dict):
            continue
        positions = record.get("crypto_positions")
        if not isinstance(positions, dict):
            continue
        record_changed = False
        try:
            wallet = max(0, int(record.get("wallet", 0)))
        except (TypeError, ValueError):
            wallet = 0
        for position in positions.values():
            if not isinstance(position, dict) or "held_principal" in position:
                continue
            try:
                invested = max(0, int(float(position.get("invested", 0))))
            except (TypeError, ValueError):
                invested = 0
            # The old command left this amount in wallet. Reserve whatever
            # remains available without ever making the wallet negative.
            wallet -= min(wallet, invested)
            position["held_principal"] = invested
            record_changed = True
        if record_changed:
            record["wallet"] = wallet
            changed = True
    return changed

def save_local_backup(data):
    temp_file = f"{DATA_FILE}.tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp_file, DATA_FILE)

def load_data():
    """Load the shared economy store from Firebase."""
    try:
        data = db_ref.get()
        if isinstance(data, dict) and data:
            changed = migrate_legacy_currency_fields(data)
            changed = migrate_unheld_crypto_positions(data) or changed
            if changed:
                db_ref.set(data)
                save_local_backup(data)
            return data

        # Preserve the existing local economy the first time Firebase is used.
        local_data = load_local_backup()
        if local_data:
            migrate_legacy_currency_fields(local_data)
            migrate_unheld_crypto_positions(local_data)
            db_ref.set(local_data)
            save_local_backup(local_data)
            return local_data
        return {}
    except Exception as exc:
        raise RuntimeError(f"Firebase read failed: {exc}") from exc

def save_data(data):
    """Persist the live store to Firebase and keep a local recovery backup."""
    if "DATA" in globals() and data is not DATA:
        data = DATA
    with DATA_LOCK:
        try:
            db_ref.set(data)
            save_local_backup(data)
            if "ECONOMY_SETTINGS" in globals():
                ECONOMY_REF.set(ECONOMY_SETTINGS)
        except Exception as exc:
            # Never leave a failed mutation visible only in memory. Reload the
            # last committed Firebase state so a later balance command cannot
            # report coins that were not actually saved.
            try:
                committed = db_ref.get()
                DATA.clear()
                if isinstance(committed, dict):
                    DATA.update(committed)
                save_local_backup(DATA)
            except Exception as rollback_exc:
                print(f"⚠️ Could not restore committed Firebase state: {rollback_exc}")
            raise RuntimeError(f"Firebase write failed: {exc}") from exc

# Keep one in-memory copy for the lifetime of the bot. Commands mutate this
# store and persist it atomically after each economy change.
DATA = load_data()

COMMAND_CATEGORY_SETTINGS_KEY = "_command_category_settings"

class CategoryDisabled(commands.CommandError):
    def __init__(self, category, display_name):
        super().__init__(f"Category '{display_name}' is disabled")
        self.category = category
        self.display_name = display_name


def normalize_category(value):
    if not value:
        return None, None
    token = (value or "").strip().lower()
    if not token:
        return None, None
    category = CATEGORY_ALIASES.get(token, token)
    display_name = category.replace("-", " ").title()
    return category, display_name


def get_disabled_category_settings():
    settings = DATA.setdefault(COMMAND_CATEGORY_SETTINGS_KEY, {})
    if not isinstance(settings, dict):
        settings = {}
        DATA[COMMAND_CATEGORY_SETTINGS_KEY] = settings
    return settings


def get_command_category(command_name):
    if not command_name:
        return None
    return COMMAND_CATEGORY_MAP.get(command_name.lower())


def is_category_enabled(category):
    if not category:
        return True
    settings = get_disabled_category_settings()
    return not bool(settings.get(category))


async def ensure_command_category_allowed(ctx):
    if ctx.command is None:
        return
    if is_owner(ctx):
        return
    if ctx.command.name.lower() in {"on", "off", "help"}:
        return
    category = get_command_category(ctx.command.name)
    if not category:
        return
    if not is_category_enabled(category):
        display_name = category.replace("-", " ").title()
        raise CategoryDisabled(category, display_name)


async def set_category_state(ctx, category, enabled):
    settings = get_disabled_category_settings()
    if enabled:
        settings.pop(category, None)
    else:
        settings[category] = True
    save_data(DATA)
    return settings


# ==============================================
# 🛡️ GUILD MODERATION STATE
# ==============================================
SERVER_MODERATION_KEY = "_server_moderation"
SPAM_TRACKER = {}
RAID_JOIN_TRACKER = {}
SUSPICIOUS_USERS = {}
GUILD_INVITES_CACHE = {}  # { guild_id: { code: uses } }


def get_invite_store(guild_id):
    invites_data = DATA.setdefault("invites", {})
    g_data = invites_data.setdefault(str(guild_id), {
        "inviters": {},      # { user_id_str: { "regular": 0, "left": 0, "fake": 0 } }
        "members": {},       # { member_id_str: { "inviter_id": str, "code": str, "joined_at": ts, "is_fake": bool } }
        "code_inviters": {}, # { code: user_id_str }
    })
    g_data.setdefault("inviters", {})
    g_data.setdefault("members", {})
    g_data.setdefault("code_inviters", {})
    return g_data


async def fetch_and_cache_guild_invites(guild):
    """Fetch invites for a guild from Discord and cache usage counters."""
    if guild is None:
        return {}
    cache = {}
    g_store = get_invite_store(guild.id)
    try:
        if hasattr(guild, "invites"):
            invs = await guild.invites()
            for inv in invs:
                cache[inv.code] = inv.uses or 0
                if inv.inviter:
                    g_store["code_inviters"][inv.code] = str(inv.inviter.id)
            save_data(DATA)
    except Exception:
        pass
    GUILD_INVITES_CACHE[guild.id] = cache
    return cache


async def find_used_invite(guild):
    """Detect which invite code was used by comparing new vs cached usage counts."""
    if guild is None:
        return None, None
    old_cache = GUILD_INVITES_CACHE.get(guild.id, {})
    new_cache = await fetch_and_cache_guild_invites(guild)

    used_code = None
    inviter_id = None

    for code, uses in new_cache.items():
        old_uses = old_cache.get(code, 0)
        if uses > old_uses:
            used_code = code
            break

    g_store = get_invite_store(guild.id)
    if used_code:
        inviter_id = g_store["code_inviters"].get(used_code)

    return used_code, inviter_id


async def track_member_join_invite(member):
    """Record member join, determine inviter, update invite counts."""
    used_code, inviter_id = await find_used_invite(member.guild)
    g_store = get_invite_store(member.guild.id)

    inviter = None
    if inviter_id:
        try:
            inviter = member.guild.get_member(int(inviter_id)) or await bot.fetch_user(int(inviter_id))
        except Exception:
            inviter = None

    if inviter and str(inviter.id) == str(member.id):
        inviter = None
        inviter_id = None

    is_fake = False
    if getattr(member, "created_at", None):
        acc_age_seconds = (datetime.now(timezone.utc) - member.created_at).total_seconds()
        if acc_age_seconds < 3 * 86400:
            is_fake = True

    if inviter_id:
        inv_stats = g_store["inviters"].setdefault(str(inviter_id), {"regular": 0, "left": 0, "fake": 0})
        if is_fake:
            inv_stats["fake"] = inv_stats.get("fake", 0) + 1
        else:
            inv_stats["regular"] = inv_stats.get("regular", 0) + 1

    g_store["members"][str(member.id)] = {
        "inviter_id": str(inviter_id) if inviter_id else None,
        "code": used_code,
        "joined_at": time.time(),
        "is_fake": is_fake
    }
    save_data(DATA)

    inviter_net = 0
    if inviter_id:
        s = g_store["inviters"].get(str(inviter_id), {})
        inviter_net = s.get("regular", 0) - s.get("left", 0) - s.get("fake", 0)

    return inviter, inviter_net, used_code


async def track_member_leave_invite(member):
    if member.guild is None:
        return
    g_store = get_invite_store(member.guild.id)
    mem_record = g_store["members"].get(str(member.id))
    if mem_record and mem_record.get("inviter_id"):
        inviter_id = str(mem_record["inviter_id"])
        inv_stats = g_store["inviters"].setdefault(inviter_id, {"regular": 0, "left": 0, "fake": 0})
        inv_stats["left"] = inv_stats.get("left", 0) + 1
        save_data(DATA)


def get_guild_moderation_settings(guild):
    moderation = DATA.setdefault(SERVER_MODERATION_KEY, {})
    guild_id = str(guild.id)
    if not isinstance(moderation.get(guild_id), dict):
        moderation[guild_id] = {
            "antinuke": False,
            "antispam": False,
            "antiraid": False,
            "antibullying": False,
            "antibullying_action": "ban",
            "raid_join_window": 120,
            "raid_join_threshold": 5,
            "modlog_channel": None,
            "welcome_channel": None,
            "whitelist": [],
        }
    else:
        moderation[guild_id].setdefault("welcome_channel", None)
    return moderation[guild_id]


def format_account_age(created_at):
    if not created_at:
        return "Unknown"
    now = datetime.now(timezone.utc)
    diff = now - created_at
    days = diff.days
    if days < 1:
        hours = max(1, int(diff.total_seconds() // 3600))
        rel = f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif days < 30:
        rel = f"{days} day{'s' if days != 1 else ''} ago"
    elif days < 365:
        months = max(1, days // 30)
        rel = f"{months} month{'s' if months != 1 else ''} ago"
    else:
        years = max(1, days // 365)
        rel = f"{years} year{'s' if years != 1 else ''} ago"

    month = created_at.month
    day = created_at.day
    year = created_at.strftime("%y")
    return f"{rel} ({month}/{day}/{year})"


def get_member_position(guild, member):
    try:
        if hasattr(guild, "members") and guild.members:
            sorted_members = sorted([m for m in guild.members if getattr(m, "joined_at", None) is not None], key=lambda m: m.joined_at)
            pos = next((i + 1 for i, m in enumerate(sorted_members) if m.id == member.id), None)
            if pos is not None:
                return pos
    except Exception:
        pass
    return getattr(guild, "member_count", 1)


def build_welcome_embed(guild, member, inviter=None, inviter_net=0):
    position = get_member_position(guild, member)
    total_members = getattr(guild, "member_count", position)
    acc_age = format_account_age(getattr(member, "created_at", None))

    embed = discord.Embed(
        title=f"Welcome to {guild.name}.",
        color=discord.Color.from_rgb(47, 49, 54)
    )

    avatar_url = None
    if hasattr(member, "display_avatar") and member.display_avatar:
        avatar_url = member.display_avatar.url
    elif hasattr(member, "avatar_url"):
        avatar_url = member.avatar_url
    if not avatar_url:
        avatar_url = "https://cdn.discordapp.com/embed/avatars/0.png"

    embed.set_thumbnail(url=avatar_url)

    if inviter:
        inviter_str = f"{inviter.mention} (**{inviter_net}** invites)"
    else:
        inviter_str = "Unknown / Direct Join"

    embed.add_field(
        name="👤 User Profile",
        value=(
            f"↳ **Mention**: {member.mention}\n"
            f"↳ **Account Age**: {acc_age}\n"
            f"↳ **Invited By**: {inviter_str}"
        ),
        inline=False
    )

    embed.add_field(
        name="📊 Server Statistics",
        value=(
            f"↳ **Position**: #{position}\n"
            f"↳ **Total Members**: {total_members}"
        ),
        inline=False
    )

    return embed


def save_guild_moderation_settings(guild):
    save_data(DATA)


def parse_duration_to_seconds(time_str: str) -> int:
    if not time_str:
        return 0
    time_str = time_str.lower().strip()
    if time_str in ["off", "0", "none", "disable"]:
        return 0
    match = re.match(r"^(\d+)([s|m|h|d|w]?)$", time_str)
    if not match:
        raise ValueError("Invalid duration format. Use numbers with s, m, h, d, w (e.g., 10m, 2h, 1d).")
    val, unit = match.groups()
    val = int(val)
    if unit == 's':
        return val
    elif unit == 'm' or unit == '':
        return val * 60
    elif unit == 'h':
        return val * 3600
    elif unit == 'd':
        return val * 86400
    elif unit == 'w':
        return val * 604800
    return val * 60


def mark_suspicious_user(guild, user_id, reason):
    guild_id = str(guild.id)
    user_id = str(user_id)
    SUSPICIOUS_USERS.setdefault(guild_id, {}).setdefault(user_id, set()).add(reason)


async def ban_user_for_moderation(guild, user, reason):
    if user is None or user.bot or user.id == bot.user.id:
        return False
    if user.id == guild.owner_id:
        return False
    settings = get_guild_moderation_settings(guild)
    # Whitelist check
    if str(user.id) in {str(x) for x in settings.get("whitelist", [])}:
        return False
    # Role position check: do not attempt to ban users whose top role is >= bot's top role
    try:
        if hasattr(user, "top_role") and hasattr(guild.me, "top_role"):
            if getattr(user.top_role, "position", 0) >= getattr(guild.me.top_role, "position", 0):
                return False
    except Exception:
        # If we can't determine roles, continue but rely on permissions to prevent failures
        pass
    if not guild.me.guild_permissions.ban_members:
        return False
    try:
        await guild.ban(user, reason=reason)
    except (discord.Forbidden, discord.HTTPException):
        return False
    mark_suspicious_user(guild, user.id, reason)
    try:
        await log_moderation_action(guild, f"Banned {user} — {reason}")
    except Exception:
        pass
    return True


async def log_moderation_action(guild, text):
    """Send a moderation log to the configured modlog channel, or system channel."""
    try:
        settings = get_guild_moderation_settings(guild)
        channel_id = settings.get("modlog_channel")
        destination = None
        if channel_id:
            try:
                destination = guild.get_channel(int(channel_id))
            except Exception:
                destination = None
        if destination is None:
            destination = guild.system_channel
        if destination is None:
            return False
        if not destination.permissions_for(guild.me).send_messages:
            return False
        await destination.send(f"[Moderation] {text}")
        return True
    except Exception:
        return False


def message_looks_like_command(message):
    content = message.content or ""
    return any(content.casefold().startswith(prefix.casefold()) for prefix in PREFIX_VARIANTS)


def _disabled_store():
    return DATA.setdefault("disabled_categories", {})


def _normalize_category(name: str):
    if not name:
        return None
    n = name.strip().lower()
    if n in {"socials", "allsocials", "social"}:
        return "socials"
    if n in {"ig", "instagram", "insta"}:
        return "instagram"
    if n in {"fb", "facebook"}:
        return "facebook"
    return n


def is_category_disabled(guild, category: str):
    cat = _normalize_category(category)
    store = _disabled_store()
    gid = "global" if guild is None else str(guild.id)
    disabled = set(store.get(gid, []))
    # If overall socials disabled, treat specific socials as disabled
    if "socials" in disabled and cat in {"instagram", "facebook"}:
        return True
    return cat in disabled


def disable_category(guild, category: str):
    cat = _normalize_category(category)
    store = _disabled_store()
    gid = "global" if guild is None else str(guild.id)
    lst = set(store.get(gid, []))
    lst.add(cat)
    store[gid] = list(lst)
    save_data(DATA)


def enable_category(guild, category: str):
    cat = _normalize_category(category)
    store = _disabled_store()
    gid = "global" if guild is None else str(guild.id)
    lst = set(store.get(gid, []))
    if cat in lst:
        lst.remove(cat)
    store[gid] = list(lst)
    save_data(DATA)


def is_recent_spam_message(message, now):
    guild_id = str(message.guild.id)
    history = SPAM_TRACKER.setdefault(guild_id, {}).setdefault(message.author.id, deque(maxlen=8))
    history.append((now, (message.content or "").strip()))
    recent = [content for timestamp, content in history if timestamp >= now - 12]
    if len(recent) < 4:
        return False
    if len(set(recent)) <= 2:
        return True
    counts = {}
    for content in recent:
        counts[content] = counts.get(content, 0) + 1
        if counts[content] >= 3:
            return True
    return len(recent) >= 6


async def handle_antispam_message(message):
    if message.guild is None or message.author.bot:
        return False
    if booster_utils.is_server_booster(message.author, get_user(message.author.id), guild=message.guild):
        return False
    settings = get_guild_moderation_settings(message.guild)
    if not settings.get("antispam", False):
        return False
    if message_looks_like_command(message):
        return False
    if not message.content or not message.content.strip():
        return False
    if is_recent_spam_message(message, time.time()):
        try:
            await message.delete()
        except discord.HTTPException:
            pass
        mark_suspicious_user(message.guild, message.author.id, "spam")
        try:
            await message.channel.send(
                f"🚫 {message.author.mention}, spam is not allowed. Your message was removed."
            )
        except discord.HTTPException:
            pass
        try:
            if await ban_user_for_moderation(message.guild, message.author, "Anti-spam protection"):
                await message.channel.send(
                    f"🚨 {message.author.mention} has been banned for spam under anti-spam protection."
                )
        except Exception:
            pass
        try:
            await log_moderation_action(message.guild, f"Deleted spam message from {message.author} in #{message.channel.name}: {message.content}")
        except Exception:
            pass
        return True
    return False


BULLYING_PATTERNS = [
    r"\b(kill\s+your\s*self|kys|k\s*y\s*s)\b",
    r"\b(go\s+die|hope\s+you\s+die|wish\s+you\s+were\s+dead)\b",
    r"\b(nobody\s+likes\s+you|everyone\s+hates\s+you|you\s+are\s+worthless)\b",
    r"\b(kill\s+urself|go\s+hang\s+yourself|slash\s+your\s+wrists)\b",
    r"\b(retard|faggot|nigger|nigga|cunt|chink|spic)\b",
    r"\b(delete\s+your\s+life|end\s+your\s+life|die\s+in\s+a\s+fire)\b",
    r"\b(ugly\s+bitch|die\s+bitch|fat\s+ugly|ugly\s+slut)\b",
    r"\b(drink\s+bleach|hang\s+yourself|jump\ off\ a\ bridge)\b",
]


async def handle_antibullying_message(message):
    if message.guild is None or message.author.bot:
        return False
    settings = get_guild_moderation_settings(message.guild)
    if not settings.get("antibullying", False):
        return False
    if message_looks_like_command(message):
        return False
    content = (message.content or "").strip().lower()
    if not content:
        return False

    # Check against severe bullying / harassment / hate speech patterns
    detected = False
    matched_reason = "Bullying / Toxicity violation"

    for pattern in BULLYING_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            detected = True
            matched_reason = "Verified severe bullying, harassment, or hate speech"
            break

    if detected:
        # Delete the toxic message immediately
        try:
            await message.delete()
        except discord.HTTPException:
            pass

        mark_suspicious_user(message.guild, message.author.id, "bullying")

        # Warn in channel
        try:
            await message.channel.send(
                f"🛡️ 🚨 **Anti-Bullying System Triggered!**\n"
                f"{message.author.mention} was verified engaging in harmful, toxic, or bullying behavior.\n"
                f"The message was deleted and the user is being banned from the server!"
            )
        except discord.HTTPException:
            pass

        # Ban offending user
        banned = False
        try:
            banned = await ban_user_for_moderation(message.guild, message.author, f"Anti-Bullying Protection: {matched_reason}")
        except Exception:
            pass

        if not banned:
            try:
                if message.guild.me.guild_permissions.kick_members:
                    await message.guild.kick(message.author, reason=f"Anti-Bullying Protection: {matched_reason}")
            except Exception:
                pass

        # Log action to modlog
        try:
            await log_moderation_action(
                message.guild,
                f"🛡️ **Anti-Bullying Action:** Deleted toxic message from {message.author} ({message.author.id}) in #{message.channel.name}.\nContent: `{message.content}`\nStatus: User banned."
            )
        except Exception:
            pass

        return True

    return False


async def toggle_moderation_option(ctx, option, label, action):
    if ctx.guild is None:
        return await ctx.send(f"{label} can only be managed inside a server.")
    if ctx.author.id != ctx.guild.owner_id and not is_owner(ctx):
        return await ctx.send("Owner only.")

    settings = get_guild_moderation_settings(ctx.guild)
    normalized = (action or "status").casefold()
    if normalized in {"status", ""}:
        status = "ON" if settings.get(option) else "OFF"
        return await ctx.send(f"{label} is currently **{status}**.")
    if normalized in {"on", "enable", "true"}:
        settings[option] = True
    elif normalized in {"off", "disable", "false"}:
        settings[option] = False
    else:
        return await ctx.send(f"Use `uwu {option} on` or `uwu {option} off`.")
    save_guild_moderation_settings(ctx.guild)
    status = "ON" if settings.get(option) else "OFF"
    return await ctx.send(f"{label} is now **{status}**.")


def build_suspicious_user_ids(guild):
    return [int(user_id) for user_id in SUSPICIOUS_USERS.get(str(guild.id), {})]


def build_suspicious_user_names(guild):
    user_ids = build_suspicious_user_ids(guild)
    return [str(guild.get_member(user_id) or user_id) for user_id in user_ids]


async def ban_actor_from_audit_log(guild, action, target_id, description):
    settings = get_guild_moderation_settings(guild)
    if not settings.get("antinuke", False):
        return
    if not guild.me.guild_permissions.ban_members or not guild.me.guild_permissions.view_audit_log:
        return
    try:
        async for entry in guild.audit_logs(action=action, limit=5):
            if getattr(entry.target, "id", None) != target_id:
                continue
            actor = entry.user
            if actor is None:
                continue
            if actor.id in {guild.owner_id, bot.user.id}:
                return
            if str(actor.id) in {str(x) for x in get_guild_moderation_settings(guild).get("whitelist", [])}:
                return
            # Try banning the actor with a few retries in case of transient errors
            for attempt in range(1, 4):
                try:
                    banned = await ban_user_for_moderation(guild, actor, description)
                    if banned:
                        try:
                            await log_moderation_action(guild, f"Anti-nuke: banned {actor} after {description}")
                        except Exception:
                            pass
                        destination = guild.system_channel
                        if destination is not None:
                            try:
                                await destination.send(
                                    f"🚨 Anti-nuke: banned {actor.mention} after {description}."
                                )
                            except discord.HTTPException:
                                pass
                        break
                except Exception:
                    # transient failure — wait a bit and retry
                    try:
                        await asyncio.sleep(1)
                    except Exception:
                        pass
            return
    except discord.Forbidden:
        return


def delete_suspicious_messages(guild, user_ids, limit_per_channel=100):
    deleted = 0
    async def _cleanup_channel(channel):
        nonlocal deleted
        if not channel.permissions_for(guild.me).read_message_history:
            return
        if not channel.permissions_for(guild.me).manage_messages:
            return
        try:
            async for message in channel.history(limit=limit_per_channel):
                if message.author and message.author.id in user_ids:
                    try:
                        await message.delete()
                        deleted += 1
                    except discord.HTTPException:
                        pass
        except discord.Forbidden:
            pass
    async def _run():
        for channel in guild.text_channels:
            await _cleanup_channel(channel)
    return deleted, _run()


def is_spam_history_message(message):
    if message.guild is None or message.author.bot or not message.content:
        return False
    now = time.time()
    history = SPAM_TRACKER.setdefault(str(message.guild.id), {}).setdefault(message.author.id, deque(maxlen=8))
    history.append((now, (message.content or "").strip()))
    return is_recent_spam_message(message, now)


def get_recent_raid_suspects(guild):
    return [int(user_id) for user_id in SUSPICIOUS_USERS.get(str(guild.id), {}) if "raid" in SUSPICIOUS_USERS[str(guild.id)][user_id]]


def get_recent_spam_suspects(guild):
    return [int(user_id) for user_id in SUSPICIOUS_USERS.get(str(guild.id), {}) if "spam" in SUSPICIOUS_USERS[str(guild.id)][user_id]]


def get_recent_nuke_suspects(guild):
    return [int(user_id) for user_id in SUSPICIOUS_USERS.get(str(guild.id), {}) if "nuke" in SUSPICIOUS_USERS[str(guild.id)][user_id]]


def clear_suspects(guild):
    SUSPICIOUS_USERS.pop(str(guild.id), None)


def get_moderation_status_text(guild):
    settings = get_guild_moderation_settings(guild)
    return (
        f"Anti-nuke: {'ON' if settings.get('antinuke') else 'OFF'}\n"
        f"Anti-spam: {'ON' if settings.get('antispam') else 'OFF'}\n"
        f"Anti-raid: {'ON' if settings.get('antiraid') else 'OFF'}"
    )


def _replace_message_cleanup_placeholder(guild):
    return None


def format_suspect_names(guild, ids):
    return [str(guild.get_member(user_id) or user_id) for user_id in ids]


def _noop():
    return None


def quote(str_value):
    return str(str_value)


def safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def is_owner_or_server_owner(ctx):
    return ctx.author.id == ctx.guild.owner_id or is_owner(ctx)


def _safe_status(value):
    return "ON" if value else "OFF"


def _hardcode():
    pass


def _no_effect():
    return False


def _build_rollback_report(deleted, banned):
    return deleted, banned


def _placeholder():
    return None


def _unused():
    return None


def _dummy():
    return False


def _helper():
    return True


def _final_helper():
    return None


def _more_helpers():
    pass


def _cleanup():
    pass


def _final_cleanup():
    pass


def _unused_helper():
    pass


def _replacer():
    pass


def _internal():
    pass


def _double_check():
    return True


def _sanity():
    return True


def _last_helper():
    return None


def _final():
    return None


def _ghost():
    return False


# -----------------------------
# Audit-log hardening events
# -----------------------------
@bot.event
async def on_guild_role_update(before: discord.Role, after: discord.Role):
    """Detect when a role's permissions are escalated and respond if antinuke is enabled."""
    guild = after.guild
    settings = get_guild_moderation_settings(guild)
    if not settings.get("antinuke"):
        return
    old_perms = before.permissions
    new_perms = after.permissions
    dangerous = [
        "administrator",
        "ban_members",
        "manage_roles",
        "manage_guild",
        "kick_members",
    ]
    added = False
    for perm in dangerous:
        if not getattr(old_perms, perm, False) and getattr(new_perms, perm, False):
            added = True
            break
    if not added:
        return
    # Find the audit log entry for this role update and take action against the actor
    try:
        async for entry in guild.audit_logs(action=discord.AuditLogAction.role_update, limit=6):
            if getattr(entry.target, "id", None) != after.id:
                continue
            actor = entry.user
            if actor is None:
                return
            if str(actor.id) in {str(x) for x in settings.get("whitelist", [])}:
                return
            if actor.id in {guild.owner_id, bot.user.id}:
                return
            await ban_user_for_moderation(guild, actor, "role permission escalation")
            return
    except discord.Forbidden:
        return


@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    """Detect server boost events and role permission escalation (antinuke)."""
    # 1. Real-time Server Boost Event Detection
    was_boosting = getattr(before, "premium_since", None) is not None or any(getattr(r, "is_premium_subscriber", lambda: False)() for r in getattr(before, "roles", []))
    is_boosting = getattr(after, "premium_since", None) is not None or any(getattr(r, "is_premium_subscriber", lambda: False)() for r in getattr(after, "roles", []))

    if not was_boosting and is_boosting:
        # Member just boosted the server!
        user_data = get_user(after.id)
        user_data["wallet"] = user_data.get("wallet", 0) + 5_000_000_000_000
        save_data(DATA)

        # Broadcast congratulatory embed in system channel or first available text channel
        guild = after.guild
        channel = guild.system_channel
        if channel is None or not channel.permissions_for(guild.me).send_messages:
            for ch in guild.text_channels:
                if ch.permissions_for(guild.me).send_messages:
                    channel = ch
                    break

        if channel:
            embed = discord.Embed(
                title="⚡ NEW SERVER BOOST DETECTED!",
                description=f"🎉 **Thank you {after.mention} for boosting {guild.name}!**\n\n"
                            f"✨ You have automatically received a **+5,000,000,000,000 (5T) uwuncy** boost bonus!\n\n"
                            f"⚡ **Unlocked Booster Perks:**\n"
                            f"• `5T` Daily rewards (`uwu booster`)\n"
                            f"• **0 Cooldowns** on standard commands\n"
                            f"• **Link/Image permissions** in restricted channels\n"
                            f"• Exclusive access to `uwu booster shop`!",
                color=discord.Color.purple()
            )
            embed.set_thumbnail(url=str(after.display_avatar.url))
            embed.set_footer(text="Thank you for supporting our server!")
            try:
                await channel.send(embed=embed)
            except Exception:
                pass

    if before.roles == after.roles:
        return
    guild = after.guild
    settings = get_guild_moderation_settings(guild)

    if not settings.get("antinuke"):
        return
    added_roles = [r for r in after.roles if r not in before.roles]
    if not added_roles:
        return
    dangerous = [
        "administrator",
        "ban_members",
        "manage_roles",
        "manage_guild",
        "kick_members",
    ]
    escalated = False
    for role in added_roles:
        for perm in dangerous:
            if getattr(role.permissions, perm, False):
                escalated = True
                break
        if escalated:
            break
    if not escalated:
        return
    # Inspect who performed the role change
    try:
        async for entry in guild.audit_logs(action=discord.AuditLogAction.member_role_update, limit=8):
            if getattr(entry.target, "id", None) != after.id:
                continue
            actor = entry.user
            if actor is None:
                return
            if str(actor.id) in {str(x) for x in settings.get("whitelist", [])}:
                return
            if actor.id in {guild.owner_id, bot.user.id}:
                return
            await ban_user_for_moderation(guild, actor, "granted privileged role to member")
            return
    except discord.Forbidden:
        return


def _padding():
    return None


def _line():
    return None


def _point():
    return None


def _trail():
    return None


def _extra():
    return None


def _final_extra():
    return None


def _sandbox():
    return None


def _sandbox2():
    return None


def _sandbox3():
    return None


def _sandbox4():
    return None


def _sandbox5():
    return None


def _sandbox6():
    return None


def _sandbox7():
    return None


def _sandbox8():
    return None


def _sandbox9():
    return None


def _sandbox10():
    return None


def _sandbox11():
    return None


def _sandbox12():
    return None


def _sandbox13():
    return None


def _sandbox14():
    return None


def _sandbox15():
    return None


def _sandbox16():
    return None


def _sandbox17():
    return None


def _sandbox18():
    return None


def _sandbox19():
    return None


def _sandbox20():
    return None


def _sandbox21():
    return None


def _sandbox22():
    return None


def _sandbox23():
    return None


def _sandbox24():
    return None


def _sandbox25():
    return None


def _sandbox26():
    return None


def _sandbox27():
    return None


def _sandbox28():
    return None


def _sandbox29():
    return None


def _sandbox30():
    return None


def _sandbox31():
    return None


def _sandbox32():
    return None


def _sandbox33():
    return None


def _sandbox34():
    return None


def _sandbox35():
    return None


def _sandbox36():
    return None


def _sandbox37():
    return None


def _sandbox38():
    return None


def _sandbox39():
    return None


def _sandbox40():
    return None


def _sandbox41():
    return None


def _sandbox42():
    return None


def _sandbox43():
    return None


def _sandbox44():
    return None


def _sandbox45():
    return None


def _sandbox46():
    return None


def _sandbox47():
    return None


def _sandbox48():
    return None


def _sandbox49():
    return None


def _sandbox50():
    return None


def _sandbox51():
    return None


def _sandbox52():
    return None


def _sandbox53():
    return None


def _sandbox54():
    return None


def _sandbox55():
    return None


def _sandbox56():
    return None


def _sandbox57():
    return None


def _sandbox58():
    return None


def _sandbox59():
    return None


def _sandbox60():
    return None


def _sandbox61():
    return None


def _sandbox62():
    return None


def _sandbox63():
    return None


def _sandbox64():
    return None


def _sandbox65():
    return None


def _sandbox66():
    return None


def _sandbox67():
    return None


def _sandbox68():
    return None


def _sandbox69():
    return None


def _sandbox70():
    return None


def _sandbox71():
    return None


def _sandbox72():
    return None


def _sandbox73():
    return None


def _sandbox74():
    return None


def _sandbox75():
    return None


def _sandbox76():
    return None


def _sandbox77():
    return None


def _sandbox78():
    return None


def _sandbox79():
    return None


def _sandbox80():
    return None


def _sandbox81():
    return None


def _sandbox82():
    return None


def _sandbox83():
    return None


def _sandbox84():
    return None


def _sandbox85():
    return None


def _sandbox86():
    return None


def _sandbox87():
    return None


def _sandbox88():
    return None


def _sandbox89():
    return None


def _sandbox90():
    return None


def _sandbox91():
    return None


def _sandbox92():
    return None


def _sandbox93():
    return None


def _sandbox94():
    return None


def _sandbox95():
    return None


def _sandbox96():
    return None


def _sandbox97():
    return None


def _sandbox98():
    return None


def _sandbox99():
    return None


def _sandbox100():
    return None


def _sandbox101():
    return None


def _sandbox102():
    return None


def _sandbox103():
    return None


def _sandbox104():
    return None


def _sandbox105():
    return None


def _sandbox106():
    return None


def _sandbox107():
    return None


def _sandbox108():
    return None


def _sandbox109():
    return None


def _sandbox110():
    return None


def _sandbox111():
    return None


def _sandbox112():
    return None


def _sandbox113():
    return None


def _sandbox114():
    return None


def _sandbox115():
    return None


def _sandbox116():
    return None


def _sandbox117():
    return None


def _sandbox118():
    return None


def _sandbox119():
    return None


def _sandbox120():
    return None


def _sandbox121():
    return None


def _sandbox122():
    return None


def _sandbox123():
    return None


def _sandbox124():
    return None


def _sandbox125():
    return None


def _sandbox126():
    return None


def _sandbox127():
    return None


def _sandbox128():
    return None


def _sandbox129():
    return None


def _sandbox130():
    return None


def _sandbox131():
    return None


def _sandbox132():
    return None


def _sandbox133():
    return None


def _sandbox134():
    return None


def _sandbox135():
    return None


def _sandbox136():
    return None


def _sandbox137():
    return None


def _sandbox138():
    return None


def _sandbox139():
    return None


def _sandbox140():
    return None


def _sandbox141():
    return None


def _sandbox142():
    return None


def _sandbox143():
    return None


def _sandbox144():
    return None


def _sandbox145():
    return None


def _sandbox146():
    return None


def _sandbox147():
    return None


def _sandbox148():
    return None


def _sandbox149():
    return None


def _sandbox150():
    return None


def _sandbox151():
    return None


def _sandbox152():
    return None


def _sandbox153():
    return None


def _sandbox154():
    return None


def _sandbox155():
    return None


def _sandbox156():
    return None


def _sandbox157():
    return None


def _sandbox158():
    return None


def _sandbox159():
    return None


def _sandbox160():
    return None


def _sandbox161():
    return None


def _sandbox162():
    return None


def _sandbox163():
    return None


def _sandbox164():
    return None


def _sandbox165():
    return None


def _sandbox166():
    return None


def _sandbox167():
    return None


def _sandbox168():
    return None


def _sandbox169():
    return None


def _sandbox170():
    return None


def _sandbox171():
    return None


def _sandbox172():
    return None


def _sandbox173():
    return None


def _sandbox174():
    return None


def _sandbox175():
    return None


def _sandbox176():
    return None


def _sandbox177():
    return None


def _sandbox178():
    return None


def _sandbox179():
    return None


def _sandbox180():
    return None


def _sandbox181():
    return None


def _sandbox182():
    return None


def _sandbox183():
    return None


def _sandbox184():
    return None


def _sandbox185():
    return None


def _sandbox186():
    return None


def _sandbox187():
    return None


def _sandbox188():
    return None


def _sandbox189():
    return None


def _sandbox190():
    return None


# -----------------------------
# Admin utility & User profile commands
# -----------------------------
@bot.command(name="profile", aliases=["pfp_info", "whois", "prof"])
async def profile_cmd(ctx, member: discord.Member = None):
    """Show a user's account and server profile in a clean, formal format."""
    member = member or ctx.author
    if ctx.guild is None:
        created = member.created_at if hasattr(member, "created_at") else None
        return await ctx.send(f"User: {member}\nCreated: {created}")

    position = get_member_position(ctx.guild, member)
    total_members = getattr(ctx.guild, "member_count", position)
    acc_age = format_account_age(getattr(member, "created_at", None))
    joined_at = getattr(member, "joined_at", None)
    joined_str = joined_at.strftime("%b %d, %Y") if joined_at else "Unknown"

    avatar_url = None
    if hasattr(member, "display_avatar") and member.display_avatar:
        avatar_url = member.display_avatar.url
    elif hasattr(member, "avatar_url"):
        avatar_url = member.avatar_url
    if not avatar_url:
        avatar_url = "https://cdn.discordapp.com/embed/avatars/0.png"

    # Inviter lookup
    g_store = get_invite_store(ctx.guild.id)
    mem_record = g_store.get("members", {}).get(str(member.id))
    if mem_record and mem_record.get("inviter_id"):
        inviter_id = mem_record["inviter_id"]
        inviter_obj = ctx.guild.get_member(int(inviter_id))
        inviter_str = inviter_obj.mention if inviter_obj else f"<@{inviter_id}>"
    else:
        inviter_str = "Unknown / Direct Join"

    embed = discord.Embed(
        title=f"User Profile — {member.display_name}",
        color=discord.Color.from_rgb(47, 49, 54)
    )
    embed.set_thumbnail(url=avatar_url)

    embed.add_field(
        name="👤 User Information",
        value=(
            f"↳ **User**: {member.mention} (`{member.id}`)\n"
            f"↳ **Account Age**: {acc_age}\n"
            f"↳ **Joined Server**: {joined_str}\n"
            f"↳ **Invited By**: {inviter_str}"
        ),
        inline=False
    )

    top_role = member.top_role.mention if member.top_role and member.top_role.name != "@everyone" else "None"
    roles = [r.mention for r in member.roles if r.name != "@everyone"]
    roles_str = ", ".join(roles[:5]) + (f" (+{len(roles)-5} more)" if len(roles) > 5 else "") if roles else "None"

    embed.add_field(
        name="📊 Server Statistics",
        value=(
            f"↳ **Position**: #{position} of {total_members}\n"
            f"↳ **Top Role**: {top_role}\n"
            f"↳ **Roles**: {roles_str}"
        ),
        inline=False
    )

    member_data = get_user(member.id)
    charisma = member_data.get("charisma", 0)
    partner_id = member_data.get("marriage_partner_id")
    if partner_id:
        marriage_level = member_data.get("marriage_level", 0)
        partner_data = get_user(partner_id)
        shared_wealth = member_data.get("wallet", 0) + member_data.get("bank", 0) + partner_data.get("wallet", 0) + partner_data.get("bank", 0)
        marriage_str = f"<@{partner_id}> (Level {marriage_level}) • 💰 Household: `{format_coins(shared_wealth)}` uwuncy"
    else:
        marriage_str = "Single"

    embed.add_field(
        name="💖 Social & Status",
        value=(
            f"↳ **Charisma EXP**: {charisma:,}\n"
            f"↳ **Marriage Status**: {marriage_str}"
        ),
        inline=False
    )

    await ctx.send(embed=embed)


@bot.command(name="avatar", aliases=[",", "av", "pfp"])
async def avatar_cmd(ctx, member: discord.Member = None):
    """Fetch full-resolution profile avatar for a user."""
    member = member or ctx.author

    avatar = member.display_avatar if hasattr(member, "display_avatar") and member.display_avatar else getattr(member, "avatar_url", None)
    avatar_url = str(avatar.url) if hasattr(avatar, "url") else (str(avatar) if avatar else "https://cdn.discordapp.com/embed/avatars/0.png")

    embed = discord.Embed(
        title=f"Avatar — {member.display_name}",
        color=discord.Color.from_rgb(47, 49, 54)
    )
    embed.set_image(url=avatar_url)
    embed.description = f"[Direct Link]({avatar_url})"
    await ctx.send(embed=embed)


@bot.command(name="banner", aliases=["userbanner", "profilebanner"])
async def banner_cmd(ctx, member: discord.Member = None):
    """Fetch full-resolution profile banner for a user."""
    member = member or ctx.author

    try:
        user_obj = await bot.fetch_user(member.id)
    except Exception:
        user_obj = member

    banner = getattr(user_obj, "banner", None)
    if not banner or not getattr(banner, "url", None):
        return await ctx.send(f"❌ **{member.display_name}** does not have a custom profile banner.")

    banner_url = banner.url
    embed = discord.Embed(
        title=f"Banner — {member.display_name}",
        color=discord.Color.from_rgb(47, 49, 54)
    )
    embed.set_image(url=banner_url)
    embed.description = f"[Direct Link]({banner_url})"
    await ctx.send(embed=embed)


# -----------------------------
# Social lookup commands (best-effort)
# -----------------------------
async def _fetch_html(url, headers=None, timeout=10):
    headers = headers or {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/125.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=timeout) as resp:
                if resp.status != 200:
                    return None, resp.status
                text = await resp.text()
                return text, resp.status
    except Exception:
        return None, None


def _extract_og_meta(html, prop):
    m = re.search(rf'<meta[^>]+property=["\']{re.escape(prop)}["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
    if m:
        return unescape(m.group(1)).strip()
    # Try name= variant
    m = re.search(rf'<meta[^>]+name=["\']{re.escape(prop)}["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
    if m:
        return unescape(m.group(1)).strip()
    return None


def _parse_counts_from_description(desc):
    if not desc:
        return {}, None
    # Common Instagram format: "1,234 Followers, 56 Following, 78 Posts - See Instagram..."
    counts = {}
    m = re.search(r'([\d,\.]+)\s+Followers', desc, re.I)
    if m:
        counts['followers'] = m.group(1)
    m = re.search(r'([\d,\.]+)\s+Following', desc, re.I)
    if m:
        counts['following'] = m.group(1)
    m = re.search(r'([\d,\.]+)\s+Posts', desc, re.I)
    if m:
        counts['posts'] = m.group(1)
    return counts, desc


@bot.command(name='ig', aliases=[',ig'])
async def ig_cmd(ctx, identifier: str):
    """Lookup an Instagram profile by username or URL (best-effort)."""
    # Check owner-disabled categories
    if is_category_disabled(ctx.guild, 'socials') or is_category_disabled(ctx.guild, 'instagram'):
        owner_name = ctx.guild.owner if ctx.guild else None
        who = ctx.author.display_name if ctx.author else f"<@{BOT_OWNER_ID}>"
        embed = discord.Embed(
            description=f"**Socials have been turned OFF by {who}**",
            color=discord.Color.gold(),
        )
        return await ctx.send(embed=embed)
    # extract username
    username = identifier.strip()
    if 'instagram.com' in username:
        # get last non-empty path part
        parts = re.split(r'[/?#]+', username)
        parts = [p for p in parts if p]
        if parts:
            username = parts[-1]
    url = f"https://www.instagram.com/{username}/"
    try:
        async with ctx.typing():
            # Try API lookup if configured
            counts = {}
            full_profile = {}
            raw = None
            api_result = await social_utils.try_instagram_api(username)
            if api_result and isinstance(api_result, dict):
                full_profile = api_result
                counts = {
                    k: api_result.get(k)
                    for k in ('followers', 'following', 'posts')
                    if api_result.get(k) is not None
                }
                raw = api_result.get('biography')
            else:
                html, status = await social_utils.fetch_html(url)
                if not html:
                    status_text = f"HTTP {status}" if status else "network error"
                    has_token = bool(social_utils.get_apify_tokens())
                    token_tip = "" if has_token else "\n💡 **Tip**: Set `APIFY_API_TOKEN` environment variable to use Apify for Instagram lookups."
                    return await ctx.send(
                        f"❌ Could not fetch Instagram profile for **@{username}**. Instagram blocked the request ({status_text}).{token_tip}"
                    )
                image = social_utils.extract_og_meta(html, 'og:image')
                desc = social_utils.extract_og_meta(html, 'og:description') or social_utils.extract_og_meta(html, 'description')
                raw = desc
                # Try structured JSON first, but fall back to regex-based extractor
                shared = social_utils.extract_window_shared_data(html) or social_utils.extract_json_ld(html)
                if shared:
                    try:
                        full_profile = social_utils.get_instagram_profile_from_shared_data(shared) or {}
                        counts = {
                            k: full_profile.get(k)
                            for k in ('followers', 'following', 'posts')
                            if full_profile.get(k) is not None
                        }
                    except Exception:
                        full_profile = {}
                        counts = {}
                if not counts:
                    counts = social_utils.get_instagram_counts_from_html(html) or {}
                if not counts and desc:
                    parsed_c, _ = social_utils.parse_counts_from_description(desc)
                    counts = parsed_c or {}
                if not full_profile:
                    full_profile = social_utils.get_instagram_profile_from_html(html) or {}
                if not raw:
                    raw = full_profile.get('biography')

            # Ensure we retrieved valid profile data before sending embed
            has_valid_info = bool(
                full_profile.get('name') or
                full_profile.get('profile_pic_url') or
                full_profile.get('biography') or
                (isinstance(counts, dict) and any(v for v in counts.values() if v is not None))
            )
            if not has_valid_info:
                return await ctx.send(
                    f"❌ Could not fetch Instagram profile for **@{username}**. The account may be private, non-existent, or Instagram blocked the request."
                )
            display_name = full_profile.get('name') or username
            is_private = bool(full_profile.get('is_private'))
            lock_suffix = " 🔒" if is_private else ""

            if full_profile.get('name') and full_profile['name'] != username:
                title_text = f"{full_profile['name']} (@{username}){lock_suffix}"
            else:
                title_text = f"@{username}{lock_suffix}"

            embed = discord.Embed(
                title=title_text,
                url=url,
                color=discord.Color.from_rgb(43, 45, 49)
            )

            avatar_url = full_profile.get('profile_pic_url')
            if avatar_url:
                embed.set_author(name=display_name, icon_url=avatar_url, url=url)
            else:
                embed.set_author(name=display_name, url=url)

            if avatar_url:
                embed.set_thumbnail(url=avatar_url)

            desc_parts = []
            if raw:
                desc_parts.append(raw)
            if full_profile.get('external_url'):
                ext_url = full_profile['external_url']
                desc_parts.append(f"🔗 [{ext_url}]({ext_url})")

            if desc_parts:
                desc_text = "\n".join(desc_parts)
                embed.description = (desc_text[:1900] + '...') if len(desc_text) > 1900 else desc_text

            def fmt_num(val):
                if val is None:
                    return "0"
                val_str = str(val).replace(',', '').strip()
                if val_str.isdigit():
                    return f"{int(val_str):,}"
                return str(val)

            posts_cnt = fmt_num(counts.get('posts'))
            following_cnt = fmt_num(counts.get('following'))
            followers_cnt = fmt_num(counts.get('followers'))

            embed.add_field(name="Posts", value=posts_cnt, inline=True)
            embed.add_field(name="Following", value=following_cnt, inline=True)
            embed.add_field(name="Followers", value=followers_cnt, inline=True)

            ig_icon_url = "https://cdn-icons-png.flaticon.com/512/174/174855.png"
            embed.set_footer(text="Instagram", icon_url=ig_icon_url)
            await ctx.send(embed=embed)
    except Exception as exc:
        print(f"Error in ig_cmd: {exc}")


@bot.command(name='fb', aliases=[',fb'])
async def fb_cmd(ctx, identifier: str):
    """Lookup a Facebook page or profile by URL or username."""
    if is_category_disabled(ctx.guild, 'socials') or is_category_disabled(ctx.guild, 'facebook'):
        who = ctx.author.display_name if ctx.author else f"<@{BOT_OWNER_ID}>"
        embed = discord.Embed(
            description=f"**Socials have been turned OFF by {who}**",
            color=discord.Color.gold(),
        )
        return await ctx.send(embed=embed)

    raw_input = identifier.strip()
    username = raw_input
    if 'facebook.com' in username:
        parts = re.split(r'[/?#]+', username)
        parts = [p for p in parts if p and p not in {'http:', 'https:', 'www.facebook.com', 'm.facebook.com', 'facebook.com'}]
        if parts:
            username = parts[0]
    username = username.lstrip('@')
    url = f"https://www.facebook.com/{username}"

    def fmt_num(val):
        if val is None:
            return "0"
        val_str = str(val).replace(',', '').strip()
        if val_str.isdigit():
            return f"{int(val_str):,}"
        return str(val)

    try:
        async with ctx.typing():
            api_result = await social_utils.try_facebook_api(raw_input)
            if not api_result or not isinstance(api_result, dict):
                # Try fallback HTML scraping
                html, status = await social_utils.fetch_html(f"https://m.facebook.com/{username}")
                if html:
                    profile = social_utils.get_facebook_profile_from_html(html)
                    if profile and (profile.get('name') or profile.get('profile_pic_url') or profile.get('biography')):
                        api_result = profile

            has_valid_info = bool(
                isinstance(api_result, dict) and (
                    api_result.get('name') or
                    api_result.get('profile_pic_url') or
                    api_result.get('biography') or
                    api_result.get('followers') or
                    api_result.get('likes')
                )
            )

            if not has_valid_info:
                return await ctx.send(
                    f"❌ Could not fetch Facebook profile for **{username}**. The account may be private, non-existent, or Facebook blocked the request."
                )

            title_name = api_result.get('name') or username
            user_handle = api_result.get('username') or username
            if title_name.lower() != user_handle.lower():
                title_text = f"{title_name} ({user_handle})"
            else:
                title_text = title_name

            profile_url = api_result.get('url') or url
            embed = discord.Embed(
                title=title_text,
                url=profile_url,
                color=discord.Color.from_rgb(24, 119, 242)
            )

            avatar_url = api_result.get('profile_pic_url')
            if avatar_url:
                embed.set_author(name=title_name, icon_url=avatar_url, url=profile_url)
                embed.set_thumbnail(url=avatar_url)
            else:
                embed.set_author(name=title_name, url=profile_url)

            desc_parts = []
            if api_result.get('biography'):
                desc_parts.append(api_result['biography'])
            if api_result.get('categories'):
                cats = api_result['categories']
                if isinstance(cats, list) and cats:
                    desc_parts.append(f"🏷️ **Category:** {', '.join(cats)}")
            if api_result.get('work'):
                desc_parts.append(f"💼 {api_result['work']}")
            if api_result.get('education'):
                desc_parts.append(f"🎓 {api_result['education']}")
            if api_result.get('city'):
                desc_parts.append(f"📍 {api_result['city']}")

            if desc_parts:
                desc_text = "\n".join(desc_parts)
                embed.description = (desc_text[:1900] + '...') if len(desc_text) > 1900 else desc_text

            if api_result.get('followers') is not None:
                embed.add_field(name="Followers", value=fmt_num(api_result['followers']), inline=True)
            if api_result.get('likes') is not None:
                embed.add_field(name="Likes", value=fmt_num(api_result['likes']), inline=True)

            fb_icon_url = "https://cdn-icons-png.flaticon.com/512/124/124010.png"
            embed.set_footer(text="Facebook", icon_url=fb_icon_url)
            await ctx.send(embed=embed)
    except Exception as exc:
        print(f"Error in fb_cmd: {exc}")


@bot.command(name='apify', aliases=[',apify', 'apifybalance', ',apifybalance', 'apifystats', ',apifystats'])
async def apify_cmd(ctx):
    """Check remaining balance and monthly usage for all configured Apify tokens."""
    try:
        async with ctx.typing():
            loop = asyncio.get_running_loop()
            stats = await loop.run_in_executor(None, social_utils.check_apify_balances)
            if not stats:
                return await ctx.send("❌ No Apify tokens found or configured.")

            embed = discord.Embed(
                title="⚡ Apify Accounts & Token Balances",
                description="Status and remaining monthly balance across all configured accounts:",
                color=discord.Color.blue()
            )

            total_remaining = 0.0
            total_spent = 0.0
            total_limit = 0.0

            for item in stats:
                idx = item["index"]
                uname = item["username"]
                token = item["masked_token"]
                status = item["status"]
                spent = item["spent_usd"]
                limit = item["limit_usd"]
                rem = item["remaining_usd"]

                total_spent += spent
                total_limit += limit
                total_remaining += rem

                icon = "🟢" if "ACTIVE" in status else "🔴"
                val = f"👤 **Account**: @{uname}\n" \
                      f"🔑 **Key**: `{token}`\n" \
                      f"💰 **Spent**: `${spent:.4f}` / `${limit:.2f}`\n" \
                      f"💵 **Remaining**: `${rem:.4f}`\n" \
                      f"📌 **Status**: {status}"
                embed.add_field(name=f"{icon} Account #{idx}", value=val, inline=False)

            embed.set_footer(
                text=f"Total Balance Available: ${total_remaining:.4f} / ${total_limit:.2f} across {len(stats)} accounts"
            )
            await ctx.send(embed=embed)
    except Exception as exc:
        print(f"Error in apify_cmd: {exc}")
        await ctx.send(f"An error occurred while fetching Apify balances: `{exc}`")





@bot.command(name="boosters", aliases=[",boosters", "boosterlist", ",boosterlist", "booststatus", ",booststatus", "boosterslist"])
async def boosters_cmd(ctx):
    """View all active Server Boosters in this server, current boost tier, and booster status."""
    guild = ctx.guild
    if guild is None:
        return await ctx.send("❌ This command can only be used inside a Discord server!")

    boosters = booster_utils.get_guild_boosters(guild)
    boost_count = getattr(guild, "premium_subscription_count", len(boosters))
    tier = getattr(guild, "premium_tier", 0)

    tier_reqs = {0: "2 boosts for Level 1", 1: "7 boosts for Level 2", 2: "14 boosts for Level 3", 3: "MAX LEVEL REACHED! 🎉"}
    next_goal = tier_reqs.get(tier, "MAX LEVEL")

    embed = discord.Embed(
        title=f"⚡ {guild.name} — Server Boosters & Status",
        description=f"**Server Boost Level:** Tier {tier} ({boost_count} total boosts)\n"
                    f"**Next Goal:** {next_goal}\n"
                    f"**Active Boosters Count:** `{len(boosters)}`",
        color=discord.Color.purple()
    )

    if boosters:
        lines = []
        for idx, member in enumerate(boosters, 1):
            boost_since = getattr(member, "premium_since", None)
            since_str = f"since <t:{int(boost_since.timestamp())}:R>" if boost_since else "Active Booster"
            count = booster_utils.get_user_boost_count(member)
            lines.append(f"`{idx}.` {member.mention} ({member.display_name}) — **{count} Boost{'s' if count > 1 else ''}** ({since_str})")

        embed.add_field(
            name="💎 Active Server Boosters",
            value="\n".join(lines[:20]),
            inline=False
        )
        if len(lines) > 20:
            embed.set_footer(text=f"And {len(lines) - 20} more boosters! Thank you everyone for supporting {guild.name}!")
        else:
            embed.set_footer(text="Boost this server to unlock 5T daily uwuncy, 0 cooldowns, and Booster Shop!")
    else:
        embed.add_field(
            name="💎 Active Server Boosters",
            value="No active boosters detected yet on this server!\nBe the first to boost by using Discord's Server Boost button to claim **5T daily uwuncy** and exclusive perks!",
            inline=False
        )

    return await ctx.send(embed=embed)


@bot.command(name="setbooster", aliases=[",setbooster", "boosteradd", "boosterremove"])
async def setbooster_cmd(ctx, target: discord.Member = None, status: str = "on"):
    """Admin command to grant or revoke server booster status manually."""
    if not is_owner(ctx) and not (ctx.guild and ctx.author.guild_permissions.administrator):
        return await ctx.send("❌ Only Administrators or Bot Owners can use this command!")
    if target is None:
        target = ctx.author

    u_data = get_user(target.id)
    state = status.lower() in ("on", "true", "enable", "add", "yes", "1")
    u_data["is_booster"] = state
    save_data(DATA)

    if state:
        await ctx.send(f"⚡ Granted **Server Booster** status & VIP perks to {target.mention}! They can now use `{get_prefix()}help` for the VIP Booster Menu!")
    else:
        await ctx.send(f"🚫 Revoked **Server Booster** status from {target.mention}.")


@bot.command(name="booster", aliases=[",booster", "boosterclaim", ",boosterclaim", "boostershop", ",boostershop", "uwubooster"])
async def booster_cmd(ctx, action: str = None, *, item_arg: str = None):
    """Server Booster daily rewards, benefits, and Booster Shop."""
    user = get_user(ctx.author.id)
    invoked_alias = ctx.invoked_with.lower() if ctx.invoked_with else ""

    if invoked_alias in ("boostershop", ",boostershop") and not action:
        action = "shop"

    is_booster = booster_utils.is_server_booster(ctx.author, user, guild=ctx.guild)
    if is_booster and not user.get("is_booster"):
        user["is_booster"] = True
        save_data(DATA)

    # Default action: claim or show status
    if not action or action.lower() in ("claim", "daily", "get", "reward"):
        if not is_booster:
            embed = discord.Embed(
                title="💎 Server Booster Perks & Exclusive Rewards",
                description="This command is exclusively reserved for **Server Boosters**! Boost this server to unlock incredible perks:",
                color=discord.Color.purple()
            )
            embed.add_field(
                name="⚡ Server Booster Benefits",
                value="• 💰 **5,000,000,000,000 (5T) Base Daily Reward**\n• 📈 **Stacking Multipliers** (2 Boosts = 2×, 3 Boosts = 3×)\n• ⚡ **No Cooldowns** on normal commands!\n• 🖼️ **Link & Image Permission** in restricted channels!\n• 📅 **Auto-Claim Pass** eligibility\n• 🛍️ **Access to Exclusive Booster Shop**",
                inline=False
            )
            embed.add_field(
                name="🛍️ Booster Shop Preview",
                value="Type `uwu booster shop` to view all exclusive booster shop items!",
                inline=False
            )
            embed.set_footer(text="Boost our server today to start claiming 5T daily uwuncy!")
            return await ctx.send(embed=embed)

        # Check 24h cooldown
        now = time.time()
        last_claim = user.get("last_booster_claim", 0)
        cooldown_time = 86400  # 24 hours strictly

        if now - last_claim < cooldown_time:
            rem_sec = int(cooldown_time - (now - last_claim))
            hours = rem_sec // 3600
            mins = (rem_sec % 3600) // 60
            embed = discord.Embed(
                title="⏳ Daily Booster Reward on Cooldown",
                description=f"You have already claimed your daily booster reward!\n\n⏰ Please wait **{hours}h {mins}m** before claiming again.\n💡 *Hint: You can buy a `Cooldown Skip` in `uwu booster shop` to claim again immediately!*",
                color=discord.Color.gold()
            )
            return await ctx.send(embed=embed)

        # Calculate reward
        boost_count = booster_utils.get_user_boost_count(ctx.author, user)
        total_reward, breakdown = booster_utils.calculate_booster_daily_reward(user, boost_count)

        user["wallet"] = user.get("wallet", 0) + total_reward
        user["last_booster_claim"] = now
        save_data(DATA)

        embed = discord.Embed(
            title="⚡ Server Booster Daily Reward Claimed!",
            description=f"Thank you for boosting **{ctx.guild.name if ctx.guild else 'our server'}**! Here is your daily reward:",
            color=discord.Color.green()
        )
        embed.add_field(name="💵 Base Reward", value="`5,000,000,000,000 uwuncy (5T)`", inline=True)
        embed.add_field(name="📈 Boost Stack", value=f"`{breakdown['count_mult']}×` ({boost_count} Boost{'s' if boost_count > 1 else ''})", inline=True)
        if breakdown['perm_mult'] > 1.0:
            embed.add_field(name="💎 Perm Bonus", value=f"`{breakdown['perm_mult']}×`", inline=True)
        if breakdown['pass_mult'] > 1.0:
            embed.add_field(name="📈 Pass Multiplier", value=f"`{breakdown['pass_mult']}×`", inline=True)

        embed.add_field(
            name="🎁 Total Earned",
            value=f"**+{booster_utils.format_trillion(total_reward)} uwuncy**",
            inline=False
        )
        embed.add_field(
            name="💳 New Wallet Balance",
            value=f"**{booster_utils.format_trillion(user['wallet'])} uwuncy**",
            inline=False
        )
        embed.set_footer(text="Cooldown: Strictly 24 hours per user. Thank you for supporting the server!")
        return await ctx.send(embed=embed)

    elif action.lower() in ("shop", "store", "catalog", "items"):
        if not is_booster:
            return await ctx.send("❌ The Booster Shop is exclusively for **Server Boosters**! Boost the server or buy Permanent Shop Access to unlock.")

        embed = discord.Embed(
            title="🛍️ Exclusive Server Booster Shop",
            description="All items are exclusively purchasable by **Server Boosters**!\nUse `uwu booster buy <item_id>` to purchase.",
            color=discord.Color.purple()
        )

        # Group by category
        categories = {}
        for item_id, item in booster_utils.BOOSTER_SHOP_ITEMS.items():
            cat = item["category"]
            categories.setdefault(cat, []).append(item)

        for cat, items in categories.items():
            val_lines = []
            for it in items:
                price_fmt = booster_utils.format_trillion(it["price"])
                val_lines.append(f"{it['icon']} **{it['name']}** (`{it['id']}`) — **{price_fmt}**\n*{it['desc']}*")
            embed.add_field(name=f"━━ {cat} ━━", value="\n\n".join(val_lines), inline=False)

        embed.set_footer(text=f"Your Balance: {booster_utils.format_trillion(user.get('wallet', 0))} uwuncy | Cooldown Skip = Instant claim!")
        return await ctx.send(embed=embed)

    elif action.lower() in ("buy", "purchase"):
        if not is_booster:
            return await ctx.send("❌ You must be a **Server Booster** to buy items from the Booster Shop!")

        if not item_arg:
            return await ctx.send("❌ Please specify an item ID to buy! Example: `uwu booster buy cooldown_skip` or `uwu booster buy 2x_earnings_pass` ")

        item_id = item_arg.lower().strip()
        if item_id not in booster_utils.BOOSTER_SHOP_ITEMS:
            return await ctx.send("❌ Invalid item ID! Type `uwu booster shop` to see all valid item IDs.")

        item = booster_utils.BOOSTER_SHOP_ITEMS[item_id]
        price = item["price"]

        if user.get("wallet", 0) < price:
            return await ctx.send(f"❌ You need **{booster_utils.format_trillion(price)} uwuncy** to buy **{item['name']}**! You currently have {booster_utils.format_trillion(user.get('wallet', 0))}.")

        # Deduct price
        user["wallet"] -= price

        # Apply purchase
        if item_id == "cooldown_skip":
            user["last_booster_claim"] = 0
            msg = f"⏱️ **Cooldown Skipped!** Reset your daily booster cooldown. You can use `uwu booster` to claim your daily 5T+ reward again right now!"
        elif item_id == "lump_sum_bonus":
            now = time.time()
            if now - user.get("last_lump_sum", 0) < 7 * 86400:
                user["wallet"] += price
                return await ctx.send("❌ You can only purchase the Lump Sum Bonus once every 7 days!")
            user["wallet"] += 5_000_000_000_000
            user["last_lump_sum"] = now
            msg = f"💵 **Lump Sum Claimed!** Added **+5,000,000,000,000 (5T) uwuncy** directly to your wallet!"
        elif item_id == "gift_token":
            inv = user.setdefault("inventory", [])
            inv.append("gift_token")
            msg = f"🕹️ **Gift Token Acquired!** Added a Gift Token to your inventory."
        elif "duration_days" in item:
            passes = user.setdefault("booster_passes", {})
            dur = item["duration_days"] * 86400
            now = time.time()
            cur = passes.get(item_id, 0)
            passes[item_id] = max(now, cur) + dur
            msg = f"🎉 **{item['icon']} {item['name']} Activated!** Valid for **{item['duration_days']} days**."
        else:
            inv = user.setdefault("inventory", [])
            if item_id in inv and not item.get("stackable"):
                user["wallet"] += price
                return await ctx.send(f"❌ You already own the permanent item **{item['name']}**!")
            inv.append(item_id)
            msg = f"💎 **{item['icon']} {item['name']} Unlocked!** Permanent booster perk added to your account!"

        save_data(DATA)

        embed = discord.Embed(
            title="🛍️ Booster Shop Purchase Successful!",
            description=msg,
            color=discord.Color.green()
        )
        embed.add_field(name="💰 Amount Spent", value=f"`{booster_utils.format_trillion(price)} uwuncy`", inline=True)
        embed.add_field(name="💳 Remaining Wallet", value=f"`{booster_utils.format_trillion(user['wallet'])} uwuncy`", inline=True)
        return await ctx.send(embed=embed)

    else:
        return await ctx.send("❌ Unknown booster subcommand! Available: `uwu booster`, `uwu booster shop`, `uwu booster buy <item_id>`")


async def _music_play_next(ctx, guild_id: str):

    await play_next_track(guild_id)


@bot.command(name='play', aliases=['!play', 'music', 'p'])
async def play_cmd(ctx, *, query: str):
    """Play a song or playlist from YouTube, Spotify, or Apple Music."""
    if is_category_disabled(ctx.guild, 'music'):
        return await ctx.send("**Music commands are currently disabled.**")
    if yt_dlp is None:
        return await ctx.send("⚠️ Music playback requires `yt-dlp`. Please install it in requirements.txt.")

    # Suppress link embeds on trigger message to prevent Spotify/YouTube 30s preview iframe widget in text chat
    try:
        await ctx.message.edit(suppress=True)
    except Exception:
        pass

    voice = await get_voice_connection(ctx)
    if voice is None:
        return

    state = get_music_state(ctx.guild.id)
    lock = get_music_lock(ctx.guild.id)

    try:
        result = await create_music_source(query)
    except Exception as exc:
        return await ctx.send(f"❌ Could not fetch music: {exc}")

    entries = result if isinstance(result, list) else [result]
    first = entries[0]
    queue_count = len(entries)

    v_channel_name = voice.channel.name if voice.channel else "Voice Channel"

    should_play = False
    async with lock:
        state["queue"].extend(entries)
        if not voice.is_playing() and not voice.is_paused() and state["current"] is None:
            should_play = True

    if should_play:
        await play_next_track(str(ctx.guild.id))
        cur = state.get("current") or first
        first_title = cur.get("title", "Unknown Track")
        uploader = cur.get("uploader", "Unknown")
        if queue_count == 1:
            await ctx.send(f"🎶 **Now Auto-Playing in {v_channel_name}:** **{first_title}**\n🔊 *Full high-quality track streaming directly in your Voice Channel!*")
        else:
            await ctx.send(f"🎶 **Now Auto-Playing in {v_channel_name}:** **{first_title}**\n✅ Added playlist with **{queue_count}** full songs to queue.")
    else:
        if queue_count == 1:
            await ctx.send(f"✅ Added to queue: **{first.get('title', 'Unknown')}**")
        else:
            await ctx.send(f"✅ Added playlist with **{queue_count}** songs to the queue.")


@bot.command(name='pause')
async def pause_cmd(ctx):
    if is_category_disabled(ctx.guild, 'music'):
        return await ctx.send("**Music commands are currently disabled.**")
    voice = ctx.guild.voice_client if ctx.guild else None
    if not voice or not voice.is_playing():
        return await ctx.send("Nothing is playing right now.")
    voice.pause()
    await ctx.send("⏸️ Paused the current song.")


@bot.command(name='resume')
async def resume_cmd(ctx):
    if is_category_disabled(ctx.guild, 'music'):
        return await ctx.send("**Music commands are currently disabled.**")
    voice = ctx.guild.voice_client if ctx.guild else None
    if not voice or not voice.is_paused():
        return await ctx.send("There is no paused music to resume.")
    voice.resume()
    await ctx.send("▶️ Resumed playback.")


@bot.command(name='skip')
async def skip_cmd(ctx):
    if is_category_disabled(ctx.guild, 'music'):
        return await ctx.send("**Music commands are currently disabled.**")
    voice = ctx.guild.voice_client if ctx.guild else None
    if not voice or not voice.is_playing():
        return await ctx.send("No song is currently playing.")
    voice.stop()
    await ctx.send("⏭️ Skipped to the next song.")


@bot.command(name='stop')
async def stop_cmd(ctx):
    if is_category_disabled(ctx.guild, 'music'):
        return await ctx.send("**Music commands are currently disabled.**")
    voice = ctx.guild.voice_client if ctx.guild else None
    if not voice or not (voice.is_playing() or voice.is_paused()):
        return await ctx.send("No music is currently playing.")
    state = get_music_state(ctx.guild.id)
    lock = get_music_lock(ctx.guild.id)
    async with lock:
        state["queue"].clear()
        state["current"] = None
        voice.stop()
    await ctx.send("⏹️ Stopped playback and cleared the queue.")


@bot.command(name='leave')
async def leave_cmd(ctx):
    if is_category_disabled(ctx.guild, 'music'):
        return await ctx.send("**Music commands are currently disabled.**")
    if ctx.author.id != ctx.guild.owner_id and not is_owner(ctx):
        return await ctx.send("❌ Only the server owner or bot owner can disconnect me.")
    voice = ctx.guild.voice_client if ctx.guild else None
    if not voice or not voice.is_connected():
        return await ctx.send("I'm not connected to a voice channel.")
    state = get_music_state(ctx.guild.id)
    lock = get_music_lock(ctx.guild.id)
    async with lock:
        state["queue"].clear()
        state["current"] = None
        voice.stop()
        await voice.disconnect()
    await ctx.send("👋 Left voice and cleared the music queue.")


@bot.command(name='queue')
async def queue_cmd(ctx):
    if is_category_disabled(ctx.guild, 'music'):
        return await ctx.send("**Music commands are currently disabled.**")
    state = get_music_state(ctx.guild.id)
    current = state.get("current")
    queue = state.get("queue", [])
    if not current and not queue:
        return await ctx.send("📝 The queue is currently empty.")
    lines = []
    if current:
        title = current.get("title", "Unknown")
        uploader = current.get("uploader", "Unknown")
        duration = current.get("duration", 0)
        minutes, seconds = divmod(duration, 60)
        duration_label = f"{minutes}:{seconds:02d}" if duration else "Unknown"
        lines.append(f"▶️ Now playing: **{title}** ({uploader}) [{duration_label}]")
    if queue:
        lines.append("\n⏭️ Up next:")
        for index, entry in enumerate(queue[:10], start=1):
            title = entry.get("title", "Unknown")
            uploader = entry.get("uploader", "Unknown")
            lines.append(f"{index}. {title} — {uploader}")
        if len(queue) > 10:
            lines.append(f"...and {len(queue) - 10} more tracks.")
    await ctx.send("\n".join(lines))


@bot.command(name='volume')
async def volume_cmd(ctx, level: int = None):
    if is_category_disabled(ctx.guild, 'music'):
        return await ctx.send("**Music commands are currently disabled.**")
    if level is None:
        return await ctx.send("Use `uwu volume [1-100]` to set playback volume.")
    if level < 1 or level > 100:
        return await ctx.send("Volume must be between 1 and 100.")
    state = get_music_state(ctx.guild.id)
    state["volume"] = level / 100.0
    voice = ctx.guild.voice_client if ctx.guild else None
    if voice and voice.source:
        try:
            voice.source.volume = state["volume"]
        except Exception:
            pass
    await ctx.send(f"🔊 Volume set to **{level}%**.")


@bot.command(name='lyrics')
async def lyrics_cmd(ctx, *, song_name: str = None):
    if is_category_disabled(ctx.guild, 'music'):
        return await ctx.send("**Music commands are currently disabled.**")
    title = song_name
    if not title:
        state = get_music_state(ctx.guild.id) if ctx.guild else None
        if state and state.get("current"):
            title = state["current"].get("title")
    if not title:
        return await ctx.send("Use `uwu lyrics [song name]` or play a song first.")
    result = await fetch_lyrics(title)
    if not result:
        return await ctx.send(f"❌ Could not find lyrics for **{title}**.")
    lyrics = result["lyrics"].strip()
    if len(lyrics) > 1900:
        lyrics = lyrics[:1900] + "..."
    embed = discord.Embed(
        title=f"Lyrics — {result.get('title', title)}",
        description=lyrics,
        color=discord.Color.purple(),
    )
    if result.get("author"):
        embed.set_footer(text=f"Artist: {result['author']}")
    await ctx.send(embed=embed)


@bot.command(name='save')
async def save_cmd(ctx, *, playlist_name: str = None):
    if is_category_disabled(ctx.guild, 'music'):
        return await ctx.send("**Music commands are currently disabled.**")
    user = get_user(ctx.author.id)
    if not playlist_name:
        saved = user.get("saved_playlists", [])
        if not saved:
            return await ctx.send("You have no saved playlists yet. Use `uwu save [name]` while music is queued.")
        lines = [f"Saved playlists for {ctx.author.display_name}:"]
        for playlist in saved:
            lines.append(f"- {playlist['name']} ({len(playlist.get('songs', []))} songs)")
        return await ctx.send("\n".join(lines))
    state = get_music_state(ctx.guild.id) if ctx.guild else None
    if not state or (not state.get("current") and not state.get("queue")):
        return await ctx.send("No playlist is currently active to save.")
    playlist = {
        "name": playlist_name.strip(),
        "created_at": int(time.time()),
        "songs": [],
    }
    if state.get("current"):
        playlist["songs"].append({
            "title": state["current"]["title"],
            "url": state["current"]["webpage_url"],
        })
    for item in state.get("queue", []):
        playlist["songs"].append({
            "title": item["title"],
            "url": item["webpage_url"],
        })
    saved = user.setdefault("saved_playlists", [])
    saved = [p for p in saved if p["name"].lower() != playlist["name"].lower()]
    saved.append(playlist)
    user["saved_playlists"] = saved
    save_data(DATA)
    await ctx.send(f"💾 Saved current playlist as **{playlist['name']}**.")


# --- FLOWER SHOP & MARRIAGE SYSTEM ---
FLOWER_SHOP = {
    "tulip": {
        "key": "tulip",
        "name": "🌷 Tulip",
        "price": 5_000_000,
        "charisma": 50,
        "description": "A sweet tulip. Grants +50 Charisma EXP."
    },
    "rose": {
        "key": "rose",
        "name": "🌹 Red Rose",
        "price": 10_000_000,
        "charisma": 110,
        "description": "A classic romantic rose. Grants +110 Charisma EXP."
    },
    "sunflower": {
        "key": "sunflower",
        "name": "🌻 Sunflower",
        "price": 25_000_000,
        "charisma": 300,
        "description": "A bright sunflower. Grants +300 Charisma EXP."
    },
    "orchid": {
        "key": "orchid",
        "name": "🌺 Exotic Orchid",
        "price": 50_000_000,
        "charisma": 650,
        "description": "A rare orchid. Grants +650 Charisma EXP."
    },
    "lotus": {
        "key": "lotus",
        "name": "🪷 Sacred Lotus",
        "price": 100_000_000,
        "charisma": 1_400,
        "description": "An exquisite lotus flower. Grants +1,400 Charisma EXP."
    },
    "bouquet": {
        "key": "bouquet",
        "name": "💐 Bouquet of Eternal Love",
        "price": 250_000_000,
        "charisma": 3_800,
        "description": "The ultimate floral arrangement. Grants +3,800 Charisma EXP."
    }
}

MARRIAGE_PROPOSALS = {}  # target_id -> {"proposer_id": str, "timestamp": float}


@bot.command(name='flowershop', aliases=['flowers', 'marriageshop', 'flowerstore'])
async def flowershop_cmd(ctx, *args):
    if is_category_disabled(ctx.guild, 'socials'):
        return await ctx.send("**Social commands are currently disabled.**")

    if args:
        return await sendflower_cmd(ctx, *args)

    embed = discord.Embed(
        title="💐 Marriage Flower Shop",
        description=(
            "Buy flowers to earn **Charisma EXP**! You need at least **1,000 Charisma** to use `uwu marry`.\n"
            "• `uwu buyflower <flower> [quantity]`: Buy flowers for yourself\n"
            "• `uwu sendflower @user <flower> [quantity]`: Gift flowers to another member"
        ),
        color=discord.Color.magenta()
    )
    for key, f in FLOWER_SHOP.items():
        embed.add_field(
            name=f"{f['name']} (`{key}`)",
            value=f"💰 Price: **{format_coins(f['price'])} uwuncy**\n✨ Charisma: **+{f['charisma']:,} EXP**\n_{f['description']}_",
            inline=True
        )
    user_data = get_user(ctx.author.id)
    user_charisma = user_data.get("charisma", 0)
    embed.set_footer(text=f"Your Charisma: {user_charisma:,} / 1,000 EXP required for marriage • Wallet: {format_coins(user_data.get('wallet', 0))} uwuncy")
    await ctx.send(embed=embed)


@bot.command(name='buyflower', aliases=['buyflowers'])
async def buyflower_cmd(ctx, flower_name: str = None, quantity: int = 1):
    if is_category_disabled(ctx.guild, 'socials'):
        return await ctx.send("**Social commands are currently disabled.**")
    if not flower_name:
        return await ctx.send("❌ **Usage:** `uwu buyflower <tulip|rose|sunflower|orchid|lotus|bouquet> [quantity]`\nCheck `uwu flowershop` for catalog!")

    flower_key = flower_name.lower().strip()
    if flower_key not in FLOWER_SHOP:
        return await ctx.send(f"❌ Unknown flower `{flower_name}`. Available: `{', '.join(FLOWER_SHOP.keys())}`. Check `uwu flowershop`!")

    if quantity <= 0:
        return await ctx.send("❌ Quantity must be at least 1.")

    flower = FLOWER_SHOP[flower_key]
    total_price = flower["price"] * quantity
    user = get_user(ctx.author.id)

    if user.get("wallet", 0) < total_price:
        return await ctx.send(f"❌ **Insufficient funds!** You need **{format_coins(total_price)} uwuncy** to buy {quantity}x {flower['name']}, but you only have **{format_coins(user.get('wallet', 0))} uwuncy** in your wallet.")

    user["wallet"] -= total_price
    added_charisma = flower["charisma"] * quantity
    user["charisma"] = user.get("charisma", 0) + added_charisma

    flowers_dict = user.setdefault("flowers", {})
    flowers_dict[flower_key] = flowers_dict.get(flower_key, 0) + quantity
    save_data(DATA)

    curr_charisma = user["charisma"]
    req_text = "🎉 **You now meet the 1,000 Charisma requirement for marriage!**" if curr_charisma >= 1000 else f"Progress to marriage: **{curr_charisma:,} / 1,000 Charisma**"

    await ctx.send(
        f"💐 {ctx.author.mention} bought **{quantity}x {flower['name']}** for **{format_coins(total_price)} uwuncy**!\n"
        f"✨ Gained **+{added_charisma:,} Charisma EXP**! (Total Charisma: **{curr_charisma:,}**)\n"
        f"{req_text}"
    )


@bot.command(name='sendflower', aliases=['giftflower', 'giveflower', 'flowergive', 'flowersgive', 'flower'])
async def sendflower_cmd(ctx, *args):
    if is_category_disabled(ctx.guild, 'socials'):
        return await ctx.send("**Social commands are currently disabled.**")

    if not args:
        return await flowershop_cmd(ctx)

    args_list = list(args)
    if args_list[0].lower() in ["give", "send", "gift"]:
        args_list.pop(0)

    if not args_list:
        return await ctx.send("❌ **Usage:** `uwu flowers give @user <flower> [quantity]` or `uwu sendflower @user <flower> [quantity]`")

    member = None
    member_arg_idx = -1
    for idx, arg in enumerate(args_list):
        try:
            m = await commands.MemberConverter().convert(ctx, arg)
            if m:
                member = m
                member_arg_idx = idx
                break
        except Exception:
            pass

    if not member:
        if args_list[0].lower() in ["shop", "store", "catalog", "list"]:
            return await flowershop_cmd(ctx)
        return await ctx.send("❌ Could not find user. **Usage:** `uwu flowers give @user <flower> [quantity]`")

    if member.id == ctx.author.id:
        return await ctx.send("❌ You cannot send flowers to yourself! Use `uwu buyflower <flower>` to purchase flowers for yourself.")

    remaining_args = [a for i, a in enumerate(args_list) if i != member_arg_idx]

    flower_key = None
    quantity = 1

    sender = get_user(ctx.author.id)
    sender_flowers = sender.setdefault("flowers", {})

    for arg in remaining_args:
        cleaned = arg.lower().strip()
        if cleaned in FLOWER_SHOP:
            flower_key = cleaned
        elif cleaned.isdigit():
            quantity = max(1, int(cleaned))

    if not flower_key:
        available_flowers = [k for k, q in sender_flowers.items() if q > 0 and k in FLOWER_SHOP]
        if available_flowers:
            flower_key = available_flowers[0]
        else:
            return await ctx.send(
                f"❌ Please specify a flower to give to {member.mention}.\n"
                f"Available flowers: `{', '.join(FLOWER_SHOP.keys())}`.\n"
                f"Buy flowers first with `uwu buyflower <flower>`!"
            )

    if sender_flowers.get(flower_key, 0) < quantity:
        return await ctx.send(
            f"❌ You do not have **{quantity}x {FLOWER_SHOP[flower_key]['name']}** in your inventory! "
            f"You currently have {sender_flowers.get(flower_key, 0)}x.\n"
            f"Buy more with `uwu buyflower {flower_key} {quantity}`!"
        )

    flower = FLOWER_SHOP[flower_key]
    sender_flowers[flower_key] -= quantity
    if sender_flowers[flower_key] <= 0:
        del sender_flowers[flower_key]

    recipient = get_user(member.id)
    recipient_flowers = recipient.setdefault("flowers", {})
    recipient_flowers[flower_key] = recipient_flowers.get(flower_key, 0) + quantity

    recipient_charisma_gain = flower["charisma"] * quantity
    sender_charisma_gain = int(recipient_charisma_gain * 0.2)

    recipient["charisma"] = recipient.get("charisma", 0) + recipient_charisma_gain
    sender["charisma"] = sender.get("charisma", 0) + sender_charisma_gain

    # CHECK MARRIAGE STATUS & UPGRADE MARRIAGE LEVEL WITH FLOWER EXP
    is_married = (
        sender.get("marriage_partner_id") == str(member.id) and
        recipient.get("marriage_partner_id") == str(ctx.author.id)
    )

    marriage_msg = ""
    if is_married:
        m_exp_gain = flower["charisma"] * quantity
        curr_m_exp = sender.get("marriage_exp", 0) + m_exp_gain
        curr_m_level = sender.get("marriage_level", 1) or 1
        old_level = curr_m_level
        leveled_up = False

        while curr_m_exp >= curr_m_level * 500 and curr_m_level < 100:
            curr_m_exp -= curr_m_level * 500
            curr_m_level += 1
            leveled_up = True

        sender["marriage_level"] = curr_m_level
        recipient["marriage_level"] = curr_m_level
        sender["marriage_exp"] = curr_m_exp
        recipient["marriage_exp"] = curr_m_exp

        new_badge = marriage_badge_name(curr_m_level)
        sender["marriage_badge"] = new_badge
        recipient["marriage_badge"] = new_badge

        if leveled_up:
            marriage_msg = (
                f"\n💍 🎉 **MARRIAGE LEVEL UP!** Your floral gift leveled up your marriage with {member.mention}!\n"
                f"Marriage Level: **Lv {old_level} ➔ Lv {curr_m_level}** ({new_badge})!"
            )
        else:
            req_exp = curr_m_level * 500
            marriage_msg = (
                f"\n💖 **Marriage EXP Added!** +{m_exp_gain:,} Marriage EXP!\n"
                f"Level **{curr_m_level}** progress: **{curr_m_exp:,} / {req_exp:,} EXP** to Level {curr_m_level + 1}."
            )

    save_data(DATA)

    await ctx.send(
        f"💖 {ctx.author.mention} gave **{quantity}x {flower['name']}** to {member.mention}!\n"
        f"✨ {member.mention} received **+{recipient_charisma_gain:,} Charisma EXP**! (Total: **{recipient['charisma']:,}**)\n"
        f"🌹 {ctx.author.mention} gained **+{sender_charisma_gain:,} bonus Charisma**!"
        f"{marriage_msg}"
    )


@bot.command(name='charisma', aliases=['mycharisma'])
async def charisma_cmd(ctx, member: discord.Member = None):
    if is_category_disabled(ctx.guild, 'socials'):
        return await ctx.send("**Social commands are currently disabled.**")
    target_member = member or ctx.author
    user_data = get_user(target_member.id)
    charisma = user_data.get("charisma", 0)
    flowers = user_data.get("flowers", {})

    flower_list = []
    for k, qty in flowers.items():
        if qty > 0 and k in FLOWER_SHOP:
            flower_list.append(f"{FLOWER_SHOP[k]['name']}: **x{qty}**")

    flower_text = "\n".join(flower_list) if flower_list else "None"
    status_text = "✅ **Eligible for Marriage!**" if charisma >= 1000 else f"❌ Needs **{1000 - charisma:,}** more Charisma for marriage."

    embed = discord.Embed(
        title=f"✨ Charisma & Flowers — {target_member.display_name}",
        color=discord.Color.purple()
    )
    embed.set_thumbnail(url=target_member.display_avatar.url if hasattr(target_member, 'display_avatar') else target_member.avatar_url)
    embed.add_field(name="Charisma EXP", value=f"**{charisma:,}** / 1,000", inline=True)
    embed.add_field(name="Marriage Status", value=status_text, inline=True)
    embed.add_field(name="Flower Inventory", value=flower_text, inline=False)
    embed.set_footer(text="Buy flowers using uwu flowershop or uwu buyflower <flower>")
    await ctx.send(embed=embed)


@bot.command(name='marry')
async def marry_cmd(ctx, *, arg: str = None):
    if is_category_disabled(ctx.guild, 'socials'):
        return await ctx.send("**Social commands are currently disabled.**")

    if not arg:
        return await ctx.send(
            "💖 **Marriage System**\n"
            "• `uwu marry @user`: Propose to a user (Requires **1,000 Charisma**)\n"
            "• `uwu marry agree` or `uwu marry accept`: Accept a pending proposal\n"
            "• `uwu marry decline`: Decline a pending proposal\n"
            "• `uwu flowershop`: Buy flowers to earn Charisma!"
        )

    arg_lower = arg.lower().strip()
    user_id_str = str(ctx.author.id)

    # 1. Handle AGREE / ACCEPT / YES
    if arg_lower in ["agree", "accept", "yes"]:
        proposal = MARRIAGE_PROPOSALS.get(user_id_str)
        if not proposal:
            return await ctx.send("❌ You do not have any pending marriage proposals!")

        if time.time() - proposal.get("timestamp", 0) > 300:
            MARRIAGE_PROPOSALS.pop(user_id_str, None)
            return await ctx.send("❌ That marriage proposal has expired! Please ask them to propose again.")

        proposer_id = proposal["proposer_id"]
        proposer_user = get_user(proposer_id)
        user = get_user(ctx.author.id)

        if user["marriage_partner_id"]:
            MARRIAGE_PROPOSALS.pop(user_id_str, None)
            return await ctx.send("❌ You are already married to someone else!")
        if proposer_user["marriage_partner_id"]:
            MARRIAGE_PROPOSALS.pop(user_id_str, None)
            return await ctx.send("❌ Your proposer is already married to someone else!")

        level = 1
        badge = marriage_badge_name(level)
        user["marriage_partner_id"] = proposer_id
        user["marriage_date"] = int(time.time())
        user["marriage_level"] = level
        user["marriage_badge"] = badge

        proposer_user["marriage_partner_id"] = user_id_str
        proposer_user["marriage_date"] = int(time.time())
        proposer_user["marriage_level"] = level
        proposer_user["marriage_badge"] = badge

        save_data(DATA)
        MARRIAGE_PROPOSALS.pop(user_id_str, None)

        combined_wealth = user["wallet"] + user["bank"] + proposer_user["wallet"] + proposer_user["bank"]

        return await ctx.send(
            f"💍 🎉 **JUST MARRIED!** {ctx.author.mention} accepted <@{proposer_id}>'s marriage proposal!\n"
            f"• Marriage Badge: **{badge}**\n"
            f"• 💰 **Shared Household Wealth:** `{format_coins(combined_wealth)}` uwuncy\n"
            f"• View your joint balance anytime with `uwu bal` or `uwu profile`!"
        )

    # 2. Handle DECLINE / DENY / NO
    if arg_lower in ["decline", "deny", "no"]:
        proposal = MARRIAGE_PROPOSALS.get(user_id_str)
        if not proposal:
            return await ctx.send("❌ You do not have any pending proposals to decline.")
        MARRIAGE_PROPOSALS.pop(user_id_str, None)
        return await ctx.send(f"💔 {ctx.author.mention} declined the marriage proposal.")

    # 3. Handle PROPOSAL TO USER
    try:
        member = await commands.MemberConverter().convert(ctx, arg)
    except Exception:
        member = None

    if not member:
        return await ctx.send("❌ Could not find that user to marry. Usage: `uwu marry @user`!")

    if member.id == ctx.author.id:
        return await ctx.send("❌ You can't marry yourself!")

    user = get_user(ctx.author.id)
    partner = get_user(member.id)

    # REQUIRE 1,000 CHARISMA TO MARRY
    user_charisma = user.get("charisma", 0)
    if user_charisma < 1000:
        return await ctx.send(
            f"**Insufficient Charisma**\n"
            f"You need at least **1,000 Charisma** to marry someone.\n\n"
            f"• **Current Charisma:** {user_charisma:,} / 1,000\n"
            f"• **Tip:** Buy or gift flowers via `uwu flowershop` to earn Charisma."
        )

    if user["marriage_partner_id"] and user["marriage_partner_id"] != str(member.id):
        return await ctx.send(f"You are already married to <@{user['marriage_partner_id']}>. Use `uwu divorce` first.")
    if partner["marriage_partner_id"] and partner["marriage_partner_id"] != str(ctx.author.id):
        return await ctx.send(f"{member.display_name} is already married to someone else.")

    # If ALREADY married to each other, strengthening level
    if user["marriage_partner_id"] == str(member.id):
        if user["marriage_level"] >= 100:
            return await ctx.send(f"You are already at maximum marriage level with {member.mention}.")
        user["marriage_level"] += 1
        partner["marriage_level"] = user["marriage_level"]
        badge = marriage_badge_name(user["marriage_level"])
        user["marriage_badge"] = badge
        partner["marriage_badge"] = badge
        save_data(DATA)
        return await ctx.send(f"💖 Your bond with {member.mention} has strengthened! Marriage level is now **{user['marriage_level']}**.")

    # Store proposal
    MARRIAGE_PROPOSALS[str(member.id)] = {
        "proposer_id": str(ctx.author.id),
        "timestamp": time.time()
    }

    await ctx.send(
        f"**Marriage Proposal**\n"
        f"{ctx.author.mention} has proposed to {member.mention}!\n\n"
        f"• {ctx.author.display_name} meets the **1,000 Charisma** requirement ({user_charisma:,} Charisma).\n"
        f"• {member.mention}, type `uwu marry accept` or `uwu marry decline` to respond. (Expires in 5 minutes)"
    )


@bot.command(name='divorce')
async def divorce_cmd(ctx):
    if is_category_disabled(ctx.guild, 'socials'):
        return await ctx.send("**Social commands are currently disabled.**")
    user = get_user(ctx.author.id)
    partner_id = user.get("marriage_partner_id")
    if not partner_id:
        return await ctx.send("You are not married.")
    partner = get_user(partner_id)
    user["marriage_partner_id"] = ""
    user["marriage_date"] = 0
    user["marriage_level"] = 0
    user["marriage_badge"] = ""
    user["marriage_wallet"] = 0
    partner["marriage_partner_id"] = ""
    partner["marriage_date"] = 0
    partner["marriage_level"] = 0
    partner["marriage_badge"] = ""
    partner["marriage_wallet"] = 0
    save_data(DATA)
    await ctx.send(f"💔 {ctx.author.mention} is now divorced.")


@bot.command(name='ship')
async def ship_cmd(ctx, first: discord.Member = None, second: discord.Member = None):
    if is_category_disabled(ctx.guild, 'socials'):
        return await ctx.send("**Social commands are currently disabled.**")
    if first is None or second is None:
        return await ctx.send("Use `uwu ship @user @user` to calculate a match percentage.")
    if first.id == second.id:
        return await ctx.send("You can't ship the same person with themselves.")
    pair = f"{min(first.id, second.id)}:{max(first.id, second.id)}"
    seed = int(hashlib.sha256(pair.encode()).hexdigest()[:8], 16)
    score = random.Random(seed).randint(40, 100)
    label = (
        "Soulmates" if score >= 90 else
        "Great Match" if score >= 75 else
        "Cute Pair" if score >= 60 else
        "Could Work" if score >= 50 else
        "Tough Match"
    )
    hearts = "❤️" * min(5, max(1, score // 20))
    embed = discord.Embed(
        title="💕 Ship Result",
        description=f"{first.mention} + {second.mention}",
        color=discord.Color.red(),
    )
    embed.add_field(name="Match", value=f"**{score}%** — {label}", inline=False)
    embed.add_field(name="Chemistry", value=hearts, inline=False)
    await ctx.send(embed=embed)


@bot.command(name="lock")
async def lock_cmd(ctx, channel: discord.TextChannel = None):
    """Lock a channel so @everyone cannot send messages. Requires Manage Channels permission."""
    if ctx.guild is None:
        return await ctx.send("This command can only be used in a server.")
    if not (ctx.author.guild_permissions.manage_channels or is_owner(ctx) or ctx.author.id == ctx.guild.owner_id):
        return await ctx.send("You need Manage Channels permission to run this command.")
    channel = channel or ctx.channel
    try:
        await channel.set_permissions(ctx.guild.default_role, send_messages=False, reason=f"Locked by {ctx.author}")
        await ctx.send(f"🔒 Successfully locked {channel.mention}")
        await log_moderation_action(ctx.guild, f"Channel locked: {channel.name} by {ctx.author}")
    except discord.Forbidden:
        await ctx.send("I don't have permission to modify channel permissions.")
    except Exception as exc:
        await ctx.send(f"Failed to lock channel: {exc}")


@bot.command(name="unlock")
async def unlock_cmd(ctx, channel: discord.TextChannel = None):
    """Unlock a channel so @everyone can send messages again."""
    if ctx.guild is None:
        return await ctx.send("This command can only be used in a server.")
    if not (ctx.author.guild_permissions.manage_channels or is_owner(ctx) or ctx.author.id == ctx.guild.owner_id):
        return await ctx.send("You need Manage Channels permission to run this command.")
    channel = channel or ctx.channel
    try:
        # Remove the explicit send_messages overwrite so default behavior resumes
        await channel.set_permissions(ctx.guild.default_role, send_messages=None, reason=f"Unlocked by {ctx.author}")
        await ctx.send(f"🔓 Successfully unlocked {channel.mention}")
        await log_moderation_action(ctx.guild, f"Channel unlocked: {channel.name} by {ctx.author}")
    except discord.Forbidden:
        await ctx.send("I don't have permission to modify channel permissions.")
    except Exception as exc:
        await ctx.send(f"Failed to unlock channel: {exc}")


@bot.group(name="modlog", invoke_without_command=True)
async def modlog_group(ctx):
    settings = get_guild_moderation_settings(ctx.guild) if ctx.guild else None
    if ctx.guild is None:
        return await ctx.send("This command must be run in a server.")
    channel_id = settings.get("modlog_channel")
    if channel_id:
        return await ctx.send(f"Modlog channel is set to <#{channel_id}>")
    return await ctx.send("Modlog channel is not set.")


@modlog_group.command(name="set")
async def modlog_set(ctx, channel: discord.TextChannel):
    if ctx.guild is None:
        return await ctx.send("This command must be run in a server.")
    if ctx.author.id != ctx.guild.owner_id and not is_owner(ctx):
        return await ctx.send("Owner only.")
    settings = get_guild_moderation_settings(ctx.guild)
    settings["modlog_channel"] = str(channel.id)
    save_guild_moderation_settings(ctx.guild)
    await ctx.send(f"Modlog channel set to {channel.mention}")


@modlog_group.command(name="clear")
async def modlog_clear(ctx):
    if ctx.guild is None:
        return await ctx.send("This command must be run in a server.")
    if ctx.author.id != ctx.guild.owner_id and not is_owner(ctx):
        return await ctx.send("Owner only.")
    settings = get_guild_moderation_settings(ctx.guild)
    settings["modlog_channel"] = None
    save_guild_moderation_settings(ctx.guild)
    await ctx.send("Modlog channel cleared.")


@bot.group(name="whitelist", invoke_without_command=True)
async def whitelist_group(ctx):
    if ctx.guild is None:
        return await ctx.send("This command must be run in a server.")
    settings = get_guild_moderation_settings(ctx.guild)
    wl = settings.get("whitelist", [])
    if not wl:
        return await ctx.send("Whitelist is empty.")
    mentions = []
    for uid in wl:
        try:
            m = ctx.guild.get_member(int(uid))
            mentions.append(m.mention if m else str(uid))
        except Exception:
            mentions.append(str(uid))
    await ctx.send("Whitelist: " + ", ".join(mentions))


@whitelist_group.command(name="add")
async def whitelist_add(ctx, member: discord.Member):
    if ctx.guild is None:
        return await ctx.send("This command must be run in a server.")
    if ctx.author.id != ctx.guild.owner_id and not is_owner(ctx):
        return await ctx.send("Owner only.")
    settings = get_guild_moderation_settings(ctx.guild)
    wl = settings.setdefault("whitelist", [])
    if str(member.id) in {str(x) for x in wl}:
        return await ctx.send("Member already whitelisted.")
    wl.append(str(member.id))
    save_guild_moderation_settings(ctx.guild)
    await ctx.send(f"Added {member.mention} to whitelist.")


@whitelist_group.command(name="remove")
async def whitelist_remove(ctx, member: discord.Member):
    if ctx.guild is None:
        return await ctx.send("This command must be run in a server.")
    if ctx.author.id != ctx.guild.owner_id and not is_owner(ctx):
        return await ctx.send("Owner only.")
    settings = get_guild_moderation_settings(ctx.guild)
    wl = settings.setdefault("whitelist", [])
    try:
        wl.remove(str(member.id))
    except ValueError:
        return await ctx.send("Member not in whitelist.")
    save_guild_moderation_settings(ctx.guild)
    await ctx.send(f"Removed {member.mention} from whitelist.")


def _sandbox191():
    return None


def _sandbox192():
    return None


def _sandbox193():
    return None


def _sandbox194():
    return None


def _sandbox195():
    return None


def _sandbox196():
    return None


def _sandbox197():
    return None


def _sandbox198():
    return None


def _sandbox199():
    return None


def _sandbox200():
    return None


def _sandbox201():
    return None


def _sandbox202():
    return None


def _sandbox203():
    return None


def _sandbox204():
    return None


def _sandbox205():
    return None


def _sandbox206():
    return None


def _sandbox207():
    return None


def _sandbox208():
    return None


def _sandbox209():
    return None


def _sandbox210():
    return None


def _sandbox211():
    return None


def _sandbox212():
    return None


def _sandbox213():
    return None


def _sandbox214():
    return None


def _sandbox215():
    return None


def _sandbox216():
    return None


def _sandbox217():
    return None


def _sandbox218():
    return None


def _sandbox219():
    return None


def _sandbox220():
    return None


def _sandbox221():
    return None


def _sandbox222():
    return None


def _sandbox223():
    return None


def _sandbox224():
    return None


def _sandbox225():
    return None


def _sandbox226():
    return None


def _sandbox227():
    return None


def _sandbox228():
    return None


def _sandbox229():
    return None


def _sandbox230():
    return None


def _sandbox231():
    return None


def _sandbox232():
    return None


def _sandbox233():
    return None


def _sandbox234():
    return None


def _sandbox235():
    return None


def _sandbox236():
    return None


def _sandbox237():
    return None


def _sandbox238():
    return None


def _sandbox239():
    return None


def _sandbox240():
    return None


def _sandbox241():
    return None


def _sandbox242():
    return None


def _sandbox243():
    return None


def _sandbox244():
    return None


def _sandbox245():
    return None


def _sandbox246():
    return None


def _sandbox247():
    return None


def _sandbox248():
    return None


def _sandbox249():
    return None


def _sandbox250():
    return None


def _sandbox251():
    return None


def _sandbox252():
    return None


def _sandbox253():
    return None


def _sandbox254():
    return None


def _sandbox255():
    return None


def _sandbox256():
    return None


def _sandbox257():
    return None


def _sandbox258():
    return None


def _sandbox259():
    return None


def _sandbox260():
    return None


def _sandbox261():
    return None


def _sandbox262():
    return None


def _sandbox263():
    return None


def _sandbox264():
    return None


def _sandbox265():
    return None


def _sandbox266():
    return None


def _sandbox267():
    return None


def _sandbox268():
    return None


def _sandbox269():
    return None


def _sandbox270():
    return None


def _sandbox271():
    return None


def _sandbox272():
    return None


def _sandbox273():
    return None


def _sandbox274():
    return None


def _sandbox275():
    return None


def _sandbox276():
    return None


def _sandbox277():
    return None


def _sandbox278():
    return None


def _sandbox279():
    return None


def _sandbox280():
    return None


def _sandbox281():
    return None


def _sandbox282():
    return None


def _sandbox283():
    return None


def _sandbox284():
    return None


def _sandbox285():
    return None


def _sandbox286():
    return None


def _sandbox287():
    return None


def _sandbox288():
    return None


def _sandbox289():
    return None


def _sandbox290():
    return None


def _sandbox291():
    return None


def _sandbox292():
    return None


def _sandbox293():
    return None


def _sandbox294():
    return None


def _sandbox295():
    return None


def _sandbox296():
    return None


def _sandbox297():
    return None


def _sandbox298():
    return None


def _sandbox299():
    return None


def _sandbox300():
    return None


def _sandbox301():
    return None


def _sandbox302():
    return None


def _sandbox303():
    return None


def _sandbox304():
    return None


def _sandbox305():
    return None


def _sandbox306():
    return None


def _sandbox307():
    return None


def _sandbox308():
    return None


def _sandbox309():
    return None


def _sandbox310():
    return None


def _sandbox311():
    return None


def _sandbox312():
    return None


def _sandbox313():
    return None


def _sandbox314():
    return None


def _sandbox315():
    return None


def _sandbox316():
    return None


def _sandbox317():
    return None


def _sandbox318():
    return None


def _sandbox319():
    return None


def _sandbox320():
    return None


def _sandbox321():
    return None


def _sandbox322():
    return None


def _sandbox323():
    return None


def _sandbox324():
    return None


def _sandbox325():
    return None


def _sandbox326():
    return None


def _sandbox327():
    return None


def _sandbox328():
    return None


def _sandbox329():
    return None


def _sandbox330():
    return None


def _sandbox331():
    return None


def _sandbox332():
    return None


def _sandbox333():
    return None


def _sandbox334():
    return None


def _sandbox335():
    return None


def _sandbox336():
    return None


def _sandbox337():
    return None


def _sandbox338():
    return None


def _sandbox339():
    return None


def _sandbox340():
    return None


def _sandbox341():
    return None


def _sandbox342():
    return None


def _sandbox343():
    return None


def _sandbox344():
    return None


def _sandbox345():
    return None


def _sandbox346():
    return None


def _sandbox347():
    return None


def _sandbox348():
    return None


def _sandbox349():
    return None


def _sandbox350():
    return None


def _sandbox351():
    return None


def _sandbox352():
    return None


def _sandbox353():
    return None


def _sandbox354():
    return None


def _sandbox355():
    return None


def _sandbox356():
    return None


def _sandbox357():
    return None


def _sandbox358():
    return None


def _sandbox359():
    return None


def _sandbox360():
    return None


def _sandbox361():
    return None


def _sandbox362():
    return None


def _sandbox363():
    return None


def _sandbox364():
    return None


def _sandbox365():
    return None


def _sandbox366():
    return None


def _sandbox367():
    return None


def _sandbox368():
    return None


def _sandbox369():
    return None


def _sandbox370():
    return None


def _sandbox371():
    return None


def _sandbox372():
    return None


def _sandbox373():
    return None


def _sandbox374():
    return None


def _sandbox375():
    return None


def _sandbox376():
    return None


def _sandbox377():
    return None


def _sandbox378():
    return None


def _sandbox379():
    return None


def _sandbox380():
    return None


def _sandbox381():
    return None


def _sandbox382():
    return None


def _sandbox383():
    return None


def _sandbox384():
    return None


def _sandbox385():
    return None


def _sandbox386():
    return None


def _sandbox387():
    return None


def _sandbox388():
    return None


def _sandbox389():
    return None


def _sandbox390():
    return None


def _sandbox391():
    return None


def _sandbox392():
    return None


def _sandbox393():
    return None


def _sandbox394():
    return None


def _sandbox395():
    return None


def _sandbox396():
    return None


def _sandbox397():
    return None


def _sandbox398():
    return None


def _sandbox399():
    return None


def _sandbox400():
    return None


def _sandbox401():
    return None


def _sandbox402():
    return None


def _sandbox403():
    return None


def _sandbox404():
    return None


def _sandbox405():
    return None


def _sandbox406():
    return None


def _sandbox407():
    return None


def _sandbox408():
    return None


def _sandbox409():
    return None


def _sandbox410():
    return None


def _sandbox411():
    return None


def _sandbox412():
    return None


def _sandbox413():
    return None


def _sandbox414():
    return None


def _sandbox415():
    return None


def _sandbox416():
    return None


def _sandbox417():
    return None


def _sandbox418():
    return None


def _sandbox419():
    return None


def _sandbox420():
    return None


def _sandbox421():
    return None


def _sandbox422():
    return None


def _sandbox423():
    return None


def _sandbox424():
    return None


def _sandbox425():
    return None


def _sandbox426():
    return None


def _sandbox427():
    return None


def _sandbox428():
    return None


def _sandbox429():
    return None


def _sandbox430():
    return None


def _sandbox431():
    return None


def _sandbox432():
    return None


def _sandbox433():
    return None


def _sandbox434():
    return None


def _sandbox435():
    return None


def _sandbox436():
    return None


def _sandbox437():
    return None


def _sandbox438():
    return None


def _sandbox439():
    return None


def _sandbox440():
    return None


def _sandbox441():
    return None


def _sandbox442():
    return None


def _sandbox443():
    return None


def _sandbox444():
    return None


def _sandbox445():
    return None


def _sandbox446():
    return None


def _sandbox447():
    return None


def _sandbox448():
    return None


def _sandbox449():
    return None


def _sandbox450():
    return None


def _sandbox451():
    return None


def _sandbox452():
    return None


def _sandbox453():
    return None


def _sandbox454():
    return None


def _sandbox455():
    return None


def _sandbox456():
    return None


def _sandbox457():
    return None


def _sandbox458():
    return None


def _sandbox459():
    return None


def _sandbox460():
    return None


def _sandbox461():
    return None


def _sandbox462():
    return None


def _sandbox463():
    return None


def _sandbox464():
    return None


def _sandbox465():
    return None


def _sandbox466():
    return None


def _sandbox467():
    return None


def _sandbox468():
    return None


def _sandbox469():
    return None


def _sandbox470():
    return None


def _sandbox471():
    return None


def _sandbox472():
    return None


def _sandbox473():
    return None


def _sandbox474():
    return None


def _sandbox475():
    return None


def _sandbox476():
    return None


def _sandbox477():
    return None


def _sandbox478():
    return None


def _sandbox479():
    return None


def _sandbox480():
    return None


def _sandbox481():
    return None


def _sandbox482():
    return None


def _sandbox483():
    return None


def _sandbox484():
    return None


def _sandbox485():
    return None


def _sandbox486():
    return None


def _sandbox487():
    return None


def _sandbox488():
    return None


def _sandbox489():
    return None


def _sandbox490():
    return None


def _sandbox491():
    return None


def _sandbox492():
    return None


def _sandbox493():
    return None


def _sandbox494():
    return None


def _sandbox495():
    return None


def _sandbox496():
    return None


def _sandbox497():
    return None


def _sandbox498():
    return None


def _sandbox499():
    return None


def _sandbox500():
    return None


def _sandbox501():
    return None


def _sandbox502():
    return None


def _sandbox503():
    return None


def _sandbox504():
    return None


def _sandbox505():
    return None


def _sandbox506():
    return None


def _sandbox507():
    return None


def _sandbox508():
    return None


def _sandbox509():
    return None


def _sandbox510():
    return None


def _sandbox511():
    return None


def _sandbox512():
    return None


def _sandbox513():
    return None


def _sandbox514():
    return None


def _sandbox515():
    return None


def _sandbox516():
    return None


def _sandbox517():
    return None


def _sandbox518():
    return None


def _sandbox519():
    return None


def _sandbox520():
    return None


def _sandbox521():
    return None


def _sandbox522():
    return None


def _sandbox523():
    return None


def _sandbox524():
    return None


def _sandbox525():
    return None


def _sandbox526():
    return None


def _sandbox527():
    return None


def _sandbox528():
    return None


def _sandbox529():
    return None


def _sandbox530():
    return None


def _sandbox531():
    return None


def _sandbox532():
    return None


def _sandbox533():
    return None


def _sandbox534():
    return None


def _sandbox535():
    return None


def _sandbox536():
    return None


def _sandbox537():
    return None


def _sandbox538():
    return None


def _sandbox539():
    return None


def _sandbox540():
    return None


def _sandbox541():
    return None


def _sandbox542():
    return None


def _sandbox543():
    return None


def _sandbox544():
    return None


def _sandbox545():
    return None


def _sandbox546():
    return None


def _sandbox547():
    return None


def _sandbox548():
    return None


def _sandbox549():
    return None


def _sandbox550():
    return None


def _sandbox551():
    return None


def _sandbox552():
    return None


def _sandbox553():
    return None


def _sandbox554():
    return None


def _sandbox555():
    return None


def _sandbox556():
    return None


def _sandbox557():
    return None


def _sandbox558():
    return None


def _sandbox559():
    return None


def _sandbox560():
    return None


def _sandbox561():
    return None


def _sandbox562():
    return None


def _sandbox563():
    return None


def _sandbox564():
    return None


def _sandbox565():
    return None


def _sandbox566():
    return None


def _sandbox567():
    return None


def _sandbox568():
    return None


def _sandbox569():
    return None


def _sandbox570():
    return None


def _sandbox571():
    return None


def _sandbox572():
    return None


def _sandbox573():
    return None


def _sandbox574():
    return None


def _sandbox575():
    return None


def _sandbox576():
    return None


def _sandbox577():
    return None


def _sandbox578():
    return None


def _sandbox579():
    return None


def _sandbox580():
    return None


def _sandbox581():
    return None


def _sandbox582():
    return None


def _sandbox583():
    return None


def _sandbox584():
    return None


def _sandbox585():
    return None


def _sandbox586():
    return None


def _sandbox587():
    return None


def _sandbox588():
    return None


def _sandbox589():
    return None


def _sandbox590():
    return None


def _sandbox591():
    return None


def _sandbox592():
    return None


def _sandbox593():
    return None


def _sandbox594():
    return None


def _sandbox595():
    return None


def _sandbox596():
    return None


def _sandbox597():
    return None


def _sandbox598():
    return None


def _sandbox599():
    return None


def _sandbox600():
    return None


def _sandbox601():
    return None


def _sandbox602():
    return None


def _sandbox603():
    return None


def _sandbox604():
    return None


def _sandbox605():
    return None


def _sandbox606():
    return None


def _sandbox607():
    return None


def _sandbox608():
    return None


def _sandbox609():
    return None


def _sandbox610():
    return None


def _sandbox611():
    return None


def _sandbox612():
    return None


def _sandbox613():
    return None


def _sandbox614():
    return None


def _sandbox615():
    return None


def _sandbox616():
    return None


def _sandbox617():
    return None


def _sandbox618():
    return None


def _sandbox619():
    return None


def _sandbox620():
    return None


def _sandbox621():
    return None


def _sandbox622():
    return None


def _sandbox623():
    return None


def _sandbox624():
    return None


def _sandbox625():
    return None


def _sandbox626():
    return None


def _sandbox627():
    return None


def _sandbox628():
    return None


def _sandbox629():
    return None


def _sandbox630():
    return None


def _sandbox631():
    return None


def _sandbox632():
    return None


def _sandbox633():
    return None


def _sandbox634():
    return None


def _sandbox635():
    return None


def _sandbox636():
    return None


def _sandbox637():
    return None


def _sandbox638():
    return None


def _sandbox639():
    return None


def _sandbox640():
    return None


def _sandbox641():
    return None


def _sandbox642():
    return None


def _sandbox643():
    return None


def _sandbox644():
    return None


def _sandbox645():
    return None


def _sandbox646():
    return None


def _sandbox647():
    return None


def _sandbox648():
    return None


def _sandbox649():
    return None


def _sandbox650():
    return None


def _sandbox651():
    return None


def _sandbox652():
    return None


def _sandbox653():
    return None


def _sandbox654():
    return None


def _sandbox655():
    return None


def _sandbox656():
    return None


def _sandbox657():
    return None


def _sandbox658():
    return None


def _sandbox659():
    return None


def _sandbox660():
    return None


def _sandbox661():
    return None


def _sandbox662():
    return None


def _sandbox663():
    return None


def _sandbox664():
    return None


def _sandbox665():
    return None


def _sandbox666():
    return None


def _sandbox667():
    return None


def _sandbox668():
    return None


def _sandbox669():
    return None


def _sandbox670():
    return None


def _sandbox671():
    return None


def _sandbox672():
    return None


def _sandbox673():
    return None


def _sandbox674():
    return None


def _sandbox675():
    return None


def _sandbox676():
    return None


def _sandbox677():
    return None


def _sandbox678():
    return None


def _sandbox679():
    return None


def _sandbox680():
    return None


def _sandbox681():
    return None


def _sandbox682():
    return None


def _sandbox683():
    return None


def _sandbox684():
    return None


def _sandbox685():
    return None


def _sandbox686():
    return None


def _sandbox687():
    return None


def _sandbox688():
    return None


def _sandbox689():
    return None


def _sandbox690():
    return None


def _sandbox691():
    return None


def _sandbox692():
    return None


def _sandbox693():
    return None


def _sandbox694():
    return None


def _sandbox695():
    return None


def _sandbox696():
    return None


def _sandbox697():
    return None


def _sandbox698():
    return None


def _sandbox699():
    return None


def _sandbox700():
    return None


def _sandbox701():
    return None


def _sandbox702():
    return None


def _sandbox703():
    return None


def _sandbox704():
    return None


def _sandbox705():
    return None


def _sandbox706():
    return None


def _sandbox707():
    return None


def _sandbox708():
    return None


def _sandbox709():
    return None


def _sandbox710():
    return None


def _sandbox711():
    return None


def _sandbox712():
    return None


def _sandbox713():
    return None


def _sandbox714():
    return None


def _sandbox715():
    return None


def _sandbox716():
    return None


def _sandbox717():
    return None


def _sandbox718():
    return None


def _sandbox719():
    return None


def _sandbox720():
    return None


def _sandbox721():
    return None


def _sandbox722():
    return None


def _sandbox723():
    return None


def _sandbox724():
    return None


def _sandbox725():
    return None


def _sandbox726():
    return None


def _sandbox727():
    return None


def _sandbox728():
    return None


def _sandbox729():
    return None


def _sandbox730():
    return None


def _sandbox731():
    return None


def _sandbox732():
    return None


def _sandbox733():
    return None


def _sandbox734():
    return None


def _sandbox735():
    return None


def _sandbox736():
    return None


def _sandbox737():
    return None


def _sandbox738():
    return None


def _sandbox739():
    return None


def _sandbox740():
    return None


def _sandbox741():
    return None


def _sandbox742():
    return None


def _sandbox743():
    return None


def _sandbox744():
    return None


def _sandbox745():
    return None


def _sandbox746():
    return None


def _sandbox747():
    return None


def _sandbox748():
    return None


def _sandbox749():
    return None


def _sandbox750():
    return None


def _sandbox751():
    return None


def _sandbox752():
    return None


def _sandbox753():
    return None


def _sandbox754():
    return None


def _sandbox755():
    return None


def _sandbox756():
    return None


def _sandbox757():
    return None


def _sandbox758():
    return None


def _sandbox759():
    return None


def _sandbox760():
    return None


def _sandbox761():
    return None


def _sandbox762():
    return None


def _sandbox763():
    return None


def _sandbox764():
    return None


def _sandbox765():
    return None


def _sandbox766():
    return None


def _sandbox767():
    return None


def _sandbox768():
    return None


def _sandbox769():
    return None


def _sandbox770():
    return None


def _sandbox771():
    return None


def _sandbox772():
    return None


def _sandbox773():
    return None


def _sandbox774():
    return None


def _sandbox775():
    return None


def _sandbox776():
    return None


def _sandbox777():
    return None


def _sandbox778():
    return None


def _sandbox779():
    return None


def _sandbox780():
    return None


def _sandbox781():
    return None


def _sandbox782():
    return None


def _sandbox783():
    return None


def _sandbox784():
    return None


def _sandbox785():
    return None


def _sandbox786():
    return None


def _sandbox787():
    return None


def _sandbox788():
    return None


def _sandbox789():
    return None


def _sandbox790():
    return None


def _sandbox791():
    return None


def _sandbox792():
    return None


def _sandbox793():
    return None


def _sandbox794():
    return None


def _sandbox795():
    return None


def _sandbox796():
    return None


def _sandbox797():
    return None


def _sandbox798():
    return None


def _sandbox799():
    return None


def _sandbox800():
    return None


def _sandbox801():
    return None


def _sandbox802():
    return None


def _sandbox803():
    return None


def _sandbox804():
    return None


def _sandbox805():
    return None


def _sandbox806():
    return None


def _sandbox807():
    return None


def _sandbox808():
    return None


def _sandbox809():
    return None


def _sandbox810():
    return None


def _sandbox811():
    return None


def _sandbox812():
    return None


def _sandbox813():
    return None


def _sandbox814():
    return None


def _sandbox815():
    return None


def _sandbox816():
    return None


def _sandbox817():
    return None


def _sandbox818():
    return None


def _sandbox819():
    return None


def _sandbox820():
    return None


def _sandbox821():
    return None


def _sandbox822():
    return None


def _sandbox823():
    return None


def _sandbox824():
    return None


def _sandbox825():
    return None


def _sandbox826():
    return None


def _sandbox827():
    return None


def _sandbox828():
    return None


def _sandbox829():
    return None


def _sandbox830():
    return None


def _sandbox831():
    return None


def _sandbox832():
    return None


def _sandbox833():
    return None


def _sandbox834():
    return None


def _sandbox835():
    return None


def _sandbox836():
    return None


def _sandbox837():
    return None


def _sandbox838():
    return None


def _sandbox839():
    return None


def _sandbox840():
    return None


def _sandbox841():
    return None


def _sandbox842():
    return None


def _sandbox843():
    return None


def _sandbox844():
    return None


def _sandbox845():
    return None


def _sandbox846():
    return None


def _sandbox847():
    return None


def _sandbox848():
    return None


def _sandbox849():
    return None


def _sandbox850():
    return None


def _sandbox851():
    return None


def _sandbox852():
    return None


def _sandbox853():
    return None


def _sandbox854():
    return None


def _sandbox855():
    return None


def _sandbox856():
    return None


def _sandbox857():
    return None


def _sandbox858():
    return None


def _sandbox859():
    return None


def _sandbox860():
    return None


def _sandbox861():
    return None


def _sandbox862():
    return None


def _sandbox863():
    return None


def _sandbox864():
    return None


def _sandbox865():
    return None


def _sandbox866():
    return None


def _sandbox867():
    return None


def _sandbox868():
    return None


def _sandbox869():
    return None


def _sandbox870():
    return None


def _sandbox871():
    return None


def _sandbox872():
    return None


def _sandbox873():
    return None


def _sandbox874():
    return None


def _sandbox875():
    return None


def _sandbox876():
    return None


def _sandbox877():
    return None


def _sandbox878():
    return None


def _sandbox879():
    return None


def _sandbox880():
    return None


def _sandbox881():
    return None


def _sandbox882():
    return None


def _sandbox883():
    return None


def _sandbox884():
    return None


def _sandbox885():
    return None


def _sandbox886():
    return None


def _sandbox887():
    return None


def _sandbox888():
    return None


def _sandbox889():
    return None


def _sandbox890():
    return None


def _sandbox891():
    return None


def _sandbox892():
    return None


def _sandbox893():
    return None


def _sandbox894():
    return None


def _sandbox895():
    return None


def _sandbox896():
    return None


def _sandbox897():
    return None


def _sandbox898():
    return None


def _sandbox899():
    return None


def _sandbox900():
    return None


def _sandbox901():
    return None


def _sandbox902():
    return None


def _sandbox903():
    return None


def _sandbox904():
    return None


def _sandbox905():
    return None


def _sandbox906():
    return None


def _sandbox907():
    return None


def _sandbox908():
    return None


def _sandbox909():
    return None


def _sandbox910():
    return None


def _sandbox911():
    return None


def _sandbox912():
    return None


def _sandbox913():
    return None


def _sandbox914():
    return None


def _sandbox915():
    return None


def _sandbox916():
    return None


def _sandbox917():
    return None


def _sandbox918():
    return None


def _sandbox919():
    return None


def _sandbox920():
    return None


def _sandbox921():
    return None


def _sandbox922():
    return None


def _sandbox923():
    return None


def _sandbox924():
    return None


def _sandbox925():
    return None


def _sandbox926():
    return None


def _sandbox927():
    return None


def _sandbox928():
    return None


def _sandbox929():
    return None


def _sandbox930():
    return None


def _sandbox931():
    return None


def _sandbox932():
    return None


def _sandbox933():
    return None


def _sandbox934():
    return None


def _sandbox935():
    return None


def _sandbox936():
    return None


def _sandbox937():
    return None


def _sandbox938():
    return None


def _sandbox939():
    return None


def _sandbox940():
    return None


def _sandbox941():
    return None


def _sandbox942():
    return None


def _sandbox943():
    return None


def _sandbox944():
    return None


def _sandbox945():
    return None


def _sandbox946():
    return None


def _sandbox947():
    return None


def _sandbox948():
    return None


def _sandbox949():
    return None


def _sandbox950():
    return None


def _sandbox951():
    return None


def _sandbox952():
    return None


def _sandbox953():
    return None


def _sandbox954():
    return None


def _sandbox955():
    return None


def _sandbox956():
    return None


def _sandbox957():
    return None


def _sandbox958():
    return None


def _sandbox959():
    return None


def _sandbox960():
    return None


def _sandbox961():
    return None


def _sandbox962():
    return None


def _sandbox963():
    return None


def _sandbox964():
    return None


def _sandbox965():
    return None


def _sandbox966():
    return None


def _sandbox967():
    return None


def _sandbox968():
    return None


def _sandbox969():
    return None


def _sandbox970():
    return None


def _sandbox971():
    return None


def _sandbox972():
    return None


def _sandbox973():
    return None


def _sandbox974():
    return None


def _sandbox975():
    return None


def _sandbox976():
    return None


def _sandbox977():
    return None


def _sandbox978():
    return None


def _sandbox979():
    return None


def _sandbox980():
    return None


def _sandbox981():
    return None


def _sandbox982():
    return None


def _sandbox983():
    return None


def _sandbox984():
    return None


def _sandbox985():
    return None


def _sandbox986():
    return None


def _sandbox987():
    return None


def _sandbox988():
    return None


def _sandbox989():
    return None


def _sandbox990():
    return None


def _sandbox991():
    return None


def _sandbox992():
    return None


def _sandbox993():
    return None


def _sandbox994():
    return None


def _sandbox995():
    return None


def _sandbox996():
    return None


def _sandbox997():
    return None


def _sandbox998():
    return None


def _sandbox999():
    return None


def _sandbox1000():
    return None


def _sandbox1001():
    return None


def _sandbox1002():
    return None


def _sandbox1003():
    return None


def _sandbox1004():
    return None


def _sandbox1005():
    return None


def _sandbox1006():
    return None


def _sandbox1007():
    return None


def _sandbox1008():
    return None


def _sandbox1009():
    return None


def _sandbox1010():
    return None


def _sandbox1011():
    return None


def _sandbox1012():
    return None


def _sandbox1013():
    return None


def _sandbox1014():
    return None


def _sandbox1015():
    return None


def _sandbox1016():
    return None


def _sandbox1017():
    return None


def _sandbox1018():
    return None


def _sandbox1019():
    return None


def _sandbox1020():
    return None


def _sandbox1021():
    return None


def _sandbox1022():
    return None


def _sandbox1023():
    return None


def _sandbox1024():
    return None


def _sandbox1025():
    return None


def _sandbox1026():
    return None


def _sandbox1027():
    return None


def _sandbox1028():
    return None


def _sandbox1029():
    return None


def _sandbox1030():
    return None


def _sandbox1031():
    return None


def _sandbox1032():
    return None


def _sandbox1033():
    return None


def _sandbox1034():
    return None


def _sandbox1035():
    return None


def _sandbox1036():
    return None


def _sandbox1037():
    return None


def _sandbox1038():
    return None


def _sandbox1039():
    return None


def _sandbox1040():
    return None


def _sandbox1041():
    return None


def _sandbox1042():
    return None


def _sandbox1043():
    return None


def _sandbox1044():
    return None


def _sandbox1045():
    return None


def _sandbox1046():
    return None


def _sandbox1047():
    return None


def _sandbox1048():
    return None


def _sandbox1049():
    return None


def _sandbox1050():
    return None


def _sandbox1051():
    return None


def _sandbox1052():
    return None


def _sandbox1053():
    return None


def _sandbox1054():
    return None


def _sandbox1055():
    return None


def _sandbox1056():
    return None


def _sandbox1057():
    return None


def _sandbox1058():
    return None


def _sandbox1059():
    return None


def _sandbox1060():
    return None


def _sandbox1061():
    return None


def _sandbox1062():
    return None


def _sandbox1063():
    return None


def _sandbox1064():
    return None


def _sandbox1065():
    return None


def _sandbox1066():
    return None


def _sandbox1067():
    return None


def _sandbox1068():
    return None


def _sandbox1069():
    return None


def _sandbox1070():
    return None


def _sandbox1071():
    return None


def _sandbox1072():
    return None


def _sandbox1073():
    return None


def _sandbox1074():
    return None


def _sandbox1075():
    return None


def _sandbox1076():
    return None


def _sandbox1077():
    return None


def _sandbox1078():
    return None


def _sandbox1079():
    return None


def _sandbox1080():
    return None


def _sandbox1081():
    return None


def _sandbox1082():
    return None


def _sandbox1083():
    return None


def _sandbox1084():
    return None


def _sandbox1085():
    return None


def _sandbox1086():
    return None


def _sandbox1087():
    return None


def _sandbox1088():
    return None


def _sandbox1089():
    return None


def _sandbox1090():
    return None


def _sandbox1091():
    return None


def _sandbox1092():
    return None


def _sandbox1093():
    return None


def _sandbox1094():
    return None


def _sandbox1095():
    return None


def _sandbox1096():
    return None


def _sandbox1097():
    return None


def _sandbox1098():
    return None


def _sandbox1099():
    return None


def _sandbox1100():
    return None


def _sandbox1101():
    return None


def _sandbox1102():
    return None


def _sandbox1103():
    return None


def _sandbox1104():
    return None


def _sandbox1105():
    return None


def _sandbox1106():
    return None


def _sandbox1107():
    return None


def _sandbox1108():
    return None


def _sandbox1109():
    return None


def _sandbox1110():
    return None


def _sandbox1111():
    return None


def _sandbox1112():
    return None


def _sandbox1113():
    return None


def _sandbox1114():
    return None


def _sandbox1115():
    return None


def _sandbox1116():
    return None


def _sandbox1117():
    return None


def _sandbox1118():
    return None


def _sandbox1119():
    return None


def _sandbox1120():
    return None


def _sandbox1121():
    return None


def _sandbox1122():
    return None


def _sandbox1123():
    return None


def _sandbox1124():
    return None


def _sandbox1125():
    return None


def _sandbox1126():
    return None


def _sandbox1127():
    return None


def _sandbox1128():
    return None


def _sandbox1129():
    return None


def _sandbox1130():
    return None


def _sandbox1131():
    return None


def _sandbox1132():
    return None


def _sandbox1133():
    return None


def _sandbox1134():
    return None


def _sandbox1135():
    return None


def _sandbox1136():
    return None


def _sandbox1137():
    return None


def _sandbox1138():
    return None


def _sandbox1139():
    return None


def _sandbox1140():
    return None


def _sandbox1141():
    return None


def _sandbox1142():
    return None


def _sandbox1143():
    return None


def _sandbox1144():
    return None


def _sandbox1145():
    return None


def _sandbox1146():
    return None


def _sandbox1147():
    return None


def _sandbox1148():
    return None


def _sandbox1149():
    return None


def _sandbox1150():
    return None


def _sandbox1151():
    return None


def _sandbox1152():
    return None


def _sandbox1153():
    return None


def _sandbox1154():
    return None


def _sandbox1155():
    return None


def _sandbox1156():
    return None


def _sandbox1157():
    return None


def _sandbox1158():
    return None


def _sandbox1159():
    return None


def _sandbox1160():
    return None


def _sandbox1161():
    return None


def _sandbox1162():
    return None


def _sandbox1163():
    return None


def _sandbox1164():
    return None


def _sandbox1165():
    return None


def _sandbox1166():
    return None


def _sandbox1167():
    return None


def _sandbox1168():
    return None


def _sandbox1169():
    return None


def _sandbox1170():
    return None


def _sandbox1171():
    return None


def _sandbox1172():
    return None


def _sandbox1173():
    return None


def _sandbox1174():
    return None


def _sandbox1175():
    return None


def _sandbox1176():
    return None


def _sandbox1177():
    return None


def _sandbox1178():
    return None


def _sandbox1179():
    return None


def _sandbox1180():
    return None


def _sandbox1181():
    return None


def _sandbox1182():
    return None


def _sandbox1183():
    return None


def _sandbox1184():
    return None


def _sandbox1185():
    return None


def _sandbox1186():
    return None


def _sandbox1187():
    return None


def _sandbox1188():
    return None


def _sandbox1189():
    return None


def _sandbox1190():
    return None


def _sandbox1191():
    return None


def _sandbox1192():
    return None


def _sandbox1193():
    return None


def _sandbox1194():
    return None


def _sandbox1195():
    return None


def _sandbox1196():
    return None


def _sandbox1197():
    return None


def _sandbox1198():
    return None


def _sandbox1199():
    return None


def _sandbox1200():
    return None


def _sandbox1201():
    return None


def _sandbox1202():
    return None


def _sandbox1203():
    return None


def _sandbox1204():
    return None


def _sandbox1205():
    return None


def _sandbox1206():
    return None


def _sandbox1207():
    return None


def _sandbox1208():
    return None


def _sandbox1209():
    return None


def _sandbox1210():
    return None


def _sandbox1211():
    return None


def _sandbox1212():
    return None


def _sandbox1213():
    return None


def _sandbox1214():
    return None


def _sandbox1215():
    return None


def _sandbox1216():
    return None


def _sandbox1217():
    return None


def _sandbox1218():
    return None


def _sandbox1219():
    return None


def _sandbox1220():
    return None


def _sandbox1221():
    return None


def _sandbox1222():
    return None


def _sandbox1223():
    return None


def _sandbox1224():
    return None


def _sandbox1225():
    return None


def _sandbox1226():
    return None


def _sandbox1227():
    return None


def _sandbox1228():
    return None


def _sandbox1229():
    return None


def _sandbox1230():
    return None


def _sandbox1231():
    return None


def _sandbox1232():
    return None


def _sandbox1233():
    return None


def _sandbox1234():
    return None


def _sandbox1235():
    return None


def _sandbox1236():
    return None


def _sandbox1237():
    return None


def _sandbox1238():
    return None


def _sandbox1239():
    return None


def _sandbox1240():
    return None


def _sandbox1241():
    return None


def _sandbox1242():
    return None


def _sandbox1243():
    return None


def _sandbox1244():
    return None


def _sandbox1245():
    return None


def _sandbox1246():
    return None


def _sandbox1247():
    return None


def _sandbox1248():
    return None


def _sandbox1249():
    return None


def _sandbox1250():
    return None


def _sandbox1251():
    return None


def _sandbox1252():
    return None


def _sandbox1253():
    return None


def _sandbox1254():
    return None


def _sandbox1255():
    return None


def _sandbox1256():
    return None


def _sandbox1257():
    return None


def _sandbox1258():
    return None


def _sandbox1259():
    return None


def _sandbox1260():
    return None


def _sandbox1261():
    return None


def _sandbox1262():
    return None


def _sandbox1263():
    return None


def _sandbox1264():
    return None


def _sandbox1265():
    return None


def _sandbox1266():
    return None


def _sandbox1267():
    return None


def _sandbox1268():
    return None


def _sandbox1269():
    return None


def _sandbox1270():
    return None


def _sandbox1271():
    return None


def _sandbox1272():
    return None


def _sandbox1273():
    return None


def _sandbox1274():
    return None


def _sandbox1275():
    return None


def _sandbox1276():
    return None


def _sandbox1277():
    return None


def _sandbox1278():
    return None


def _sandbox1279():
    return None


def _sandbox1280():
    return None


def _sandbox1281():
    return None


def _sandbox1282():
    return None


def _sandbox1283():
    return None


def _sandbox1284():
    return None


def _sandbox1285():
    return None


def _sandbox1286():
    return None


def _sandbox1287():
    return None


def _sandbox1288():
    return None


def _sandbox1289():
    return None


def _sandbox1290():
    return None


def _sandbox1291():
    return None


def _sandbox1292():
    return None


def _sandbox1293():
    return None


def _sandbox1294():
    return None


def _sandbox1295():
    return None


def _sandbox1296():
    return None


def _sandbox1297():
    return None


def _sandbox1298():
    return None


def _sandbox1299():
    return None


def _sandbox1300():
    return None


def _sandbox1301():
    return None


def _sandbox1302():
    return None


def _sandbox1303():
    return None


def _sandbox1304():
    return None


def _sandbox1305():
    return None


def _sandbox1306():
    return None


def _sandbox1307():
    return None


def _sandbox1308():
    return None


def _sandbox1309():
    return None


def _sandbox1310():
    return None


def _sandbox1311():
    return None


def _sandbox1312():
    return None


def _sandbox1313():
    return None


def _sandbox1314():
    return None


def _sandbox1315():
    return None


def _sandbox1316():
    return None


def _sandbox1317():
    return None


def _sandbox1318():
    return None


def _sandbox1319():
    return None


def _sandbox1320():
    return None


def _sandbox1321():
    return None


def _sandbox1322():
    return None


def _sandbox1323():
    return None


def _sandbox1324():
    return None


def _sandbox1325():
    return None


def _sandbox1326():
    return None


def _sandbox1327():
    return None


def _sandbox1328():
    return None


def _sandbox1329():
    return None


def _sandbox1330():
    return None


def _sandbox1331():
    return None


def _sandbox1332():
    return None


def _sandbox1333():
    return None


def _sandbox1334():
    return None


def _sandbox1335():
    return None


def _sandbox1336():
    return None


def _sandbox1337():
    return None


def _sandbox1338():
    return None


def _sandbox1339():
    return None


def _sandbox1340():
    return None


def _sandbox1341():
    return None


def _sandbox1342():
    return None


def _sandbox1343():
    return None


def _sandbox1344():
    return None


def _sandbox1345():
    return None


def _sandbox1346():
    return None


def _sandbox1347():
    return None


def _sandbox1348():
    return None


def _sandbox1349():
    return None


def _sandbox1350():
    return None


def _sandbox1351():
    return None


def _sandbox1352():
    return None


def _sandbox1353():
    return None


def _sandbox1354():
    return None


def _sandbox1355():
    return None


def _sandbox1356():
    return None


def _sandbox1357():
    return None


def _sandbox1358():
    return None


def _sandbox1359():
    return None


def _sandbox1360():
    return None


def _sandbox1361():
    return None


def _sandbox1362():
    return None


def _sandbox1363():
    return None


def _sandbox1364():
    return None


def _sandbox1365():
    return None


def _sandbox1366():
    return None


def _sandbox1367():
    return None


def _sandbox1368():
    return None


def _sandbox1369():
    return None


def _sandbox1370():
    return None


def _sandbox1371():
    return None


def _sandbox1372():
    return None


def _sandbox1373():
    return None


def _sandbox1374():
    return None


def _sandbox1375():
    return None


def _sandbox1376():
    return None


def _sandbox1377():
    return None


def _sandbox1378():
    return None


def _sandbox1379():
    return None


def _sandbox1380():
    return None


def _sandbox1381():
    return None


def _sandbox1382():
    return None


def _sandbox1383():
    return None


def _sandbox1384():
    return None


def _sandbox1385():
    return None


def _sandbox1386():
    return None


def _sandbox1387():
    return None


def _sandbox1388():
    return None


def _sandbox1389():
    return None


def _sandbox1390():
    return None


def _sandbox1391():
    return None


def _sandbox1392():
    return None


def _sandbox1393():
    return None


def _sandbox1394():
    return None


def _sandbox1395():
    return None


def _sandbox1396():
    return None


def _sandbox1397():
    return None


def _sandbox1398():
    return None


def _sandbox1399():
    return None


def _sandbox1400():
    return None


def _sandbox1401():
    return None


def _sandbox1402():
    return None


def _sandbox1403():
    return None


def _sandbox1404():
    return None


def _sandbox1405():
    return None


def _sandbox1406():
    return None


def _sandbox1407():
    return None


def _sandbox1408():
    return None


def _sandbox1409():
    return None


def _sandbox1410():
    return None


def _sandbox1411():
    return None


def _sandbox1412():
    return None


def _sandbox1413():
    return None


def _sandbox1414():
    return None


def _sandbox1415():
    return None


def _sandbox1416():
    return None


def _sandbox1417():
    return None


def _sandbox1418():
    return None


def _sandbox1419():
    return None


def _sandbox1420():
    return None


def _sandbox1421():
    return None


def _sandbox1422():
    return None


def _sandbox1423():
    return None


def _sandbox1424():
    return None


def _sandbox1425():
    return None


def _sandbox1426():
    return None


def _sandbox1427():
    return None


def _sandbox1428():
    return None


def _sandbox1429():
    return None


def _sandbox1430():
    return None


def _sandbox1431():
    return None


def _sandbox1432():
    return None


def _sandbox1433():
    return None


def _sandbox1434():
    return None


def _sandbox1435():
    return None


def _sandbox1436():
    return None


def _sandbox1437():
    return None


def _sandbox1438():
    return None


def _sandbox1439():
    return None


def _sandbox1440():
    return None


def _sandbox1441():
    return None


def _sandbox1442():
    return None


def _sandbox1443():
    return None


def _sandbox1444():
    return None


def _sandbox1445():
    return None


def _sandbox1446():
    return None


def _sandbox1447():
    return None


def _sandbox1448():
    return None


def _sandbox1449():
    return None


def _sandbox1450():
    return None


def _sandbox1451():
    return None


def _sandbox1452():
    return None


def _sandbox1453():
    return None


def _sandbox1454():
    return None


def _sandbox1455():
    return None


def _sandbox1456():
    return None


def _sandbox1457():
    return None


def _sandbox1458():
    return None


def _sandbox1459():
    return None


def _sandbox1460():
    return None


def _sandbox1461():
    return None


def _sandbox1462():
    return None


def _sandbox1463():
    return None


def _sandbox1464():
    return None


def _sandbox1465():
    return None


def _sandbox1466():
    return None


def _sandbox1467():
    return None


def _sandbox1468():
    return None


def _sandbox1469():
    return None


def _sandbox1470():
    return None


def _sandbox1471():
    return None


def _sandbox1472():
    return None


def _sandbox1473():
    return None


def _sandbox1474():
    return None


def _sandbox1475():
    return None


def _sandbox1476():
    return None


def _sandbox1477():
    return None


def _sandbox1478():
    return None


def _sandbox1479():
    return None


def _sandbox1480():
    return None


def _sandbox1481():
    return None


def _sandbox1482():
    return None


def _sandbox1483():
    return None


def _sandbox1484():
    return None


def _sandbox1485():
    return None


def _sandbox1486():
    return None


def _sandbox1487():
    return None


def _sandbox1488():
    return None


def _sandbox1489():
    return None


def _sandbox1490():
    return None


def _sandbox1491():
    return None


def _sandbox1492():
    return None


def _sandbox1493():
    return None


def _sandbox1494():
    return None


def _sandbox1495():
    return None


def _sandbox1496():
    return None


def _sandbox1497():
    return None


def _sandbox1498():
    return None


def _sandbox1499():
    return None


def _sandbox1500():
    return None


def _sandbox1501():
    return None


def _sandbox1502():
    return None


def _sandbox1503():
    return None


def _sandbox1504():
    return None


def _sandbox1505():
    return None


def _sandbox1506():
    return None


def _sandbox1507():
    return None


def _sandbox1508():
    return None


def _sandbox1509():
    return None


def _sandbox1510():
    return None


def _sandbox1511():
    return None


def _sandbox1512():
    return None


def _sandbox1513():
    return None


def _sandbox1514():
    return None


def _sandbox1515():
    return None


def _sandbox1516():
    return None


def _sandbox1517():
    return None


def _sandbox1518():
    return None


def _sandbox1519():
    return None


def _sandbox1520():
    return None


def _sandbox1521():
    return None


def _sandbox1522():
    return None


def _sandbox1523():
    return None


def _sandbox1524():
    return None


def _sandbox1525():
    return None


def _sandbox1526():
    return None


def _sandbox1527():
    return None


def _sandbox1528():
    return None


def _sandbox1529():
    return None


def _sandbox1530():
    return None


def _sandbox1531():
    return None


def _sandbox1532():
    return None


def _sandbox1533():
    return None


def _sandbox1534():
    return None


def _sandbox1535():
    return None


def _sandbox1536():
    return None


def _sandbox1537():
    return None


def _sandbox1538():
    return None


def _sandbox1539():
    return None


def _sandbox1540():
    return None


def _sandbox1541():
    return None


def _sandbox1542():
    return None


def _sandbox1543():
    return None


def _sandbox1544():
    return None


def _sandbox1545():
    return None


def _sandbox1546():
    return None


def _sandbox1547():
    return None


def _sandbox1548():
    return None


def _sandbox1549():
    return None


def _sandbox1550():
    return None


def _sandbox1551():
    return None


def _sandbox1552():
    return None


def _sandbox1553():
    return None


def _sandbox1554():
    return None


def _sandbox1555():
    return None


def _sandbox1556():
    return None


def _sandbox1557():
    return None


def _sandbox1558():
    return None


def _sandbox1559():
    return None


def _sandbox1560():
    return None


def _sandbox1561():
    return None


def _sandbox1562():
    return None


def _sandbox1563():
    return None


def _sandbox1564():
    return None


def _sandbox1565():
    return None


def _sandbox1566():
    return None


def _sandbox1567():
    return None


def _sandbox1568():
    return None


def _sandbox1569():
    return None


def _sandbox1570():
    return None


def _sandbox1571():
    return None


def _sandbox1572():
    return None


def _sandbox1573():
    return None


def _sandbox1574():
    return None


def _sandbox1575():
    return None


def _sandbox1576():
    return None


def _sandbox1577():
    return None


def _sandbox1578():
    return None


def _sandbox1579():
    return None


def _sandbox1580():
    return None


def _sandbox1581():
    return None


def _sandbox1582():
    return None


def _sandbox1583():
    return None


def _sandbox1584():
    return None


def _sandbox1585():
    return None


def _sandbox1586():
    return None


def _sandbox1587():
    return None


def _sandbox1588():
    return None


def _sandbox1589():
    return None


def _sandbox1590():
    return None


def _sandbox1591():
    return None


def _sandbox1592():
    return None


def _sandbox1593():
    return None


def _sandbox1594():
    return None


def _sandbox1595():
    return None


def _sandbox1596():
    return None


def _sandbox1597():
    return None


def _sandbox1598():
    return None


def _sandbox1599():
    return None


def _sandbox1600():
    return None


def _sandbox1601():
    return None


def _sandbox1602():
    return None


def _sandbox1603():
    return None


def _sandbox1604():
    return None


def _sandbox1605():
    return None


def _sandbox1606():
    return None


def _sandbox1607():
    return None


def _sandbox1608():
    return None


def _sandbox1609():
    return None


def _sandbox1610():
    return None


def _sandbox1611():
    return None


def _sandbox1612():
    return None


def _sandbox1613():
    return None


def _sandbox1614():
    return None


def _sandbox1615():
    return None


def _sandbox1616():
    return None


def _sandbox1617():
    return None


def _sandbox1618():
    return None


def _sandbox1619():
    return None


def _sandbox1620():
    return None


def _sandbox1621():
    return None


def _sandbox1622():
    return None


def _sandbox1623():
    return None


def _sandbox1624():
    return None


def _sandbox1625():
    return None


def _sandbox1626():
    return None


def _sandbox1627():
    return None


def _sandbox1628():
    return None


def _sandbox1629():
    return None


def _sandbox1630():
    return None


def _sandbox1631():
    return None


def _sandbox1632():
    return None


def _sandbox1633():
    return None


def _sandbox1634():
    return None


def _sandbox1635():
    return None


def _sandbox1636():
    return None


def _sandbox1637():
    return None


def _sandbox1638():
    return None


def _sandbox1639():
    return None


def _sandbox1640():
    return None


def _sandbox1641():
    return None


def _sandbox1642():
    return None


def _sandbox1643():
    return None


def _sandbox1644():
    return None


def _sandbox1645():
    return None


def _sandbox1646():
    return None


def _sandbox1647():
    return None


def _sandbox1648():
    return None


def _sandbox1649():
    return None


def _sandbox1650():
    return None


def _sandbox1651():
    return None


def _sandbox1652():
    return None


def _sandbox1653():
    return None


def _sandbox1654():
    return None


def _sandbox1655():
    return None


def _sandbox1656():
    return None


def _sandbox1657():
    return None


def _sandbox1658():
    return None


def _sandbox1659():
    return None


def _sandbox1660():
    return None


def _sandbox1661():
    return None


def _sandbox1662():
    return None


def _sandbox1663():
    return None


def _sandbox1664():
    return None


def _sandbox1665():
    return None


def _sandbox1666():
    return None


def _sandbox1667():
    return None


def _sandbox1668():
    return None


def _sandbox1669():
    return None


def _sandbox1670():
    return None


def _sandbox1671():
    return None


def _sandbox1672():
    return None


def _sandbox1673():
    return None


def _sandbox1674():
    return None


def _sandbox1675():
    return None


def _sandbox1676():
    return None


def _sandbox1677():
    return None


def _sandbox1678():
    return None


def _sandbox1679():
    return None


def _sandbox1680():
    return None


def _sandbox1681():
    return None


def _sandbox1682():
    return None


def _sandbox1683():
    return None


def _sandbox1684():
    return None


def _sandbox1685():
    return None


def _sandbox1686():
    return None


def _sandbox1687():
    return None


def _sandbox1688():
    return None


def _sandbox1689():
    return None


def _sandbox1690():
    return None


def _sandbox1691():
    return None


def _sandbox1692():
    return None


def _sandbox1693():
    return None


def _sandbox1694():
    return None


def _sandbox1695():
    return None


def _sandbox1696():
    return None


def _sandbox1697():
    return None


def _sandbox1698():
    return None


def _sandbox1699():
    return None


def _sandbox1700():
    return None


def _sandbox1701():
    return None


def _sandbox1702():
    return None


def _sandbox1703():
    return None


def _sandbox1704():
    return None


def _sandbox1705():
    return None


def _sandbox1706():
    return None


def _sandbox1707():
    return None


def _sandbox1708():
    return None


def _sandbox1709():
    return None


def _sandbox1710():
    return None


def _sandbox1711():
    return None


def _sandbox1712():
    return None


def _sandbox1713():
    return None


def _sandbox1714():
    return None


def _sandbox1715():
    return None


def _sandbox1716():
    return None


def _sandbox1717():
    return None


def _sandbox1718():
    return None


def _sandbox1719():
    return None


def _sandbox1720():
    return None


def _sandbox1721():
    return None


def _sandbox1722():
    return None


def _sandbox1723():
    return None


def _sandbox1724():
    return None


def _sandbox1725():
    return None


def _sandbox1726():
    return None


def _sandbox1727():
    return None


def _sandbox1728():
    return None


def _sandbox1729():
    return None


def _sandbox1730():
    return None


def _sandbox1731():
    return None


def _sandbox1732():
    return None


def _sandbox1733():
    return None


def _sandbox1734():
    return None


def _sandbox1735():
    return None


def _sandbox1736():
    return None


def _sandbox1737():
    return None


def _sandbox1738():
    return None


def _sandbox1739():
    return None


def _sandbox1740():
    return None


def _sandbox1741():
    return None


def _sandbox1742():
    return None


def _sandbox1743():
    return None


def _sandbox1744():
    return None


def _sandbox1745():
    return None


def _sandbox1746():
    return None


def _sandbox1747():
    return None


def _sandbox1748():
    return None


def _sandbox1749():
    return None


def _sandbox1750():
    return None


def _sandbox1751():
    return None


def _sandbox1752():
    return None


def _sandbox1753():
    return None


def _sandbox1754():
    return None


def _sandbox1755():
    return None


def _sandbox1756():
    return None


def _sandbox1757():
    return None


def _sandbox1758():
    return None


def _sandbox1759():
    return None


def _sandbox1760():
    return None


def _sandbox1761():
    return None


def _sandbox1762():
    return None


def _sandbox1763():
    return None


def _sandbox1764():
    return None


def _sandbox1765():
    return None


def _sandbox1766():
    return None


def _sandbox1767():
    return None


def _sandbox1768():
    return None


def _sandbox1769():
    return None


def _sandbox1770():
    return None


def _sandbox1771():
    return None


def _sandbox1772():
    return None


def _sandbox1773():
    return None


def _sandbox1774():
    return None


def _sandbox1775():
    return None


def _sandbox1776():
    return None


def _sandbox1777():
    return None


def _sandbox1778():
    return None


def _sandbox1779():
    return None


def _sandbox1780():
    return None


def _sandbox1781():
    return None


def _sandbox1782():
    return None


def _sandbox1783():
    return None


def _sandbox1784():
    return None


def _sandbox1785():
    return None


def _sandbox1786():
    return None


def _sandbox1787():
    return None


def _sandbox1788():
    return None


def _sandbox1789():
    return None


def _sandbox1790():
    return None


def _sandbox1791():
    return None


def _sandbox1792():
    return None


def _sandbox1793():
    return None


def _sandbox1794():
    return None


def _sandbox1795():
    return None


def _sandbox1796():
    return None


def _sandbox1797():
    return None


def _sandbox1798():
    return None


def _sandbox1799():
    return None


def _sandbox1800():
    return None


def _sandbox1801():
    return None


def _sandbox1802():
    return None


def _sandbox1803():
    return None


def _sandbox1804():
    return None


def _sandbox1805():
    return None


def _sandbox1806():
    return None


def _sandbox1807():
    return None


def _sandbox1808():
    return None


def _sandbox1809():
    return None


def _sandbox1810():
    return None


def _sandbox1811():
    return None


def _sandbox1812():
    return None


def _sandbox1813():
    return None


def _sandbox1814():
    return None


def _sandbox1815():
    return None


def _sandbox1816():
    return None


def _sandbox1817():
    return None


def _sandbox1818():
    return None


def _sandbox1819():
    return None


def _sandbox1820():
    return None


def _sandbox1821():
    return None


def _sandbox1822():
    return None


def _sandbox1823():
    return None


def _sandbox1824():
    return None


def _sandbox1825():
    return None


def _sandbox1826():
    return None


def _sandbox1827():
    return None


def _sandbox1828():
    return None


def _sandbox1829():
    return None


def _sandbox1830():
    return None


def _sandbox1831():
    return None


def _sandbox1832():
    return None


def _sandbox1833():
    return None


def _sandbox1834():
    return None


def _sandbox1835():
    return None


def _sandbox1836():
    return None


def _sandbox1837():
    return None


def _sandbox1838():
    return None


def _sandbox1839():
    return None


def _sandbox1840():
    return None


def _sandbox1841():
    return None


def _sandbox1842():
    return None


def _sandbox1843():
    return None


def _sandbox1844():
    return None


def _sandbox1845():
    return None


def _sandbox1846():
    return None


def _sandbox1847():
    return None


def _sandbox1848():
    return None


def _sandbox1849():
    return None


def _sandbox1850():
    return None


def _sandbox1851():
    return None


def _sandbox1852():
    return None


def _sandbox1853():
    return None


def _sandbox1854():
    return None


def _sandbox1855():
    return None


def _sandbox1856():
    return None


def _sandbox1857():
    return None


def _sandbox1858():
    return None


def _sandbox1859():
    return None


def _sandbox1860():
    return None


def _sandbox1861():
    return None


def _sandbox1862():
    return None


def _sandbox1863():
    return None


def _sandbox1864():
    return None


def _sandbox1865():
    return None


def _sandbox1866():
    return None


def _sandbox1867():
    return None


def _sandbox1868():
    return None


def _sandbox1869():
    return None


def _sandbox1870():
    return None


def _sandbox1871():
    return None


def _sandbox1872():
    return None


def _sandbox1873():
    return None


def _sandbox1874():
    return None


def _sandbox1875():
    return None


def _sandbox1876():
    return None


def _sandbox1877():
    return None


def _sandbox1878():
    return None


def _sandbox1879():
    return None


def _sandbox1880():
    return None


def _sandbox1881():
    return None


def _sandbox1882():
    return None


def _sandbox1883():
    return None


def _sandbox1884():
    return None


def _sandbox1885():
    return None


def _sandbox1886():
    return None


def _sandbox1887():
    return None


def _sandbox1888():
    return None


def _sandbox1889():
    return None


def _sandbox1890():
    return None


def _sandbox1891():
    return None


def _sandbox1892():
    return None


def _sandbox1893():
    return None


def _sandbox1894():
    return None


def _sandbox1895():
    return None


def _sandbox1896():
    return None


def _sandbox1897():
    return None


def _sandbox1898():
    return None


def _sandbox1899():
    return None


def _sandbox1900():
    return None


def _sandbox1901():
    return None


def _sandbox1902():
    return None


def _sandbox1903():
    return None


def _sandbox1904():
    return None


def _sandbox1905():
    return None


def _sandbox1906():
    return None


def _sandbox1907():
    return None


def _sandbox1908():
    return None


def _sandbox1909():
    return None


def _sandbox1910():
    return None


def _sandbox1911():
    return None


def _sandbox1912():
    return None


def _sandbox1913():
    return None


def _sandbox1914():
    return None


def _sandbox1915():
    return None


def _sandbox1916():
    return None


def _sandbox1917():
    return None


def _sandbox1918():
    return None


def _sandbox1919():
    return None


def _sandbox1920():
    return None


def _sandbox1921():
    return None


def _sandbox1922():
    return None


def _sandbox1923():
    return None


def _sandbox1924():
    return None


def _sandbox1925():
    return None


def _sandbox1926():
    return None


def _sandbox1927():
    return None


def _sandbox1928():
    return None


def _sandbox1929():
    return None


def _sandbox1930():
    return None


def _sandbox1931():
    return None


def _sandbox1932():
    return None


def _sandbox1933():
    return None


def _sandbox1934():
    return None


def _sandbox1935():
    return None


def _sandbox1936():
    return None


def _sandbox1937():
    return None


def _sandbox1938():
    return None


def _sandbox1939():
    return None


def _sandbox1940():
    return None


def _sandbox1941():
    return None


def _sandbox1942():
    return None


def _sandbox1943():
    return None


def _sandbox1944():
    return None


def _sandbox1945():
    return None


def _sandbox1946():
    return None


def _sandbox1947():
    return None


def _sandbox1948():
    return None


def _sandbox1949():
    return None


def _sandbox1950():
    return None


def _sandbox1951():
    return None


def _sandbox1952():
    return None


def _sandbox1953():
    return None


def _sandbox1954():
    return None


def _sandbox1955():
    return None


def _sandbox1956():
    return None


def _sandbox1957():
    return None


def _sandbox1958():
    return None


def _sandbox1959():
    return None


def _sandbox1960():
    return None


def _sandbox1961():
    return None


def _sandbox1962():
    return None


def _sandbox1963():
    return None


def _sandbox1964():
    return None


def _sandbox1965():
    return None


def _sandbox1966():
    return None


def _sandbox1967():
    return None


def _sandbox1968():
    return None


def _sandbox1969():
    return None


def _sandbox1970():
    return None


def _sandbox1971():
    return None


def _sandbox1972():
    return None


def _sandbox1973():
    return None


def _sandbox1974():
    return None


def _sandbox1975():
    return None


def _sandbox1976():
    return None


def _sandbox1977():
    return None


def _sandbox1978():
    return None


def _sandbox1979():
    return None


def _sandbox1980():
    return None


def _sandbox1981():
    return None


def _sandbox1982():
    return None


def _sandbox1983():
    return None


def _sandbox1984():
    return None


def _sandbox1985():
    return None


def _sandbox1986():
    return None


def _sandbox1987():
    return None


def _sandbox1988():
    return None


def _sandbox1989():
    return None


def _sandbox1990():
    return None


def _sandbox1991():
    return None


def _sandbox1992():
    return None


def _sandbox1993():
    return None


def _sandbox1994():
    return None


def _sandbox1995():
    return None


def _sandbox1996():
    return None


def _sandbox1997():
    return None


def _sandbox1998():
    return None


def _sandbox1999():
    return None


def _sandbox2000():
    return None


def _sandbox2001():
    return None


def _sandbox2002():
    return None


def _sandbox2003():
    return None


def _sandbox2004():
    return None


def _sandbox2005():
    return None


def _sandbox2006():
    return None


def _sandbox2007():
    return None


def _sandbox2008():
    return None


def _sandbox2009():
    return None


def _sandbox2010():
    return None


def _sandbox2011():
    return None


def _sandbox2012():
    return None


def _sandbox2013():
    return None


def _sandbox2014():
    return None


def _sandbox2015():
    return None


def _sandbox2016():
    return None


def _sandbox2017():
    return None


def _sandbox2018():
    return None


def _sandbox2019():
    return None


def _sandbox2020():
    return None


# ==============================================

def format_coins(amount):
    return f"{int(amount):,}"

def credit_wallet(user, amount):
    """Credit only non-negative coins and return the resulting wallet."""
    amount = max(0, int(amount))
    user["wallet"] += amount
    return user["wallet"]

def debit_wallet(user, amount):
    """Debit the full amount only when the wallet can cover it."""
    amount = int(amount)
    if amount < 0 or user["wallet"] < amount:
        return False
    user["wallet"] -= amount
    return True

def transfer_wallet(sender, receiver, amount):
    """Move wallet coins atomically between normalized users."""
    amount = int(amount)
    if amount <= 0 or not debit_wallet(sender, amount):
        return False
    credit_wallet(receiver, amount)
    return True

def debit_available_balance(user, amount):
    """Spend from wallet first, then bank; crypto holdings remain untouched."""
    amount = int(amount)
    if amount < 0 or user["wallet"] + user["bank"] < amount:
        return False
    from_wallet = min(user["wallet"], amount)
    user["wallet"] -= from_wallet
    user["bank"] -= amount - from_wallet
    return True

DAILY_BASE_START = 5_000
DAILY_BASE_DAY_FIVE = 10_000
DAILY_STREAK_RAMP_DAYS = 5
HUNT_MAX_LEVEL = 100_000
HUNT_STAGES = (
    (1, "New Paw", 1.00),
    (10, "Scout", 1.05),
    (100, "Tracker", 1.10),
    (1_000, "Hunter", 1.20),
    (5_000, "Ranger", 1.35),
    (10_000, "Elite Hunter", 1.50),
    (25_000, "Master Hunter", 1.70),
    (50_000, "Legendary Hunter", 1.90),
    (75_000, "Mythic Hunter", 2.10),
    (100_000, "Grandmaster Hunter", 2.50),
)
DAILY_QUEST_TEMPLATES = (
    ("games", "Play 3 games", 3, 1_000),
    ("wins", "Win 2 games", 2, 1_500),
    ("hunt", "Hunt 3 times", 3, 1_000),
    ("wager", "Wager 10,000 uwuncy", 10_000, 1_500),
)
ACHIEVEMENT_DEFINITIONS = {
    "first_game": ("First Game", "Complete your first game", 500),
    "first_win": ("First Win", "Win your first game", 750),
    "games_10": ("Getting Started", "Play 10 games", 1_000),
    "wins_10": ("On a Roll", "Win 10 games", 2_000),
    "daily_7": ("Weekly Habit", "Reach a 7-day daily streak", 2_500),
    "millionaire": ("Millionaire", "Reach 1,000,000 total uwuncy", 10_000),
}

def utc_date():
    return datetime.now(timezone.utc).date().isoformat()

def daily_base_for_streak(streak):
    """Ramp from 5,000 on day one to 10,000 by day five."""
    if streak <= 1:
        return DAILY_BASE_START
    step = (DAILY_BASE_DAY_FIVE - DAILY_BASE_START) / (DAILY_STREAK_RAMP_DAYS - 1)
    return min(DAILY_BASE_DAY_FIVE, int(DAILY_BASE_START + (streak - 1) * step))

def get_hunt_stage(level):
    level = max(1, min(HUNT_MAX_LEVEL, int(level)))
    current = HUNT_STAGES[0]
    for stage in HUNT_STAGES:
        if level >= stage[0]:
            current = stage
        else:
            break
    return current

def hunt_reward(level, boosted=False, rng=None):
    """Calculate the reward for a Hunt level and stage."""
    level = max(1, min(HUNT_MAX_LEVEL, int(level)))
    rng = rng or random
    base = rng.randint(10, 85)
    stage_level, stage_name, multiplier = get_hunt_stage(level)
    reward = int((base + level // 100) * multiplier)
    if boosted:
        reward = int(reward * 1.5)
    return {
        "base": base,
        "stage_level": stage_level,
        "stage_name": stage_name,
        "multiplier": multiplier,
        "reward": reward,
    }

def advance_hunt(user):
    user["hunt_level"] = min(HUNT_MAX_LEVEL, user["hunt_level"] + 1)
    user["hunt_total"] += 1
    return user["hunt_level"]

def ensure_daily_quests(user):
    today = utc_date()
    if user.get("quest_date") == today and isinstance(user.get("quests"), list):
        return
    chosen = random.sample(DAILY_QUEST_TEMPLATES, 3)
    user["quest_date"] = today
    user["quests"] = [
        {
            "event": event,
            "description": description,
            "target": target,
            "progress": 0,
            "reward": reward,
            "claimed": False,
        }
        for event, description, target, reward in chosen
    ]

def award_xp(user, amount):
    user["xp"] += max(0, int(amount))
    user["level"] = max(1, 1 + user["xp"] // 1_000)

def update_achievements(user):
    total = user["wallet"] + user["bank"]
    _crypto_rows, _crypto_invested, crypto_value, crypto_profit = crypto_portfolio(user)
    _crypto_rows, _crypto_invested, crypto_value, crypto_profit = crypto_portfolio(user)
    checks = {
        "first_game": user["games_played"] >= 1,
        "first_win": user["games_won"] >= 1,
        "games_10": user["games_played"] >= 10,
        "wins_10": user["games_won"] >= 10,
        "daily_7": user["streak"] >= 7,
        "millionaire": total >= 1_000_000,
    }
    for key, unlocked in checks.items():
        if unlocked and key not in user["achievements"]:
            user["achievements"].append(key)
            award_xp(user, 100)
            credit_wallet(user, ACHIEVEMENT_DEFINITIONS[key][2])

def update_quest_progress(user, event, amount=1):
    ensure_daily_quests(user)
    for quest in user["quests"]:
        if quest["event"] != event or quest["claimed"]:
            continue
        quest["progress"] = min(
            quest["target"], quest["progress"] + max(0, int(amount))
        )
        if quest["progress"] >= quest["target"]:
            quest["claimed"] = True
            credit_wallet(user, quest["reward"])
            award_xp(user, 100)

def add_history(user, entry):
    user["history"].insert(0, {
        "time": int(time.time()),
        **entry,
    })
    del user["history"][20:]

def add_jackpot_contribution(bet):
    contribution = max(1, int(bet * 0.01))
    ECONOMY_SETTINGS["jackpot"] += contribution
    return contribution

def start_game(user, bet, game):
    user["games_played"] += 1
    user["total_wagered"] += bet
    award_xp(user, 10)
    update_quest_progress(user, "games")
    update_quest_progress(user, "wager", bet)
    add_jackpot_contribution(bet)
    return ECONOMY_SETTINGS["jackpot"]

def record_game_result(user, game, bet, won, amount):
    if won:
        user["games_won"] += 1
        user["total_won"] += max(0, int(amount))
        award_xp(user, 25)
        update_quest_progress(user, "wins")
    else:
        user["games_lost"] += 1
        user["total_lost"] += max(0, int(amount))
    add_history(user, {
        "type": game,
        "result": "win" if won else "loss",
        "bet": int(bet),
        "amount": int(amount),
    })
    award_season_score(user, 10 + (25 if won else 0))
    update_achievements(user)

def game_bet_limit_message(game, bet):
    limits = GAME_BET_LIMITS.get(game)
    if not limits:
        return None
    minimum = int(limits.get("min", 1))
    maximum = int(limits.get("max", 0))
    if bet < minimum:
        return (
            f"Minimum **{game}** bet is "
            f"`{format_coins(minimum)}` uwuncy."
        )
    if maximum and bet > maximum:
        return (
            f"Maximum **{game}** bet is "
            f"`{format_coins(maximum)}` uwuncy."
        )
    return None


def validate_bet(user, bet, game=None):
    if bet <= 0:
        return "Bet must be greater than zero."
    if game:
        limit_error = game_bet_limit_message(game, bet)
        if limit_error:
            return limit_error
    if user["wallet"] < bet:
        return (
            f"Not enough uwuncy. Wallet: `{format_coins(user['wallet'])}` uwuncy."
        )
    return bet_limit_message(user, bet)

def apply_bank_interest(user):
    """Apply 1% daily bank interest once per elapsed UTC day."""
    now = time.time()
    if not user.get("last_interest"):
        user["last_interest"] = now
        return 0
    elapsed_days = int((now - user["last_interest"]) // 86400)
    if elapsed_days < 1:
        return 0
    days = min(elapsed_days, 30)
    earned = int(user["bank"] * 0.01 * days)
    user["bank"] += earned
    user["interest_earned"] += earned
    user["last_interest"] += days * 86400
    if earned:
        add_history(user, {
            "type": "bank_interest",
            "result": "reward",
            "bet": 0,
            "amount": earned,
        })
    return earned

def bet_limit_message(user, bet):
    percent = ECONOMY_SETTINGS.get("max_bet_percent", 0)
    if not ECONOMY_SETTINGS.get("bet_cap_enabled", True) or percent <= 0:
        return None
    limit = int(user["wallet"] * percent / 100)
    if bet > limit:
        return (
            f"Maximum bet is **{percent:.1f}%** of your wallet: "
            f"`{format_coins(limit)}` uwuncy."
        )
    return None

def jackpot_payout(user, game, bet):
    """Award and reset the global jackpot after a winning trigger."""
    amount = int(ECONOMY_SETTINGS["jackpot"])
    if amount <= 0:
        return 0
    ECONOMY_SETTINGS["jackpot"] = DEFAULT_ECONOMY_SETTINGS["jackpot"]
    save_economy_settings()
    credit_wallet(user, amount)
    award_xp(user, 250)
    add_history(user, {
        "type": f"{game}_jackpot",
        "result": "win",
        "bet": int(bet),
        "amount": amount,
    })
    update_achievements(user)
    return amount

def normalize_user(user):
    """Keep older Firebase accounts compatible with the current economy schema."""
    user.setdefault("wallet", 0)
    user.setdefault("last_booster_claim", 0)
    if not isinstance(user.get("booster_passes"), dict):
        user["booster_passes"] = {}
    user.setdefault("last_lump_sum", 0)
    user.setdefault("birthday", "")
    user.setdefault("bank", 0)
    user.setdefault("last_daily", 0)
    user.setdefault("last_hunt", 0)
    user.setdefault("hunt_level", 1)
    user.setdefault("hunt_total", 0)
    user.setdefault("streak", 0)
    user.setdefault("last_interest", 0)
    user.setdefault("interest_earned", 0)
    user.setdefault("xp", 0)
    user.setdefault("level", 1)
    user.setdefault("prestige", 0)
    user.setdefault("prestige_points", 0)
    if not isinstance(user.get("properties"), list):
        user["properties"] = []
    if not isinstance(user.get("collection"), list):
        user["collection"] = []
    user.setdefault("season_score", 0)
    user.setdefault("season_key", utc_date()[:7])
    user.setdefault("season_claimed", False)
    user.setdefault("clan_id", "")
    if not isinstance(user.get("clan_invites"), list):
        user["clan_invites"] = []
    user.setdefault("games_played", 0)
    user.setdefault("games_won", 0)
    user.setdefault("games_lost", 0)
    user.setdefault("total_wagered", 0)
    user.setdefault("total_won", 0)
    user.setdefault("total_lost", 0)
    if not isinstance(user.get("achievements"), list):
        user["achievements"] = []
    if not isinstance(user.get("history"), list):
        user["history"] = []
    if not isinstance(user.get("quests"), list):
        user["quests"] = []
    user.setdefault("quest_date", "")
    user["crypto_private"] = bool(user.get("crypto_private", False))
    user.setdefault("marriage_partner_id", "")
    user.setdefault("marriage_date", 0)
    user.setdefault("marriage_level", 0)
    user.setdefault("marriage_exp", 0)
    user.setdefault("marriage_wallet", 0)
    user.setdefault("marriage_badge", "")
    user.setdefault("charisma", 0)
    if not isinstance(user.get("flowers"), dict):
        user["flowers"] = {}
    user.setdefault("saved_playlists", [])
    user["level"] = max(int(user.get("level", 1)), 1 + int(user.get("xp", 0)) // 1_000)
    inventory = user.get("inventory")
    if not isinstance(inventory, list):
        user["inventory"] = []
    if not isinstance(user.get("crypto_positions"), dict):
        user["crypto_positions"] = {}
    return user

def marriage_badge_name(level: int) -> str:
    level = max(1, min(int(level or 1), 100))
    return f"💍 Marriage Badge Lv {level}"

async def fetch_lyrics(song_name: str):
    if not song_name:
        return None
    query = quote_plus(song_name)
    urls = [
        f"https://some-random-api.ml/lyrics?title={query}",
    ]
    for url in urls:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status != 200:
                        continue
                    data = await resp.json()
                    lyrics = data.get("lyrics") or data.get("lyrics_body")
                    author = data.get("author") or data.get("artist")
                    if lyrics:
                        return {
                            "title": data.get("title", song_name),
                            "author": author,
                            "lyrics": lyrics,
                        }
        except Exception:
            continue
    return None

async def get_voice_connection(ctx):
    if ctx.guild is None:
        await ctx.send("This command must be used in a server.")
        return None

    if not ctx.author.voice or ctx.author.voice.channel is None:
        await ctx.send("Join a voice channel first.")
        return None

    target_channel = ctx.author.voice.channel
    voice = ctx.guild.voice_client

    if voice:
        if voice.is_connected():
            if voice.channel != target_channel:
                try:
                    await voice.move_to(target_channel)
                except Exception as exc:
                    await ctx.send(f"⚠️ Could not move to your voice channel: `{exc}`")
                    return None
            return voice
        else:
            try:
                await voice.disconnect(force=True)
            except Exception:
                pass

    try:
        return await target_channel.connect(timeout=15.0, reconnect=True, self_deaf=True)
    except Exception as exc:
        err_msg = str(exc)
        if "davey" in err_msg.lower() or "pynacl" in err_msg.lower():
            await ctx.send(f"⚠️ Voice library missing on bot process: `{exc}`\n👉 Run `pip install PyNaCl davey \"discord.py[voice]\"` on your host machine and restart the bot.")
        else:
            await ctx.send(f"⚠️ Could not connect to your voice channel: `{exc}`")
        print(f"Voice connect failed: {exc}")
        return None

def resolve_spotify_url(url: str):
    results = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

    # 1. Spotify Track
    track_m = re.search(r'spotify(?:\.com|:)(?:/embed)?/track[/:]([a-zA-Z0-9]+)', url)
    if track_m:
        t_id = track_m.group(1)
        embed_url = f"https://open.spotify.com/embed/track/{t_id}"
        try:
            req = urllib.request.Request(embed_url, headers=headers)
            with urllib.request.urlopen(req, timeout=8) as resp:
                html = resp.read().decode('utf-8')
                m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html)
                if m:
                    data = json.loads(m.group(1))
                    entity = data.get('props', {}).get('pageProps', {}).get('state', {}).get('data', {}).get('entity', {})
                    t_title = entity.get('title') or entity.get('name')
                    artists = entity.get('artists', [])
                    a_names = ', '.join([a['name'] for a in artists if isinstance(a, dict) and 'name' in a])
                    q = f"{a_names} - {t_title}" if a_names and t_title else (t_title or a_names)
                    if q:
                        results.append({'title': q, 'query': f"ytsearch1:{q} audio"})
                        return results
        except Exception:
            pass

        # Fallback oEmbed for track
        try:
            oembed_url = f"https://open.spotify.com/oembed?url=https://open.spotify.com/track/{t_id}"
            req = urllib.request.Request(oembed_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                title = data.get('title')
                author = data.get('author_name')
                q = f"{author} - {title}" if author and title else title
                if q:
                    results.append({'title': q, 'query': f"ytsearch1:{q} audio"})
                    return results
        except Exception:
            pass

    # 2. Spotify Playlist / Album
    p_m = re.search(r'spotify(?:\.com|:)(?:/embed)?/(playlist|album)[/:]([a-zA-Z0-9]+)', url)
    if p_m:
        p_type = p_m.group(1)
        p_id = p_m.group(2)
        embed_url = f"https://open.spotify.com/embed/{p_type}/{p_id}"
        try:
            req = urllib.request.Request(embed_url, headers=headers)
            with urllib.request.urlopen(req, timeout=8) as resp:
                html = resp.read().decode('utf-8')
                m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html)
                if m:
                    data = json.loads(m.group(1))
                    pageProps = data.get('props', {}).get('pageProps', {})
                    entity = pageProps.get('state', {}).get('data', {}).get('entity', {})
                    tracks = entity.get('trackList', []) or entity.get('tracks', [])
                    for t in tracks:
                        if not isinstance(t, dict):
                            continue
                        t_title = t.get('title') or t.get('name')
                        t_sub = t.get('subtitle')
                        if not t_sub and isinstance(t.get('artists'), list):
                            t_sub = ', '.join([a.get('name') for a in t.get('artists') if isinstance(a, dict) and a.get('name')])
                        q = f"{t_sub} - {t_title}" if t_sub and t_title else (t_title or t_sub)
                        if q:
                            results.append({'title': q, 'query': f"ytsearch1:{q} audio"})
                    if results:
                        return results
        except Exception:
            pass

    # 3. Fallback open.spotify page title / og:title
    headers_browser = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    req = urllib.request.Request(url, headers=headers_browser)
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            og_title = re.search(r'<meta property="og:title" content="([^"]+)"', html)
            og_desc = re.search(r'<meta property="og:description" content="([^"]+)"', html)
            title_str = og_title.group(1) if og_title else ''
            desc_str = og_desc.group(1) if og_desc else ''
            clean_t = title_str.replace(' | Spotify', '').replace(' - song and lyrics by ', ' ').replace(' - Song by ', ' ')
            if clean_t and clean_t != 'Spotify':
                q = f"{clean_t} {desc_str}".strip() if desc_str and not desc_str.startswith("Listen to") else clean_t
                results.append({'title': clean_t, 'query': f"ytsearch1:{q} audio"})
                return results
    except Exception:
        pass

    return results


def resolve_apple_music_url(url: str):
    results = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

    # 1. Lookup Album or Track ID via iTunes Search API
    id_match = re.search(r'/album/[^/]+/([0-9]+)', url) or re.search(r'[?&]i=([0-9]+)', url) or re.search(r'/song/[^/]+/([0-9]+)', url)
    if id_match:
        entity_id = id_match.group(1)
        lookup_url = f"https://itunes.apple.com/lookup?id={entity_id}&entity=song"
        req = urllib.request.Request(lookup_url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                items = data.get('results', [])
                for item in items:
                    if item.get('wrapperType') == 'track' or 'trackName' in item:
                        t_name = item.get('trackName')
                        a_name = item.get('artistName')
                        q = f"{a_name} - {t_name}" if a_name else t_name
                        if q:
                            results.append({'title': q, 'query': f"ytsearch1:{q} audio"})
                if results:
                    return results
        except Exception:
            pass

    # 2. Extract Slug or meta tags from Apple Music URL
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            og_title = re.search(r'<meta property="og:title" content="([^"]+)"', html)
            if og_title:
                clean_t = og_title.group(1).replace(' on Apple Music', '').replace(' Apple Music', '')
                results.append({'title': clean_t, 'query': f"ytsearch1:{clean_t} audio"})
                return results
    except Exception:
        pass

    slug_match = re.search(r'music\.apple\.com/[^/]+/(playlist|album|song)/([^/]+)', url)
    if slug_match:
        slug = slug_match.group(2).replace('-', ' ').title()
        results.append({'title': slug, 'query': f"ytsearch1:{slug} audio"})
        return results

    return results


async def get_or_resolve_stream_url(entry: dict, force_refresh: bool = False) -> str:
    now = time.time()
    cached_url = entry.get("stream_url")
    cached_at = entry.get("resolved_at", 0)

    # Re-extract if stream_url is missing or older than 5 minutes (300s) to avoid 403 stream expiry
    if not force_refresh and cached_url and (now - cached_at < 300):
        return cached_url

    search_query = entry.get("query") or entry.get("webpage_url") or entry.get("title")
    if not search_query:
        if cached_url:
            return cached_url
        raise ValueError("No search query available for track.")

    if not search_query.startswith("http://") and not search_query.startswith("https://") and not search_query.startswith("ytsearch1:"):
        search_query = f"ytsearch1:{search_query}"

    ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)
    info = await asyncio.to_thread(ytdl.extract_info, search_query, download=False)
    if not info:
        if cached_url:
            return cached_url
        raise RuntimeError(f"Could not extract info for query: {search_query}")

    if "entries" in info and isinstance(info["entries"], list) and info["entries"]:
        info = info["entries"][0]

    stream_url = info.get("url")
    if not stream_url and info.get("formats"):
        formats = [f for f in info.get("formats", []) if f.get("acodec") != "none"]
        stream_url = formats[-1].get("url") if formats else None

    if not stream_url:
        if cached_url:
            return cached_url
        raise RuntimeError(f"No valid audio stream URL found for {search_query}")

    entry["stream_url"] = stream_url
    entry["resolved_at"] = now
    if info.get("title"):
        entry["title"] = info["title"]
    if info.get("uploader"):
        entry["uploader"] = info["uploader"]
    if info.get("duration"):
        entry["duration"] = int(info["duration"])

    return stream_url


async def create_music_source(query: str):
    if yt_dlp is None:
        raise RuntimeError("yt-dlp is not installed. Install it in requirements.txt to enable music playback.")

    search_term = query.strip()
    if not search_term:
        raise RuntimeError("You must provide a search term or link.")

    # 1. Spotify URL
    if "spotify.com" in search_term or "spotify:" in search_term:
        spotify_items = await asyncio.to_thread(resolve_spotify_url, search_term)
        if not spotify_items:
            raise RuntimeError("Could not resolve tracks from Spotify link.")
        
        first_item = spotify_items[0]
        try:
            first_stream = await get_or_resolve_stream_url(first_item)
            first_item["stream_url"] = first_stream
        except Exception:
            pass

        entries = []
        for item in spotify_items:
            entries.append({
                "title": item.get("title", search_term),
                "query": item.get("query", search_term),
                "webpage_url": None,
                "stream_url": item.get("stream_url"),
                "duration": item.get("duration", 0),
                "uploader": item.get("uploader", "Spotify"),
            })
        return entries if len(entries) > 1 else entries[0]

    # 2. Apple Music (iMusic) URL
    if "music.apple.com" in search_term or "itunes.apple.com" in search_term:
        apple_items = await asyncio.to_thread(resolve_apple_music_url, search_term)
        if not apple_items:
            raise RuntimeError("Could not resolve tracks from Apple Music link.")

        first_item = apple_items[0]
        try:
            first_stream = await get_or_resolve_stream_url(first_item)
            first_item["stream_url"] = first_stream
        except Exception:
            pass

        entries = []
        for item in apple_items:
            entries.append({
                "title": item.get("title", search_term),
                "query": item.get("query", search_term),
                "webpage_url": None,
                "stream_url": item.get("stream_url"),
                "duration": item.get("duration", 0),
                "uploader": item.get("uploader", "Apple Music"),
            })
        return entries if len(entries) > 1 else entries[0]

    # 3. YouTube URL or Search Query
    ytdl_opts = dict(YTDL_OPTIONS)
    is_url = search_term.startswith("http://") or search_term.startswith("https://")
    search_target = search_term if is_url else f"ytsearch1:{search_term}"

    ytdl = yt_dlp.YoutubeDL(ytdl_opts)
    info = await asyncio.to_thread(ytdl.extract_info, search_target, download=False)
    if not info:
        raise RuntimeError("No results found.")

    entries_list = []
    if "entries" in info and isinstance(info["entries"], list):
        for item in info["entries"]:
            if not item:
                continue
            item_url = item.get("url") or item.get("webpage_url") or (f"https://www.youtube.com/watch?v={item['id']}" if item.get("id") else None)
            entries_list.append({
                "title": item.get("title", search_term),
                "query": item_url or search_term,
                "webpage_url": item_url or search_term,
                "stream_url": item.get("url") if (item.get("url") and "googlevideo.com" in item.get("url")) else None,
                "duration": int(item.get("duration", 0) or 0),
                "uploader": item.get("uploader", "YouTube"),
            })
    else:
        stream_url = info.get("url")
        if not stream_url and info.get("formats"):
            formats = [f for f in info.get("formats", []) if f.get("acodec") != "none"]
            stream_url = formats[-1].get("url") if formats else None

        entries_list.append({
            "title": info.get("title", search_term),
            "query": search_term,
            "webpage_url": info.get("webpage_url", search_term),
            "stream_url": stream_url,
            "duration": int(info.get("duration", 0) or 0),
            "uploader": info.get("uploader", "YouTube"),
        })

    if not entries_list:
        raise RuntimeError("Could not resolve a playable audio stream.")

    if not entries_list[0].get("stream_url"):
        entries_list[0]["stream_url"] = await get_or_resolve_stream_url(entries_list[0])

    return entries_list if len(entries_list) > 1 else entries_list[0]


def get_music_state(guild_id):
    key = str(guild_id)
    return MUSIC_STATES.setdefault(key, {
        "queue": [],
        "current": None,
        "volume": 0.5,
    })

def get_music_lock(guild_id):
    key = str(guild_id)
    lock = MUSIC_LOCKS.get(key)
    if lock is None:
        lock = asyncio.Lock()
        MUSIC_LOCKS[key] = lock
    return lock

async def play_next_track(guild_id: str):
    lock = get_music_lock(guild_id)
    async with lock:
        state = MUSIC_STATES.get(str(guild_id))
        if not state:
            return
        if not state["queue"]:
            state["current"] = None
            return
        next_entry = state["queue"].pop(0)
        state["current"] = next_entry

    guild = bot.get_guild(int(guild_id))
    if guild is None:
        return
    voice = guild.voice_client
    if not voice or not voice.is_connected():
        return

    try:
        # Force refresh stream URL right before playing so YouTube token/URL is never expired
        stream_url = await get_or_resolve_stream_url(next_entry, force_refresh=True)
    except Exception as err:
        print(f"Error resolving stream for {next_entry.get('title')}: {err}")
        return await play_next_track(guild_id)

    if not stream_url:
        return await play_next_track(guild_id)

    try:
        vol = state.get("volume", 0.5)
        player = None

        def create_pcm_player():
            source = discord.FFmpegPCMAudio(stream_url, **FFMPEG_OPTIONS)
            return discord.PCMVolumeTransformer(source, volume=vol)

        player = await asyncio.to_thread(create_pcm_player)

        def after_play(error):
            if error:
                print(f"Music playback error on guild {guild_id}: {error}")
            bot.loop.call_soon_threadsafe(lambda: asyncio.create_task(play_next_track(str(guild_id))))

        voice.play(player, after=after_play)
    except Exception as exc:
        print(f"Failed to play audio stream on guild {guild_id}: {exc}")
        bot.loop.call_soon_threadsafe(lambda: asyncio.create_task(play_next_track(str(guild_id))))

    title = next_entry.get("title")
    duration = next_entry.get("duration", 0)
    minutes, seconds = divmod(duration, 60)
    duration_label = f"{minutes}:{seconds:02d}" if duration else "Unknown"
    coro = guild.system_channel.send if guild.system_channel else None
    if coro is not None and not voice.is_playing():
        # do not spam on every song; system channel may still be appropriate
        pass


def format_music_entry(entry):
    title = entry.get("title", "Unknown")
    duration = entry.get("duration", 0)
    if duration:
        minutes, seconds = divmod(duration, 60)
        return f"{title} ({minutes}:{seconds:02d})"
    return title


def get_user(uid):
    uid = str(uid)  # ✅ GLOBAL DISCORD USER ID — shared across all servers
    if uid not in DATA:
        DATA[uid] = {
            "wallet": 0,
            "bank": 0,
            "last_daily": 0,
            "last_claim": 0,
            "last_hunt": 0,
            "hunt_level": 1,
            "hunt_total": 0,
            "streak": 0,
            "last_interest": 0,
            "interest_earned": 0,
            "xp": 0,
            "level": 1,
            "prestige": 0,
            "prestige_points": 0,
            "properties": [],
            "collection": [],
            "season_score": 0,
            "season_key": utc_date()[:7],
            "season_claimed": False,
            "clan_id": "",
            "clan_invites": [],
            "games_played": 0,
            "games_won": 0,
            "games_lost": 0,
            "total_wagered": 0,
            "total_won": 0,
            "total_lost": 0,
            "achievements": [],
            "history": [],
            "quest_date": "",
            "quests": [],
            "inventory": [],
            "crypto_positions": {},
            "crypto_private": False,
            "marriage_partner_id": "",
            "marriage_date": 0,
            "marriage_level": 0,
            "marriage_exp": 0,
            "marriage_wallet": 0,
            "marriage_badge": "",
            "charisma": 0,
            "flowers": {},
            "saved_playlists": [],
        }
        save_data(DATA)
    return normalize_user(DATA[uid])

def consume_item(user, item):
    inventory = user["inventory"]
    if item not in inventory:
        return False
    inventory.remove(item)
    return True

def count_item(user, item):
    return user["inventory"].count(item)

SHIELD_PROTECTION_TIERS = (
    (1000, 100_000, 0.50),
    (100_000, 500_000, 0.30),
    (500_000, 1_000_000, 0.20),
    (1_000_000, 1_000_000_001, 0.10),
)

def get_shield_protection_rate(bet):
    """Return the fractional protection for a bet, or zero if uncovered."""
    for minimum, maximum_exclusive, rate in SHIELD_PROTECTION_TIERS:
        if minimum <= bet < maximum_exclusive:
            return rate
    return 0.0

def shield_notice(user, bet):
    """Describe the Shield tier before a game resolves."""
    if not count_item(user, "shield"):
        return None
    rate = get_shield_protection_rate(bet)
    if rate == 0:
        return (
            "Loss Shield available, but this bet is outside the protected "
            "range of 1,000–1,000,000,000 uwuncy."
        )
    return (
        f"Loss Shield active: protects **{rate:.0%}** of this bet if you lose."
    )

def settle_loss(user, bet, bet_reserved=False):
    """Apply a loss with tiered Shield protection when the bet is covered."""
    protection_rate = get_shield_protection_rate(bet)
    shielded = protection_rate > 0 and consume_item(user, "shield")
    protected_amount = int(bet * protection_rate) if shielded else 0
    remaining_loss = bet - protected_amount
    if shielded:
        if bet_reserved:
            credit_wallet(user, protected_amount)
        else:
            debit_wallet(user, remaining_loss)
    elif not bet_reserved:
        debit_wallet(user, bet)
    return {
        "shielded": shielded,
        "protected_amount": protected_amount,
        "remaining_loss": remaining_loss,
        "protection_rate": protection_rate if shielded else 0.0,
    }

def describe_loss(loss_result, bet, label="Loss"):
    """Format a consistent loss result for both reserved and instant bets."""
    if loss_result["shielded"]:
        return (
            f"{label}. Loss Shield protected **"
            f"{format_coins(loss_result['protected_amount'])} uwuncy "
            f"({loss_result['protection_rate']:.0%})**. "
            f"Remaining loss: **-{format_coins(loss_result['remaining_loss'])} uwuncy**"
        )
    return f"{label}: **-{format_coins(bet)} uwuncy**"

def settle_win(user, payout):
    """Apply a winning payout and consume one potion for a 15% bonus."""
    boosted = consume_item(user, "luckypot")
    bonus = int(payout * 0.15) if boosted else 0
    total_payout = payout + bonus
    credit_wallet(user, total_payout)
    return total_payout, bonus, boosted

def record_push(user, game, bet, bet_reserved=False):
    # Only an interactive round that reserved its stake needs a push refund.
    if bet_reserved:
        credit_wallet(user, bet)
    add_history(user, {
        "type": game,
        "result": "push",
        "bet": int(bet),
        "amount": int(bet),
    })

def begin_game(user, game, bet, reserve_bet=False):
    """Start a game, optionally reserving the stake for interactive views."""
    if reserve_bet and not debit_wallet(user, bet):
        return False
    start_game(user, bet, game)
    return True

def finish_game(user, game, bet, won, amount):
    record_game_result(user, game, bet, won, amount)

# --- SHOP ITEMS ---
SHOP = {
    "huntboost": {
        "name": "Hunt Boost",
        "price": 2000,
        "uses": 2,
        "desc": "+50% more uwuncy from hunting (2 uses per bundle)",
    },
    "luckypot": {
        "name": "Lucky Potion",
        "price": 25000,
        "uses": 1,
        "desc": "+15% payout on your next winning game (1 use)",
    },
    "bag": {
        "name": "Treasure Bag",
        "price": 2000,
        "uses": 0,
        "desc": "Awards a random 1,000–5,000 uwuncy reward",
    },
    "shield": {
        "name": "Loss Shield",
        "price": 100000,
        "uses": 1,
        "desc": "Protects 50%–10% of one losing bet by tier (1 use)",
    },
}

def purchase_shop_item(user, item, quantity=1):
    """Purchase one or more complete shop bundles without partial charging."""
    if item not in SHOP:
        return None
    if not isinstance(quantity, int) or quantity < 1:
        return None

    shop_item = SHOP[item]
    total_cost = shop_item["price"] * quantity
    if user["wallet"] < total_cost:
        return {
            "ok": False,
            "total_cost": total_cost,
            "quantity": quantity,
            "item": shop_item,
        }

    # Validate the full purchase before mutating the account.
    debit_wallet(user, total_cost)
    if item == "bag":
        reward = sum(random.randint(1000, 5000) for _ in range(quantity))
        credit_wallet(user, reward)
        return {
            "ok": True,
            "total_cost": total_cost,
            "quantity": quantity,
            "reward": reward,
            "item": shop_item,
        }

    granted_uses = shop_item["uses"] * quantity
    user["inventory"].extend([item] * granted_uses)
    return {
        "ok": True,
        "total_cost": total_cost,
        "quantity": quantity,
        "granted_uses": granted_uses,
        "item": shop_item,
    }

def parse_coins(value, wallet_balance=None):
    """Parse a user-entered coin amount, supporting k, m, b, t, q suffixes, decimals, all, and half."""
    if value is None:
        return None
    try:
        text = str(value).strip().replace(",", "").replace("_", "").casefold()
        if text in ["all", "max"]:
            if wallet_balance is not None:
                return max(0, int(wallet_balance))
            return None
        if text in ["half", "1/2"]:
            if wallet_balance is not None:
                return max(0, int(wallet_balance // 2))
            return None

        multiplier = 1
        if text.endswith(("k", "m", "b", "t", "q")):
            suffix = text[-1]
            multiplier = {
                "k": 1_000,
                "m": 1_000_000,
                "b": 1_000_000_000,
                "t": 1_000_000_000_000,
                "q": 1_000_000_000_000_000,
            }[suffix]
            text = text[:-1]

        val = float(text) * multiplier
        if val < 0:
            return None
        return int(val)
    except (TypeError, ValueError):
        return None

# ==============================================
# 🏟️ ARENA GAMES
# ==============================================
ARENA_CREATION_REQUIREMENT = 100_000_000_000
ARENA_PLAYER_REQUIREMENT = 100_000_000_000
ARENA_ENTRY_FEE = 50_000_000_000
ARENA_MATCH_RESERVE = 70_000_000_000
ARENA_ROUND_BET = 10_000_000_000
ARENA_ROUNDS = 7
ARENA_MINES_PHASE_TIMEOUT = 60
ARENA_UNO_TIMEOUT = 180
ARENA_LUCKY9_TIMEOUT = 60
ARENA_DEAL_TIMEOUT = 60
ARENA_DEAL_TILE_COUNT = 20
ARENA_DEAL_ATTEMPTS = 3
ARENA_ROUND_RESULT_DELAY = 5
ARENA_MATCH_WIN_POINTS = 7
ARENA_TEAM_NAMES = {1: "RED", 2: "BLUE"}
ARENA_CHANNEL_LOCKS = {}
ARENA_GAME_VIEWS = {}
ARENA_MATH_VIEWS = {}
# Backward-compatible names used by older arena records and status text.
ARENA_REGISTRATION_FEE = ARENA_ENTRY_FEE
ARENA_MIN_BET = ARENA_ROUND_BET
ARENA_MAX_BET = ARENA_ROUND_BET
ARENA_GAME_POOL = (
    ("dice", "Team Dice Clash"),
    ("highlow", "Team High/Low"),
    ("color", "Color Clash"),
    ("roulette", "Team Roulette"),
    ("number", "Number Duel"),
    ("arena_mines", "Arena Mines"),
    ("coinrush", "Team Coin Rush"),
    ("carddraw", "Team Card Draw"),
    ("treasure", "Team Treasure Hunt"),
    ("battlepower", "Team Battle Power"),
    ("math", "Math Sprint"),
    ("bugtong", "BUGTONG-BUGTONG"),
    ("uno", "UNO"),
    ("lucky9", "LUCKY 9"),
    ("deal_or_no_deal", "DEAL OR NO DEAL"),
)

ARENA_GAME_DESCRIPTIONS = {
    "dice": "Each teammate rolls a die; the higher team total wins.",
    "highlow": "Each teammate draws 1–100; the higher team total wins.",
    "color": "Each teammate draws a color score; the higher team total wins.",
    "roulette": "Each teammate draws a roulette number; the higher team total wins.",
    "number": "Each teammate draws 1–1,000; the higher team total wins.",
    "arena_mines": "One team hides four bombs; the other team must find four safe tiles.",
    "coinrush": "Each teammate flips two coins; the team with more heads wins.",
    "carddraw": "Each teammate draws a playing card from 1–13; the higher total wins.",
    "treasure": "Each teammate opens a random treasure chest; the higher haul wins.",
    "battlepower": "Each teammate rolls a tactical power combo; the higher team power wins.",
    "math": "Both teams race to type the correct answer. The first correct team wins the question.",
    "bugtong": "Read the Filipino riddle and click the correct answer from three choices.",
    "uno": "Play your seven-card hand by matching color or value. Action cards can skip, reverse, and stack draw penalties.",
    "lucky9": "The bot chooses one representative from each team. Representatives reveal two cards, then may stand or draw one optional third card. Highest score wins.",
    "deal_or_no_deal": "Find the shared target number hidden behind 20 briefcase tiles. The bot chooses the first team; each team gets only three public flips.",
}

UNO_COLORS = ("red", "blue", "violet", "green")
UNO_COLOR_EMOJI = {
    "red": "🟥",
    "blue": "🟦",
    "violet": "🟪",
    "green": "🟩",
    "wild": "⬛",
}
UNO_COLOR_LABELS = {
    "red": "Red",
    "blue": "Blue",
    "violet": "Violet",
    "green": "Green",
}
UNO_ACTION_VALUES = {"skip", "reverse", "draw2", "wild", "wild4"}
LUCKY9_SUITS = ("♠", "♥", "♦", "♣")
LUCKY9_RANKS = (
    ("A", 1),
    ("2", 2),
    ("3", 3),
    ("4", 4),
    ("5", 5),
    ("6", 6),
    ("7", 7),
    ("8", 8),
    ("9", 9),
    ("10", 0),
    ("J", 0),
    ("Q", 0),
    ("K", 0),
)

ARENA_BUGTONG_RIDDLES = (
    {
        "prompt": "SA HARAP KO TINAPAT SA BABA LUMABAS",
        "answer": "FLASHLIGHT",
        "choices": ("FLASHLIGHT", "SALAMIN", "PAYONG"),
    },
    {
        "prompt": "MAY PAKPAK, NGUNIT HINDI IBON; LUMILIPAD SA GABI",
        "answer": "PANIKI",
        "choices": ("PANIKI", "ISDA", "KABAYO"),
    },
    {
        "prompt": "MAY BUNTOT AT MAY ULO, PERO WALANG BUHAY",
        "answer": "BARYA",
        "choices": ("BARYA", "PUNO", "SAPATOS"),
    },
    {
        "prompt": "MALIIT PA SI NENENG, PERO MARUNONG NANG UMANGKAS",
        "answer": "KUTSARA",
        "choices": ("KUTSARA", "PUSA", "KANDILA"),
    },
    {
        "prompt": "DALAWANG BALON, HINDI MATA; MALALIM KUNG TINGNAN",
        "answer": "BALON",
        "choices": ("BALON", "TASA", "BINTANA"),
    },
)

def load_arenas():
    try:
        stored = ARENAS_REF.get()
        return stored if isinstance(stored, dict) else {}
    except Exception as exc:
        raise RuntimeError(f"Firebase arena read failed: {exc}") from exc

def save_arenas():
    try:
        ARENAS_REF.set(ARENAS)
    except Exception as exc:
        raise RuntimeError(f"Firebase arena write failed: {exc}") from exc

def load_arena_channels():
    try:
        stored = ARENA_CHANNELS_REF.get()
        return stored if isinstance(stored, dict) else {}
    except Exception as exc:
        raise RuntimeError(f"Firebase arena channel read failed: {exc}") from exc

def save_arena_channels():
    try:
        ARENA_CHANNELS_REF.set(ARENA_CHANNELS)
    except Exception as exc:
        raise RuntimeError(f"Firebase arena channel write failed: {exc}") from exc

def load_arena_channel_redo():
    try:
        stored = ARENA_CHANNEL_REDO_REF.get()
        return stored if isinstance(stored, dict) else {}
    except Exception as exc:
        raise RuntimeError(f"Firebase arena channel redo read failed: {exc}") from exc

def save_arena_channel_redo():
    try:
        ARENA_CHANNEL_REDO_REF.set(ARENA_CHANNEL_REDO)
    except Exception as exc:
        raise RuntimeError(f"Firebase arena channel redo write failed: {exc}") from exc

ARENAS = load_arenas()
ARENA_CHANNELS = load_arena_channels()
ARENA_CHANNEL_REDO = load_arena_channel_redo()

def arena_id():
    return uuid.uuid4().hex[:8].upper()

def active_arena_status(arena):
    return arena.get("status") in {"lobby", "betting", "match"}

def arena_players(arena):
    return list(arena.get("players", {}).keys())

def arena_team_index(arena, user_id):
    user_id = str(user_id)
    for index, team in enumerate(arena.get("teams", []), start=1):
        if user_id in team:
            return index
    return None

def arena_team_name(team_number):
    return ARENA_TEAM_NAMES.get(int(team_number), f"TEAM {team_number}")

def arena_score_token(score):
    return ("0", "I", "II", "III", "IV", "V", "VI", "VII")[
        min(max(int(score), 0), 7)
    ]

def arena_scoreboard(arena):
    wins = arena.get("team_wins", {})
    return (
        f"**{arena_team_name(1)} {arena_score_token(wins.get('1', 0))}**"
        f" | **{arena_team_name(2)} {arena_score_token(wins.get('2', 0))}**"
    )

def arena_has_match_winner(arena):
    wins = arena.get("team_wins", {})
    return any(int(wins.get(str(team), 0)) >= ARENA_MATCH_WIN_POINTS for team in (1, 2))

def arena_winning_team(arena):
    wins = arena.get("team_wins", {})
    for team in (1, 2):
        if int(wins.get(str(team), 0)) >= ARENA_MATCH_WIN_POINTS:
            return team
    return None

def active_arena_for_channel(channel_id):
    channel_id = str(channel_id)
    for current_id, arena in ARENAS.items():
        if (
            arena.get("status") == "match"
            and str(arena.get("channel_id")) == channel_id
        ):
            return current_id, arena
    return None, None

def arena_channel_for_guild(guild):
    if guild is None:
        return None
    channel_id = ARENA_CHANNELS.get(str(guild.id))
    if not channel_id:
        return None
    try:
        return guild.get_channel(int(channel_id))
    except (TypeError, ValueError):
        return None

async def fetch_arena_channel(guild):
    """Resolve the configured arena channel even when it is not in cache."""
    channel = arena_channel_for_guild(guild)
    if channel is not None:
        return channel
    channel_id = str(ARENA_CHANNELS.get(str(getattr(guild, "id", "")), ""))
    if not channel_id.isdigit():
        return None
    try:
        channel = await bot.fetch_channel(int(channel_id))
    except (discord.HTTPException, discord.NotFound):
        return None
    return channel if isinstance(channel, discord.TextChannel) and channel.guild.id == guild.id else None

def resolve_arena_channel(guild, raw_channel):
    if guild is None:
        return None
    raw_channel = str(raw_channel or "").strip()
    match = re.fullmatch(r"<#(\d+)>", raw_channel)
    channel_id = match.group(1) if match else raw_channel
    if not channel_id.isdigit():
        return None
    channel = guild.get_channel(int(channel_id))
    return channel if isinstance(channel, discord.TextChannel) else None

def arena_permission_target_kind(target):
    if isinstance(target, discord.Role):
        return "role"
    if isinstance(target, discord.Member):
        return "member"
    return None

def arena_permission_snapshot_record(target, overwrite):
    target_kind = arena_permission_target_kind(target)
    if target_kind is None:
        return None
    if overwrite is None:
        permission_data = None
    else:
        allow, deny = overwrite.pair()
        permission_data = {
            "allow": int(allow.value),
            "deny": int(deny.value),
        }
    return {
        "target_id": str(target.id),
        "target_kind": target_kind,
        "permissions": permission_data,
    }

def arena_permission_target(guild, record):
    if record.get("target_kind") == "role":
        return guild.get_role(int(record["target_id"]))
    if record.get("target_kind") == "member":
        return guild.get_member(int(record["target_id"]))
    return None

async def restore_arena_permission_target(guild, record):
    target = arena_permission_target(guild, record)
    if target is not None:
        return target
    if record.get("target_kind") == "member":
        try:
            return await guild.fetch_member(int(record["target_id"]))
        except (discord.HTTPException, discord.NotFound):
            return None
    return None

def arena_permission_overwrite(record):
    permissions = record.get("permissions")
    if permissions is None:
        return None
    return discord.PermissionOverwrite.from_pair(
        discord.Permissions(permissions=int(permissions["allow"])),
        discord.Permissions(permissions=int(permissions["deny"])),
    )

async def restore_arena_channel_snapshot(guild, redo_record):
    if guild is None or not isinstance(redo_record, dict):
        return False
    channel_id = str(redo_record.get("channel_id", ""))
    channel = guild.get_channel(int(channel_id)) if channel_id.isdigit() else None
    if not isinstance(channel, discord.TextChannel):
        return False
    restored_any = False
    for record in redo_record.get("snapshot", []):
        if not isinstance(record, dict):
            continue
        target = await restore_arena_permission_target(guild, record)
        if target is None:
            continue
        try:
            await channel.set_permissions(
                target,
                overwrite=arena_permission_overwrite(record),
            )
            restored_any = True
        except discord.HTTPException:
            continue
    return restored_any

def arena_permission_snapshot(channel, target):
    for existing_target, overwrite in channel.overwrites.items():
        if existing_target.id == target.id and type(existing_target) is type(target):
            return overwrite
    return None

async def lock_arena_channel(arena_id_value, arena, channel):
    if channel is None or channel.guild is None:
        return False
    snapshots = {}
    everyone = channel.guild.default_role
    locked_overwrite = discord.PermissionOverwrite(
        view_channel=True,
        read_message_history=True,
        send_messages=False,
        add_reactions=False,
        create_public_threads=False,
        create_private_threads=False,
        send_messages_in_threads=False,
        use_application_commands=False,
    )
    targets = []

    def add_target(target, overwrite):
        key = (type(target).__name__, str(target.id))
        for index, (existing_target, _existing_overwrite) in enumerate(targets):
            if (type(existing_target).__name__, str(existing_target.id)) == key:
                targets[index] = (target, overwrite)
                return
        targets.append((target, overwrite))

    add_target(everyone, locked_overwrite)
    for existing_target, _existing_overwrite in channel.overwrites.items():
        add_target(existing_target, locked_overwrite)

    player_members = []
    for user_id in arena_players(arena):
        try:
            member = channel.guild.get_member(int(user_id))
            if member is None:
                member = await channel.guild.fetch_member(int(user_id))
        except (discord.HTTPException, discord.NotFound, TypeError, ValueError) as exc:
            print(f"❌ Could not fetch arena player {user_id} for arena {arena_id_value}: {exc!r}")
            return False
        player_members.append(member)
        add_target(member, discord.PermissionOverwrite(
            view_channel=True,
            read_message_history=True,
            send_messages=True,
            add_reactions=True,
            create_public_threads=True,
            create_private_threads=True,
            send_messages_in_threads=True,
            use_application_commands=True,
        ))
    if channel.guild.me and all(
        target.id != channel.guild.me.id for target, _overwrite in targets
    ):
        add_target(channel.guild.me, discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            add_reactions=True,
            embed_links=True,
            attach_files=True,
            read_message_history=True,
            send_messages_in_threads=True,
            use_application_commands=True,
        ))
    snapshot_records = []
    for target, _overwrite in targets:
        snapshot = arena_permission_snapshot(channel, target)
        record = arena_permission_snapshot_record(target, snapshot)
        if record is not None:
            snapshot_records.append(record)
    ARENA_CHANNEL_REDO[str(channel.guild.id)] = {
        "guild_id": str(channel.guild.id),
        "channel_id": str(channel.id),
        "arena_id": str(arena_id_value),
        "snapshot": snapshot_records,
        "updated_at": int(time.time()),
    }
    save_arena_channel_redo()
    applied = []
    try:
        for target, overwrite in targets:
            key = (type(target).__name__, str(target.id))
            snapshots[key] = arena_permission_snapshot(channel, target)
            await channel.set_permissions(target, overwrite=overwrite)
            applied.append(target)
    except discord.HTTPException:
        for target in reversed(applied):
            key = (type(target).__name__, str(target.id))
            previous = snapshots.get(key)
            try:
                await channel.set_permissions(target, overwrite=previous)
            except discord.HTTPException:
                pass
        ARENA_CHANNEL_REDO.pop(str(channel.guild.id), None)
        save_arena_channel_redo()
        return False
    ARENA_CHANNEL_LOCKS[arena_id_value] = {
        "channel": channel,
        "snapshots": snapshots,
        "targets": targets,
    }
    arena["channel_id"] = str(channel.id)
    arena["channel_locked"] = True
    return True

def arena_start_is_stale(arena_id_value, arena):
    """Identify a start that failed before a channel lock or round charge."""
    if arena.get("status") != "match":
        return False
    if arena_id_value in ARENA_CHANNEL_LOCKS or arena.get("channel_locked"):
        return False
    return not any(
        isinstance(round_state, dict) and round_state.get("reserve_spent")
        for round_state in arena.get("rounds", [])
    )

def reset_stale_arena_start(arena):
    """Return a pre-lock failed start to its lobby without moving uwuncy."""
    arena["status"] = "lobby"
    arena["round_index"] = 0
    arena["team_wins"] = {"1": 0, "2": 0}
    arena.pop("channel_id", None)
    arena["channel_locked"] = False
    for round_state in arena.get("rounds", []):
        if isinstance(round_state, dict):
            round_state.pop("reserve_spent", None)
            round_state.pop("winner_team", None)
            round_state.pop("scores", None)
    save_arenas()

async def unlock_arena_channel(arena_id_value, arena=None):
    lock = ARENA_CHANNEL_LOCKS.pop(arena_id_value, None)
    if not lock:
        if arena is not None:
            channel_id = str(arena.get("channel_id", ""))
            channel = (
                bot.get_channel(int(channel_id))
                if channel_id.isdigit()
                else None
            )
            guild = getattr(channel, "guild", None)
            if guild is None:
                guild_id = str(arena.get("guild_id", ""))
                guild = bot.get_guild(int(guild_id)) if guild_id.isdigit() else None
            if guild is not None:
                redo_record = ARENA_CHANNEL_REDO.get(str(guild.id))
                if isinstance(redo_record, dict) and str(redo_record.get("channel_id")) == channel_id:
                    await restore_arena_channel_snapshot(guild, redo_record)
                    ARENA_CHANNEL_REDO.pop(str(guild.id), None)
                    save_arena_channel_redo()
        if arena is not None:
            arena["channel_locked"] = False
            save_arenas()
        return
    channel = lock["channel"]
    for target, _overwrite in lock["targets"]:
        key = (type(target).__name__, str(target.id))
        previous = lock["snapshots"].get(key)
        try:
            await channel.set_permissions(target, overwrite=previous)
        except discord.HTTPException:
            pass
    if arena is not None:
        arena["channel_locked"] = False
        guild_id = str(channel.guild.id)
        if str(ARENA_CHANNEL_REDO.get(guild_id, {}).get("arena_id")) == str(arena_id_value):
            ARENA_CHANNEL_REDO.pop(guild_id, None)
            save_arena_channel_redo()
        save_arenas()

async def redo_arena_channel(guild):
    """Restore the persisted pre-match permissions for a guild's arena channel."""
    if guild is None:
        return False, "This command can only be used inside a server."
    configured_channel = arena_channel_for_guild(guild)
    if configured_channel is not None:
        active_id, _active_arena = active_arena_for_channel(configured_channel.id)
        if active_id:
            return False, f"Arena `{active_id}` is active. Finish or cancel it before using channel redo."
    redo_record = ARENA_CHANNEL_REDO.get(str(guild.id))
    if not isinstance(redo_record, dict):
        return False, "There is no saved arena permission change to redo."
    restored = await restore_arena_channel_snapshot(guild, redo_record)
    if not restored:
        return False, "I could not find the saved channel or restore its permissions."
    ARENA_CHANNEL_REDO.pop(str(guild.id), None)
    save_arena_channel_redo()
    return True, "✅ Restored the arena channel's original permissions."

def arena_team_lines(arena):
    lines = []
    for index, team in enumerate(arena.get("teams", []), start=1):
        names = []
        for user_id in team:
            names.append(f"<@{user_id}>")
        lines.append(f"{arena_team_name(index)}: " + (", ".join(names) if names else "Empty"))
    return "\n".join(lines)

def find_user_arena(user_id, status=None):
    matches = []
    user_id = str(user_id)
    for current_id, arena in ARENAS.items():
        if status and arena.get("status") != status:
            continue
        if user_id in arena_players(arena):
            matches.append((current_id, arena))
    return matches

def find_arena_for_pair(first_id, second_id, requested_id=None):
    if requested_id:
        arena = ARENAS.get(str(requested_id).upper())
        if arena and str(first_id) in arena_players(arena) and str(second_id) in arena_players(arena):
            return str(requested_id).upper(), arena
        return None, None
    for current_id, arena in ARENAS.items():
        if not active_arena_status(arena):
            continue
        players = arena_players(arena)
        if str(first_id) in players and str(second_id) in players:
            return current_id, arena
    return None, None

def arena_score(game_key, team):
    """Generate a team score for an arena-only game."""
    count = max(1, len(team))
    if game_key == "dice":
        return sum(random.randint(1, 6) for _ in range(count))
    if game_key == "highlow":
        return sum(random.randint(1, 100) for _ in range(count))
    if game_key == "color":
        return sum(random.choice((1, 2, 3, 4)) for _ in range(count))
    if game_key == "roulette":
        return sum(random.randint(0, 36) for _ in range(count))
    if game_key == "coinrush":
        return sum(random.choice((0, 2)) + random.choice((0, 2)) for _ in range(count))
    if game_key == "carddraw":
        return sum(random.randint(1, 13) for _ in range(count))
    if game_key == "treasure":
        return sum(random.choice((10, 25, 50, 75, 100)) for _ in range(count))
    if game_key == "battlepower":
        return sum(random.randint(1, 20) * random.randint(1, 6) for _ in range(count))
    return sum(random.randint(1, 1_000) for _ in range(count))

def arena_player_commitment(record):
    """Return an arena player's configured commitment, with legacy fallbacks."""
    if not isinstance(record, dict):
        return ARENA_PLAYER_REQUIREMENT
    if record.get("bet_paid") is not None:
        return int(record.get("bet_paid", 0))
    return int(record.get("entry_paid", ARENA_ENTRY_FEE)) + int(
        record.get("match_reserve_total", ARENA_MATCH_RESERVE)
    )

def arena_total_requirement(arena):
    return int(arena.get("player_requirement", ARENA_PLAYER_REQUIREMENT))

def arena_entry_fee(arena):
    return int(arena.get("entry_fee", ARENA_ENTRY_FEE))

def arena_match_reserve(arena):
    return int(arena.get("match_reserve", ARENA_MATCH_RESERVE))

def arena_round_bet(arena):
    if arena.get("bet_charge_mode") == "single_bet":
        return 0
    return int(
        arena.get(
            "round_bet",
            arena_match_reserve(arena) // ARENA_ROUNDS,
        )
    )

def arena_player_bet(arena):
    """Return the one-time bet for new single-bet arenas."""
    if arena.get("bet_charge_mode") == "single_bet":
        return int(arena.get("bet_per_player", arena_total_requirement(arena)))
    return arena_total_requirement(arena)

def arena_uses_single_bet(arena):
    return arena.get("bet_charge_mode") == "single_bet"

def arena_uses_deferred_reserve(arena):
    """New arenas charge their reserve as each round starts."""
    return arena.get("reserve_charge_mode") == "per_round"

def arena_rounds_played(arena):
    return len([
        round_state for round_state in arena.get("rounds", [])
        if isinstance(round_state, dict)
        and (round_state.get("completed") or round_state.get("winner_team"))
    ])

def arena_current_round(arena):
    rounds = arena.get("rounds", [])
    index = int(arena.get("round_index", 0))
    if not isinstance(rounds, list) or index >= len(rounds):
        return None
    return rounds[index]

def arena_team_user_ids(arena, team_number):
    teams = arena.get("teams", [])
    index = int(team_number) - 1
    return [str(user_id) for user_id in teams[index]] if 0 <= index < len(teams) else []

def arena_round_reserve_is_available(arena):
    if arena_uses_single_bet(arena):
        return True
    round_bet = arena_round_bet(arena)
    if not arena_uses_deferred_reserve(arena):
        return all(
            isinstance(record, dict)
            and int(
                record.get("match_reserve_remaining", arena_match_reserve(arena))
            ) >= round_bet
            for record in arena.get("players", {}).values()
        )
    return all(
        isinstance(record, dict)
        and int(
            record.get("match_reserve_remaining", arena_match_reserve(arena))
        ) >= round_bet
        and user_total_balance(get_user(user_id)) >= round_bet
        for user_id, record in arena.get("players", {}).items()
    )

def reserve_arena_round(arena):
    """Charge one configured round amount from new players' available balances."""
    if arena_uses_single_bet(arena):
        return True
    round_bet = arena_round_bet(arena)
    if not arena_round_reserve_is_available(arena):
        return False
    for user_id, record in arena.get("players", {}).items():
        if arena_uses_deferred_reserve(arena):
            if not debit_available_balance(get_user(user_id), round_bet):
                return False
        record["match_reserve_remaining"] = (
            int(record.get("match_reserve_remaining", arena_match_reserve(arena)))
            - round_bet
        )
    if arena_uses_deferred_reserve(arena):
        save_data(DATA)
    return True

def arena_round_reserve_is_available_legacy(arena):
    """Compatibility helper retained for old callers."""
    round_bet = arena_round_bet(arena)
    return all(
        isinstance(record, dict)
        and int(
            record.get("match_reserve_remaining", arena_match_reserve(arena))
        ) >= round_bet
        for record in arena.get("players", {}).values()
    )

def arena_round_winner(arena, round_state, winner_team):
    round_state["winner_team"] = int(winner_team)
    round_state["completed"] = True
    arena.setdefault("team_wins", {"1": 0, "2": 0})
    arena["team_wins"][str(winner_team)] = (
        int(arena["team_wins"].get(str(winner_team), 0)) + 1
    )
    if arena["team_wins"][str(winner_team)] >= ARENA_MATCH_WIN_POINTS:
        arena["match_winner_team"] = int(winner_team)

def reroll_arena_mines_round(arena, round_state):
    """Replace a timed-out Mines round without charging another round reserve."""
    used_games = {
        item.get("game_key")
        for item in arena.get("rounds", [])
        if isinstance(item, dict) and item is not round_state
    }
    replacement_pool = [
        game for game in ARENA_GAME_POOL
        if game[0] != "arena_mines" and game[0] not in used_games
    ]
    if not replacement_pool:
        replacement_pool = [
            game for game in ARENA_GAME_POOL
            if game[0] != "arena_mines"
        ]
    game_key, game_name = random.choice(replacement_pool)
    number = round_state.get("number", 1)
    reserve_spent = round_state.get("reserve_spent", arena_round_bet(arena))
    round_state.clear()
    round_state.update({
        "number": number,
        "game_key": game_key,
        "game_name": game_name,
        "reserve_spent": reserve_spent,
        "rerolled": True,
    })
    if game_key == "bugtong":
        arena_prepare_bugtong_round(round_state, arena)
    elif game_key == "uno":
        arena_prepare_uno_round(round_state, arena)
    elif game_key == "lucky9":
        arena_prepare_lucky9_round(round_state, arena)
    elif game_key == "deal_or_no_deal":
        arena_prepare_deal_round(round_state)

def arena_prepare_bugtong_round(round_state, arena=None):
    """Attach one Filipino riddle and two bot-selected team representatives."""
    previous_prompt = round_state.get("bugtong_prompt")
    available = [
        riddle for riddle in ARENA_BUGTONG_RIDDLES
        if riddle["prompt"] != previous_prompt
    ] or list(ARENA_BUGTONG_RIDDLES)
    riddle = random.choice(available)
    choices = list(riddle["choices"])
    random.shuffle(choices)
    round_state["bugtong_prompt"] = riddle["prompt"]
    round_state["bugtong_answer"] = riddle["answer"]
    round_state["bugtong_choices"] = choices
    round_state["bugtong_answers"] = {}
    round_state["bugtong_question_number"] = int(
        round_state.get("bugtong_question_number", 0)
    ) + 1
    if arena is not None:
        round_state["bugtong_representatives"] = {
            "1": random.choice(arena_team_user_ids(arena, 1)),
            "2": random.choice(arena_team_user_ids(arena, 2)),
        }

def lucky9_card_text(card):
    """Return a visible Lucky 9 card label with its scoring value."""
    rank = str(card.get("rank", "?"))
    suit = str(card.get("suit", ""))
    value = int(card.get("value", 0))
    return f"**{rank}{suit}** (`{value}`)"

def lucky9_make_deck():
    deck = []
    card_number = 0
    for suit in LUCKY9_SUITS:
        for rank, value in LUCKY9_RANKS:
            deck.append({
                "id": f"lucky9-{card_number}",
                "rank": rank,
                "suit": suit,
                "value": value,
            })
            card_number += 1
    random.shuffle(deck)
    return deck

def lucky9_score(cards):
    """Lucky 9 score: add card values and keep only the final digit."""
    return sum(int(card.get("value", 0)) for card in cards) % 10

def arena_prepare_lucky9_round(round_state, arena):
    """Choose one visible representative per team and deal two cards each."""
    representatives = {
        "1": random.choice(arena_team_user_ids(arena, 1)),
        "2": random.choice(arena_team_user_ids(arena, 2)),
    }
    deck = lucky9_make_deck()
    cards = {"1": [deck.pop(), deck.pop()], "2": [deck.pop(), deck.pop()]}
    scores = {
        team: lucky9_score(team_cards)
        for team, team_cards in cards.items()
    }
    natural_teams = [
        int(team)
        for team, score in scores.items()
        if score == 9
    ]
    active_teams = [team for team in (1, 2) if team not in natural_teams]
    round_state.update({
        "lucky9_representatives": representatives,
        "lucky9_deck": deck,
        "lucky9_cards": cards,
        "lucky9_scores": scores,
        "lucky9_third_drawn": {"1": False, "2": False},
        "lucky9_stood": {
            "1": 1 in natural_teams,
            "2": 2 in natural_teams,
        },
        "lucky9_natural_teams": natural_teams,
        "lucky9_current_team": random.choice(active_teams) if active_teams else None,
        "lucky9_last_action": (
            "The bot selected one representative from each team. "
            "Both opening hands are visible."
        ),
    })

def arena_prepare_deal_round(round_state):
    """Create one shared 20-briefcase board with a unique target number."""
    target_number = random.randint(10, 99)
    tile_numbers = random.sample(
        [number for number in range(10, 100) if number != target_number],
        ARENA_DEAL_TILE_COUNT - 1,
    )
    target_index = random.randrange(ARENA_DEAL_TILE_COUNT)
    tile_numbers.insert(target_index, target_number)
    round_state.update({
        "deal_target_number": target_number,
        "deal_tiles": [
            {
                "index": index,
                "number": number,
                "revealed": False,
                "revealed_by_team": None,
                "revealed_by_user": None,
            }
            for index, number in enumerate(tile_numbers)
        ],
        "deal_attempts": {"1": 0, "2": 0},
        "deal_current_team": random.choice((1, 2)),
        "deal_time_remaining": ARENA_DEAL_TIMEOUT,
        "deal_last_action": "The bot selected which team flips first.",
    })

def uno_card_text(card):
    """Return a compact, player-readable UNO card label."""
    color = str(card.get("color", "wild"))
    value = str(card.get("value", ""))
    if value == "wild":
        label = "WILD"
    elif value == "wild4":
        label = "+4"
    elif value == "draw2":
        label = "+2"
    elif value == "skip":
        label = "BLOCK"
    else:
        label = value
    return f"{UNO_COLOR_EMOJI.get(color, '⬛')} {UNO_COLOR_LABELS.get(color, 'Wild')} {label}"

def uno_card_button_label(card):
    color = str(card.get("color", "wild"))
    value = str(card.get("value", ""))
    prefix = {
        "red": "R",
        "blue": "B",
        "violet": "V",
        "green": "G",
        "wild": "W",
    }.get(color, "W")
    label = {
        "draw2": "+2",
        "wild4": "+4",
        "skip": "BLOCK",
        "reverse": "REV",
        "wild": "WILD",
    }.get(value, value)
    return f"{prefix} {label}"

def uno_make_deck():
    deck = []
    card_number = 0
    for color in UNO_COLORS:
        for value in range(10):
            copies = 1 if value == 0 else 2
            for _ in range(copies):
                deck.append({
                    "id": f"uno-{card_number}",
                    "color": color,
                    "value": str(value),
                })
                card_number += 1
        for value in ("skip", "reverse", "draw2"):
            for _ in range(2):
                deck.append({
                    "id": f"uno-{card_number}",
                    "color": color,
                    "value": value,
                })
                card_number += 1
    for value in ("wild", "wild4"):
        for _ in range(4):
            deck.append({
                "id": f"uno-{card_number}",
                "color": "wild",
                "value": value,
            })
            card_number += 1
    random.shuffle(deck)
    return deck

def uno_draw_cards(round_state, user_id, amount):
    """Draw cards, rebuilding the draw pile from the discard history if needed."""
    hands = round_state.setdefault("uno_hands", {})
    hand = hands.setdefault(str(user_id), [])
    discard = round_state.setdefault("uno_discard", [])
    draw_pile = round_state.setdefault("uno_draw_pile", [])
    for _ in range(max(0, int(amount))):
        if not draw_pile:
            if len(discard) <= 1:
                break
            top = discard[-1]
            draw_pile.extend(discard[:-1])
            discard[:] = [top]
            random.shuffle(draw_pile)
        if draw_pile:
            hand.append(draw_pile.pop())
    return hand

def uno_active_color(round_state):
    return str(round_state.get("uno_active_color") or
               round_state.get("uno_discard", [{}])[-1].get("color", "red"))

def uno_card_is_legal(card, round_state):
    """Apply color/value matching plus strict same-color draw stacking."""
    discard = round_state.get("uno_discard", [])
    if not discard:
        return True
    top = discard[-1]
    value = str(card.get("value"))
    color = str(card.get("color"))
    pending = int(round_state.get("uno_pending_draw", 0))
    pending_type = str(round_state.get("uno_pending_type", ""))
    if pending:
        if pending_type == "draw2":
            return value == "draw2" and color == str(top.get("color"))
        if pending_type == "wild4":
            return value == "wild4"
    if value in {"wild", "wild4"}:
        return True
    return color == uno_active_color(round_state) or value == str(top.get("value"))

def uno_selected_cards(hand, selected_ids):
    selected = {str(card_id) for card_id in selected_ids}
    return [card for card in hand if str(card.get("id")) in selected]

def uno_cards_can_be_dropped(cards, round_state):
    if not cards or any(not uno_card_is_legal(card, round_state) for card in cards):
        return False
    if len(cards) == 1:
        return True
    first = cards[0]
    return all(
        str(card.get("color")) == str(first.get("color"))
        and str(card.get("value")) == str(first.get("value"))
        for card in cards
    )

def arena_prepare_uno_round(round_state, arena):
    """Deal seven private cards per contestant and choose a random first turn."""
    players = [str(user_id) for user_id in arena_players(arena)]
    deck = uno_make_deck()
    hands = {user_id: [] for user_id in players}
    for _ in range(7):
        for user_id in players:
            hands[user_id].append(deck.pop())
    starter_index = random.randrange(len(players))
    while deck and (
        deck[-1].get("value") in UNO_ACTION_VALUES
        or deck[-1].get("color") == "wild"
    ):
        random.shuffle(deck)
    first_card = deck.pop()
    round_state.update({
        "uno_order": players,
        "uno_hands": hands,
        "uno_draw_pile": deck,
        "uno_discard": [first_card],
        "uno_active_color": first_card["color"],
        "uno_current_index": starter_index,
        "uno_direction": 1,
        "uno_pending_draw": 0,
        "uno_pending_type": "",
        "uno_drawn_this_turn": False,
        "uno_last_played_cards": [],
        "uno_last_action": (
            f"Bot selected <@{players[starter_index]}> to play first."
        ),
    })

def arena_round_description(round_state):
    if round_state.get("game_key") == "arena_mines":
        return (
            f"Defending team: **{arena_team_name(round_state.get('defender_team'))}**\n"
            f"Clicking team: **{arena_team_name(round_state.get('attacker_team'))}**\n"
            f"The defending team has {ARENA_MINES_PHASE_TIMEOUT} seconds to secretly "
            f"place 4 bombs. The clicking team then has {ARENA_MINES_PHASE_TIMEOUT} "
            "seconds to find 4 safe tiles from 15 choices."
        )
    if round_state.get("game_key") == "math":
        total_questions = int(round_state.get("math_question_total", 1))
        return (
            f"Both teams race on **{total_questions} question"
            f"{'s' if total_questions != 1 else ''}**. "
            "The first correct team wins each question; the question majority "
            "wins this one arena round."
        )
    if round_state.get("game_key") == "bugtong":
        representatives = round_state.get("bugtong_representatives", {})
        return (
            "Basahin ang bugtong at piliin ang tamang sagot. "
            f"RED representative: <@{representatives.get('1', 'unknown')}>. "
            f"BLUE representative: <@{representatives.get('2', 'unknown')}>. "
            "Ang dalawang representative lang ang puwedeng sumagot."
        )
    if round_state.get("game_key") == "uno":
        order = round_state.get("uno_order", [])
        current_index = int(round_state.get("uno_current_index", 0))
        current_user = order[current_index] if order else "unknown"
        return (
            "Each player starts with 7 cards. Match the active color or value; "
            "BLOCK, REVERSE, +2, and +4 cards have their normal effects. "
            "You may select multiple identical cards of the same color and value "
            "before dropping them together.\n"
            f"Current turn: <@{current_user}>. "
            f"UNO lasts up to {ARENA_UNO_TIMEOUT} seconds."
        )
    if round_state.get("game_key") == "lucky9":
        representatives = round_state.get("lucky9_representatives", {})
        return (
            "The bot selected one representative from each team. "
            "Both representatives reveal two cards publicly. "
            "A hand score is the final digit of the card total; 9 is highest. "
            "A starting 9 stands immediately. Otherwise, each representative "
            f"may stand or draw one optional third card within {ARENA_LUCKY9_TIMEOUT} seconds.\n"
            f"RED: <@{representatives.get('1', 'unknown')}> • "
            f"BLUE: <@{representatives.get('2', 'unknown')}>"
        )
    if round_state.get("game_key") == "deal_or_no_deal":
        attempts = round_state.get("deal_attempts", {})
        current_team = round_state.get("deal_current_team")
        return (
            "One hidden target number is behind the same 20 briefcase tiles "
            "visible to both teams. "
            f"Each team gets only {ARENA_DEAL_ATTEMPTS} flips. "
            f"Current turn: **{arena_team_name(current_team)}**. "
            f"RED flips: **{attempts.get('1', 0)}/{ARENA_DEAL_ATTEMPTS}** • "
            f"BLUE flips: **{attempts.get('2', 0)}/{ARENA_DEAL_ATTEMPTS}**. "
            f"Time limit: **{ARENA_DEAL_TIMEOUT} seconds**."
        )
    return (
        "Every registered player must click the game button once. "
        f"You have {ARENA_MINES_PHASE_TIMEOUT} seconds; players who do not act "
        "score zero for this round."
    )

def arena_math_question():
    """Create a simple, exact-integer arithmetic question without eval()."""
    operation = random.choice(("+", "-", "x", "/"))
    if operation == "+":
        left = random.randint(10, 250)
        right = random.randint(10, 250)
        return f"{left} + {right}", left + right
    if operation == "-":
        left = random.randint(50, 300)
        right = random.randint(10, left)
        return f"{left} - {right}", left - right
    if operation == "x":
        left = random.randint(2, 25)
        right = random.randint(2, 20)
        return f"{left} x {right}", left * right
    divisor = random.randint(2, 20)
    quotient = random.randint(2, 25)
    return f"{divisor * quotient} / {divisor}", quotient

def arena_game_action_label(game_key):
    return {
        "dice": "🎲 Roll Dice",
        "highlow": "📈 Make High/Low Pick",
        "color": "🎨 Pick a Color",
        "roulette": "🎡 Spin Roulette",
        "number": "🔢 Pick a Number",
        "coinrush": "🪙 Flip Coins",
        "carddraw": "🃏 Draw a Card",
        "treasure": "🗝️ Open a Chest",
        "battlepower": "⚔️ Battle",
        "math": "⌨️ Type Answer",
        "bugtong": "📜 Answer Bugtong",
    }.get(game_key, "🎮 Play Round")

def arena_game_player_score(game_key):
    """Generate one player's result after that player submits the round."""
    return int(arena_score(game_key, [0]))

def arena_game_score(game_key, choice=None, round_state=None):
    """Resolve one contestant's action for an interactive arena round."""
    value = str(choice or "").strip().casefold()
    if game_key == "dice":
        if value:
            roll = int(value)
            if roll < 1 or roll > 6:
                raise ValueError("Dice choice must be a number from 1 to 6.")
            return roll
        return random.randint(1, 6)
    if game_key == "highlow":
        if value and value not in {"high", "low"}:
            raise ValueError("High/Low choice must be `high` or `low`.")
        number = random.randint(1, 100)
        if not value:
            return number
        return number if (value == "high") == (number > 50) else 0
    if game_key == "color":
        colors = {"red", "blue", "green", "yellow"}
        if value and value not in colors:
            raise ValueError("Color choice must be red, blue, green, or yellow.")
        return random.randint(1, 4) if not value else (
            4 if random.choice(tuple(colors)) == value else 1
        )
    if game_key == "roulette":
        if value:
            number = int(value)
            if number < 0 or number > 36:
                raise ValueError("Roulette choice must be a number from 0 to 36.")
            spun = random.randint(0, 36)
            return max(0, 37 - abs(spun - number))
        return random.randint(0, 36)
    if game_key == "number":
        if value:
            number = int(value)
            if number < 1 or number > 1_000:
                raise ValueError("Number choice must be from 1 to 1,000.")
            target = random.randint(1, 1_000)
            return 1_000 - abs(target - number)
        return random.randint(1, 1_000)
    if game_key == "coinrush":
        if value and value not in {"heads", "tails"}:
            raise ValueError("Coin choice must be `heads` or `tails`.")
        flips = [random.choice(("heads", "tails")) for _ in range(2)]
        return sum(flip == (value or "heads") for flip in flips)
    if game_key == "carddraw":
        if value:
            number = int(value)
            if number < 1 or number > 13:
                raise ValueError("Card choice must be a number from 1 to 13.")
            drawn = random.randint(1, 13)
            return drawn if drawn == number else max(1, 13 - abs(drawn - number))
        return random.randint(1, 13)
    if game_key == "treasure":
        if value and value not in {"1", "2", "3"}:
            raise ValueError("Treasure choice must be chest 1, 2, or 3.")
        return random.choice((10, 25, 50, 75, 100))
    if game_key == "battlepower":
        if value and value not in {"attack", "defend"}:
            raise ValueError("Battle choice must be `attack` or `defend`.")
        return random.randint(1, 20) * random.randint(1, 6)
    if game_key == "bugtong":
        answer = str((round_state or {}).get("bugtong_answer", "")).strip().casefold()
        if not answer:
            return 0
        return 1 if value == answer else 0
    return arena_game_player_score(game_key)

def arena_round_draw_embed(arena_id_value, arena, round_state, result):
    return discord.Embed(
        title=f"⚖️ **ROUND {round_state.get('number', 1)} DRAW**",
        description=(
            f"**{result}**\n\n"
            f"**No team wins this round.**\n"
            f"**Scoreboard: {arena_scoreboard(arena)}**\n\n"
            f"**Next game begins in {ARENA_ROUND_RESULT_DELAY} seconds...**"
        ),
        color=discord.Color.gold(),
    )

def arena_round_winner_embed(arena_id_value, arena, round_state, winner_team, result):
    """Create the bold gold five-second transition screen between rounds."""
    match_won = arena_has_match_winner(arena)
    transition = (
        f"**{arena_team_name(winner_team)} TEAM WON!**\n"
        f"**Final match result follows in {ARENA_ROUND_RESULT_DELAY} seconds...**"
        if match_won
        else f"**Next game begins in {ARENA_ROUND_RESULT_DELAY} seconds...**"
    )
    return discord.Embed(
        title=(
            f"🏆 **{arena_team_name(winner_team)} TEAM WON!**"
            if match_won
            else f"🏆 **ROUND {round_state.get('number', 1)} WINNER**"
        ),
        description=(
            f"**{result}**\n\n"
            f"**{arena_team_name(winner_team)} TEAM WINS THIS ROUND!**\n"
            f"**Scoreboard: {arena_scoreboard(arena)}**\n\n"
            f"{transition}"
        ),
        color=discord.Color.gold(),
    )

async def complete_arena_match(arena_id_value, arena, channel):
    if arena.get("status") == "completed":
        return
    winner_team = arena_winning_team(arena)
    if winner_team is None:
        winner_team = (
            1
            if int(arena.get("team_wins", {}).get("1", 0))
            > int(arena.get("team_wins", {}).get("2", 0))
            else 2
        )
    arena["winner_team"] = winner_team
    finish_arena_match(arena_id_value, arena)
    await unlock_arena_channel(arena_id_value, arena)
    await channel.send(
        embed=discord.Embed(
            title=f"🏆 **{arena_team_name(winner_team)} TEAM WON!**",
            description=(
                f"**Final scoreboard: {arena_scoreboard(arena)}**\n\n"
                f"{arena_result_text(arena_id_value, arena)}\n\n"
                + (
                    "The winner payout has been credited automatically from "
                    "the total bet pool ×2."
                    if arena_uses_single_bet(arena)
                    else (
                        "No automatic cash reward was issued for this legacy "
                        "arena. The bot owner decides what prize, if any, to give."
                    )
                )
            ),
            color=discord.Color.gold(),
        )
    )

async def animate_arena_round_start(
    channel,
    arena_id_value,
    arena,
    round_state,
):
    """Show a short edited countdown before every arena round begins."""
    message = await channel.send(
        embed=arena_round_embed(
            arena_id_value,
            arena,
            round_state,
            "🎬 **Round starting...**",
        ),
    )
    for count in (3, 2, 1):
        await asyncio.sleep(0.35)
        try:
            await message.edit(
                embed=arena_round_embed(
                    arena_id_value,
                    arena,
                    round_state,
                    f"🎬 **Round starts in {count}...**",
                )
            )
        except discord.HTTPException:
            pass
    return message

async def continue_arena_match(arena_id_value, arena, channel):
    """Charge and open one interactive round at a time."""
    while arena.get("round_index", 0) < ARENA_ROUNDS:
        if arena_has_match_winner(arena):
            await complete_arena_match(arena_id_value, arena, channel)
            return
        round_state = arena_current_round(arena)
        if not round_state:
            break
        if round_state.get("completed") or round_state.get("winner_team"):
            arena["round_index"] = int(arena.get("round_index", 0)) + 1
            continue
        if not arena_uses_single_bet(arena) and not round_state.get("reserve_spent"):
            if not reserve_arena_round(arena):
                arena["status"] = "cancelled"
                await unlock_arena_channel(arena_id_value, arena)
                save_data(DATA)
                save_arenas()
                return await channel.send(
                    f"⚠️ Arena `{arena_id_value}` could not fund the next configured "
                    "round from every player's available balance. The match was "
                    "cancelled and the arena channel was unlocked."
                )
            round_state["reserve_spent"] = arena_round_bet(arena)
        if round_state.get("game_key") == "arena_mines":
            view = ArenaMinesView(arena_id_value, arena, round_state)
            message = await animate_arena_round_start(
                channel, arena_id_value, arena, round_state
            )
            await message.edit(
                embed=arena_round_embed(arena_id_value, arena, round_state),
                view=view,
            )
            view.message = message
            save_arenas()
            return
        if round_state.get("game_key") == "uno":
            game = UnoArenaGame(arena_id_value, arena, round_state)
            view = UnoArenaView(game)
            game.set_public_view(view)
            message = await animate_arena_round_start(
                channel, arena_id_value, arena, round_state
            )
            ARENA_GAME_VIEWS[arena_id_value] = game
            await message.edit(embed=game.public_embed(), view=view)
            game.message = message
            game.start_timer()
            save_arenas()
            return
        if round_state.get("game_key") == "lucky9":
            view = Lucky9View(arena_id_value, arena, round_state)
            message = await animate_arena_round_start(
                channel, arena_id_value, arena, round_state
            )
            ARENA_GAME_VIEWS[arena_id_value] = view
            await message.edit(embed=view.embed(), view=view)
            view.message = message
            view.start_timer()
            save_arenas()
            return
        if round_state.get("game_key") == "deal_or_no_deal":
            view = DealOrNoDealView(arena_id_value, arena, round_state)
            message = await animate_arena_round_start(
                channel, arena_id_value, arena, round_state
            )
            ARENA_GAME_VIEWS[arena_id_value] = view
            await message.edit(embed=view.embed(), view=view)
            view.message = message
            view.start_timer()
            save_arenas()
            return
        if round_state.get("game_key") == "math":
            view = ArenaMathRound(arena_id_value, arena, round_state)
            message = await animate_arena_round_start(
                channel, arena_id_value, arena, round_state
            )
            ARENA_MATH_VIEWS[arena_id_value] = view
            await message.edit(embed=view.round_embed())
            view.message = message
            view.start_timer()
            save_arenas()
            return
        view = ArenaGameView(arena_id_value, arena, round_state)
        message = await animate_arena_round_start(
            channel, arena_id_value, arena, round_state
        )
        ARENA_GAME_VIEWS[arena_id_value] = view
        round_state["players_played"] = []
        save_arenas()
        await message.edit(embed=view.round_embed(), view=view)
        view.message = message
        if round_state.get("game_key") == "bugtong":
            view.start_bugtong_timer()
        return
    if (
        arena.get("status") == "match"
        and (
            arena_has_match_winner(arena)
            or arena_rounds_played(arena) >= ARENA_ROUNDS
        )
    ):
        await complete_arena_match(arena_id_value, arena, channel)

def arena_round_embed(arena_id_value, arena, round_state, status=None):
    game_name = round_state.get("game_name", "Arena Game")
    defender = round_state.get("defender_team")
    attacker = round_state.get("attacker_team")
    description = (
        f"Match round **{round_state.get('number', 1)}/{ARENA_ROUNDS}**\n"
        f"Game: **{game_name}**\n"
        f"Player bet: **{format_coins(arena_player_bet(arena))} uwuncy**\n"
        f"Scoreboard: {arena_scoreboard(arena)}"
    )
    game_key = round_state.get("game_key")
    if game_key in ARENA_GAME_DESCRIPTIONS:
        description += f"\n{ARENA_GAME_DESCRIPTIONS[game_key]}"
    if game_key != "arena_mines":
        description += f"\n{arena_round_description(round_state)}"
    if game_name == "Arena Mines":
        description += (
            f"\nDefending team: **{arena_team_name(defender)}**"
            f"\nClicking team: **{arena_team_name(attacker)}**"
            "\nThe defending team places four hidden bombs. The other team must find four safe tiles."
            f"\nEach phase has a {ARENA_MINES_PHASE_TIMEOUT}-second timer. A timeout rerolls this round."
        )
    if status:
        description += f"\n\n{status}"
    return discord.Embed(
        title=f"🏟️ Arena {arena_id_value} — Round {round_state.get('number', 1)}",
        description=description,
        color=discord.Color.orange(),
    )

def arena_winner(arena, game_key):
    teams = arena.get("teams", [])
    scores = {}
    while True:
        scores = {index: arena_score(game_key, team) for index, team in enumerate(teams, start=1)}
        highest = max(scores.values())
        winners = [index for index, score in scores.items() if score == highest]
        if len(winners) == 1:
            return winners[0], scores

def arena_fee_status(arena):
    return sum(
        1 for record in arena.get("players", {}).values()
        if isinstance(record, dict) and record.get("fee_paid")
    )

def arena_ready(arena):
    required_players = int(arena["team_size"]) * 2
    if len(arena_players(arena)) != required_players:
        return False
    if arena["team_size"] == 1:
        return True
    groups = arena.get("groups", [])
    return (
        len(groups) == 2
        and all(len(group) == int(arena["team_size"]) for group in groups)
    )

def arena_embed(arena_id_value, arena):
    required = int(arena["team_size"]) * 2
    players = arena_players(arena)
    status = arena.get("status", "lobby").title()
    if arena_uses_single_bet(arena):
        description = (
            f"**{len(players)}/{required}** players registered\n"
            f"Bet per player: `{format_coins(arena_player_bet(arena))}` uwuncy\n"
            f"Total pool: `{format_coins(len(players) * arena_player_bet(arena))}` uwuncy\n"
            f"Winner payout: **total pool ×2**, split equally among the winning team\n"
            f"Teams: {arena_team_size_label(arena['team_size'])}"
        )
    else:
        description = (
            f"**{len(players)}/{required}** players registered\n"
            f"Entry fee: `{format_coins(arena_entry_fee(arena))}` uwuncy\n"
            f"Round reserve available: `{format_coins(arena_match_reserve(arena))}` uwuncy\n"
            f"Planned total per player: `{format_coins(arena_total_requirement(arena))}` uwuncy\n"
            f"Match: `{ARENA_ROUNDS}` rounds × `{format_coins(arena_round_bet(arena))}` per player\n"
            f"Teams: {arena_team_size_label(arena['team_size'])}"
        )
    round_state = arena_current_round(arena)
    if round_state and round_state.get("game_name"):
        description += (
            f"\nCurrent round: **{round_state['game_name']}**"
            f" ({arena_rounds_played(arena)}/{ARENA_ROUNDS} complete)"
        )
    embed = discord.Embed(
        title=f"🏟️ Arena {arena_id_value}",
        description=description,
        color=discord.Color.gold(),
    )
    embed.add_field(name="Status", value=f"`{status}`", inline=True)
    embed.add_field(name="Entry fee paid", value=f"`{arena_fee_status(arena)}/{required}`", inline=True)
    if arena.get("teams"):
        embed.add_field(name="Teams", value=arena_team_lines(arena), inline=False)
        if arena.get("unpaired"):
            embed.add_field(
                name="Unpaired registered players",
                value=" ".join(f"<@{user_id}>" for user_id in arena["unpaired"]),
                inline=False,
            )
    else:
        embed.add_field(
            name="Pairing",
            value=(
                "Use `uwu paired @user` to form teammate pairs."
                if arena["team_size"] > 1
                else "1v1 players become separate teams automatically."
            ),
            inline=False,
        )
    if arena.get("status") == "match" and not arena_uses_single_bet(arena):
        remaining = min(
            int(record.get("match_reserve_remaining", 0))
            for record in arena.get("players", {}).values()
            if isinstance(record, dict)
        ) if arena.get("players") else 0
        embed.add_field(
            name="Seven-round reserve",
            value=(
                f"Remaining to charge per player: `{format_coins(remaining)}` uwuncy\n"
                f"Round cost: `{format_coins(arena_round_bet(arena))}` per player"
            ),
            inline=False,
        )
    elif arena.get("status") == "match":
        embed.add_field(
            name="Winner payout",
            value=(
                f"Total bets ×2: `{format_coins(len(players) * arena_player_bet(arena) * 2)}` uwuncy\n"
                "Split equally among the winning team."
            ),
            inline=False,
        )
    if arena.get("team_wins"):
        embed.add_field(
            name="Match score",
            value=arena_scoreboard(arena),
            inline=False,
        )
    embed.set_footer(text="Bank uwuncy may pay arena costs; crypto holdings never count.")
    return embed

def arena_team_size_label(team_size):
    return f"{team_size}v{team_size}"

def arena_rebuild_teams(arena):
    """Build the current team view from explicit paired groups."""
    team_size = int(arena["team_size"])
    groups = [
        list(dict.fromkeys(str(user_id) for user_id in group))
        for group in arena.get("groups", [])
        if group
    ]
    assigned = {user_id for group in groups for user_id in group}
    if team_size == 1:
        groups = [[user_id] for user_id in arena_players(arena)]
    arena["groups"] = groups
    arena["teams"] = groups
    arena["unpaired"] = [
        user_id for user_id in arena_players(arena)
        if user_id not in assigned and team_size > 1
    ]
    return groups

def arena_group_for_user(arena, user_id):
    user_id = str(user_id)
    for group in arena.get("groups", []):
        if user_id in group:
            return group
    return None

def arena_result_text(arena_id_value, arena):
    winner = int(arena.get("winner_team", 0))
    lines = [
        f"🏟️ **Arena {arena_id_value} complete!**",
        f"Match winner: **{arena_team_name(winner)} TEAM**",
        (
            f"Final scoreboard: **{arena_scoreboard(arena)}**"
        ),
        (
            f"Total bet pool: **{format_coins(arena.get('total_pot', 0))} uwuncy**"
            if arena_uses_single_bet(arena)
            else f"Entry and round charges consumed: **{format_coins(arena.get('total_pot', 0))} uwuncy**"
        ),
    ]
    if arena_uses_single_bet(arena):
        lines.append(
            f"Winner payout pool: **{format_coins(arena.get('payout_pool', 0))} uwuncy** "
            "(2× total bets), split equally among the winning team."
        )
    for round_state in arena.get("rounds", []):
        if isinstance(round_state, dict) and round_state.get("winner_team"):
            lines.append(
                f"Round {round_state.get('number')}: "
                f"**{round_state.get('game_name', 'Arena Game')}** — "
                f"**{arena_team_name(round_state['winner_team'])}** won"
            )
    for user_id, payout in arena.get("payouts", {}).items():
        if payout:
            lines.append(f"<@{user_id}> won **+{format_coins(payout)} uwuncy**")
    return "\n".join(lines)

def get_active_arena_for_user(user_id):
    matches = find_user_arena(user_id)
    active = [
        (arena_id_value, arena)
        for arena_id_value, arena in matches
        if arena.get("status") in {"lobby", "betting", "match"}
    ]
    return active[0] if active else (None, None)

def get_active_arena_for_guild(guild_id):
    """Return the server's active arena, if it already has one."""
    guild_id = str(guild_id)
    for arena_id_value, arena in ARENAS.items():
        if (
            str(arena.get("guild_id", "")) == guild_id
            and arena.get("status") in {"lobby", "betting", "match"}
        ):
            return arena_id_value, arena
    return None, None

def finish_arena_match(arena_id_value, arena):
    """Complete an arena and pay the winner pool once for new single-bet matches."""
    if arena.get("status") == "completed":
        return int(arena.get("total_pot", 0))
    if arena_uses_deferred_reserve(arena):
        total_pot = sum(
            int(record.get("entry_paid", arena_entry_fee(arena)))
            + (
                int(record.get("match_reserve_total", arena_match_reserve(arena)))
                - int(record.get("match_reserve_remaining", 0))
            )
            for record in arena.get("players", {}).values()
            if isinstance(record, dict)
        )
    else:
        total_pot = sum(
            int(record.get("entry_paid", arena_entry_fee(arena)))
            + int(record.get("match_reserve_total", arena_match_reserve(arena)))
            for record in arena.get("players", {}).values()
            if isinstance(record, dict)
        )
    if arena_uses_single_bet(arena):
        total_pot = sum(
            int(record.get("bet_paid", arena_player_bet(arena)))
            for record in arena.get("players", {}).values()
            if isinstance(record, dict)
        )
        payout_pool = total_pot * 2
        winning_players = arena_team_user_ids(
            arena,
            int(arena.get("winner_team", 0)),
        )
        per_player = payout_pool // len(winning_players) if winning_players else 0
        payouts = {
            str(user_id): per_player
            for user_id in winning_players
            if per_player > 0
        }
        for user_id, payout in payouts.items():
            credit_wallet(get_user(user_id), payout)
        arena["payout_pool"] = payout_pool
        arena["payouts"] = payouts
        arena["payout_multiplier"] = 2
        save_data(DATA)
    else:
        arena["payouts"] = {}
    arena["total_pot"] = total_pot
    arena["status"] = "completed"
    save_arenas()
    return total_pot

class ArenaMathRound:
    """Typed-answer team race for one arena round."""

    def __init__(self, arena_id_value, arena, round_state):
        self.arena_id_value = arena_id_value
        self.arena = arena
        self.round_state = round_state
        self.message = None
        self.closed = False
        self.lock = asyncio.Lock()
        team_size = int(arena.get("team_size", 1))
        question_total = 1 if team_size <= 2 else 3
        self.round_state["math_question_total"] = question_total
        questions = self.round_state.get("math_questions")
        if not isinstance(questions, list) or len(questions) != question_total:
            questions = []
            for _ in range(question_total):
                prompt, answer = arena_math_question()
                questions.append({"prompt": prompt, "answer": answer})
            self.round_state["math_questions"] = questions
        self.questions = questions
        self.question_index = int(self.round_state.get("math_question_index", 0))
        self.question_scores = {
            "1": int(self.round_state.get("math_question_scores", {}).get("1", 0)),
            "2": int(self.round_state.get("math_question_scores", {}).get("2", 0)),
        }
        self.timer_task = None

    @property
    def question_total(self):
        return len(self.questions)

    @property
    def current_question(self):
        if self.question_index >= self.question_total:
            return None
        return self.questions[self.question_index]

    def round_embed(self, status=None):
        question = self.current_question
        question_number = min(self.question_index + 1, self.question_total)
        description = (
            f"Match round **{self.round_state.get('number', 1)}/{ARENA_ROUNDS}**\n"
            f"Game: **Math Sprint**\n"
            f"Question **{question_number}/{self.question_total}**: "
            f"**{question.get('prompt') if question else 'Round complete'}**\n"
            "Both teams can answer. Type only the number in this channel.\n"
            f"Question score: **RED {self.question_scores['1']}** • "
            f"**BLUE {self.question_scores['2']}**\n"
            f"Time limit: **{ARENA_MINES_PHASE_TIMEOUT} seconds for the round**\n"
            f"Match scoreboard: {arena_scoreboard(self.arena)}"
        )
        if status:
            description += f"\n\n{status}"
        return discord.Embed(
            title=f"🏟️ Arena {self.arena_id_value} — Math Sprint",
            description=description,
            color=discord.Color.orange(),
        )

    def start_timer(self):
        self.timer_task = asyncio.create_task(self.run_timer())

    async def run_timer(self):
        try:
            await asyncio.sleep(ARENA_MINES_PHASE_TIMEOUT)
            await self.finish_round(self.message.channel if self.message else None, timed_out=True)
        except asyncio.CancelledError:
            return

    async def submit_answer_text(self, user_id, text, channel=None, ctx=None):
        if self.closed or self.current_question is None:
            return False
        user_id = str(user_id)
        if user_id not in arena_players(self.arena):
            return False
        try:
            normalized = str(text).strip().replace(",", "")
            if not re.fullmatch(r"-?\d+", normalized):
                return False
            answer = int(normalized)
        except (TypeError, ValueError):
            return False

        async with self.lock:
            if self.closed or self.current_question is None:
                return True
            if answer != int(self.current_question["answer"]):
                return True
            team_number = arena_team_index(self.arena, user_id)
            if team_number not in (1, 2):
                return True
            winning_team = int(team_number)
            prompt = self.current_question["prompt"]
            self.question_scores[str(winning_team)] += 1
            self.question_index += 1
            self.round_state["math_question_index"] = self.question_index
            self.round_state["math_question_scores"] = dict(self.question_scores)
            save_arenas()
            status = (
                f"✅ **{arena_team_name(winning_team)} TEAM** got the first correct "
                f"answer for **{prompt}**. "
                f"Question score: RED `{self.question_scores['1']}` • "
                f"BLUE `{self.question_scores['2']}`."
            )
            required = self.question_total // 2 + 1
            majority_reached = (
                self.question_scores["1"] >= required
                or self.question_scores["2"] >= required
            )
            questions_finished = self.question_index >= self.question_total
            if majority_reached or questions_finished:
                if self.message:
                    try:
                        await self.message.edit(
                            embed=self.round_embed(
                                f"⚡ **{arena_team_name(winning_team)} TEAM** "
                                "wins the question. Resolving..."
                            )
                        )
                    except discord.HTTPException:
                        pass
                    await asyncio.sleep(0.45)
                await self.finish_round(
                    channel or (ctx.channel if ctx else self.message.channel),
                    status=status,
                )
            else:
                if self.message:
                    try:
                        await self.message.edit(
                            embed=self.round_embed(
                                f"⚡ **{arena_team_name(winning_team)} TEAM** "
                                "wins the question. Resolving..."
                            )
                        )
                    except discord.HTTPException:
                        pass
                    await asyncio.sleep(0.45)
                    try:
                        await self.message.edit(embed=self.round_embed(status))
                    except discord.HTTPException:
                        pass
            return True

    async def finish_round(self, channel, timed_out=False, status=None):
        if self.closed:
            return
        self.closed = True
        ARENA_MATH_VIEWS.pop(self.arena_id_value, None)
        if self.timer_task and self.timer_task is not asyncio.current_task():
            self.timer_task.cancel()
        self.round_state["math_question_index"] = self.question_index
        self.round_state["math_question_scores"] = dict(self.question_scores)
        self.round_state["completed"] = True
        self.arena["round_index"] = int(self.arena.get("round_index", 0)) + 1
        red_score = self.question_scores["1"]
        blue_score = self.question_scores["2"]
        required_majority = self.question_total // 2 + 1
        if max(red_score, blue_score) < required_majority:
            result = (
                f"{status + ' ' if status else ''}"
                f"Math score: RED `{red_score}` • BLUE `{blue_score}`. "
                f"No team reached the required {required_majority}-question majority, "
                "so this arena round is a draw."
            )
            save_arenas()
            embed = arena_round_draw_embed(
                self.arena_id_value, self.arena, self.round_state, result
            )
        else:
            winner_team = 1 if red_score > blue_score else 2
            result = (
                f"{status + ' ' if status else ''}"
                f"Math score: RED `{red_score}` • BLUE `{blue_score}`. "
                f"{arena_team_name(winner_team)} wins the Math round point."
            )
            arena_round_winner(self.arena, self.round_state, winner_team)
            save_arenas()
            embed = arena_round_winner_embed(
                self.arena_id_value,
                self.arena,
                self.round_state,
                winner_team,
                result,
            )
        if timed_out and status is None:
            embed.description = (
                f"⏰ **Math timer expired.**\n\n{embed.description}"
            )
        if self.message:
            try:
                await self.message.edit(embed=embed)
            except discord.HTTPException:
                pass
        await asyncio.sleep(ARENA_ROUND_RESULT_DELAY)
        if channel is not None:
            await continue_arena_match(self.arena_id_value, self.arena, channel)

class Lucky9View(discord.ui.View):
    """Public Lucky 9 table for one bot-selected representative per team."""

    def __init__(self, arena_id_value, arena, round_state):
        super().__init__(timeout=None)
        self.arena_id_value = arena_id_value
        self.arena = arena
        self.round_state = round_state
        self.message = None
        self.closed = False
        self.lock = asyncio.Lock()
        self.timer_task = None
        self.add_controls()

    def representatives(self):
        return self.round_state.get("lucky9_representatives", {})

    def current_team(self):
        value = self.round_state.get("lucky9_current_team")
        return int(value) if value in (1, 2, "1", "2") else None

    def add_controls(self):
        self.clear_items()
        for label, action, style in (
            ("🛑 Stand", "stand", discord.ButtonStyle.secondary),
            ("🃏 Draw 1 Card", "draw", discord.ButtonStyle.primary),
        ):
            button = discord.ui.Button(label=label, style=style, row=0)

            async def callback(interaction, selected_action=action):
                await self.take_action(interaction, selected_action)

            button.callback = callback
            self.add_item(button)

    def result_card_lines(self):
        cards = self.round_state.get("lucky9_cards", {})
        scores = self.round_state.get("lucky9_scores", {})
        reps = self.representatives()
        return (
            f"🔴 **RED** — <@{reps.get('1', 'unknown')}>: "
            f"{' • '.join(lucky9_card_text(card) for card in cards.get('1', []))} "
            f"→ **{scores.get('1', 0)}**",
            f"🔵 **BLUE** — <@{reps.get('2', 'unknown')}>: "
            f"{' • '.join(lucky9_card_text(card) for card in cards.get('2', []))} "
            f"→ **{scores.get('2', 0)}**",
        )

    def embed(self, status=None):
        reps = self.representatives()
        cards = self.round_state.get("lucky9_cards", {})
        scores = self.round_state.get("lucky9_scores", {})
        third_drawn = self.round_state.get("lucky9_third_drawn", {})
        stood = self.round_state.get("lucky9_stood", {})
        lines = [
            f"**RED representative:** <@{reps.get('1', 'unknown')}>",
            f"Cards: {' • '.join(lucky9_card_text(card) for card in cards.get('1', []))}",
            f"Score: **{scores.get('1', 0)}** • "
            f"{'✅ Stood' if stood.get('1') else ('🃏 Third card drawn' if third_drawn.get('1') else '⏳ Playing')}",
            "",
            f"**BLUE representative:** <@{reps.get('2', 'unknown')}>",
            f"Cards: {' • '.join(lucky9_card_text(card) for card in cards.get('2', []))}",
            f"Score: **{scores.get('2', 0)}** • "
            f"{'✅ Stood' if stood.get('2') else ('🃏 Third card drawn' if third_drawn.get('2') else '⏳ Playing')}",
        ]
        current_team = self.current_team()
        if current_team:
            lines.extend([
                "",
                f"Current turn: **{arena_team_name(current_team)}** "
                f"(<@{reps.get(str(current_team), 'unknown')}>)",
                "The representative may stand or draw one optional third card.",
                f"⏱️ **Time to compute: "
                f"{self.round_state.get('lucky9_time_remaining', ARENA_LUCKY9_TIMEOUT)} seconds**",
            ])
        else:
            lines.extend(["", "Both hands are locked. Resolving Lucky 9..."])
        if self.round_state.get("lucky9_last_action"):
            lines.extend(["", f"Last action: {self.round_state['lucky9_last_action']}"])
        if status:
            lines.extend(["", status])
        return discord.Embed(
            title=f"🎴 Arena {self.arena_id_value} — LUCKY 9",
            description="\n".join(lines),
            color=discord.Color.gold(),
        )

    def start_timer(self):
        if self.round_state.get("lucky9_natural_teams"):
            self.timer_task = asyncio.create_task(self.resolve_natural())
        elif self.current_team() is None:
            self.timer_task = asyncio.create_task(self.finish_round(
                self.message.channel if self.message else None,
                timed_out=False,
            ))
        else:
            self.timer_task = asyncio.create_task(self.run_timer())

    async def resolve_natural(self):
        try:
            await asyncio.sleep(0.8)
            natural = self.round_state.get("lucky9_natural_teams", [])
            winner = int(natural[0]) if len(natural) == 1 else None
            await self.finish_round(
                self.message.channel if self.message else None,
                winner_team=winner,
                natural=True,
            )
        except asyncio.CancelledError:
            return

    async def run_timer(self):
        try:
            remaining = ARENA_LUCKY9_TIMEOUT
            self.round_state["lucky9_time_remaining"] = remaining
            while remaining > 0 and not self.closed:
                wait_time = min(10, remaining)
                await asyncio.sleep(wait_time)
                remaining -= wait_time
                self.round_state["lucky9_time_remaining"] = remaining
                save_arenas()
                if self.message and not self.closed:
                    try:
                        await self.message.edit(embed=self.embed(), view=self)
                    except discord.HTTPException:
                        pass
            if not self.closed:
                await self.finish_round(
                    self.message.channel if self.message else None,
                    timed_out=True,
                )
        except asyncio.CancelledError:
            return

    async def interaction_check(self, interaction):
        if self.closed:
            await interaction.response.send_message(
                "This Lucky 9 round is already finished.", ephemeral=True
            )
            return False
        team = self.current_team()
        representative = self.representatives().get(str(team))
        if team is None or str(interaction.user.id) != str(representative):
            await interaction.response.send_message(
                "Only the bot-selected representative whose turn is active can play Lucky 9.",
                ephemeral=True,
            )
            return False
        return True

    async def take_action(self, interaction, action):
        await interaction.response.defer()
        async with self.lock:
            if self.closed:
                return
            team = self.current_team()
            team_key = str(team)
            cards = self.round_state.setdefault("lucky9_cards", {})
            scores = self.round_state.setdefault("lucky9_scores", {})
            stood = self.round_state.setdefault("lucky9_stood", {})
            third_drawn = self.round_state.setdefault("lucky9_third_drawn", {})
            if action == "draw":
                if third_drawn.get(team_key):
                    return await interaction.followup.send(
                        "This representative already used the optional third card.",
                        ephemeral=True,
                    )
                deck = self.round_state.setdefault("lucky9_deck", [])
                if not deck:
                    return await interaction.followup.send(
                        "The Lucky 9 deck is empty, so this hand must stand.",
                        ephemeral=True,
                    )
                cards.setdefault(team_key, []).append(deck.pop())
                third_drawn[team_key] = True
                scores[team_key] = lucky9_score(cards[team_key])
                action_text = (
                    f"{arena_team_name(team)} representative drew a third card: "
                    f"{lucky9_card_text(cards[team_key][-1])}. "
                    f"New score: **{scores[team_key]}**."
                )
            else:
                action_text = (
                    f"{arena_team_name(team)} representative stood on "
                    f"**{scores.get(team_key, 0)}**."
                )
            stood[team_key] = True
            self.round_state["lucky9_last_action"] = action_text
            active = [
                number for number in (1, 2)
                if not stood.get(str(number), False)
            ]
            self.round_state["lucky9_current_team"] = (
                active[0] if active else None
            )
            save_arenas()
            finished = not active
        if finished:
            return await self.finish_round(
                interaction.channel,
                timed_out=False,
                interaction=interaction,
            )
        try:
            await interaction.edit_original_response(
                embed=self.embed(),
                view=self,
            )
        except discord.HTTPException:
            pass
        if self.message:
            try:
                await self.message.edit(embed=self.embed(), view=self)
            except discord.HTTPException:
                pass

    async def finish_round(
        self,
        channel,
        timed_out=False,
        winner_team=None,
        natural=False,
        interaction=None,
    ):
        async with self.lock:
            if self.closed:
                return
            self.closed = True
            ARENA_GAME_VIEWS.pop(self.arena_id_value, None)
            if self.timer_task and self.timer_task is not asyncio.current_task():
                self.timer_task.cancel()
            if winner_team is None:
                scores = self.round_state.get("lucky9_scores", {})
                red_score = int(scores.get("1", 0))
                blue_score = int(scores.get("2", 0))
                if red_score != blue_score:
                    winner_team = 1 if red_score > blue_score else 2
            red_cards, blue_cards = self.result_card_lines()
            self.round_state["completed"] = True
            self.round_state["scores"] = {
                1: 1 if winner_team == 1 else 0,
                2: 1 if winner_team == 2 else 0,
            }
            self.arena["round_index"] = int(self.arena.get("round_index", 0)) + 1
            if winner_team:
                arena_round_winner(self.arena, self.round_state, winner_team)
                result = (
                    f"Lucky 9 scores — RED: **{self.round_state.get('lucky9_scores', {}).get('1', 0)}** "
                    f"• BLUE: **{self.round_state.get('lucky9_scores', {}).get('2', 0)}**. "
                    f"{arena_team_name(winner_team)} wins this round.\n\n"
                    f"{red_cards}\n{blue_cards}"
                )
                if natural:
                    result = (
                        f"{arena_team_name(winner_team)} hit a natural Lucky 9 "
                        "with the opening two cards and wins immediately.\n\n"
                        f"{red_cards}\n{blue_cards}"
                    )
                elif timed_out:
                    result = f"Time expired. {result}"
                embed = arena_round_winner_embed(
                    self.arena_id_value,
                    self.arena,
                    self.round_state,
                    winner_team,
                    result,
                )
            else:
                result = (
                    f"Lucky 9 scores tied — RED: **{self.round_state.get('lucky9_scores', {}).get('1', 0)}** "
                    f"• BLUE: **{self.round_state.get('lucky9_scores', {}).get('2', 0)}**. "
                    "This arena round is a draw.\n\n"
                    f"{red_cards}\n{blue_cards}"
                )
                embed = arena_round_draw_embed(
                    self.arena_id_value,
                    self.arena,
                    self.round_state,
                    result,
                )
            self.stop()
            for child in self.children:
                child.disabled = True
            save_arenas()
            if self.message:
                try:
                    await self.message.edit(embed=embed, view=self)
                except discord.HTTPException:
                    pass
            if interaction:
                try:
                    await interaction.edit_original_response(embed=embed, view=self)
                except discord.HTTPException:
                    pass
        await asyncio.sleep(ARENA_ROUND_RESULT_DELAY)
        if channel is not None:
            await continue_arena_match(self.arena_id_value, self.arena, channel)


class DealOrNoDealView(discord.ui.View):
    """Public shared 20-briefcase board for both arena teams."""

    def __init__(self, arena_id_value, arena, round_state):
        super().__init__(timeout=None)
        self.arena_id_value = arena_id_value
        self.arena = arena
        self.round_state = round_state
        self.message = None
        self.closed = False
        self.lock = asyncio.Lock()
        self.timer_task = None
        self.rebuild()

    def current_team(self):
        value = self.round_state.get("deal_current_team")
        return int(value) if value in (1, 2, "1", "2") else None

    def tiles(self):
        return self.round_state.setdefault("deal_tiles", [])

    def attempts(self):
        return self.round_state.setdefault("deal_attempts", {"1": 0, "2": 0})

    def rebuild(self):
        self.clear_items()
        for tile in self.tiles():
            index = int(tile.get("index", len(self.children)))
            revealed = bool(tile.get("revealed"))
            button = discord.ui.Button(
                label=(
                    f"💼 {tile.get('number', '?')}"
                    if revealed
                    else f"💼 Case {index + 1}"
                ),
                style=(
                    discord.ButtonStyle.success
                    if revealed and int(tile.get("number", -1))
                    == int(self.round_state.get("deal_target_number", -2))
                    else (
                        discord.ButtonStyle.secondary
                        if not revealed
                        else discord.ButtonStyle.danger
                    )
                ),
                row=index // 5,
                disabled=revealed or self.closed,
            )

            async def callback(interaction, selected_index=index):
                await self.flip_tile(interaction, selected_index)

            button.callback = callback
            self.add_item(button)

    def board_text(self):
        tiles = self.tiles()
        return " ".join(
            (
                f"**💼 {tile.get('number', '?')}**"
                if tile.get("revealed")
                else f"💼 `{int(tile.get('index', 0)) + 1:02d}`"
            )
            for tile in tiles
        )

    def embed(self, status=None):
        attempts = self.attempts()
        current_team = self.current_team()
        revealed = sum(1 for tile in self.tiles() if tile.get("revealed"))
        description = (
            f"**Target number to find: `{self.round_state.get('deal_target_number', '??')}`**\n"
            "Find it behind the briefcases.\n"
            f"20 shared tiles • **{revealed}/20** revealed\n\n"
            f"{self.board_text()}\n\n"
            f"🔴 RED flips: **{attempts.get('1', 0)}/{ARENA_DEAL_ATTEMPTS}**\n"
            f"🔵 BLUE flips: **{attempts.get('2', 0)}/{ARENA_DEAL_ATTEMPTS}**\n"
        )
        if current_team:
            description += (
                f"\n🎯 Current turn: **{arena_team_name(current_team)}**\n"
                f"⏱️ Time remaining: **{self.round_state.get('deal_time_remaining', ARENA_DEAL_TIMEOUT)} seconds**\n"
                "Any teammate on the active team may flip one tile. "
                "Every reveal is public to both teams."
            )
        else:
            description += "\nBoth teams have finished their flips. Revealing the result..."
        if self.round_state.get("deal_last_action"):
            description += f"\n\nLast action: {self.round_state['deal_last_action']}"
        if status:
            description += f"\n\n{status}"
        return discord.Embed(
            title=f"💼 Arena {self.arena_id_value} — DEAL OR NO DEAL",
            description=description,
            color=discord.Color.blurple(),
        )

    def start_timer(self):
        self.timer_task = asyncio.create_task(self.run_timer())

    async def run_timer(self):
        try:
            remaining = ARENA_DEAL_TIMEOUT
            self.round_state["deal_time_remaining"] = remaining
            while remaining > 0 and not self.closed:
                wait_time = min(10, remaining)
                await asyncio.sleep(wait_time)
                remaining -= wait_time
                self.round_state["deal_time_remaining"] = remaining
                save_arenas()
                if self.message and not self.closed:
                    try:
                        await self.message.edit(embed=self.embed(), view=self)
                    except discord.HTTPException:
                        pass
            if not self.closed:
                await self.finish_round(
                    self.message.channel if self.message else None,
                    timed_out=True,
                )
        except asyncio.CancelledError:
            return

    async def interaction_check(self, interaction):
        if self.closed:
            await interaction.response.send_message(
                "This Deal or No Deal round is already finished.",
                ephemeral=True,
            )
            return False
        user_id = str(interaction.user.id)
        if user_id not in arena_players(self.arena):
            await interaction.response.send_message(
                "Only registered arena players can flip a briefcase.",
                ephemeral=True,
            )
            return False
        team = arena_team_index(self.arena, user_id)
        if team != self.current_team():
            await interaction.response.send_message(
                f"It is currently {arena_team_name(self.current_team())} team's turn.",
                ephemeral=True,
            )
            return False
        return True

    async def flip_tile(self, interaction, tile_index):
        await interaction.response.defer()
        should_finish = False
        found_team = None
        status = None
        async with self.lock:
            if self.closed:
                return
            team = self.current_team()
            team_key = str(team)
            attempts = self.attempts()
            if int(attempts.get(team_key, 0)) >= ARENA_DEAL_ATTEMPTS:
                return await interaction.followup.send(
                    "Your team has used all three flips.",
                    ephemeral=True,
                )
            tiles = self.tiles()
            if tile_index < 0 or tile_index >= len(tiles):
                return await interaction.followup.send(
                    "That briefcase is not available.",
                    ephemeral=True,
                )
            tile = tiles[tile_index]
            if tile.get("revealed"):
                return await interaction.followup.send(
                    "That briefcase has already been flipped. Choose a covered tile.",
                    ephemeral=True,
                )
            attempts[team_key] = int(attempts.get(team_key, 0)) + 1
            tile["revealed"] = True
            tile["revealed_by_team"] = team
            tile["revealed_by_user"] = str(interaction.user.id)
            tile_number = int(tile.get("number"))
            target_number = int(self.round_state.get("deal_target_number"))
            self.round_state["deal_last_action"] = (
                f"{arena_team_name(team)} flipped Case {tile_index + 1} "
                f"and revealed **{tile_number}**."
            )
            found = tile_number == target_number
            no_attempts = all(
                int(attempts.get(str(team_number), 0)) >= ARENA_DEAL_ATTEMPTS
                for team_number in (1, 2)
            )
            if found:
                self.round_state["deal_current_team"] = None
                found_team = team
                should_finish = True
            elif no_attempts:
                self.round_state["deal_current_team"] = None
                should_finish = True
            else:
                other_team = 2 if team == 1 else 1
                if int(attempts.get(str(other_team), 0)) < ARENA_DEAL_ATTEMPTS:
                    self.round_state["deal_current_team"] = other_team
                else:
                    self.round_state["deal_current_team"] = team
            save_arenas()
            self.rebuild()
            status = (
                f"🔎 **{arena_team_name(team)}** revealed **{tile_number}** — "
                f"{'🎉 TARGET FOUND!' if found else 'not the target.'}"
            )
        if should_finish:
            await self.finish_round(
                interaction.channel,
                found_team=found_team,
                timed_out=False,
                interaction=interaction,
            )
            return
        if status:
            try:
                await interaction.edit_original_response(
                    embed=self.embed(status),
                    view=self,
                )
            except discord.HTTPException:
                pass
            if self.message:
                try:
                    await self.message.edit(embed=self.embed(status), view=self)
                except discord.HTTPException:
                    pass

    async def finish_round(
        self,
        channel,
        found_team=None,
        timed_out=False,
        interaction=None,
    ):
        async with self.lock:
            if self.closed:
                return
            self.closed = True
            ARENA_GAME_VIEWS.pop(self.arena_id_value, None)
            if self.timer_task and self.timer_task is not asyncio.current_task():
                self.timer_task.cancel()
            self.round_state["deal_current_team"] = None
            self.round_state["completed"] = True
            self.round_state["deal_time_remaining"] = 0
            self.arena["round_index"] = int(self.arena.get("round_index", 0)) + 1
            target_number = int(self.round_state.get("deal_target_number"))
            target_tile = next(
                (
                    tile for tile in self.tiles()
                    if int(tile.get("number", -1)) == target_number
                ),
                None,
            )
            if target_tile and not target_tile.get("revealed"):
                target_tile["revealed"] = True
                target_tile["revealed_by_team"] = None
                target_tile["revealed_by_user"] = None
            self.rebuild()
            target_text = (
                f"Target number: **{target_number}** "
                f"(Case {int(target_tile.get('index', 0)) + 1 if target_tile else '?'})."
            )
            if found_team:
                arena_round_winner(self.arena, self.round_state, found_team)
                self.round_state["scores"] = {
                    1: 1 if found_team == 1 else 0,
                    2: 1 if found_team == 2 else 0,
                }
                result = (
                    f"🎉 **{arena_team_name(found_team)} found the target and wins!**\n"
                    f"{target_text}\n"
                    f"{arena_team_name(found_team)} used "
                    f"{self.attempts().get(str(found_team), 0)}/{ARENA_DEAL_ATTEMPTS} flips."
                )
                embed = arena_round_winner_embed(
                    self.arena_id_value,
                    self.arena,
                    self.round_state,
                    found_team,
                    result,
                )
            else:
                self.round_state["scores"] = {"1": 0, "2": 0}
                result = (
                    f"😔 **No team found the target in three flips.**\n"
                    f"{target_text}\n"
                    "This Deal or No Deal round is a draw."
                )
                if timed_out:
                    result = f"⏰ **Time expired.**\n{result}"
                embed = arena_round_draw_embed(
                    self.arena_id_value,
                    self.arena,
                    self.round_state,
                    result,
                )
            save_arenas()
            if self.message:
                try:
                    await self.message.edit(embed=embed, view=self)
                except discord.HTTPException:
                    pass
            if interaction:
                try:
                    await interaction.edit_original_response(embed=embed, view=self)
                except discord.HTTPException:
                    pass
        await asyncio.sleep(ARENA_ROUND_RESULT_DELAY)
        if channel is not None:
            await continue_arena_match(self.arena_id_value, self.arena, channel)

    async def on_timeout(self):
        if not self.closed:
            await self.finish_round(
                self.message.channel if self.message else None,
                timed_out=True,
            )


class UnoArenaView(discord.ui.View):
    """Public UNO panel; each player opens a private hand to keep cards hidden."""

    def __init__(self, game):
        super().__init__(timeout=None)
        self.game = game
        button = discord.ui.Button(
            label="🃏 Open My UNO Hand",
            style=discord.ButtonStyle.primary,
            row=0,
        )
        button.callback = self.open_hand
        self.add_item(button)

    async def open_hand(self, interaction):
        if self.game.closed:
            return await interaction.response.send_message(
                "This UNO round is already finished.", ephemeral=True
            )
        user_id = str(interaction.user.id)
        if user_id not in self.game.hands:
            return await interaction.response.send_message(
                "Only registered arena players can play UNO.", ephemeral=True
            )
        hand_view = UnoHandView(self.game, user_id)
        await interaction.response.send_message(
            embed=self.game.hand_embed(user_id),
            view=hand_view,
            ephemeral=True,
        )


class UnoHandView(discord.ui.View):
    """Private, clickable UNO hand for one arena player."""

    def __init__(self, game, user_id):
        super().__init__(timeout=ARENA_UNO_TIMEOUT)
        self.game = game
        self.user_id = str(user_id)
        self.selected_ids = set()
        self.page = 0
        self.awaiting_color = False
        self.rebuild()

    def card_page(self):
        hand = self.game.hands.get(self.user_id, [])
        start = self.page * 15
        return hand[start:start + 15]

    def rebuild(self):
        self.clear_items()
        if self.awaiting_color:
            for color, style in (
                ("red", discord.ButtonStyle.danger),
                ("blue", discord.ButtonStyle.primary),
                ("violet", discord.ButtonStyle.secondary),
                ("green", discord.ButtonStyle.success),
            ):
                button = discord.ui.Button(
                    label=f"{UNO_COLOR_EMOJI[color]} {UNO_COLOR_LABELS[color]}",
                    style=style,
                    row=0,
                )

                async def color_callback(interaction, chosen_color=color):
                    await self.choose_color(interaction, chosen_color)

                button.callback = color_callback
                self.add_item(button)
            cancel = discord.ui.Button(
                label="Cancel selection",
                style=discord.ButtonStyle.secondary,
                row=1,
            )
            cancel.callback = self.cancel_color
            self.add_item(cancel)
            return

        cards = self.card_page()
        for card in cards:
            card_id = str(card.get("id"))
            selected = card_id in self.selected_ids
            color = str(card.get("color", "wild"))
            style = {
                "red": discord.ButtonStyle.danger,
                "blue": discord.ButtonStyle.primary,
                "violet": discord.ButtonStyle.secondary,
                "green": discord.ButtonStyle.success,
                "wild": discord.ButtonStyle.secondary,
            }.get(color, discord.ButtonStyle.secondary)
            button = discord.ui.Button(
                label=("✅ " if selected else "") + uno_card_button_label(card),
                style=style,
                row=len(self.children) // 5,
            )

            async def card_callback(interaction, selected_card_id=card_id):
                await self.toggle_card(interaction, selected_card_id)

            button.callback = card_callback
            self.add_item(button)

        controls_row = min(4, (len(cards) + 4) // 5)
        drop = discord.ui.Button(
            label="Drop selected",
            style=discord.ButtonStyle.success,
            row=controls_row,
        )
        drop.callback = self.drop_selected
        self.add_item(drop)
        draw = discord.ui.Button(
            label="Draw card",
            style=discord.ButtonStyle.primary,
            row=controls_row,
        )
        draw.callback = self.draw_card
        self.add_item(draw)
        if self.page > 0:
            previous = discord.ui.Button(
                label="◀ Previous",
                style=discord.ButtonStyle.secondary,
                row=controls_row,
            )
            previous.callback = self.previous_page
            self.add_item(previous)
        if (self.page + 1) * 15 < len(self.game.hands.get(self.user_id, [])):
            next_page = discord.ui.Button(
                label="Next ▶",
                style=discord.ButtonStyle.secondary,
                row=controls_row,
            )
            next_page.callback = self.next_page
            self.add_item(next_page)

    async def interaction_check(self, interaction):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message(
                "This is another player's private UNO hand.", ephemeral=True
            )
            return False
        if self.game.closed:
            await interaction.response.send_message(
                "This UNO round is already finished.", ephemeral=True
            )
            return False
        return True

    async def refresh(self, interaction, status=None):
        self.rebuild()
        await interaction.edit_original_response(
            embed=self.game.hand_embed(self.user_id, status),
            view=self,
        )

    async def toggle_card(self, interaction, card_id):
        await interaction.response.defer()
        if card_id in self.selected_ids:
            self.selected_ids.remove(card_id)
        else:
            self.selected_ids.add(card_id)
        await self.refresh(interaction)

    async def drop_selected(self, interaction):
        await interaction.response.defer()
        selected = uno_selected_cards(
            self.game.hands.get(self.user_id, []),
            self.selected_ids,
        )
        if not selected:
            return await self.refresh(interaction, "Select one or more cards first.")
        if any(card.get("value") in {"wild", "wild4"} for card in selected):
            self.awaiting_color = True
            return await self.refresh(
                interaction,
                "Choose the color that the next player must match.",
            )
        await self.game.play_cards(
            interaction,
            self.user_id,
            selected,
            None,
            self,
        )

    async def choose_color(self, interaction, color):
        await interaction.response.defer()
        selected = uno_selected_cards(
            self.game.hands.get(self.user_id, []),
            self.selected_ids,
        )
        self.awaiting_color = False
        await self.game.play_cards(
            interaction,
            self.user_id,
            selected,
            color,
            self,
        )

    async def cancel_color(self, interaction):
        await interaction.response.defer()
        self.awaiting_color = False
        await self.refresh(interaction)

    async def draw_card(self, interaction):
        await interaction.response.defer()
        await self.game.draw_for_player(interaction, self.user_id, self)

    async def previous_page(self, interaction):
        await interaction.response.defer()
        self.page = max(0, self.page - 1)
        await self.refresh(interaction)

    async def next_page(self, interaction):
        await interaction.response.defer()
        if (self.page + 1) * 15 < len(self.game.hands.get(self.user_id, [])):
            self.page += 1
        await self.refresh(interaction)

    async def on_timeout(self):
        self.stop()


class UnoArenaGame:
    """Stateful UNO engine used by the arena-specific private card views."""

    def __init__(self, arena_id_value, arena, round_state):
        self.arena_id_value = arena_id_value
        self.arena = arena
        self.round_state = round_state
        self.message = None
        self.closed = False
        self.lock = asyncio.Lock()
        self.timer_task = None

    @property
    def hands(self):
        return self.round_state.setdefault("uno_hands", {})

    @property
    def order(self):
        return self.round_state.get("uno_order", [])

    def current_user(self):
        if not self.order:
            return None
        index = int(self.round_state.get("uno_current_index", 0)) % len(self.order)
        return str(self.order[index])

    def hand_embed(self, user_id, status=None):
        hand = self.hands.get(str(user_id), [])
        top = self.round_state.get("uno_discard", [{}])[-1]
        pending = int(self.round_state.get("uno_pending_draw", 0))
        description = (
            f"You have **{len(hand)} card(s)**.\n"
            f"Active card: **{uno_card_text(top)}**\n"
            f"Active color: **{UNO_COLOR_LABELS.get(uno_active_color(self.round_state), 'Wild')}**\n"
            "Match the active **color** or **number/value** to play a card.\n"
            f"Current turn: <@{self.current_user() or 'unknown'}>\n"
            f"Selected cards: **0**"
        )
        if pending:
            description += (
                f"\n⚠️ You must stack **{pending} card(s)** or draw the penalty."
            )
        if status:
            description += f"\n\n{status}"
        embed = discord.Embed(
            title=f"🃏 UNO hand — {self.arena_id_value}",
            description=description,
            color=discord.Color.blurple(),
        )
        last_played = self.round_state.get("uno_last_played_cards", [])
        if last_played:
            embed.add_field(
                name="Last card dropped",
                value=" • ".join(uno_card_text(card) for card in last_played),
                inline=False,
            )
        embed.add_field(
            name="Your cards",
            inline=False,
        )
        return embed

    def public_embed(self, status=None):
        top = self.round_state.get("uno_discard", [{}])[-1]
        hand_counts = self.round_state.get("uno_hands", {})
        counts = []
        for team_number in (1, 2):
            team_total = sum(
                len(hand_counts.get(str(user_id), []))
                for user_id in arena_team_user_ids(self.arena, team_number)
            )
            counts.append(f"{arena_team_name(team_number)}: `{team_total}`")
        pending = int(self.round_state.get("uno_pending_draw", 0))
        description = (
            f"Match round **{self.round_state.get('number', 1)}/{ARENA_ROUNDS}**\n"
            f"Top discard: **{uno_card_text(top)}**\n"
            f"Active color: **{UNO_COLOR_LABELS.get(uno_active_color(self.round_state), 'Wild')}**\n"
            "Next player may match the active color or the card number/value.\n"
            f"Current turn: <@{self.current_user() or 'unknown'}>\n"
            f"Draw pile: `{len(self.round_state.get('uno_draw_pile', []))}` cards\n"
            f"Cards remaining — {' • '.join(counts)}\n"
            f"Last action: {self.round_state.get('uno_last_action', 'UNO has started.')}"
        )
        if pending:
            description += f"\n⚠️ Draw penalty waiting: **{pending} card(s)**"
        if status:
            description += f"\n\n{status}"
        embed = discord.Embed(
            title=f"🃏 Arena {self.arena_id_value} — UNO",
            description=description,
            color=discord.Color.orange(),
        )
        embed.add_field(
            name="Last card dropped",
            value=(
                " • ".join(
                    uno_card_text(card)
                    for card in self.round_state.get("uno_last_played_cards", [])
                )
                if self.round_state.get("uno_last_played_cards")
                else uno_card_text(top)
            ),
            inline=False,
        )
        return embed

    async def publish(self, status=None):
        if self.message:
            try:
                await self.message.edit(embed=self.public_embed(status), view=self.public_view)
            except discord.HTTPException:
                pass

    @property
    def public_view(self):
        return getattr(self, "_public_view", None)

    def set_public_view(self, view):
        self._public_view = view

    def start_timer(self):
        self.timer_task = asyncio.create_task(self.run_timer())

    async def run_timer(self):
        try:
            await asyncio.sleep(ARENA_UNO_TIMEOUT)
            await self.finish_round(
                self.message.channel if self.message else None,
                timed_out=True,
            )
        except asyncio.CancelledError:
            return

    def advance_turn(self, steps=1):
        if not self.order:
            return
        direction = int(self.round_state.get("uno_direction", 1))
        current = int(self.round_state.get("uno_current_index", 0))
        self.round_state["uno_current_index"] = (
            current + direction * int(steps)
        ) % len(self.order)

    def is_current_player(self, user_id):
        return str(user_id) == self.current_user()

    async def draw_for_player(self, interaction, user_id, hand_view):
        async with self.lock:
            if not self.is_current_player(user_id):
                return await hand_view.refresh(
                    interaction,
                    f"It is <@{self.current_user()}>’s turn.",
                )
            penalty = int(self.round_state.get("uno_pending_draw", 0))
            if self.round_state.get("uno_drawn_this_turn"):
                return await hand_view.refresh(
                    interaction,
                    "You already drew this turn. Play the drawn card if it is legal.",
                )
            amount = penalty or 1
            uno_draw_cards(self.round_state, user_id, amount)
            self.round_state["uno_drawn_this_turn"] = True
            self.round_state["uno_pending_draw"] = 0
            self.round_state["uno_pending_type"] = ""
            drawn = self.hands.get(str(user_id), [])[-amount:]
            self.round_state["uno_last_action"] = (
                f"<@{user_id}> drew **{len(drawn)}** card(s)."
            )
            if penalty:
                self.advance_turn()
                status = (
                    f"You drew the **{len(drawn)}-card penalty** and your turn was skipped."
                )
                self.round_state["uno_drawn_this_turn"] = False
            else:
                playable = any(
                    uno_card_is_legal(card, self.round_state) for card in drawn
                )
                if playable:
                    status = "You drew a card. Play it if it is legal; otherwise the turn passes."
                else:
                    self.advance_turn()
                    self.round_state["uno_drawn_this_turn"] = False
                    status = "You drew a card with no legal play, so the turn passed."
            save_arenas()
        await self.publish()
        await hand_view.refresh(interaction, status)

    async def play_cards(self, interaction, user_id, cards, chosen_color, hand_view):
        async with self.lock:
            if not self.is_current_player(user_id):
                return await hand_view.refresh(
                    interaction,
                    f"It is <@{self.current_user()}>’s turn.",
                )
            hand = self.hands.get(str(user_id), [])
            if not uno_cards_can_be_dropped(cards, self.round_state):
                return await hand_view.refresh(
                    interaction,
                    "Those cards cannot be dropped together. Match the active color/value; "
                    "draw cards must stack on the same color.",
                )
            values = {str(card.get("value")) for card in cards}
            if "wild4" in values:
                active_color = uno_active_color(self.round_state)
                has_matching_color = any(
                    str(card.get("color")) == active_color
                    and str(card.get("value")) not in {"wild", "wild4"}
                    and str(card.get("id")) not in {
                        str(selected.get("id")) for selected in cards
                    }
                    for card in hand
                )
                if has_matching_color:
                    return await hand_view.refresh(
                        interaction,
                        "You cannot use +4 while you still have a card matching the active color.",
                    )
            if any(card.get("value") in {"wild", "wild4"} for card in cards):
                if chosen_color not in UNO_COLORS:
                    return await hand_view.refresh(
                        interaction,
                        "Choose red, blue, violet, or green for the wild card.",
                    )
            hand_ids = {str(card.get("id")) for card in cards}
            self.hands[str(user_id)] = [
                card for card in hand if str(card.get("id")) not in hand_ids
            ]
            self.round_state["uno_drawn_this_turn"] = False
            self.round_state.setdefault("uno_discard", []).extend(cards)
            self.round_state["uno_last_played_cards"] = list(cards)
            last = cards[-1]
            value = str(last.get("value"))
            if value in {"wild", "wild4"}:
                self.round_state["uno_active_color"] = chosen_color
            else:
                self.round_state["uno_active_color"] = str(last.get("color"))
            if value == "draw2":
                self.round_state["uno_pending_draw"] = (
                    int(self.round_state.get("uno_pending_draw", 0))
                    + 2 * len(cards)
                )
                self.round_state["uno_pending_type"] = "draw2"
            elif value == "wild4":
                self.round_state["uno_pending_draw"] = (
                    int(self.round_state.get("uno_pending_draw", 0))
                    + 4 * len(cards)
                )
                self.round_state["uno_pending_type"] = "wild4"
            else:
                self.round_state["uno_pending_draw"] = 0
                self.round_state["uno_pending_type"] = ""
            if value == "reverse":
                if len(self.order) == 2:
                    self.advance_turn(2)
                else:
                    self.round_state["uno_direction"] = (
                        -int(self.round_state.get("uno_direction", 1))
                    )
                    self.advance_turn()
            elif value == "skip":
                self.advance_turn(2)
            elif value in {"draw2", "wild4"}:
                self.advance_turn()
            else:
                self.advance_turn()
            self.round_state["uno_last_action"] = (
                f"<@{user_id}> dropped {len(cards)} card(s): "
                + ", ".join(uno_card_text(card) for card in cards)
                + "."
            )
            emptied = not self.hands.get(str(user_id))
            save_arenas()
        if emptied:
            return await self.finish_round(
                interaction.channel if interaction else None,
                winner_user=user_id,
                interaction=interaction,
            )
        await self.publish()
        hand_view.selected_ids.clear()
        await hand_view.refresh(interaction, "Cards dropped successfully.")

    async def finish_round(self, channel, timed_out=False, winner_user=None, interaction=None):
        async with self.lock:
            if self.closed:
                return
            self.closed = True
            if self.timer_task and self.timer_task is not asyncio.current_task():
                self.timer_task.cancel()
            ARENA_GAME_VIEWS.pop(self.arena_id_value, None)
            if winner_user:
                winner_team = arena_team_index(self.arena, winner_user)
                result = (
                    f"<@{winner_user}> emptied their UNO hand. "
                    f"{arena_team_name(winner_team)} wins the UNO round."
                )
            else:
                team_totals = {
                    team_number: sum(
                        len(self.hands.get(str(user_id), []))
                        for user_id in arena_team_user_ids(self.arena, team_number)
                    )
                    for team_number in (1, 2)
                }
                if team_totals[1] == team_totals[2]:
                    winner_team = None
                    result = (
                        f"UNO timed out after {ARENA_UNO_TIMEOUT} seconds. "
                        f"Card totals tied at `{team_totals[1]}`; the round is a draw."
                    )
                else:
                    winner_team = 1 if team_totals[1] < team_totals[2] else 2
                    result = (
                        f"UNO timed out after {ARENA_UNO_TIMEOUT} seconds. "
                        f"{arena_team_name(winner_team)} had fewer cards "
                        f"({team_totals[winner_team]}) and wins the round."
                    )
            self.round_state["completed"] = True
            self.round_state["scores"] = {
                1: 1 if winner_team == 1 else 0,
                2: 1 if winner_team == 2 else 0,
            }
            self.arena["round_index"] = int(self.arena.get("round_index", 0)) + 1
            if winner_team:
                arena_round_winner(self.arena, self.round_state, winner_team)
                embed = arena_round_winner_embed(
                    self.arena_id_value,
                    self.arena,
                    self.round_state,
                    winner_team,
                    result,
                )
            else:
                embed = arena_round_draw_embed(
                    self.arena_id_value,
                    self.arena,
                    self.round_state,
                    result,
                )
            save_arenas()
            if self.public_view:
                self.public_view.stop()
            if self.message:
                try:
                    await self.message.edit(embed=embed, view=self.public_view)
                except discord.HTTPException:
                    pass
            if interaction:
                try:
                    await interaction.edit_original_response(embed=embed, view=None)
                except discord.HTTPException:
                    pass
        await asyncio.sleep(ARENA_ROUND_RESULT_DELAY)
        if channel is not None:
            await continue_arena_match(self.arena_id_value, self.arena, channel)


class ArenaGameView(discord.ui.View):
    """Interactive one-action panel for every non-Mines arena game."""

    def __init__(self, arena_id_value, arena, round_state):
        super().__init__(
            timeout=None
            if round_state.get("game_key") == "bugtong"
            else ARENA_MINES_PHASE_TIMEOUT
        )
        self.arena_id_value = arena_id_value
        self.arena = arena
        self.round_state = round_state
        self.message = None
        self.closed = False
        self.bugtong_lock = asyncio.Lock()
        self.bugtong_timer_task = None
        self.scores = {
            str(user_id): int(score)
            for user_id, score in round_state.get("scores_by_player", {}).items()
        }
        if round_state.get("game_key") == "bugtong":
            self.add_bugtong_buttons()
        else:
            button = discord.ui.Button(
                label=arena_game_action_label(round_state.get("game_key")),
                style=discord.ButtonStyle.primary,
            )
            button.callback = self.play_button
            self.add_item(button)

    def round_embed(self, status=None):
        players = arena_players(self.arena)
        if self.round_state.get("game_key") == "bugtong":
            representatives = self.round_state.get(
                "bugtong_representatives", {}
            )
            waiting = [
                str(user_id)
                for user_id in representatives.values()
                if str(user_id) not in self.round_state.get("bugtong_answers", {})
            ]
            played_text = (
                f"Representatives answered: "
                f"**{2 - len(waiting)}/2**"
            )
        else:
            waiting = [user_id for user_id in players if user_id not in self.scores]
            played_text = f"Played: **{len(self.scores)}/{len(players)}** players"
        description = (
            f"Match round **{self.round_state.get('number', 1)}/{ARENA_ROUNDS}**\n"
            f"Game: **{self.round_state.get('game_name', 'Arena Game')}**\n"
            f"{played_text}\n"
            f"Time limit: **{ARENA_MINES_PHASE_TIMEOUT} seconds**"
        )
        if self.round_state.get("game_key") == "bugtong":
            description += (
                "\n\n📜 **BUGTONG-BUGTONG**\n"
                f"**{self.round_state.get('bugtong_prompt', 'Bugtong')}**\n"
                "Piliin ng RED at BLUE representative ang tamang sagot. "
                "Parehong sagot ang kailangan bago malutas ang tanong."
            )
            representatives = self.round_state.get("bugtong_representatives", {})
            answers = self.round_state.get("bugtong_answers", {})
            description += (
                f"\nRED representative: <@{representatives.get('1', 'unknown')}> — "
                f"{'✅ answered' if str(representatives.get('1')) in answers else '⏳ waiting'}"
                f"\nBLUE representative: <@{representatives.get('2', 'unknown')}> — "
                f"{'✅ answered' if str(representatives.get('2')) in answers else '⏳ waiting'}"
                f"\nTime limit: **{ARENA_MINES_PHASE_TIMEOUT} seconds**"
            )
        else:
            description += (
                f"\n**{arena_game_action_label(self.round_state.get('game_key'))}** "
                "button: click once to play."
            )
        if waiting:
            description += (
                "\nWaiting for: "
                + " ".join(f"<@{user_id}>" for user_id in waiting)
            )
        if status:
            description += f"\n\n{status}"
        return discord.Embed(
            title=(
                f"🏟️ Arena {self.arena_id_value} — "
                f"Round {self.round_state.get('number', 1)}"
            ),
            description=description,
            color=discord.Color.orange(),
        )

    def is_player(self, user_id):
        return str(user_id) in {
            str(player_id) for player_id in arena_players(self.arena)
        }

    def add_bugtong_buttons(self):
        self.clear_items()
        for choice in self.round_state.get("bugtong_choices", []):
            button = discord.ui.Button(
                label=str(choice),
                style=discord.ButtonStyle.primary,
                row=0,
            )

            async def bugtong_callback(interaction, selected_choice=choice):
                await self.submit_player(
                    str(interaction.user.id),
                    choice=selected_choice,
                    interaction=interaction,
                )

            button.callback = bugtong_callback
            self.add_item(button)

    def start_bugtong_timer(self):
        if self.round_state.get("game_key") != "bugtong":
            return
        if self.bugtong_timer_task:
            self.bugtong_timer_task.cancel()
        self.bugtong_timer_task = asyncio.create_task(self.run_bugtong_timer())

    async def run_bugtong_timer(self):
        try:
            await asyncio.sleep(ARENA_MINES_PHASE_TIMEOUT)
            await self.finish_bugtong_question(
                self.message.channel if self.message else None,
                timed_out=True,
            )
        except asyncio.CancelledError:
            return

    async def interaction_check(self, interaction):
        user_id = str(interaction.user.id)
        if self.closed:
            await interaction.response.send_message(
                "This arena round is already finished.", ephemeral=True
            )
            return False
        if self.round_state.get("game_key") == "bugtong":
            representatives = {
                str(value)
                for value in self.round_state.get(
                    "bugtong_representatives", {}
                ).values()
            }
            if user_id not in representatives:
                await interaction.response.send_message(
                    "Only the bot-selected RED and BLUE representatives can answer this Bugtong.",
                    ephemeral=True,
                )
                return False
            if user_id in self.round_state.get("bugtong_answers", {}):
                await interaction.response.send_message(
                    "You already answered this Bugtong question.",
                    ephemeral=True,
                )
                return False
            return True
        if not self.is_player(user_id):
            await interaction.response.send_message(
                "Only registered arena players can play this round.",
                ephemeral=True,
            )
            return False
        if user_id in self.scores:
            await interaction.response.send_message(
                "You already played this round.", ephemeral=True
            )
            return False
        return True

    async def play_button(self, interaction):
        await self.submit_player(str(interaction.user.id), interaction=interaction)

    async def submit_player(self, user_id, choice=None, interaction=None, ctx=None):
        user_id = str(user_id)
        if self.closed:
            response = "This arena round is already finished."
        elif not self.is_player(user_id):
            response = "Only registered arena players can play this round."
        elif user_id in self.scores:
            response = "You already played this round."
        else:
            response = None
        if response:
            if interaction:
                return await interaction.response.send_message(response, ephemeral=True)
            if ctx:
                return await ctx.send(response)
            return False

        if interaction:
            await interaction.response.defer()
        if self.round_state.get("game_key") == "bugtong":
            return await self.submit_bugtong_answer(
                user_id,
                choice,
                interaction=interaction,
            )
        try:
            score = arena_game_score(
                self.round_state["game_key"],
                choice,
                self.round_state,
            )
        except (TypeError, ValueError) as exc:
            response = str(exc)
            if interaction:
                return await interaction.followup.send(response, ephemeral=True)
            if ctx:
                return await ctx.send(response)
            return False

        self.scores[user_id] = int(score)
        self.round_state["scores_by_player"] = dict(self.scores)
        self.round_state["players_played"] = list(self.scores)
        save_arenas()
        if self.round_state.get("game_key") == "bugtong":
            status = f"<@{user_id}> selected an answer."
        else:
            status = f"<@{user_id}> played and scored **{score}**."
        if interaction:
            try:
                await interaction.edit_original_response(
                    embed=self.round_embed(f"⚡ {status} Resolving..."),
                    view=self,
                )
            except discord.HTTPException:
                pass
            await asyncio.sleep(0.45)
        if len(self.scores) >= len(arena_players(self.arena)):
            await self.finish_round(
                interaction.channel if interaction else ctx.channel,
                interaction=interaction,
            )
        else:
            if self.message:
                try:
                    await self.message.edit(embed=self.round_embed(status), view=self)
                except discord.HTTPException:
                    pass
            if interaction:
                await interaction.edit_original_response(
                    embed=self.round_embed(status),
                    view=self,
                )
            elif ctx:
                await ctx.send(f"✅ {status}")
        return True

    async def submit_bugtong_answer(self, user_id, choice, interaction=None):
        should_finish = False
        finish_channel = None
        async with self.bugtong_lock:
            representatives = self.round_state.get(
                "bugtong_representatives", {}
            )
            team_number = next(
                (
                    int(team)
                    for team, representative in representatives.items()
                    if str(representative) == str(user_id)
                ),
                None,
            )
            if team_number not in (1, 2):
                return False
            answers = self.round_state.setdefault("bugtong_answers", {})
            if str(user_id) in answers:
                return True
            correct = (
                str(choice).strip().casefold()
                == str(self.round_state.get("bugtong_answer", "")).casefold()
            )
            answers[str(user_id)] = {
                "team": team_number,
                "choice": str(choice),
                "correct": correct,
            }
            save_arenas()
            status = (
                f"✅ {arena_team_name(team_number)} representative answered. "
                "Waiting for the other team..."
            )
            if len(answers) < 2:
                if self.message:
                    await self.message.edit(
                        embed=self.round_embed(status),
                        view=self,
                    )
                if interaction:
                    await interaction.edit_original_response(
                        embed=self.round_embed(status),
                        view=self,
                    )
                return True
            should_finish = True
            finish_channel = (
                interaction.channel
                if interaction
                else (self.message.channel if self.message else None)
            )
        if should_finish:
            await self.finish_bugtong_question(
                finish_channel,
                interaction=interaction,
            )
        return True

    async def finish_bugtong_question(
        self,
        channel,
        timed_out=False,
        interaction=None,
    ):
        if self.closed:
            return
        async with self.bugtong_lock:
            if self.closed:
                return
            answers = self.round_state.setdefault("bugtong_answers", {})
            representatives = self.round_state.get(
                "bugtong_representatives", {}
            )
            if timed_out:
                for team_number in (1, 2):
                    representative = str(representatives.get(str(team_number), ""))
                    if representative and representative not in answers:
                        answers[representative] = {
                            "team": team_number,
                            "choice": None,
                            "correct": False,
                            "timed_out": True,
                        }
            if len(answers) < 2:
                return
            if self.bugtong_timer_task:
                self.bugtong_timer_task.cancel()
                self.bugtong_timer_task = None
            correct_teams = {
                int(answer["team"])
                for answer in answers.values()
                if answer.get("correct")
            }
            if correct_teams == {1, 2}:
                if self.message:
                    await self.message.edit(
                        embed=self.round_embed(
                            "🎉 Both representatives got it correct! "
                            "Next Bugtong is loading..."
                        ),
                        view=self,
                    )
                await asyncio.sleep(0.8)
                arena_prepare_bugtong_round(self.round_state, self.arena)
                self.add_bugtong_buttons()
                save_arenas()
                if self.message:
                    await self.message.edit(
                        embed=self.round_embed(),
                        view=self,
                    )
                self.start_bugtong_timer()
                return
            self.closed = True
            self.round_state["scores"] = {
                1: 1 if 1 in correct_teams else 0,
                2: 1 if 2 in correct_teams else 0,
            }
            self.round_state["completed"] = True
            self.arena["round_index"] = int(
                self.arena.get("round_index", 0)
            ) + 1
            self.stop()
            for child in self.children:
                child.disabled = True
            answer = self.round_state.get("bugtong_answer")
            if correct_teams:
                winner_team = next(iter(correct_teams))
                arena_round_winner(
                    self.arena,
                    self.round_state,
                    winner_team,
                )
                result = (
                    f"Correct answer: **{answer}**. "
                    f"{arena_team_name(winner_team)} representative was "
                    "correct, so that team wins this arena round."
                )
                embed = arena_round_winner_embed(
                    self.arena_id_value,
                    self.arena,
                    self.round_state,
                    winner_team,
                    result,
                )
            else:
                result = (
                    f"Correct answer: **{answer}**. "
                    "Both representatives were incorrect or timed out. "
                    "No team wins this arena round."
                )
                embed = arena_round_draw_embed(
                    self.arena_id_value,
                    self.arena,
                    self.round_state,
                    result,
                )
            save_arenas()
            if self.message:
                await self.message.edit(embed=embed, view=self)
            if interaction:
                try:
                    await interaction.edit_original_response(
                        embed=embed,
                        view=self,
                    )
                except discord.HTTPException:
                    pass
            await asyncio.sleep(ARENA_ROUND_RESULT_DELAY)
            if channel is not None:
                await continue_arena_match(
                    self.arena_id_value,
                    self.arena,
                    channel,
                )

    async def finish_round(self, channel, timed_out=False, interaction=None):
        if self.closed:
            return
        self.closed = True
        ARENA_GAME_VIEWS.pop(self.arena_id_value, None)
        players = arena_players(self.arena)
        missing = [user_id for user_id in players if user_id not in self.scores]
        for user_id in missing:
            self.scores[user_id] = 0
        self.round_state["scores_by_player"] = dict(self.scores)
        team_scores = {
            team_number: sum(
                self.scores.get(str(user_id), 0)
                for user_id in arena_team_user_ids(self.arena, team_number)
            )
            for team_number in (1, 2)
        }
        self.round_state["scores"] = team_scores
        self.round_state["completed"] = True
        self.arena["round_index"] = int(self.arena.get("round_index", 0)) + 1
        self.stop()
        for child in self.children:
            child.disabled = True

        timeout_note = (
            f"⏰ Time expired; {len(missing)} player(s) scored zero. "
            if timed_out and missing else ""
        )
        bugtong_answer = self.round_state.get("bugtong_answer")
        answer_note = (
            f"Correct answer: **{bugtong_answer}**. "
            if self.round_state.get("game_key") == "bugtong" and bugtong_answer
            else ""
        )
        if team_scores[1] == team_scores[2]:
            save_arenas()
            result = (
                f"{timeout_note}{answer_note}"
                f"Both teams scored **{team_scores[1]}**. "
                "This round is a draw."
            )
            embed = arena_round_draw_embed(
                self.arena_id_value, self.arena, self.round_state, result
            )
        else:
            winner_team = 1 if team_scores[1] > team_scores[2] else 2
            arena_round_winner(self.arena, self.round_state, winner_team)
            save_arenas()
            result = (
                f"{timeout_note}{answer_note}"
                f"Scores: RED `{team_scores[1]}` • "
                f"BLUE `{team_scores[2]}`."
            )
            embed = arena_round_winner_embed(
                self.arena_id_value,
                self.arena,
                self.round_state,
                winner_team,
                result,
            )
        if interaction is not None:
            try:
                await interaction.edit_original_response(embed=embed, view=self)
            except discord.HTTPException:
                pass
        elif self.message:
            try:
                await self.message.edit(embed=embed, view=self)
            except discord.HTTPException:
                pass
        await asyncio.sleep(ARENA_ROUND_RESULT_DELAY)
        await continue_arena_match(self.arena_id_value, self.arena, channel)

    async def on_timeout(self):
        if self.closed:
            return
        await self.finish_round(self.message.channel, timed_out=True)

PROPERTY_SHOP = {
    "penthouse": {
        "name": "Uwuncy Penthouse",
        "price": 100_000_000_000,
        "description": "A permanent luxury profile badge.",
    },
    "mansion": {
        "name": "Golden Mansion",
        "price": 500_000_000_000,
        "description": "A permanent elite property title.",
    },
    "moonbase": {
        "name": "Moonbase",
        "price": 2_000_000_000_000,
        "description": "A rare endgame property collectible.",
    },
}
COLLECTIBLE_SHOP = {
    "jackpotcrown": {
        "name": "Jackpot Crown",
        "price": 250_000_000_000,
        "description": "A prestigious crown for the richest gamblers.",
    },
    "arena-trophy": {
        "name": "Arena Trophy",
        "price": 100_000_000_000,
        "description": "A trophy commemorating arena champions.",
    },
    "diamond-paw": {
        "name": "Diamond Paw",
        "price": 750_000_000_000,
        "description": "A limited-looking collectible badge.",
    },
}
CLAN_UPGRADES = {
    "banner": {"price": 100_000_000_000, "description": "Unlocks a clan banner title."},
    "vault": {"price": 500_000_000_000, "description": "Unlocks a larger clan treasury badge."},
    "colosseum": {"price": 1_000_000_000_000, "description": "Unlocks clan tournament prestige."},
}
SEASON_REWARDS = (
    (1, 500_000_000_000, "Season Champion"),
    (2, 250_000_000_000, "Season Runner-up"),
    (3, 100_000_000_000, "Season Medalist"),
)

def load_clans():
    try:
        stored = CLANS_REF.get()
        return stored if isinstance(stored, dict) else {}
    except Exception as exc:
        raise RuntimeError(f"Firebase clan read failed: {exc}") from exc

def save_clans():
    try:
        CLANS_REF.set(CLANS)
    except Exception as exc:
        raise RuntimeError(f"Firebase clan write failed: {exc}") from exc

CLANS = load_clans()

def load_seasons():
    try:
        stored = SEASONS_REF.get()
        return stored if isinstance(stored, dict) else {}
    except Exception as exc:
        raise RuntimeError(f"Firebase season read failed: {exc}") from exc

def save_seasons():
    try:
        SEASONS_REF.set(SEASONS)
    except Exception as exc:
        raise RuntimeError(f"Firebase season write failed: {exc}") from exc

SEASONS = load_seasons()

def current_season_key():
    return utc_date()[:7]

def ensure_season(user):
    season = current_season_key()
    if user.get("season_key") != season:
        user["season_key"] = season
        user["season_score"] = 0
        user["season_claimed"] = False
    return season

def user_total_balance(user):
    return int(user.get("wallet", 0)) + int(user.get("bank", 0))

def clan_members(clan):
    members = clan.get("members", [])
    return [str(member) for member in members] if isinstance(members, list) else []

def season_rows():
    rows = []
    season = current_season_key()
    for user_id, record in DATA.items():
        if not isinstance(record, dict):
            continue
        user = normalize_user(record)
        ensure_season(user)
        if user.get("season_key") == season:
            rows.append((str(user_id), int(user.get("season_score", 0))))
    return sorted(rows, key=lambda item: (-item[1], item[0]))

def award_season_score(user, amount):
    ensure_season(user)
    user["season_score"] += max(0, int(amount))

# Four deliberately clear choices keep the color game easy to understand.
COLOR_CHOICES = {
    "red": "🟥",
    "blue": "🟦",
    "green": "🟩",
    "yellow": "🟨",
}
COLOR_SHORTCUTS = {
    "r": "red",
    "b": "blue",
    "g": "green",
    "y": "yellow",
}

def color_game_embed(game, status=None, timer=None):
    slots = game.get("slots", ["❔", "❔", "❔"])
    selection = game.get("selection")
    embed = discord.Embed(
        title="Color Game",
        description=(
            "Choose a color to start the round.\n"
            f"**{game['player_name']}** is playing"
        ),
        color=discord.Color.blurple(),
    )
    embed.add_field(
        name="Bet",
        value=f"`{format_coins(game['bet'])} uwuncy`",
        inline=True,
    )
    embed.add_field(
        name="Selection",
        value=(
            f"{COLOR_CHOICES[selection]} `{selection.title()}`"
            if selection else "`Choose below`"
        ),
        inline=True,
    )
    embed.add_field(
        name="Multiplier",
        value="`3.00x` for 3 matching slots\n`2.00x` for 2 matching slots",
        inline=False,
    )
    embed.add_field(
        name="Result",
        value=f"{slots[0]}  {slots[1]}  {slots[2]}",
        inline=False,
    )
    shield_status = game.get("shield_notice")
    if shield_status:
        embed.add_field(name="Loss Shield", value=shield_status, inline=False)
    if timer is not None:
        embed.add_field(name="Time", value=f"`{timer}s`", inline=True)
    if status:
        embed.add_field(name="Status", value=status, inline=False)
    embed.set_footer(text="Red (r) • Blue (b) • Green (g) • Yellow (y)")
    return embed

class ColorGameView(discord.ui.View):
    """A Mines-style color picker with a ten-second selection window."""

    def __init__(self, owner_id, game):
        super().__init__(timeout=10)
        self.owner_id = owner_id
        self.game = game
        self.message = None
        self.closed = False

        button_config = [
            ("Red", "red", discord.ButtonStyle.danger),
            ("Blue", "blue", discord.ButtonStyle.primary),
            ("Green", "green", discord.ButtonStyle.success),
            ("Yellow", "yellow", discord.ButtonStyle.secondary),
        ]
        for label, color, style in button_config:
            button = discord.ui.Button(
                label=label,
                style=style,
                custom_id=f"color_game_{color}",
                row=0,
            )

            async def color_callback(interaction, chosen=color):
                await self.choose(interaction, chosen)

            button.callback = color_callback
            self.add_item(button)

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "This is not your Color Game.",
                ephemeral=True,
            )
            return False
        if self.closed:
            await interaction.response.send_message(
                "This Color Game is already finished.",
                ephemeral=True,
            )
            return False
        return True

    def disable_buttons(self):
        for child in self.children:
            child.disabled = True

    async def choose(self, interaction, color):
        if self.closed:
            return await interaction.response.send_message(
                "This Color Game is already finished.",
                ephemeral=True,
            )
        self.closed = True
        self.game["selection"] = color
        self.disable_buttons()

        await interaction.response.edit_message(
            embed=color_game_embed(self.game, "Color locked. Spinning the slots..."),
            view=self,
        )
        await self.resolve()

    async def start_with_color(self, color):
        """Resolve a color selected in the command syntax, e.g. `cg r 500`."""
        if self.closed:
            return
        self.closed = True
        self.game["selection"] = color
        self.disable_buttons()
        if self.message:
            await self.message.edit(
                embed=color_game_embed(
                    self.game,
                    f"{COLOR_CHOICES[color]} {color.title()} selected. Spinning the slots...",
                ),
                view=self,
            )
        await self.resolve()

    async def resolve(self):
        colors = list(COLOR_CHOICES)
        selected = self.game["selection"]
        if self.game.get("target_win"):
            self.game["slots"] = [selected] * 3
        else:
            losing_colors = [color for color in colors if color != selected]
            if random.random() < 0.5:
                # Near miss: a pair the player did not pick, so it never pays.
                pair_color = random.choice(losing_colors)
                third_color = random.choice(
                    [color for color in colors if color != pair_color]
                )
                self.game["slots"] = [pair_color, pair_color, third_color]
                random.shuffle(self.game["slots"])
            else:
                self.game["slots"] = [
                    random.choice(losing_colors) for _ in range(3)
                ]
        if self.message:
            try:
                await self.message.edit(
                    embed=color_game_embed(self.game, "Final result..."),
                    view=self,
                )
            except discord.HTTPException:
                # The outcome still settles even when Discord cannot edit.
                pass
        slots = self.game["slots"]
        matching = slots.count(selected)
        if matching == 3:
            # The bet is reserved, so the multiplier is a total return.
            multiplier = INSTANT_WIN_RETURN
            payout = int(self.game["bet"] * multiplier)
            outcome = (
                f"Three {COLOR_CHOICES[selected]} **{selected.title()}** slots. "
                f"Profit: **+{format_coins(payout - self.game['bet'])} uwuncy**"
            )
        elif matching == 2:
            multiplier = COLORGAME_PAIR_RETURN
            payout = int(self.game["bet"] * multiplier)
            outcome = (
                f"Two {COLOR_CHOICES[selected]} **{selected.title()}** slots. "
                f"Profit: **+{format_coins(payout - self.game['bet'])} uwuncy**"
            )
        else:
            multiplier = 0
            payout = 0
            user = get_user(self.owner_id)
            loss_result = settle_loss(user, self.game["bet"], bet_reserved=True)
            outcome = describe_loss(loss_result, self.game["bet"], "No match")

        if matching:
            user = get_user(self.owner_id)
            total_payout, bonus, boosted = settle_win(user, payout)
            finish_game(user, "colorgame", self.game["bet"], True, total_payout)
        else:
            finish_game(user, "colorgame", self.game["bet"], False, loss_result["remaining_loss"])
            total_payout, bonus, boosted = 0, 0, False
        save_data(DATA)
        self.disable_buttons()
        if self.message:
            await self.message.edit(
                embed=color_game_embed(
                    self.game,
                    f"{outcome}\n"
                    + (
                        f"Lucky Potion bonus: **+{format_coins(bonus)} uwuncy**\n"
                        if boosted else ""
                    )
                    + (
                        f"Total credited: **+{format_coins(total_payout)} uwuncy** (profit + stake returned)\n"
                        if matching else ""
                    )
                    + f"Multiplier: **{multiplier:.2f}x**",
                ),
                view=self,
            )
        self.stop()
        await offer_double_or_nothing(
            self.message, self.owner_id, "colorgame", total_payout
        )

    async def on_timeout(self):
        if self.closed:
            return
        self.closed = True
        self.disable_buttons()
        credit_wallet(get_user(self.owner_id), self.game["bet"])
        save_data(DATA)
        if self.message:
            try:
                await self.message.edit(
                    embed=color_game_embed(
                        self.game,
                        "Time expired. Your bet was returned.",
                        0,
                    ),
                    view=self,
                )
            except discord.HTTPException:
                pass

def mines_tile_survival(bombs, found):
    """Natural chance the next tile is safe on a 4x4 board."""
    remaining = 16 - found
    if remaining <= 0:
        return 0.0
    return max(0.0, (remaining - bombs) / remaining)

def mines_multiplier(bombs, found):
    """Progressive total return for a 4x4 Mines board, after the house edge."""
    multiplier = 1.0 - HOUSE_EDGE
    safe_tiles = 16 - bombs
    for step in range(found):
        multiplier *= (16 - step) / (safe_tiles - step)
    return multiplier

def mines_embed(game, status=None):
    current = mines_multiplier(game["bombs"], len(game["revealed"]))
    next_multiplier = (
        current * (16 - len(game["revealed"])) /
        (16 - game["bombs"] - len(game["revealed"]))
        if len(game["revealed"]) < 16 - game["bombs"]
        else current
    )
    embed = discord.Embed(
        title="Mines",
        description=(
            f"Choose a tile, watch the multiplier rise, then cash out.\n"
            f"**{game['player_name']}** is playing"
        ),
        color=discord.Color.blurple(),
    )
    embed.add_field(name="Bet", value=f"`{format_coins(game['bet'])} uwuncy`", inline=True)
    embed.add_field(name="Bombs", value=f"`{game['bombs']}`", inline=True)
    embed.add_field(name="Found", value=f"`{len(game['revealed'])}/{16 - game['bombs']}`", inline=True)
    embed.add_field(name="Current", value=f"`{current:.2f}x` ({format_coins(int(game['bet'] * current))} uwuncy)", inline=True)
    embed.add_field(name="Next safe tile", value=f"`{next_multiplier:.2f}x` ({format_coins(int(game['bet'] * next_multiplier))} uwuncy)", inline=True)
    shield_status = game.get("shield_notice")
    if shield_status:
        embed.add_field(name="Loss Shield", value=shield_status, inline=False)
    if status:
        embed.add_field(name="Status", value=status, inline=False)
    embed.set_footer(text="Select a tile to continue • Cash out when you are ready")
    return embed

class MinesView(discord.ui.View):
    """A private 4x4 Mines board rendered with Discord buttons."""

    def __init__(self, owner_id, game):
        super().__init__(timeout=180)
        self.owner_id = owner_id
        self.game = game
        self.message = None
        self.closed = False

        for index in range(16):
            button = discord.ui.Button(
                label=str(index + 1),
                style=discord.ButtonStyle.secondary,
                row=index // 4,
            )

            async def tile_callback(interaction, tile=index):
                await self.reveal(interaction, tile)

            button.callback = tile_callback
            self.add_item(button)

        cashout = discord.ui.Button(
            label="Cash Out",
            style=discord.ButtonStyle.success,
            row=4,
        )
        cashout.callback = self.cash_out
        self.add_item(cashout)

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "This is not your Mines game.",
                ephemeral=True,
            )
            return False
        if self.closed:
            await interaction.response.send_message(
                "This Mines game is already finished.",
                ephemeral=True,
            )
            return False
        return True

    def disable_board(self, reveal_bombs=False):
        for index, child in enumerate(self.children):
            child.disabled = True
            if index < 16 and reveal_bombs:
                if index in self.game["bomb_locations"]:
                    child.label = "💣"
                    child.style = discord.ButtonStyle.danger
                elif index in self.game["revealed"]:
                    child.label = "💎"
                    child.style = discord.ButtonStyle.success
                else:
                    child.label = "·"

    async def reveal(self, interaction, tile):
        if tile in self.game["revealed"]:
            return await interaction.response.send_message(
                "That tile is already revealed.",
                ephemeral=True,
            )

        # Every tile is rolled under the configured odds, then the board is
        # rearranged to match, so the visible layout never contradicts the roll.
        bombs = self.game["bomb_locations"]
        survived = survive_step(
            "mines",
            mines_tile_survival(self.game["bombs"], len(self.game["revealed"])),
            self.owner_id,
        )
        if survived and tile in bombs:
            safe_replacements = [
                index for index in range(16)
                if index != tile
                and index not in bombs
                and index not in self.game["revealed"]
            ]
            if safe_replacements:
                bombs.remove(tile)
                bombs.add(random.choice(safe_replacements))
        elif not survived and tile not in bombs:
            bombs.remove(random.choice(tuple(bombs)))
            bombs.add(tile)

        button = self.children[tile]
        if tile in self.game["bomb_locations"]:
            self.closed = True
            user = get_user(self.owner_id)
            button.label = "💣"
            button.style = discord.ButtonStyle.danger
            self.disable_board(reveal_bombs=True)
            loss_result = settle_loss(user, self.game["bet"], bet_reserved=True)
            finish_game(user, "mines", self.game["bet"], False, loss_result["remaining_loss"])
            save_data(DATA)
            await interaction.response.edit_message(
                embed=mines_embed(
                    self.game,
                    describe_loss(loss_result, self.game["bet"], "💥 Bomb hit"),
                ),
                view=self,
            )
            self.stop()
            return

        self.game["revealed"].add(tile)
        button.label = "💎"
        button.style = discord.ButtonStyle.success
        button.disabled = True
        found = len(self.game["revealed"])
        safe_tiles = 16 - self.game["bombs"]

        if found == safe_tiles:
            self.closed = True
            multiplier = mines_multiplier(self.game["bombs"], found)
            payout = int(self.game["bet"] * multiplier)
            user = get_user(self.owner_id)
            total_payout, bonus, boosted = settle_win(user, payout)
            finish_game(user, "mines", self.game["bet"], True, total_payout)
            save_data(DATA)
            self.disable_board(reveal_bombs=True)
            await interaction.response.edit_message(
                embed=mines_embed(
                    self.game,
                    f"Board cleared. Payout: **+{format_coins(total_payout)} uwuncy**"
                    + (
                        f" (includes Lucky Potion bonus of "
                        f"+{format_coins(bonus)} uwuncy)"
                        if boosted else ""
                    ),
                ),
                view=self,
            )
            self.stop()
            await offer_double_or_nothing(
                self.message, self.owner_id, "mines", total_payout
            )
            return

        await interaction.response.edit_message(
            embed=mines_embed(
                self.game,
                f"Safe tile. You found **{found}** — keep going or cash out.",
            ),
            view=self,
        )

    async def cash_out(self, interaction):
        found = len(self.game["revealed"])
        if found == 0:
            return await interaction.response.send_message(
                "Reveal at least one safe tile before cashing out.",
                ephemeral=True,
            )
        self.closed = True
        multiplier = mines_multiplier(self.game["bombs"], found)
        payout = int(self.game["bet"] * multiplier)
        user = get_user(self.owner_id)
        total_payout, bonus, boosted = settle_win(user, payout)
        finish_game(user, "mines", self.game["bet"], True, total_payout)
        save_data(DATA)
        self.disable_board(reveal_bombs=True)
        await interaction.response.edit_message(
            embed=mines_embed(
                self.game,
                f"Cashed out at **{multiplier:.2f}x**. "
                f"Payout: **+{format_coins(total_payout)} uwuncy**"
                + (
                    f" (includes Lucky Potion bonus of "
                    f"+{format_coins(bonus)} uwuncy)"
                    if boosted else ""
                ),
            ),
            view=self,
        )
        self.stop()
        await offer_double_or_nothing(
            self.message, self.owner_id, "mines", total_payout
        )

    async def on_timeout(self):
        if self.closed:
            return
        self.closed = True
        # Return the reserved bet on expiry so an abandoned board cannot trap coins.
        credit_wallet(get_user(self.owner_id), self.game["bet"])
        save_data(DATA)
        self.disable_board(reveal_bombs=True)
        if self.message:
            try:
                await self.message.edit(
                    embed=mines_embed(self.game, "Game expired. Your bet was returned."),
                    view=self,
                )
            except discord.HTTPException:
                pass

class ArenaMinesView(discord.ui.View):
    """Two-team Arena Mines: one team hides four bombs, the other finds four safe tiles."""

    def __init__(
        self,
        arena_id_value,
        arena,
        round_state,
        phase="placement",
        bomb_locations=None,
    ):
        super().__init__(timeout=ARENA_MINES_PHASE_TIMEOUT)
        self.arena_id_value = arena_id_value
        self.arena = arena
        self.round_state = round_state
        self.message = None
        self.closed = False
        self.phase = phase
        self.bomb_locations = set(bomb_locations or [])
        self.safe_clicks = set()
        self.placement_complete = bool(
            phase == "placement" and len(self.bomb_locations) == 4
        )

        for index in range(15):
            button = discord.ui.Button(
                label=str(index + 1),
                style=discord.ButtonStyle.secondary,
                row=index // 5,
            )

            async def tile_callback(interaction, tile=index):
                await self.choose_tile(interaction, tile)

            button.callback = tile_callback
            self.add_item(button)

    def team_members(self, team_number):
        return set(arena_team_user_ids(self.arena, team_number))

    def phase_team(self):
        return (
            int(self.round_state["defender_team"])
            if self.phase == "placement"
            else int(self.round_state["attacker_team"])
        )

    async def interaction_check(self, interaction):
        if self.closed:
            await interaction.response.send_message(
                "This Arena Mines round is already finished.",
                ephemeral=True,
            )
            return False
        if self.phase == "placement" and self.placement_complete:
            await interaction.response.send_message(
                "All four bombs are locked. The enemy team gets the board when "
                "the 60-second placement timer ends.",
                ephemeral=True,
            )
            return False
        if str(interaction.user.id) not in {
            str(user_id) for user_id in self.team_members(self.phase_team())
        }:
            role = "defending" if self.phase == "placement" else "attacking"
            await interaction.response.send_message(
                f"Only the {role} team can use the board right now.",
                ephemeral=True,
            )
            return False
        return True

    def disable_board(self, reveal_bombs=False):
        for index, child in enumerate(self.children):
            child.disabled = True
            if reveal_bombs:
                if index in self.bomb_locations:
                    child.label = "💣"
                    child.style = discord.ButtonStyle.danger
                elif index in self.safe_clicks:
                    child.label = "✅"
                    child.style = discord.ButtonStyle.success
                else:
                    child.label = "·"

    def mark_visible_result(self, bomb_tile=None):
        """Disable Arena Mines while revealing only visible results."""
        self.disable_board(reveal_bombs=False)
        for tile in self.safe_clicks:
            self.children[tile].label = "✅"
            self.children[tile].style = discord.ButtonStyle.success
        if bomb_tile is not None:
            self.children[bomb_tile].label = "💣"
            self.children[bomb_tile].style = discord.ButtonStyle.danger

    def board_embed(self, status=None):
        phase_label = (
            f"Placement: `{len(self.bomb_locations)}/4` bombs selected "
            f"({ARENA_MINES_PHASE_TIMEOUT}s limit)"
            if self.phase == "placement"
            else (
                f"Safe tiles found: `{len(self.safe_clicks)}/4` "
                f"({ARENA_MINES_PHASE_TIMEOUT}s limit)"
            )
        )
        return arena_round_embed(
            self.arena_id_value,
            self.arena,
            self.round_state,
            f"{phase_label}\n{status}" if status else phase_label,
        )

    async def choose_tile(self, interaction, tile):
        if self.phase == "placement":
            if tile in self.bomb_locations:
                return await interaction.response.send_message(
                    "That tile already contains one of your hidden bombs.",
                    ephemeral=True,
                )
            self.bomb_locations.add(tile)
            if len(self.bomb_locations) == 4:
                self.placement_complete = True
            await interaction.response.send_message(
                f"Bomb hidden in tile **{tile + 1}**. "
                f"You have placed `{len(self.bomb_locations)}/4` bombs.",
                ephemeral=True,
            )
            if self.placement_complete:
                self.round_state["bomb_locations"] = sorted(self.bomb_locations)
                await self.message.edit(
                    embed=self.board_embed(
                        "All four bombs are locked. The enemy team gets the board "
                        "after the placement timer ends."
                    ),
                    view=self,
                )
                save_arenas()
            return

        if tile in self.safe_clicks:
            return await interaction.response.send_message(
                "That safe tile was already selected.",
                ephemeral=True,
            )
        # A Firebase write can outlast Discord's three-second interaction
        # response window. Acknowledge the button before persisting the result.
        await interaction.response.defer()
        if tile in self.bomb_locations:
            self.closed = True
            self.round_state["bomb_hit"] = tile
            self.mark_visible_result(bomb_tile=tile)
            arena_round_winner(
                self.arena,
                self.round_state,
                self.round_state["defender_team"],
            )
            self.arena["round_index"] = int(self.arena.get("round_index", 0)) + 1
            save_arenas()
            await interaction.edit_original_response(
                embed=arena_round_winner_embed(
                    self.arena_id_value,
                    self.arena,
                    self.round_state,
                    self.round_state["defender_team"],
                    "💣 **Bomb hit! The attacking team loses immediately.**",
                ),
                view=self,
            )
            self.stop()
            await asyncio.sleep(ARENA_ROUND_RESULT_DELAY)
            await continue_arena_match(self.arena_id_value, self.arena, interaction.channel)
            return

        self.safe_clicks.add(tile)
        self.round_state["safe_tiles"] = sorted(self.safe_clicks)
        if len(self.safe_clicks) == 4:
            self.closed = True
            arena_round_winner(
                self.arena,
                self.round_state,
                self.round_state["attacker_team"],
            )
            self.arena["round_index"] = int(self.arena.get("round_index", 0)) + 1
            self.mark_visible_result()
            save_arenas()
            await interaction.edit_original_response(
                embed=arena_round_winner_embed(
                    self.arena_id_value,
                    self.arena,
                    self.round_state,
                    self.round_state["attacker_team"],
                    "✅ **Four safe tiles found!**",
                ),
                view=self,
            )
            self.stop()
            await asyncio.sleep(ARENA_ROUND_RESULT_DELAY)
            await continue_arena_match(self.arena_id_value, self.arena, interaction.channel)
            return

        await interaction.edit_original_response(
            embed=self.board_embed(
                f"Safe tile. Find `{4 - len(self.safe_clicks)}` more safe tile(s)."
            ),
            view=self,
        )

    async def on_timeout(self):
        if self.closed:
            return
        self.closed = True
        if self.phase == "placement" and self.placement_complete:
            attack_view = ArenaMinesView(
                self.arena_id_value,
                self.arena,
                self.round_state,
                phase="attack",
                bomb_locations=self.bomb_locations,
            )
            attack_view.message = self.message
            self.stop()
            if self.message:
                try:
                    await self.message.edit(
                        embed=attack_view.board_embed(
                            "The 60-second placement timer ended. "
                            "The attacking team has 60 seconds to find 4 safe tiles."
                        ),
                        view=attack_view,
                    )
                except discord.HTTPException:
                    pass
            save_arenas()
            return
        self.disable_board(reveal_bombs=False)
        phase_name = "bomb placement" if self.phase == "placement" else "tile selection"
        save_arenas()
        if self.message:
            try:
                await self.message.edit(
                    embed=self.board_embed(
                        f"⏰ The 60-second {phase_name} timer expired. "
                        "Arena Mines is being rerolled into a new game."
                    ),
                    view=self,
                )
            except discord.HTTPException:
                pass
        self.stop()
        reroll_arena_mines_round(self.arena, self.round_state)
        save_arenas()
        if self.message and self.message.channel:
            await asyncio.sleep(ARENA_ROUND_RESULT_DELAY)
            await continue_arena_match(
                self.arena_id_value,
                self.arena,
                self.message.channel,
            )

# ==============================================
# ACCOUNT INFO COMMANDS
# ==============================================
async def send_user_info(ctx, member):
    """Send the detailed account view that is separate from the short balance command."""
    user = get_user(member.id)
    interest = apply_bank_interest(user)
    ensure_daily_quests(user)
    if interest:
        save_data(DATA)
    total = user["wallet"] + user["bank"]
    streak_label = "day" if user["streak"] == 1 else "days"
    _hunt_stage_level, hunt_stage_name, hunt_multiplier = get_hunt_stage(user["hunt_level"])
    clan_details = ""
    if user.get("clan_id") in CLANS:
        clan_details = f"\nClan: **{CLANS[user['clan_id']]['name']}**"
    permanent_progress = (
        f"\nPrestige: **{user['prestige']}**"
        f"\nProperties: `{len(user.get('properties', []))}`"
        f" • Collectibles: `{len(user.get('collection', []))}`"
        f"{clan_details}"
    )
    if user["crypto_private"]:
        crypto_details = ""
    else:
        _crypto_rows, _crypto_invested, crypto_value, crypto_profit = crypto_portfolio(user)
        crypto_details = (
            f"\nCrypto held value: `{format_crypto_price(crypto_value)}` uwuncy"
            f"\nCrypto profit/loss: `{crypto_profit:+,.2f} uwuncy`"
        )
    await ctx.send(f"""**{member.display_name}'s Info**
Wallet: `{format_coins(user['wallet'])}` uwuncy
Bank: `{format_coins(user['bank'])}` uwuncy
Daily streak: `{user['streak']} {streak_label}`
Level: **{user['level']}** (`{format_coins(user['xp'])}` XP)
Hunt: **Level {user['hunt_level']:,}** — {hunt_stage_name} (`{hunt_multiplier:.2f}x`)
Games: **{user['games_played']}** played • **{user['games_won']}** wins
Bank interest earned: `{format_coins(user['interest_earned'])}` uwuncy
{permanent_progress}
{crypto_details}
**Total: {format_coins(total)} uwuncy**""")


@bot.command(name="info", aliases=["userinfo"])
async def user_info(ctx, member: discord.Member = None):
    await send_user_info(ctx, member or ctx.author)


async def handle_user_info_suffix(message):
    """Support `uwu @user info` in addition to `uwu info @user`."""
    content = message.content.strip()
    if len(content) < 4 or content[:3].casefold() != "uwu":
        return False
    if len(content) > 3 and not content[3].isspace():
        return False
    parts = content[3:].strip().split()
    if len(parts) != 2 or parts[1].casefold() != "info":
        return False
    if not re.fullmatch(r"<@!?\d+>", parts[0]):
        return False

    ctx = await bot.get_context(message)
    try:
        member = await commands.MemberConverter().convert(ctx, parts[0])
    except commands.MemberNotFound:
        await message.channel.send("❌ I couldn't find that user in this server.")
    else:
        await send_user_info(ctx, member)
    return True


@bot.event
async def on_member_join(member):
    if member.guild is None:
        return

    # Track real-time invite
    inviter, inviter_net, _used_code = await track_member_join_invite(member)

    settings = get_guild_moderation_settings(member.guild)

    # 1. Anti-raid check
    banned_by_antiraid = False
    if settings.get("antiraid", False):
        now = time.time()
        guild_id = str(member.guild.id)
        joins = RAID_JOIN_TRACKER.setdefault(guild_id, deque())
        joins.append((now, member.id))
        while joins and joins[0][0] < now - settings.get("raid_join_window", 120):
            joins.popleft()
        if len(joins) >= settings.get("raid_join_threshold", 5):
            banned_members = []
            for _, user_id in list(joins):
                suspect = member.guild.get_member(user_id)
                if suspect is None or suspect.id == member.guild.owner_id:
                    continue
                if await ban_user_for_moderation(member.guild, suspect, "Anti-raid protection"):
                    banned_members.append(suspect.mention)
                    if suspect.id == member.id:
                        banned_by_antiraid = True
            if banned_members:
                destination = member.guild.system_channel
                if destination is not None:
                    try:
                        await destination.send(
                            "🚨 Anti-raid active: banned recent joiners to protect the server."
                        )
                    except discord.HTTPException:
                        pass

    if banned_by_antiraid:
        return

    # 2. Welcome Card
    welcome_channel_id = settings.get("welcome_channel")
    if welcome_channel_id:
        channel = member.guild.get_channel(welcome_channel_id)
        if channel is not None:
            embed = build_welcome_embed(member.guild, member, inviter=inviter, inviter_net=inviter_net)
            try:
                await channel.send(f"Welcome to {member.guild.name}, {member.mention}!", embed=embed)
            except discord.HTTPException:
                pass

    # 3. Dedicated Invite Log Channel (if configured via uwu invites set #channel)
    invite_channel_id = settings.get("invite_channel")
    if invite_channel_id:
        inv_channel = member.guild.get_channel(invite_channel_id)
        if inv_channel is not None:
            if inviter:
                msg_text = f"🎉 {member.mention} joined! Invited by {inviter.mention} (**{inviter_net}** total invites)."
            else:
                msg_text = f"🎉 {member.mention} joined! (Direct join / unknown inviter)."
            try:
                await inv_channel.send(msg_text)
            except discord.HTTPException:
                pass


@bot.event
async def on_member_remove(member):
    await track_member_leave_invite(member)


@bot.event
async def on_invite_create(invite):
    if invite.guild:
        cache = GUILD_INVITES_CACHE.setdefault(invite.guild.id, {})
        cache[invite.code] = invite.uses or 0
        if invite.inviter:
            g_store = get_invite_store(invite.guild.id)
            g_store["code_inviters"][invite.code] = str(invite.inviter.id)
            save_data(DATA)


@bot.event
async def on_invite_delete(invite):
    if invite.guild and invite.guild.id in GUILD_INVITES_CACHE:
        GUILD_INVITES_CACHE[invite.guild.id].pop(invite.code, None)


@bot.event
async def on_guild_channel_delete(channel):
    await ban_actor_from_audit_log(
        channel.guild,
        discord.AuditLogAction.channel_delete,
        channel.id,
        "nuke channel deletion",
    )


@bot.event
async def on_guild_role_delete(role):
    await ban_actor_from_audit_log(
        role.guild,
        discord.AuditLogAction.role_delete,
        role.id,
        "nuke role deletion",
    )


@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if message.guild is not None:
        u_data = get_user(message.author.id)
        if booster_utils.is_server_booster(message.author, u_data, guild=message.guild):
            now_ts = time.time()
            last_c = u_data.get("last_booster_claim", 0)
            if now_ts - last_c >= 86400:
                has_autoclaim = u_data.get("booster_passes", {}).get("auto_claim_pass", 0) > now_ts
                if has_autoclaim:
                    b_count = booster_utils.get_user_boost_count(message.author, u_data)
                    tot_rew, _ = booster_utils.calculate_booster_daily_reward(u_data, b_count)
                    u_data["wallet"] = u_data.get("wallet", 0) + tot_rew
                    u_data["last_booster_claim"] = now_ts
                    save_data(DATA)
                    try:
                        await message.channel.send(f"✨ **[Auto-Claim]** {message.author.mention}, your daily **+{booster_utils.format_trillion(tot_rew)} uwuncy** booster reward was automatically collected! ⚡")
                    except Exception:
                        pass
    if message.guild is not None and await handle_antispam_message(message):
        return
    if message.guild is not None and await handle_antibullying_message(message):
        return
    arena_channel_id = message.channel.id
    if getattr(message.channel, "parent", None) is not None:
        arena_channel_id = message.channel.parent.id
    active_id, active_arena = active_arena_for_channel(arena_channel_id)
    if active_arena is not None and str(message.author.id) not in arena_players(active_arena):
        try:
            await message.delete()
        except discord.HTTPException:
            pass
        return
    if active_id and active_arena is not None:
        math_view = ARENA_MATH_VIEWS.get(active_id)
        round_state = arena_current_round(active_arena)
        is_numeric_answer = bool(
            re.fullmatch(r"\s*-?\d[\d,]*\s*", message.content or "")
        )
        is_command = any(
            (message.content or "").casefold().startswith(prefix.casefold())
            for prefix in PREFIX_VARIANTS
        )
        if (
            math_view is not None
            and not math_view.closed
            and round_state
            and round_state.get("game_key") == "math"
            and is_numeric_answer
            and not is_command
        ):
            await math_view.submit_answer_text(
                str(message.author.id),
                message.content,
                channel=message.channel,
            )
            try:
                await message.delete()
            except discord.HTTPException:
                pass
            return
        if active_arena.get("status") == "match":
            try:
                await message.delete()
            except discord.HTTPException:
                pass
            return
    if await handle_user_info_suffix(message):
        return
    await bot.process_commands(message)

@bot.event
async def on_raw_reaction_add(payload):
    if bot.user and payload.user_id == bot.user.id:
        return
    channel = bot.get_channel(payload.channel_id)
    if channel is None:
        return
    arena_channel_id = channel.parent.id if getattr(channel, "parent", None) else channel.id
    _arena_id, arena = active_arena_for_channel(arena_channel_id)
    if arena is None or str(payload.user_id) in arena_players(arena):
        return
    try:
        message = await channel.fetch_message(payload.message_id)
        await message.remove_reaction(payload.emoji, discord.Object(id=payload.user_id))
    except (discord.HTTPException, discord.NotFound):
        pass


@bot.event
async def on_ready():
    print(f"\n✅ BOT ONLINE — LOGGED IN AS: {bot.user}")
    print(f"✅ CURRENT PREFIX: '{CURRENT_PREFIX}'")
    print("✅ OWNER MODE ACTIVE\n")
    if not crypto_market_loop.is_running():
        crypto_market_loop.start()
        print("✅ UWUCRYPTO MARKET LOOP ACTIVE")
    for guild in bot.guilds:
        try:
            await fetch_and_cache_guild_invites(guild)
        except Exception:
            pass
    print("✅ LIVE INVITE TRACKER ACTIVE FOR ALL GUILDS")

@bot.before_invoke
async def category_guard(ctx):
    await ensure_command_category_allowed(ctx)

@bot.event
async def on_command_error(ctx, error):
    """Keep command mistakes readable without hiding real persistence failures."""
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.CommandOnCooldown):
        if ctx.command and ctx.command.name.lower() != "booster" and booster_utils.is_server_booster(ctx.author, get_user(ctx.author.id), guild=ctx.guild):
            ctx.command.reset_cooldown(ctx)
            await ctx.reinvoke()
            return
        return await ctx.send(f"⏳ Cooldown! Try again in `{error.retry_after:.1f}s`.")
    if isinstance(error, commands.MissingRequiredArgument):
        return await ctx.send(
            f"❌ Missing `{error.param.name}`. Use `{get_prefix()}help` for command examples."
        )
    if isinstance(error, commands.BadArgument):
        return await ctx.send(
            f"❌ Invalid argument. Check the amount/member format and try again, or use `{get_prefix()}help`."
        )
    if isinstance(error, commands.CheckFailure):
        return await ctx.send("❌ You do not have permission to use that command.")
    if isinstance(error, CategoryDisabled):
        embed = discord.Embed(
            title="🔒 Category Disabled",
            description=f"**{error.display_name}** commands are currently disabled by the owner.",
            color=discord.Color.gold(),
        )
        return await ctx.send(embed=embed)
    if isinstance(error, commands.CommandInvokeError):
        original = error.original
        print(f"❌ Command `{ctx.command}` failed: {original!r}")
        traceback.print_exception(type(original), original, original.__traceback__)
        if isinstance(original, RuntimeError) and (
            str(original).startswith("Firebase game odds read failed")
            or str(original).startswith("Firebase game odds write failed")
        ):
            return await ctx.send(
                "⚠️ Game win chances could not be saved right now. "
                "Please try again shortly."
            )
        if isinstance(original, RuntimeError) and (
            str(original).startswith("Firebase read failed")
            or str(original).startswith("Firebase write failed")
        ):
            return await ctx.send(
                "⚠️ Your balance could not be saved right now. No new uwuncy were granted; please try again shortly."
            )
        if isinstance(original, RuntimeError) and (
            str(original).startswith("Firebase economy settings read failed")
            or str(original).startswith("Firebase economy settings write failed")
        ):
            return await ctx.send(
                "⚠️ Global economy settings could not be saved right now. "
                "Please try again shortly."
            )
        return await ctx.send("⚠️ Something went wrong while running that command. Please try again.")
    print(f"❌ Unhandled command error in `{ctx.command}`: {error!r}")

# ==============================================
# ✅ FIXED DAILY — CHECK FIRST → SAVE → NO UNLIMITED
# ==============================================
@bot.command(name="daily")
async def daily(ctx):
    user = get_user(ctx.author.id)
    interest = apply_bank_interest(user)
    ensure_daily_quests(user)
    now = time.time()
    diff = now - user["last_daily"]

    # ✅ CHECK COOLDOWN FIRST — BEFORE GIVING ANYTHING
    if diff < 86400:
        wait = int(86400 - diff)
        h = wait // 3600
        m = (wait % 3600) // 60
        if interest:
            save_data(DATA)
        return await ctx.send(f"📅 Already claimed today! Next in **{h}h {m}m**\n🔥 Current streak: **{user['streak']} days**")

    # ✅ ANIMATION ONLY IF COOLDOWN PASSED
    msg = await ctx.send("✨ Checking your streak...")
    await asyncio.sleep(0.4)
    await msg.edit(content="🎁 Preparing your reward...")
    await asyncio.sleep(0.4)

    # ✅ UPDATE VALUES
    user["streak"] = user["streak"] + 1 if diff < 172800 else 1
    base = daily_base_for_streak(user["streak"])
    total = base * user["streak"]
    credit_wallet(user, total)
    user["last_daily"] = now
    award_xp(user, 50 + user["streak"] * 5)
    update_achievements(user)
    add_history(user, {
        "type": "daily",
        "result": "reward",
        "bet": 0,
        "amount": total,
    })

    # ✅ SAVE — MUST RUN OR NOTHING STICKS
    save_data(DATA)

    # ✅ FINAL RESULT
    await msg.edit(content=f"""**Daily reward claimed**
Streak: **{user['streak']} days**
Daily amount: {format_coins(base)} × {user['streak']}
Total added: **{format_coins(total)} uwuncy**
Next streak reward scales with your streak.""")


@bot.command(name="claim")
async def claim_cmd(ctx):
    """Claim daily reward (500,000,000,000 uwuncy by default, 24-hour cooldown)."""
    user = get_user(ctx.author.id)
    now = time.time()
    last_claim = user.get("last_claim", 0)
    diff = now - last_claim

    if diff < 86400:
        remaining = int(86400 - diff)
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        seconds = remaining % 60
        return await ctx.send(
            f"⏳ **{ctx.author.display_name}**, you have already claimed your daily reward!\n"
            f"Please wait **{hours}h {minutes}m {seconds}s** before claiming again."
        )

    reward = ECONOMY_SETTINGS.get("claim_reward", 500_000_000_000)
    user["last_claim"] = now
    credit_wallet(user, reward)
    add_history(user, {
        "type": "claim",
        "result": "reward",
        "bet": 0,
        "amount": reward,
    })
    save_data(DATA)

    embed = discord.Embed(
        title="🎁 Daily Claim Success!",
        description=(
            f"Successfully claimed **{format_coins(reward)}** uwuncy!\n"
            f"💰 **New Wallet Balance:** `{format_coins(user['wallet'])}` uwuncy"
        ),
        color=discord.Color.green()
    )
    embed.set_footer(text="You can claim again in 24 hours.")
    await ctx.send(embed=embed)


@bot.command(name="claimamount", aliases=["setclaim", "claiminfo", "setclaimamount"])
async def claim_amount_cmd(ctx, amount_text: str = None):
    """Owner command to view/set daily claim reward amount and view claim usage count."""
    if not is_owner(ctx):
        return await ctx.send("❌ **Owner only command!**")

    claimed_users_count = sum(1 for uid, udata in DATA.items() if isinstance(udata, dict) and udata.get("last_claim", 0) > 0)
    total_users_count = len([uid for uid, udata in DATA.items() if isinstance(udata, dict)])
    current_reward = ECONOMY_SETTINGS.get("claim_reward", 500_000_000_000)

    if amount_text is None:
        embed = discord.Embed(
            title="⚙️ Daily Claim Settings & Stats",
            color=discord.Color.blurple()
        )
        embed.add_field(
            name="💵 Claim Reward Amount",
            value=f"**{format_coins(current_reward)}** uwuncy",
            inline=False
        )
        embed.add_field(
            name="📊 Claim Usage Statistics",
            value=f"↳ **Users who have claimed**: `{claimed_users_count:,}` of `{total_users_count:,}` users",
            inline=False
        )
        embed.set_footer(text="To update amount, use: uwu setclaim <amount>")
        return await ctx.send(embed=embed)

    new_amount = parse_coins(amount_text)
    if new_amount is None or new_amount < 0:
        return await ctx.send("❌ Invalid amount. Example: `uwu setclaim 500000000000` or `500b`.")

    ECONOMY_SETTINGS["claim_reward"] = new_amount
    save_economy_settings()

    await ctx.send(
        f"✅ **Daily claim reward updated!**\n"
        f"Users will now receive **{format_coins(new_amount)}** uwuncy when they type `uwu claim`.\n"
        f"📊 **Claimed users so far**: `{claimed_users_count:,}` / `{total_users_count:,}`"
    )

# ==============================================
# 📊 ALL OTHER COMMANDS
# ==============================================
@bot.command(name="money", aliases=["bal", "balance"])
async def money(ctx):
    user = get_user(ctx.author.id)
    crypto_line = ""
    if not user["crypto_private"]:
        _crypto_rows, _crypto_invested, crypto_value, _crypto_profit = crypto_portfolio(user)
        crypto_line = f"\n**{format_crypto_price(crypto_value)} Crypto held value**"

    marriage_line = ""
    partner_id = user.get("marriage_partner_id")
    if partner_id:
        partner_user = get_user(partner_id)
        partner_wallet = partner_user.get("wallet", 0)
        partner_bank = partner_user.get("bank", 0)
        shared_total = user["wallet"] + user["bank"] + partner_wallet + partner_bank
        try:
            partner_member = await bot.fetch_user(int(partner_id))
            partner_name = partner_member.display_name
        except Exception:
            partner_name = f"Partner ({partner_id})"
        marriage_line = (
            f"\n💍 **Married to {partner_name}** | Partner Wallet: `{format_coins(partner_wallet)}` | "
            f"**Shared Household Total:** `{format_coins(shared_total)} uwuncy`"
        )

    await ctx.send(
        f"🍁 **{ctx.author.display_name}**, you currently have "
        f"**{format_coins(user['wallet'])} uwuncy** in wallet (`{format_coins(user['bank'])}` in bank)!\n"
        f"{crypto_line}{marriage_line}"
    )


async def set_crypto_privacy(ctx, private):
    user = get_user(ctx.author.id)
    user["crypto_private"] = private
    save_data(DATA)
    if private:
        await ctx.send(
            "🔒 Crypto details are now private. "
            "`uwu bal` and `uwu info` will only show your wallet."
        )
    else:
        await ctx.send(
            "🔓 Crypto details are now visible. "
            "`uwu bal` and `uwu info` will show your crypto information."
        )


@bot.command(name="history", aliases=["bets", "recent"])
async def history(ctx):
    user = get_user(ctx.author.id)
    if not user["history"]:
        return await ctx.send("No activity history yet.")
    lines = []
    for entry in user["history"][:10]:
        result = entry.get("result", "event").upper()
        amount = format_coins(entry.get("amount", 0))
        bet = entry.get("bet", 0)
        bet_label = f" • bet {format_coins(bet)}" if bet else ""
        lines.append(
            f"- **{entry.get('type', 'activity')}** — {result}"
            f"{bet_label} — `{amount}` uwuncy"
        )
    await ctx.send("**Recent activity**\n" + "\n".join(lines))

@bot.command(name="achievements", aliases=["ach", "badges"])
async def achievements(ctx):
    user = get_user(ctx.author.id)
    lines = []
    for key, (name, description, reward) in ACHIEVEMENT_DEFINITIONS.items():
        status = "✅" if key in user["achievements"] else "🔒"
        lines.append(f"{status} **{name}** — {description} (+{format_coins(reward)} uwuncy)")
    await ctx.send(
        f"**Achievements** ({len(user['achievements'])}/{len(ACHIEVEMENT_DEFINITIONS)})\n"
        + "\n".join(lines)
    )

@bot.command(name="quests", aliases=["quest", "missions"])
async def quests(ctx):
    user = get_user(ctx.author.id)
    ensure_daily_quests(user)
    save_data(DATA)
    lines = [
        f"{'✅' if q['claimed'] else '⬜'} {q['description']}: "
        f"`{q['progress']}/{q['target']}` — reward `{format_coins(q['reward'])}` uwuncy"
        for q in user["quests"]
    ]
    await ctx.send("**Daily quests**\n" + "\n".join(lines))

@bot.command(name="jackpot")
async def jackpot(ctx):
    await ctx.send(
        f"🎰 **Global Jackpot:** `{format_coins(ECONOMY_SETTINGS['jackpot'])}` uwuncy\n"
        "Every game bet contributes 1%. A diamond slot jackpot claims it."
    )

@bot.command(name="hunt")
async def hunt(ctx):
    user = get_user(ctx.author.id)
    now = time.time()
    if now - user["last_hunt"] < 10:
        return await ctx.send("Please wait 10 seconds before hunting again.")
    animals = ["🐱 Cat", "🐶 Dog", "🦊 Fox", "🐇 Rabbit", "🐺 Wolf", "🦅 Eagle", "🐉 Dragon", "🦁 Lion", "🐻 Bear"]
    boosted = consume_item(user, "huntboost")
    details = hunt_reward(user["hunt_level"], boosted)
    earn = details["reward"]
    hunt_msg = await ctx.send("**Hunt**\nTracking a target...")
    for frame in ["Searching.", "Searching..", "Searching..."]:
        await hunt_msg.edit(content=f"**Hunt**\n{frame}")
        await asyncio.sleep(0.2)
    credit_wallet(user, earn)
    user["last_hunt"] = now
    previous_level = user["hunt_level"]
    advance_hunt(user)
    update_quest_progress(user, "hunt")
    award_xp(user, 15)
    add_history(user, {
        "type": "hunt",
        "result": "reward",
        "bet": 0,
        "amount": earn,
    })
    save_data(DATA)
    boost_note = " (Hunt Boost used)" if boosted else ""
    level_note = (
        f"\nHunt level: **{previous_level:,} → {user['hunt_level']:,}**"
        if user["hunt_level"] != previous_level
        else "\nHunt level: **100,000 (MAX)**"
    )
    await hunt_msg.edit(content=(
        f"**Hunt — Result**\n"
        f"Caught a **{random.choice(animals)}**.\n"
        f"Stage: **{details['stage_name']}** (`{details['multiplier']:.2f}x`)\n"
        f"Earned: **+{format_coins(earn)} uwuncy**{boost_note}{level_note}"
    ))

@bot.command(name="huntinfo", aliases=["huntlevel", "huntstats"])
async def huntinfo(ctx):
    user = get_user(ctx.author.id)
    stage_level, stage_name, multiplier = get_hunt_stage(user["hunt_level"])
    next_stage = next(
        (stage for stage in HUNT_STAGES if stage[0] > user["hunt_level"]),
        None,
    )
    progress = (
        f"Next stage: **{next_stage[1]}** at level **{next_stage[0]:,}**"
        if next_stage else "You have reached the final Hunt stage."
    )
    await ctx.send(
        f"**Hunt Progress**\n"
        f"Level: **{user['hunt_level']:,}/{HUNT_MAX_LEVEL:,}**\n"
        f"Stage: **{stage_name}** (unlocked at {stage_level:,})\n"
        f"Reward multiplier: **{multiplier:.2f}x**\n"
        f"Successful hunts: **{user['hunt_total']:,}**\n"
        f"{progress}"
    )

@bot.command(name="cf", aliases=["coinflip"])
async def cf(ctx, first: str, second: str):
    """Flip a coin with `uwu cf h <bet>` or `uwu cf t <bet>`."""
    user = get_user(ctx.author.id)
    valid_sides = {"h", "t", "heads", "tails"}
    if first.lower() in valid_sides:
        side = first.lower()
        bet_text = second
    elif second.lower() in valid_sides:
        # Keep the previous order working during the command transition.
        side = second.lower()
        bet_text = first
    else:
        return await ctx.send(
            "Use: `uwu cf h <bet>` or `uwu cf t <bet>` "
            "(example: `uwu cf h 20,000`)."
        )
    bet = parse_coins(bet_text, user.get("wallet", 0))
    if bet is None or bet <= 0:
        return await ctx.send(
            "❌ The bet must be a valid amount. Examples: `uwu cf h 1k`, `uwu cf h 1m`, `uwu cf h 1b`, `uwu cf h 1t`, `uwu cf h 1q`, `uwu cf h all`."
        )
    validation_error = validate_bet(user, bet, "coinflip")
    if validation_error:
        return await ctx.send(
            validation_error
        )

    begin_game(user, "coinflip", bet)
    protection_notice = shield_notice(user, bet)
    selected_side = "heads" if side in ["h", "heads"] else "tails"
    losing_side = "tails" if selected_side == "heads" else "heads"
    result = (
        selected_side
        if chance_roll("coinflip", user_id=ctx.author.id)
        else losing_side
    )
    win = (side in ["h","heads"] and result == "heads") or (side in ["t","tails"] and result == "tails")

    if win:
        total_payout, bonus, boosted = settle_win(user, int(bet * WIN_PROFIT))
        finish_game(user, "coinflip", bet, True, total_payout)
        msg = (
            f"**Coin flip result**\nThe coin landed on **{result.title()}**.\n"
            f"Outcome: **WIN**\n"
            f"Profit: **+{format_coins(total_payout)} uwuncy**"
            + (
                f" (includes Lucky Potion bonus of +{format_coins(bonus)} uwuncy)"
                if boosted else ""
            )
            + "\n"
            f"Wallet: `{format_coins(user['wallet'])}` uwuncy"
        )
    else:
        loss_result = settle_loss(user, bet)
        finish_game(user, "coinflip", bet, False, loss_result["remaining_loss"])
        msg = (
            f"**Coin flip result**\nThe coin landed on **{result.title()}**.\n"
            f"{describe_loss(loss_result, bet)}\n"
            f"Wallet: `{format_coins(user['wallet'])}` uwuncy"
        )

    if protection_notice:
        msg += f"\n{protection_notice}"
    save_data(DATA)
    await send_with_double_or_nothing(
        ctx, msg, "coinflip", total_payout if win else 0
    )

@bot.command(name="deposit", aliases=["dep"])
async def deposit(ctx, amount: int):
    user = get_user(ctx.author.id)
    apply_bank_interest(user)
    if amount <= 0 or not debit_wallet(user, amount):
        return await ctx.send("❌ Not enough uwuncy!")
    user["bank"] += amount
    save_data(DATA)
    await ctx.send(f"Deposited **{format_coins(amount)} uwuncy**.")

async def complete_crypto_withdrawal(ctx, crypto, amount_text="all"):
    symbol = resolve_crypto(crypto)
    if symbol is None:
        return await ctx.send(
            "Choose a crypto and use: "
            "`uwu withdraw crypto <crypto> <amount>` or `all`."
        )

    user = get_user(ctx.author.id)
    result = crypto_position_value(user, symbol)
    if result is None:
        return await ctx.send(
            f"You do not have a {CRYPTO_DISPLAY_NAMES[symbol]} position."
        )
    position, invested, units, current_value = result
    if str(amount_text).casefold() == "all":
        withdrawal_value = current_value
        remaining_fraction = 0.0
    else:
        withdrawal_value = parse_coins(amount_text)
        if withdrawal_value is None or withdrawal_value <= 0:
            return await ctx.send(
                "Withdrawal amount must be greater than zero. "
                "Use `uwu withdraw crypto <crypto> <amount>` or `all`."
            )
        if withdrawal_value > current_value:
            return await ctx.send(
                f"That position is currently worth **{current_value:,.2f} uwuncy**."
            )
        remaining_fraction = max(0.0, 1.0 - (withdrawal_value / current_value))

    credit_wallet(user, int(withdrawal_value))
    if remaining_fraction <= 0.000000001:
        del user["crypto_positions"][symbol]
    else:
        position["units"] = round(units * remaining_fraction, 10)
        position["invested"] = round(invested * remaining_fraction, 4)
        position["held_principal"] = round(
            float(position.get("held_principal", invested)) * remaining_fraction,
            4,
        )
    save_data(DATA)
    remaining_value = max(0.0, current_value - withdrawal_value)
    withdrawal_label = (
        "the full position"
        if remaining_fraction <= 0.000000001
        else f"{format_coins(withdrawal_value)} uwuncy of the position"
    )
    await ctx.send(
        f"✅ Withdrew **{withdrawal_label}** from "
        f"**{CRYPTO_DISPLAY_NAMES[symbol]}** for **{withdrawal_value:,.2f} uwuncy**.\n"
        f"Position profit/loss before withdrawal: **{current_value - invested:+,.2f} uwuncy**\n"
        f"Remaining crypto value: `{remaining_value:,.2f}` uwuncy\n"
        f"Spendable wallet: `{format_coins(user['wallet'])}` uwuncy."
    )

@bot.command(name="withdraw", aliases=["with"])
async def withdraw(ctx, *args):
    if args and str(args[0]).casefold() == "crypto":
        if len(args) != 3:
            return await ctx.send(
                "Use `uwu withdraw crypto <crypto> <amount>` or `all`."
            )
        return await complete_crypto_withdrawal(ctx, args[1], args[2])
    if len(args) != 1:
        return await ctx.send(
            "Use `uwu withdraw <amount>` for bank uwuncy, or "
            "`uwu withdraw crypto <crypto> <amount>`."
        )
    try:
        amount = parse_coins(args[0])
    except (TypeError, ValueError):
        amount = None
    user = get_user(ctx.author.id)
    apply_bank_interest(user)
    if amount is None or amount <= 0 or user["bank"] < amount:
        return await ctx.send("❌ Not enough uwuncy!")
    user["bank"] -= amount
    credit_wallet(user, amount)
    save_data(DATA)
    await ctx.send(f"Withdrew **{format_coins(amount)} uwuncy**.")

@bot.command(name="withdrawcrypto", aliases=["cryptowithdraw"])
async def withdraw_crypto(ctx, crypto: str = None, amount_text: str = "all"):
    await complete_crypto_withdrawal(ctx, crypto, amount_text)

@bot.command(name="give", aliases=["pay"])
async def give(ctx, *, args: str):
    # --- PART 1: DETECT ROLE MENTION ---
    role = None
    if ctx.message.role_mentions:
        role = ctx.message.role_mentions[0]
        args = args.replace(f"{role.mention}", "").strip()

    # --- PART 2: ROLE MODE ---
    if role:
        # Get amount & check split
        split_mode = "split" in args.lower()
        clean_args = args.lower().replace("split", "").strip()
        try:
            amount = int(clean_args.replace(",", ""))
        except ValueError:
            return await ctx.send("❌ Enter valid number! Example: `uwu give role @VIP 1000` or `uwu give role @VIP split 5000`")

        # Get members: WITH ROLE, NOT BOT, NOT YOU
        members = [m for m in ctx.guild.members if role in m.roles and not m.bot and m != ctx.author]
        if not members:
            return await ctx.send("❌ No valid members found in that role!")

        # Calculate
        if split_mode:
            each_get = amount // len(members)
            total_pay = amount
            mode_text = f"(split equally: each gets {each_get:,})"
        else:
            each_get = amount
            total_pay = each_get * len(members)
            mode_text = f"(each gets full {each_get:,})"

        # Check sender balance
        sender = get_user(ctx.author.id)
        if sender["wallet"] < total_pay:
            return await ctx.send(f"❌ You need **{total_pay:,} uwuncy**! You only have {sender['wallet']:,}")

        # Deduct & distribute
        sender["wallet"] -= total_pay
        for user in members:
            receiver = get_user(user.id)
            receiver["wallet"] += each_get

        save_data(DATA)
        return await ctx.send(f"✅ Gave **{role.name}** {len(members)} members {mode_text}\n💸 Total paid from you: **{total_pay:,} uwuncy**")

    # --- PART 3: ORIGINAL DIRECT USER GIVE (KEEP YOUR OLD WORKING!) ---
    else:
        parts = args.split()
        if len(parts) < 2:
            return await ctx.send("❌ Use: `uwu give @user amount` or `uwu give role @Role amount / split amount`")
        try:
            member = await commands.MemberConverter().convert(ctx, parts[0])
            amount = int(parts[1].replace(",", ""))
        except:
            return await ctx.send("❌ Invalid format! Example: `uwu give @Mark 50000`")

        if amount <= 0 or member == ctx.author:
            return await ctx.send("❌ Invalid amount or cannot send to yourself!")

        sender = get_user(ctx.author.id)
        receiver = get_user(member.id)

        if sender["wallet"] < amount:
            return await ctx.send("❌ Not enough uwuncy!")

        if not transfer_wallet(sender, receiver, amount):
            return await ctx.send("❌ Transfer could not be completed.")

        save_data(DATA)
        await ctx.send(f"✅ Sent **{format_coins(amount)} uwuncy** to {member.mention}.")

@bot.command(name="slot", aliases=["slots"])
async def slot(ctx, bet_text: str = None):
    user = get_user(ctx.author.id)
    bet = parse_coins(bet_text, user.get("wallet", 0))
    if bet is None or bet <= 0:
        return await ctx.send("❌ Usage: `uwu slots <bet>` (e.g., `uwu slots 1k`, `uwu slots 50m`, `uwu slots 1b`, `uwu slots 1t`, `uwu slots 1q`, `uwu slots all`).")
    validation_error = validate_bet(user, bet, "slots")
    if validation_error:
        return await ctx.send(f"❌ {validation_error}")
    begin_game(user, "slots", bet)

    protection_notice = shield_notice(user, bet)
    if chance_roll("slots", user_id=ctx.author.id):
        winning_symbol, win_return = draw_slot_symbol()
        final = [winning_symbol] * 3
    else:
        win_return = 0.0
        final = random.sample(SLOT_SYMBOLS, 3)
    res = f"🎰 **RESULT** 🎰\n| {final[0]} | {final[1]} | {final[2]} |\n"

    if win_return:
        # The stake is never debited on a win, so only the profit is credited.
        total_payout, bonus, boosted = settle_win(
            user, int(bet * (win_return - 1.0))
        )
        jackpot_amount = jackpot_payout(user, "slots", bet) if final[0] == "💎" else 0
        finish_game(user, "slots", bet, True, total_payout + jackpot_amount)
        res += (
            f"**Three {final[0]}** at `{win_return:g}x`: "
            f"+{format_coins(total_payout)} uwuncy"
        )
        if jackpot_amount:
            res += f"\n🎰 Global jackpot claimed: **+{format_coins(jackpot_amount)} uwuncy**"
        if boosted:
            res += f" (includes Lucky Potion bonus of +{format_coins(bonus)} uwuncy)"
    else:
        total_payout = 0
        loss_result = settle_loss(user, bet)
        finish_game(user, "slots", bet, False, loss_result["remaining_loss"])
        res += describe_loss(loss_result, bet, "No match")

    if protection_notice:
        res += f"\n{protection_notice}"
    save_data(DATA)
    await send_with_double_or_nothing(ctx, res, "slots", total_payout)

@bot.command(name="leaderboard", aliases=["lb", "top"])
async def leaderboard(ctx, category: str = None):
    if category and category.casefold() in {"crypto", "crypwuncy", "investments"}:
        return await send_crypto_leaderboard(ctx)
    data = load_data()
    if not data:
        return await ctx.send("❌ No data yet!")

    users = sorted(
        [
            (uid, normalize_user(record)["wallet"] + normalize_user(record)["bank"])
            for uid, record in data.items()
            if isinstance(record, dict)
        ],
        key=lambda item: (-item[1], item[0]),
    )[:10]
    if not users:
        return await ctx.send("❌ No players on the leaderboard yet!")

    embed = discord.Embed(
        title="🏆 GLOBAL LEADERBOARD",
        description=(
            "The Top 10 titles are assigned live from total wallet + bank balance.\n"
            "Ranks update automatically whenever someone moves up or down."
        ),
        color=discord.Color.gold(),
    )
    medals = ["🥇", "🥈", "🥉"] + [f"**{rank}.**" for rank in range(4, 11)]
    for index, (uid, total) in enumerate(users):
        rank = index + 1
        try:
            profile = await bot.fetch_user(int(uid))
            name = profile.display_name
        except (discord.HTTPException, ValueError, TypeError):
            name = f"User {uid}"
        title = f"Top {rank} Global"
        embed.add_field(
            name=f"{medals[index]} {name}",
            value=f"`{format_coins(total)}` uwuncy  •  **{title}**",
            inline=False,
        )
    embed.set_footer(text="Only the current Top 10 receive global titles.")
    await ctx.send(embed=embed)

async def send_crypto_leaderboard(ctx):
    """Show the Top 10 users by current crypto profit."""
    rows = []
    data = load_data()
    for uid, record in data.items():
        if not isinstance(record, dict):
            continue
        user = normalize_user(record)
        positions, invested, value, profit = crypto_portfolio(user)
        if invested > 0:
            rows.append((str(uid), profit, invested, value))
    rows.sort(key=lambda item: (-item[1], item[0]))
    rows = rows[:10]
    if not rows:
        return await ctx.send(
            "📊 No crypto investments yet. Start with "
            "`uwu invest memwuncy 1,000,000`."
        )

    embed = discord.Embed(
        title="🏆 TOP CRYPTO — Highest Profit",
        description="Top 10 investors ranked by current unrealized crypto profit.",
        color=discord.Color.purple(),
    )
    medals = ["🥇", "🥈", "🥉"] + [f"**{rank}.**" for rank in range(4, 11)]
    for index, (uid, profit, invested, value) in enumerate(rows):
        try:
            profile = await bot.fetch_user(int(uid))
            name = profile.display_name
        except (discord.HTTPException, ValueError, TypeError):
            name = f"User {uid}"
        embed.add_field(
            name=f"{medals[index]} {name}",
            value=(
                f"Profit: **{profit:+,.2f} uwuncy**\n"
                f"Portfolio: `{value:,.2f}` • Invested: `{invested:,.2f}`"
            ),
            inline=False,
        )
    embed.set_footer(text="Use uwu top crypto • Profit changes with the live market.")
    await ctx.send(embed=embed)

@bot.command(name="crypwuncy", aliases=["crypto", "cryptos", "market"])
async def crypwuncy(ctx):
    """Display the live crypto market with animated graph updates."""
    message = await ctx.send(embed=crypto_market_embed())
    # Edit one message instead of sending spam while the graph animates.
    for _ in range(6):
        await asyncio.sleep(5)
        update_crypto_market()
        await message.edit(embed=crypto_market_embed())

@bot.command(name="invest")
async def invest(ctx, crypto: str = None, amount_text: str = None):
    """Hold wallet uwuncy in a crypto position at the current market price."""
    symbol = resolve_crypto(crypto)
    amount = parse_coins(amount_text)
    if symbol is None:
        choices = ", ".join(CRYPTO_SYMBOLS)
        return await ctx.send(
            f"Choose a crypto: `{choices}`\n"
            "Example: `uwu invest memwuncy 1,000,000`"
        )
    if amount is None or amount <= 0:
        return await ctx.send(
            "Investment amount must be greater than zero. "
            "Example: `uwu invest memwuncy 1,000,000`"
        )

    user = get_user(ctx.author.id)
    if user["wallet"] < amount:
        return await ctx.send(
            f"❌ You need `{format_coins(amount)}` available uwuncy to invest. "
            f"Spendable wallet: `{format_coins(user['wallet'])}` uwuncy."
        )
    debit_wallet(user, amount)
    positions = user.setdefault("crypto_positions", {})
    position = positions.setdefault(
        symbol,
        {"invested": 0.0, "held_principal": 0.0, "units": 0.0},
    )
    price = crypto_price(symbol)
    position["invested"] = round(float(position.get("invested", 0)) + amount, 4)
    position["held_principal"] = round(
        float(position.get("held_principal", 0)) + amount,
        4,
    )
    position["units"] = round(float(position.get("units", 0)) + amount / price, 10)
    save_data(DATA)

    await ctx.send(
        f"✅ **Investment recorded!**\n"
        f"**{format_coins(amount)} uwuncy** is now held in "
        f"**{CRYPTO_DISPLAY_NAMES[symbol]}** at **{format_crypto_price(price)}** per unit.\n"
        f"Spendable wallet: `{format_coins(user['wallet'])}` uwuncy.\n"
        f"Use `uwu investments` to track the live value."
    )

@bot.command(name="sell", aliases=["cashout", "sellcrypto"])
async def sell_crypto(ctx, crypto: str = None, amount_text: str = "all"):
    """Sell a held crypto position at its current market value."""
    symbol = resolve_crypto(crypto)
    if symbol is None:
        return await ctx.send(
            "Choose a crypto and use `all`, for example: "
            "`uwu sell memwuncy all`."
        )
    if str(amount_text).casefold() != "all":
        return await ctx.send(
            "For safety, crypto positions currently sell as a whole position: "
            "`uwu sell <crypto> all`."
        )

    user = get_user(ctx.author.id)
    result = crypto_position_value(user, symbol)
    if result is None:
        return await ctx.send(
            f"You do not have a {CRYPTO_DISPLAY_NAMES[symbol]} position."
        )
    position, invested, units, current_value = result
    credit_wallet(user, int(current_value))
    del user["crypto_positions"][symbol]
    save_data(DATA)
    await ctx.send(
        f"✅ Sold **{CRYPTO_DISPLAY_NAMES[symbol]}** for "
        f"**{current_value:,.2f} uwuncy**.\n"
        f"Original held amount: `{invested:,.2f}` uwuncy • "
        f"Profit/loss: **{current_value - invested:+,.2f} uwuncy**\n"
        f"Spendable wallet: `{format_coins(user['wallet'])}` uwuncy."
    )

@bot.command(name="investments", aliases=["portfolio", "invested"])
async def investments(ctx):
    user = get_user(ctx.author.id)
    rows, total_invested, total_value, total_profit = crypto_portfolio(user)
    if not rows:
        return await ctx.send(
            "📊 You have no crypto investments yet. "
            "Try `uwu invest memwuncy 1,000,000`."
        )
    lines = []
    for row in rows:
        lines.append(
            f"**{CRYPTO_DISPLAY_NAMES[row['symbol']]}** — "
            f"Value `{row['value']:,.2f}` • "
            f"Profit **{row['profit']:+,.2f} uwuncy**"
        )
    await ctx.send(
        f"📊 **{ctx.author.display_name}'s Crypto Portfolio**\n"
        + "\n".join(lines)
        + f"\n\nInvested: `{total_invested:,.2f}` uwuncy"
        f" • Current value: `{total_value:,.2f}` uwuncy"
        f" • Total profit: **{total_profit:+,.2f} uwuncy**"
    )

@bot.command(name="shop", aliases=["store"])
async def shop_cmd(ctx):
    p = get_prefix()
    msg = "**Item Shop**\n"
    for k, v in SHOP.items():
        msg += f"`{k}` — {v['name']} — {format_coins(v['price'])} uwuncy\n{v['desc']}\n"
    msg += f"\nPurchase with: `{p}buy <item> [quantity]`"
    await ctx.send(msg)

@bot.command(name="buy")
async def buy(ctx, item=None, quantity_text="1"):
    user = get_user(ctx.author.id)
    item = item.lower() if item else None
    if not item or item not in SHOP:
        return await ctx.send(
            "Invalid item. Use `uwu shop` to see the available items."
        )
    try:
        quantity = int(str(quantity_text).replace(",", ""))
    except (TypeError, ValueError):
        return await ctx.send("Quantity must be a positive whole number.")
    if quantity < 1:
        return await ctx.send("Quantity must be at least 1.")

    result = purchase_shop_item(user, item, quantity)
    if not result["ok"]:
        return await ctx.send(
            f"Not enough uwuncy for {quantity} × **{result['item']['name']}**. "
            f"Total cost: `{format_coins(result['total_cost'])}` uwuncy. "
            f"Wallet: `{format_coins(user['wallet'])}` uwuncy."
        )

    save_data(DATA)
    if item == "bag":
        await ctx.send(
            f"Purchased **{quantity} × {result['item']['name']}** for "
            f"`{format_coins(result['total_cost'])}` uwuncy.\n"
            f"Reward: **+{format_coins(result['reward'])} uwuncy** "
            f"(1,000–5,000 each)\n"
            f"Wallet: `{format_coins(user['wallet'])}` uwuncy"
        )
    else:
        await ctx.send(
            f"Purchased **{quantity} × {result['item']['name']}** for "
            f"`{format_coins(result['total_cost'])}` uwuncy.\n"
            f"Granted uses: **{result['granted_uses']}**\n"
            f"Wallet: `{format_coins(user['wallet'])}` uwuncy"
        )

@bot.command(name="inventory", aliases=["inv"])
async def inv(ctx):
    user = get_user(ctx.author.id)
    if not user["inventory"]:
        return await ctx.send("Your inventory is empty.")
    labels = {
        "huntboost": "Hunt Boost",
        "luckypot": "Lucky Potion",
        "shield": "Loss Shield",
    }
    lines = [
        f"- {labels.get(item, item)}: {count_item(user, item)}"
        for item in dict.fromkeys(user["inventory"])
    ]
    await ctx.send("**Inventory**\n" + "\n".join(lines))

@bot.command(name="bj", aliases=["blackjack"])
async def blackjack(ctx, bet_text: str = None):
    user = get_user(ctx.author.id)
    bet = parse_coins(bet_text, user.get("wallet", 0))
    if bet is None or bet <= 0:
        return await ctx.send("❌ Usage: `uwu bj <bet>` (e.g., `uwu bj 1k`, `uwu bj 50m`, `uwu bj 1b`, `uwu bj 1t`, `uwu bj 1q`, `uwu bj all`).")
    validation_error = validate_bet(user, bet, "blackjack")
    if validation_error:
        return await ctx.send(validation_error)
    begin_game(user, "blackjack", bet)

    def show(hand):
        return " ".join(f"`{card[0]}`" for card in hand)

    target_win = chance_roll("blackjack", user_id=ctx.author.id)
    player_initial, dealer_initial, player, dealer = build_blackjack_round(target_win)

    p, d = blackjack_score(player), blackjack_score(dealer)
    total_payout = 0
    if p == 21 and len(player) == 2 and not (d == 21 and len(dealer) == 2):
        total_payout, bonus, boosted = settle_win(
            user, int(bet * BLACKJACK_NATURAL_PROFIT)
        )
        finish_game(user, "blackjack", bet, True, total_payout)
        result = f"Blackjack. Profit: **+{format_coins(total_payout)} uwuncy**"
        if boosted:
            result += f" (includes Lucky Potion bonus of +{format_coins(bonus)} uwuncy)"
    elif p > 21:
        loss_result = settle_loss(user, bet)
        finish_game(user, "blackjack", bet, False, loss_result["remaining_loss"])
        result = describe_loss(loss_result, bet, "Bust")
    elif d > 21 or p > d:
        total_payout, bonus, boosted = settle_win(user, int(bet * WIN_PROFIT))
        finish_game(user, "blackjack", bet, True, total_payout)
        result = f"Win. Profit: **+{format_coins(total_payout)} uwuncy**"
        if boosted:
            result += f" (includes Lucky Potion bonus of +{format_coins(bonus)} uwuncy)"
    elif p == d:
        record_push(user, "blackjack", bet)
        result = "Push. Your bet was returned."
    else:
        loss_result = settle_loss(user, bet)
        finish_game(user, "blackjack", bet, False, loss_result["remaining_loss"])
        result = describe_loss(loss_result, bet)

    save_data(DATA)
    await send_with_double_or_nothing(
        ctx,
        f"**Blackjack — Final**\n"
        f"Your hand: {show(player)} → **{p}**\n"
        f"Dealer: {show(dealer)} → **{d}**\n"
        f"{result}\n"
        f"Wallet: `{format_coins(user['wallet'])}` uwuncy",
        "blackjack",
        total_payout,
    )

@bot.command(name="colorgame", aliases=["cg"])
async def colorgame(ctx, first: str = None, bet_text: str = None):
    if not first:
        return await ctx.send("❌ Usage: `uwu cg [color] <bet>` (e.g., `uwu cg red 1b`, `uwu cg 50m`).")
    user = get_user(ctx.author.id)
    requested_color = None
    if bet_text is None:
        bet = parse_coins(first, user.get("wallet", 0))
    else:
        requested_color = COLOR_SHORTCUTS.get(first.lower(), first.lower())
        bet = parse_coins(bet_text, user.get("wallet", 0))
        if requested_color not in COLOR_CHOICES:
            return await ctx.send(
                "Choose one color: `r` red, `b` blue, `g` green, or `y` yellow."
            )
    if bet is None or bet <= 0:
        return await ctx.send("❌ Invalid bet amount. Examples: `1k`, `50m`, `1b`, `1t`, `1q`, `all`.")
    validation_error = validate_bet(user, bet, "colorgame")
    if validation_error:
        return await ctx.send(validation_error)

    begin_game(user, "colorgame", bet, reserve_bet=True)
    save_data(DATA)
    game = {
        "player_name": ctx.author.display_name,
        "bet": bet,
        "selection": None,
        "slots": ["❔", "❔", "❔"],
        "target_win": chance_roll("colorgame", user_id=ctx.author.id),
        "shield_notice": shield_notice(user, bet),
    }
    view = ColorGameView(ctx.author.id, game)
    message = await ctx.send(
        embed=color_game_embed(
            game,
            "Choose a color within 10 seconds."
            if requested_color is None
            else "Your command selection is ready.",
            10 if requested_color is None else None,
        ),
        view=view,
    )
    view.message = message
    if requested_color is not None:
        await view.start_with_color(requested_color)

@bot.command(name="mines", aliases=["m"])
async def mines(ctx, bombs_input: str = None, bet_text: str = None):
    if not bombs_input or not bet_text:
        return await ctx.send("❌ Usage: `uwu mines <bombs 1-15> <bet>` (e.g., `uwu mines 3 1b`, `uwu mines 5 50m`).")
    try:
        bombs = int(bombs_input)
    except ValueError:
        return await ctx.send("❌ Bombs count must be a number between 1 and 15.")
    user = get_user(ctx.author.id)
    bet = parse_coins(bet_text, user.get("wallet", 0))
    if bombs < 1 or bombs > 15:
        return await ctx.send("Bombs must be between 1 and 15.")
    if bet is None or bet <= 0:
        return await ctx.send("❌ Invalid bet amount. Examples: `1k`, `50m`, `1b`, `1t`, `1q`, `all`.")
    validation_error = validate_bet(user, bet, "mines")
    if validation_error:
        return await ctx.send(validation_error)

    begin_game(user, "mines", bet, reserve_bet=True)
    save_data(DATA)
    game = {
        "player_name": ctx.author.display_name,
        "bet": bet,
        "bombs": bombs,
        "revealed": set(),
        "bomb_locations": set(random.sample(range(16), bombs)),
        "shield_notice": shield_notice(user, bet),
    }
    view = MinesView(ctx.author.id, game)
    message = await ctx.send(embed=mines_embed(game), view=view)
    view.message = message

@bot.command(name="dice", aliases=["roll"])
async def dice(ctx, *args):
    if not args:
        return await ctx.send("❌ Usage: `uwu dice <bet> <guess 1-6>` (e.g., `uwu dice 1b 6`, `uwu dice 50m 3`).")
    user = get_user(ctx.author.id)
    bet = None
    guess = None
    for arg in args:
        if arg.isdigit() and int(arg) in range(1, 7) and guess is None:
            guess = int(arg)
        else:
            parsed = parse_coins(arg, user.get("wallet", 0))
            if parsed is not None and bet is None:
                bet = parsed

    if bet is None or bet <= 0 or guess is None:
        return await ctx.send("❌ Usage: `uwu dice <bet> <guess 1-6>` (e.g., `uwu dice 1b 6`).")

    validation_error = validate_bet(user, bet, "dice")
    if validation_error:
        return await ctx.send(f"❌ {validation_error}")

    begin_game(user, "dice", bet)
    protection_notice = shield_notice(user, bet)
    if chance_roll("dice", user_id=ctx.author.id):
        num = guess
    else:
        num = random.choice([value for value in range(1, 7) if value != guess])
    if num == guess:
        total_payout, bonus, boosted = settle_win(user, int(bet * WIN_PROFIT))
        finish_game(user, "dice", bet, True, total_payout)
        res = f"Result: **{num}** — Win: **+{format_coins(total_payout)} uwuncy**"
        if boosted:
            res += f" (includes Lucky Potion bonus of +{format_coins(bonus)} uwuncy)"
    else:
        total_payout = 0
        loss_result = settle_loss(user, bet)
        finish_game(user, "dice", bet, False, loss_result["remaining_loss"])
        res = f"Result: **{num}** — {describe_loss(loss_result, bet, 'Loss')}"

    if protection_notice:
        res += f"\n{protection_notice}"
    save_data(DATA)
    await send_with_double_or_nothing(ctx, res, "dice", total_payout)

@bot.command(name="highlow", aliases=["hl"])
async def highlow(ctx, *args):
    if not args:
        return await ctx.send("❌ Usage: `uwu hl <bet> <high|low>` (e.g., `uwu hl 1b high`, `uwu hl 50m low`).")
    user = get_user(ctx.author.id)
    bet = None
    pick = None
    for arg in args:
        clean = arg.lower()
        if clean in ["high", "low"]:
            pick = clean
        else:
            parsed = parse_coins(arg, user.get("wallet", 0))
            if parsed is not None and bet is None:
                bet = parsed

    if bet is None or bet <= 0 or not pick:
        return await ctx.send("❌ Usage: `uwu hl <bet> <high|low>` (e.g., `uwu hl 1b high`, `uwu hl 50m low`).")

    validation_error = validate_bet(user, bet, "highlow")
    if validation_error:
        return await ctx.send(f"❌ {validation_error}")

    begin_game(user, "highlow", bet)
    protection_notice = shield_notice(user, bet)
    winning_numbers = (
        list(range(51, 101))
        if pick == "high"
        else list(range(1, 51))
    )
    losing_numbers = (
        list(range(1, 51))
        if pick == "high"
        else list(range(51, 101))
    )
    num = random.choice(
        winning_numbers
        if chance_roll("highlow", user_id=ctx.author.id)
        else losing_numbers
    )

    if (pick=="high" and num>50) or (pick=="low" and num<=50):
        total_payout, bonus, boosted = settle_win(user, int(bet * WIN_PROFIT))
        finish_game(user, "highlow", bet, True, total_payout)
        res = f"Number: **{num}** — Win: **+{format_coins(total_payout)} uwuncy**"
        if boosted:
            res += f" (includes Lucky Potion bonus of +{format_coins(bonus)} uwuncy)"
    else:
        total_payout = 0
        loss_result = settle_loss(user, bet)
        finish_game(user, "highlow", bet, False, loss_result["remaining_loss"])
        res = f"Number: **{num}** — {describe_loss(loss_result, bet, 'Loss')}"

    if protection_notice:
        res += f"\n{protection_notice}"
    save_data(DATA)
    await send_with_double_or_nothing(ctx, res, "highlow", total_payout)

@bot.command(name="rr", aliases=["roulette"])
async def rr(ctx, bet_text: str = None):
    user = get_user(ctx.author.id)
    bet = parse_coins(bet_text, user.get("wallet", 0))
    if bet is None or bet <= 0:
        return await ctx.send("❌ Usage: `uwu rr <bet>` (e.g., `uwu rr 1k`, `uwu rr 50m`, `uwu rr 1b`, `uwu rr 1t`, `uwu rr 1q`, `uwu rr all`).")
    validation_error = validate_bet(user, bet, "roulette")
    if validation_error:
        return await ctx.send(f"❌ {validation_error}")

    begin_game(user, "roulette", bet)
    protection_notice = shield_notice(user, bet)
    if chance_roll("roulette", user_id=ctx.author.id):
        total_payout, bonus, boosted = settle_win(user, int(bet * WIN_PROFIT))
        finish_game(user, "roulette", bet, True, total_payout)
        res = f"Click. You survived. Profit: **+{format_coins(total_payout)} uwuncy**"
        if boosted:
            res += f" (includes Lucky Potion bonus of +{format_coins(bonus)} uwuncy)"
    else:
        total_payout = 0
        loss_result = settle_loss(user, bet)
        finish_game(user, "roulette", bet, False, loss_result["remaining_loss"])
        res = describe_loss(loss_result, bet, "Bang. Loss")

    if protection_notice:
        res += f"\n{protection_notice}"
    save_data(DATA)
    await send_with_double_or_nothing(ctx, res, "roulette", total_payout)

# ==============================================
# 🚀 CASH-OUT & INSTANT GAMBLING GAMES
# ==============================================
# All five games below reserve the stake up front (like Mines), so a payout
# multiplier is always a *total* return: 2.00x on a 1,000 bet credits 2,000 and
# nets +1,000. Every multiplier table is priced off BASELINE_WIN_CHANCE, which
# is what keeps `uwu odds` and `uwu userodds` meaningful here.
def settle_cashout_win(user_id, game, bet, total_return):
    """Credit a reserved-stake win and report the payout breakdown."""
    user = get_user(user_id)
    total_payout, bonus, boosted = settle_win(user, int(bet * total_return))
    finish_game(user, game, bet, True, total_payout)
    save_data(DATA)
    return total_payout, bonus, boosted

def settle_cashout_loss(user_id, game, bet):
    """Resolve a reserved-stake bust, honouring the Loss Shield."""
    user = get_user(user_id)
    loss_result = settle_loss(user, bet, bet_reserved=True)
    finish_game(user, game, bet, False, loss_result["remaining_loss"])
    save_data(DATA)
    return loss_result

def payout_line(total_payout, bonus, boosted):
    line = f"Payout: **+{format_coins(total_payout)} uwuncy**"
    if boosted:
        line += (
            f" (includes Lucky Potion bonus of +{format_coins(bonus)} uwuncy)"
        )
    return line

def claim_round_jackpot(user_id, game, bet):
    """Award the global jackpot for a perfect run and describe it."""
    amount = jackpot_payout(get_user(user_id), game, bet)
    save_data(DATA)
    if not amount:
        return ""
    return f"\n🎰 Global jackpot claimed: **+{format_coins(amount)} uwuncy**"

def refund_reserved_bet(user_id, bet):
    """Return a reserved stake when a board expires unfinished."""
    credit_wallet(get_user(user_id), bet)
    save_data(DATA)

def resolve_gambling_bet(ctx, bet_text, game, usage):
    """Parse and validate a wager, returning the amount or an error message."""
    user = get_user(ctx.author.id)
    bet = parse_coins(bet_text, user.get("wallet", 0))
    if bet is None or bet <= 0:
        return None, f"❌ Invalid bet. Example: `{usage}` (supports 1k, 1m, 1b, 1t, 1q, all, half)."
    validation_error = validate_bet(user, bet, game)
    if validation_error:
        return None, f"❌ {validation_error}"
    return bet, None

# ---------- 🚀 CRASH ----------
CRASH_BASE_SURVIVAL = 0.85
CRASH_MAX_TICKS = 20
CRASH_TICK_SECONDS = 1.4
CRASH_GRAPH_WIDTH = 16
CRASH_GRAPH_HEIGHT = 7

def crash_return(tick):
    """Total return offered after `tick` surviving ticks."""
    return max(1.0, cashout_multiplier(CRASH_BASE_SURVIVAL, tick))

def crash_graph(tick, crashed=False):
    """A rocket trail climbing an exponential curve as the round survives."""
    reached = max(
        1,
        min(
            CRASH_GRAPH_WIDTH,
            int(tick / CRASH_MAX_TICKS * CRASH_GRAPH_WIDTH) + 1,
        ),
    )
    rows = []
    for row in range(CRASH_GRAPH_HEIGHT):
        line = []
        for col in range(CRASH_GRAPH_WIDTH):
            level = int(
                ((col / (CRASH_GRAPH_WIDTH - 1)) ** 1.8)
                * (CRASH_GRAPH_HEIGHT - 1)
            )
            if level != CRASH_GRAPH_HEIGHT - 1 - row or col >= reached:
                line.append(" ")
            elif col == reached - 1:
                line.append("X" if crashed else "/")
            else:
                line.append(".")
        rows.append("|" + "".join(line) + "|")
    rows.append("+" + "-" * CRASH_GRAPH_WIDTH + "+")
    return "```\n" + "\n".join(rows) + "\n```"

def crash_embed(game, status=None, color=None):
    multiplier = crash_return(game["tick"])
    embed = discord.Embed(
        title="🚀 CRASH",
        description=(
            crash_graph(game["tick"], crashed=game.get("crashed", False))
            + f"\n# {multiplier:.2f}x"
        ),
        color=color or discord.Color.orange(),
    )
    embed.add_field(name="Player", value=game["player_name"], inline=True)
    embed.add_field(
        name="Bet",
        value=f"`{format_coins(game['bet'])} uwuncy`",
        inline=True,
    )
    embed.add_field(
        name="Cash out now",
        value=f"`{format_coins(int(game['bet'] * multiplier))} uwuncy`",
        inline=True,
    )
    if game.get("auto_cashout"):
        embed.add_field(
            name="Auto cash out",
            value=f"`{game['auto_cashout']:.2f}x`",
            inline=True,
        )
    if game.get("shield_notice"):
        embed.add_field(
            name="Loss Shield", value=game["shield_notice"], inline=False
        )
    if status:
        embed.add_field(name="Status", value=status, inline=False)
    embed.set_footer(
        text=f"Tick {game['tick']}/{CRASH_MAX_TICKS} • "
        f"Max {crash_return(CRASH_MAX_TICKS):.2f}x"
    )
    return embed

class CrashView(discord.ui.View):
    """A live Crash round whose multiplier climbs until the player bails out."""

    def __init__(self, owner_id, game):
        super().__init__(timeout=None)
        self.owner_id = owner_id
        self.game = game
        self.message = None
        self.closed = False
        self.settled = False
        self.cashout_button = discord.ui.Button(
            label="💰 Cash Out",
            style=discord.ButtonStyle.success,
        )
        self.cashout_button.callback = self.cash_out
        self.add_item(self.cashout_button)

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "This is not your Crash round.", ephemeral=True
            )
            return False
        return True

    async def run(self):
        """Tick the multiplier until the round busts, tops out, or is banked."""
        while not self.closed and self.game["tick"] < CRASH_MAX_TICKS:
            await asyncio.sleep(CRASH_TICK_SECONDS)
            if self.closed:
                return
            if not survive_step("crash", CRASH_BASE_SURVIVAL, self.owner_id):
                return await self.bust()
            self.game["tick"] += 1
            target = self.game.get("auto_cashout")
            if target and crash_return(self.game["tick"]) >= target:
                return await self.pay_out(
                    f"🤖 Auto cashed out at {target:.2f}x"
                )
            if self.game["tick"] >= CRASH_MAX_TICKS:
                return await self.pay_out("🏁 Rode it to the top", jackpot=True)
            await self.refresh()

    async def refresh(self):
        if not self.message:
            return
        try:
            await self.message.edit(embed=crash_embed(self.game), view=self)
        except discord.HTTPException:
            pass

    async def render(self, status, color):
        if not self.message:
            return
        try:
            await self.message.edit(
                embed=crash_embed(self.game, status, color), view=self
            )
        except discord.HTTPException:
            pass

    async def bust(self):
        if self.settled:
            return
        self.settled = True
        self.closed = True
        self.game["crashed"] = True
        self.cashout_button.disabled = True
        loss_result = settle_cashout_loss(self.owner_id, "crash", self.game["bet"])
        await self.render(
            describe_loss(loss_result, self.game["bet"], "💥 Crashed"),
            discord.Color.red(),
        )
        self.stop()

    async def pay_out(self, label, jackpot=False):
        if self.settled:
            return
        self.settled = True
        self.closed = True
        self.cashout_button.disabled = True
        bet = self.game["bet"]
        multiplier = crash_return(self.game["tick"])
        total_payout, bonus, boosted = settle_cashout_win(
            self.owner_id, "crash", bet, multiplier
        )
        status = (
            f"{label} at **{multiplier:.2f}x**.\n"
            f"{payout_line(total_payout, bonus, boosted)}"
        )
        if jackpot:
            status += claim_round_jackpot(self.owner_id, "crash", bet)
        await self.render(status, discord.Color.green())
        self.stop()
        await offer_double_or_nothing(
            self.message, self.owner_id, "crash", total_payout
        )

    async def cash_out(self, interaction):
        if self.closed:
            return await interaction.response.send_message(
                "This Crash round is already finished.", ephemeral=True
            )
        if self.game["tick"] < 1:
            return await interaction.response.send_message(
                "Wait for the first tick before cashing out.", ephemeral=True
            )
        self.closed = True
        await interaction.response.defer()
        await self.pay_out("💰 Cashed out")

@bot.command(name="crash", aliases=["rocket"])
async def crash(ctx, bet_text: str = None, auto_cashout: str = None):
    """Ride a rising multiplier and cash out before the rocket crashes."""
    if bet_text is None:
        return await ctx.send(
            "Use `uwu crash <bet>` or `uwu crash <bet> <auto-cashout>` — "
            "example: `uwu crash 50,000 2.5`."
        )
    bet, error = resolve_gambling_bet(ctx, bet_text, "crash", "uwu crash 50,000")
    if error:
        return await ctx.send(error)

    target = None
    if auto_cashout is not None:
        try:
            target = float(str(auto_cashout).casefold().replace("x", ""))
        except ValueError:
            return await ctx.send(
                "❌ Auto cash out must be a multiplier, for example `2.5`."
            )
        if target <= 1.0:
            return await ctx.send("❌ Auto cash out must be above `1.00x`.")

    user = get_user(ctx.author.id)
    game = {
        "player_name": ctx.author.display_name,
        "bet": bet,
        "tick": 0,
        "auto_cashout": target,
        "shield_notice": shield_notice(user, bet),
    }
    begin_game(user, "crash", bet, reserve_bet=True)
    save_data(DATA)
    view = CrashView(ctx.author.id, game)
    view.message = await ctx.send(
        embed=crash_embed(game, "Lift off…"), view=view
    )
    await view.run()

# ---------- 🏯 TOWER ----------
TOWER_FLOORS = 8
TOWER_MODES = {
    "easy": {"label": "Easy", "doors": 4},
    "normal": {"label": "Normal", "doors": 3},
    "hard": {"label": "Hard", "doors": 2},
}
TOWER_MODE_ALIASES = {
    "easy": "easy",
    "e": "easy",
    "normal": "normal",
    "n": "normal",
    "medium": "normal",
    "mid": "normal",
    "hard": "hard",
    "h": "hard",
    "insane": "hard",
}

def tower_survival(mode):
    doors = TOWER_MODES[mode]["doors"]
    return (doors - 1) / doors

def tower_return(mode, floors_cleared):
    return cashout_multiplier(tower_survival(mode), floors_cleared)

def tower_embed(game, status=None, color=None):
    doors = TOWER_MODES[game["mode"]]["doors"]
    cleared = game["floor"]
    lines = []
    for floor in range(TOWER_FLOORS, 0, -1):
        marker = "▫️"
        row = " ".join("⬛" for _ in range(doors))
        if game.get("trap_floor") == floor:
            marker = "💥"
            row = " ".join(
                "💀" if index == game["trap_door"] else "⬜"
                for index in range(doors)
            )
        elif floor <= cleared:
            marker = "✅"
            row = " ".join(
                "🟩" if index == game["path"].get(floor) else "⬜"
                for index in range(doors)
            )
        elif floor == cleared + 1 and not game.get("over"):
            marker = "➡️"
            row = " ".join("🚪" for _ in range(doors))
        lines.append(f"{marker} `{tower_return(game['mode'], floor):7.2f}x` {row}")

    embed = discord.Embed(
        title="🏯 TOWER",
        description="\n".join(lines),
        color=color or discord.Color.blurple(),
    )
    embed.add_field(name="Player", value=game["player_name"], inline=True)
    embed.add_field(
        name="Bet", value=f"`{format_coins(game['bet'])} uwuncy`", inline=True
    )
    embed.add_field(
        name="Difficulty",
        value=f"{TOWER_MODES[game['mode']]['label']} • {doors} doors",
        inline=True,
    )
    banked = tower_return(game["mode"], cleared) if cleared else 0.0
    embed.add_field(
        name="Banked",
        value=(
            f"`{banked:.2f}x` ({format_coins(int(game['bet'] * banked))} uwuncy)"
            if cleared
            else "`—`"
        ),
        inline=True,
    )
    if cleared < TOWER_FLOORS and not game.get("over"):
        step = tower_return(game["mode"], cleared + 1)
        embed.add_field(
            name="Next floor",
            value=f"`{step:.2f}x` ({format_coins(int(game['bet'] * step))} uwuncy)",
            inline=True,
        )
    if game.get("shield_notice"):
        embed.add_field(
            name="Loss Shield", value=game["shield_notice"], inline=False
        )
    if status:
        embed.add_field(name="Status", value=status, inline=False)
    embed.set_footer(text="Pick a door to climb • Cash out whenever you like")
    return embed

class TowerView(discord.ui.View):
    """An eight-floor climb where one door on every floor ends the run."""

    def __init__(self, owner_id, game):
        super().__init__(timeout=180)
        self.owner_id = owner_id
        self.game = game
        self.message = None
        self.closed = False

        for index in range(TOWER_MODES[game["mode"]]["doors"]):
            button = discord.ui.Button(
                label=f"Door {index + 1}",
                style=discord.ButtonStyle.primary,
                row=0,
            )

            async def door_callback(interaction, door=index):
                await self.open_door(interaction, door)

            button.callback = door_callback
            self.add_item(button)

        self.cashout_button = discord.ui.Button(
            label="💰 Cash Out",
            style=discord.ButtonStyle.success,
            row=1,
            disabled=True,
        )
        self.cashout_button.callback = self.cash_out
        self.add_item(self.cashout_button)

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "This is not your Tower run.", ephemeral=True
            )
            return False
        if self.closed:
            await interaction.response.send_message(
                "This Tower run is already finished.", ephemeral=True
            )
            return False
        return True

    def disable_all(self):
        for child in self.children:
            child.disabled = True

    async def open_door(self, interaction, door):
        mode = self.game["mode"]
        if not survive_step("tower", tower_survival(mode), self.owner_id):
            self.closed = True
            self.game["over"] = True
            self.game["trap_floor"] = self.game["floor"] + 1
            self.game["trap_door"] = door
            self.disable_all()
            loss_result = settle_cashout_loss(
                self.owner_id, "tower", self.game["bet"]
            )
            await interaction.response.edit_message(
                embed=tower_embed(
                    self.game,
                    describe_loss(
                        loss_result,
                        self.game["bet"],
                        f"💀 Door {door + 1} was the trap",
                    ),
                    discord.Color.red(),
                ),
                view=self,
            )
            self.stop()
            return

        self.game["floor"] += 1
        self.game["path"][self.game["floor"]] = door
        self.cashout_button.disabled = False
        if self.game["floor"] >= TOWER_FLOORS:
            return await self.pay_out(interaction, "🏆 Tower cleared", jackpot=True)

        multiplier = tower_return(mode, self.game["floor"])
        await interaction.response.edit_message(
            embed=tower_embed(
                self.game,
                f"Safe. Floor {self.game['floor']} cleared — "
                f"**{multiplier:.2f}x** banked. Climb or cash out.",
            ),
            view=self,
        )

    async def pay_out(self, interaction, label, jackpot=False):
        self.closed = True
        self.game["over"] = True
        self.disable_all()
        bet = self.game["bet"]
        multiplier = tower_return(self.game["mode"], self.game["floor"])
        total_payout, bonus, boosted = settle_cashout_win(
            self.owner_id, "tower", bet, multiplier
        )
        status = (
            f"{label} at **{multiplier:.2f}x**.\n"
            f"{payout_line(total_payout, bonus, boosted)}"
        )
        if jackpot:
            status += claim_round_jackpot(self.owner_id, "tower", bet)
        await interaction.response.edit_message(
            embed=tower_embed(self.game, status, discord.Color.green()),
            view=self,
        )
        self.stop()
        await offer_double_or_nothing(
            self.message, self.owner_id, "tower", total_payout
        )

    async def cash_out(self, interaction):
        if self.game["floor"] < 1:
            return await interaction.response.send_message(
                "Clear at least one floor before cashing out.", ephemeral=True
            )
        await self.pay_out(interaction, "💰 Cashed out")

    async def on_timeout(self):
        if self.closed:
            return
        self.closed = True
        self.game["over"] = True
        self.disable_all()
        refund_reserved_bet(self.owner_id, self.game["bet"])
        if self.message:
            try:
                await self.message.edit(
                    embed=tower_embed(
                        self.game, "Run expired. Your bet was returned."
                    ),
                    view=self,
                )
            except discord.HTTPException:
                pass

@bot.command(name="tower", aliases=["climb"])
async def tower(ctx, bet_text: str = None, mode: str = "normal"):
    """Climb an eight-floor tower, dodging one trap door per floor."""
    if bet_text is None:
        return await ctx.send(
            "Use `uwu tower <bet> [easy|normal|hard]` — "
            "example: `uwu tower 50,000 hard`."
        )
    normalized_mode = TOWER_MODE_ALIASES.get(str(mode).casefold())
    if normalized_mode is None:
        return await ctx.send("❌ Difficulty must be `easy`, `normal`, or `hard`.")
    bet, error = resolve_gambling_bet(ctx, bet_text, "tower", "uwu tower 50,000")
    if error:
        return await ctx.send(error)

    user = get_user(ctx.author.id)
    game = {
        "player_name": ctx.author.display_name,
        "bet": bet,
        "mode": normalized_mode,
        "floor": 0,
        "path": {},
        "shield_notice": shield_notice(user, bet),
    }
    begin_game(user, "tower", bet, reserve_bet=True)
    save_data(DATA)
    view = TowerView(ctx.author.id, game)
    view.message = await ctx.send(
        embed=tower_embed(game, "Pick a door on floor 1."), view=view
    )

# ---------- 🎡 WHEEL ----------
WHEEL_SLOTS = 8
WHEEL_SPIN_STEPS = 11
WHEEL_TIERS = {
    "low": {
        "label": "Low risk",
        "table": balance_payout_table(
            ((1.5, 55), (2.5, 33), (4.0, 10), (10.0, 2))
        ),
    },
    "mid": {
        "label": "Mid risk",
        "table": balance_payout_table(
            ((1.0, 60), (2.0, 25), (5.0, 12), (18.0, 3))
        ),
    },
    "high": {
        "label": "High risk",
        "table": balance_payout_table(
            ((1.0, 78), (2.0, 15), (8.0, 5), (38.0, 2))
        ),
    },
}
WHEEL_TIER_ALIASES = {
    "low": "low",
    "l": "low",
    "safe": "low",
    "mid": "mid",
    "m": "mid",
    "medium": "mid",
    "normal": "mid",
    "high": "high",
    "h": "high",
    "risky": "high",
}

def wheel_layout(tier, prize):
    """Lay out the visible wheel so the pointer can land on a real result."""
    table = WHEEL_TIERS[tier]["table"]
    slots = [
        None if index % 2 == 0 else draw_payout(table)
        for index in range(WHEEL_SLOTS)
    ]
    candidates = [
        index
        for index in range(WHEEL_SLOTS)
        if (slots[index] is None) == (prize is None)
    ]
    target = random.choice(candidates)
    if prize is not None:
        slots[target] = prize
    return slots, target

def wheel_strip(slots, pointer):
    """Render the wheel with the pointer under the current segment."""
    labels = "".join(
        f"{('💀' if value is None else f'{value:g}x'):^7}" for value in slots
    )
    caret = "".join(
        ("▲" if index == pointer else " ").center(7)
        for index in range(len(slots))
    )
    return f"```\n{labels}\n{caret}\n```"

def wheel_embed(game, status=None, color=None):
    embed = discord.Embed(
        title="🎡 WHEEL",
        description=wheel_strip(game["slots"], game["pointer"]),
        color=color or discord.Color.gold(),
    )
    embed.add_field(name="Player", value=game["player_name"], inline=True)
    embed.add_field(
        name="Bet", value=f"`{format_coins(game['bet'])} uwuncy`", inline=True
    )
    embed.add_field(
        name="Risk", value=WHEEL_TIERS[game["tier"]]["label"], inline=True
    )
    top_prize = max(
        multiplier for multiplier, _ in WHEEL_TIERS[game["tier"]]["table"]
    )
    embed.add_field(name="Top prize", value=f"`{top_prize:g}x`", inline=True)
    if game.get("shield_notice"):
        embed.add_field(
            name="Loss Shield", value=game["shield_notice"], inline=False
        )
    if status:
        embed.add_field(name="Status", value=status, inline=False)
    embed.set_footer(text="Low, mid and high risk pay the same on average")
    return embed

@bot.command(name="wheel", aliases=["spin"])
async def wheel(ctx, bet_text: str = None, tier: str = "mid"):
    """Spin a segmented wheel for a multiplier, at the risk level you choose."""
    if bet_text is None:
        return await ctx.send(
            "Use `uwu wheel <bet> [low|mid|high]` — example: `uwu wheel 50,000 high`."
        )
    normalized_tier = WHEEL_TIER_ALIASES.get(str(tier).casefold())
    if normalized_tier is None:
        return await ctx.send("❌ Risk must be `low`, `mid`, or `high`.")
    bet, error = resolve_gambling_bet(ctx, bet_text, "wheel", "uwu wheel 50,000")
    if error:
        return await ctx.send(error)

    user = get_user(ctx.author.id)
    protection_notice = shield_notice(user, bet)
    won = chance_roll("wheel", user_id=ctx.author.id)
    prize = draw_payout(WHEEL_TIERS[normalized_tier]["table"]) if won else None
    slots, target = wheel_layout(normalized_tier, prize)
    game = {
        "player_name": ctx.author.display_name,
        "bet": bet,
        "tier": normalized_tier,
        "slots": slots,
        "pointer": 0,
        "shield_notice": protection_notice,
    }
    begin_game(user, "wheel", bet, reserve_bet=True)
    save_data(DATA)

    message = await ctx.send(embed=wheel_embed(game, "Spinning…"))
    # Decelerate into the winning segment so the landing reads as a real spin.
    total_steps = WHEEL_SPIN_STEPS + ((target - WHEEL_SPIN_STEPS) % WHEEL_SLOTS)
    for step in range(1, total_steps + 1):
        game["pointer"] = step % WHEEL_SLOTS
        await asyncio.sleep(0.28 + 0.9 * (step / total_steps) ** 3)
        try:
            await message.edit(embed=wheel_embed(game, "Spinning…"))
        except discord.HTTPException:
            break
    game["pointer"] = target

    if prize is None:
        loss_result = settle_cashout_loss(ctx.author.id, "wheel", bet)
        status = describe_loss(loss_result, bet, "💀 Landed on a bust segment")
        color = discord.Color.red()
        total_payout = 0
    else:
        total_payout, bonus, boosted = settle_cashout_win(
            ctx.author.id, "wheel", bet, prize
        )
        status = (
            f"🎯 Landed on **{prize:g}x**.\n"
            f"{payout_line(total_payout, bonus, boosted)}"
        )
        color = discord.Color.green()

    try:
        await message.edit(embed=wheel_embed(game, status, color))
    except discord.HTTPException:
        pass
    await offer_double_or_nothing(message, ctx.author.id, "wheel", total_payout)

# ---------- 🪜 LADDER ----------
LADDER_BASE_SURVIVAL = 0.55
LADDER_MAX_RUNGS = 10
CARD_FACES = {1: "A", 11: "J", 12: "Q", 13: "K"}
CARD_SUITS = ("♠", "♥", "♦", "♣")

def card_face(rank):
    return CARD_FACES.get(rank, str(rank))

def ladder_return(rungs):
    return cashout_multiplier(LADDER_BASE_SURVIVAL, rungs)

def ladder_next_card(current, guess, survived):
    """Draw the next card so the revealed rank matches the decided outcome."""
    if guess == "higher":
        winning = [rank for rank in range(1, 14) if rank > current]
        losing = [rank for rank in range(1, 14) if rank <= current]
    else:
        winning = [rank for rank in range(1, 14) if rank < current]
        losing = [rank for rank in range(1, 14) if rank >= current]
    pool = winning if survived else losing
    return random.choice(pool or losing or winning)

def ladder_embed(game, status=None, color=None):
    rungs = []
    for rung in range(LADDER_MAX_RUNGS, 0, -1):
        marker = "🟩" if rung <= game["rung"] else "⬜"
        rungs.append(f"{marker} `{ladder_return(rung):8.2f}x`")
    embed = discord.Embed(
        title="🪜 LADDER",
        description=(
            f"## {game['suit']} {card_face(game['card'])}\n"
            + "\n".join(rungs)
        ),
        color=color or discord.Color.teal(),
    )
    embed.add_field(name="Player", value=game["player_name"], inline=True)
    embed.add_field(
        name="Bet", value=f"`{format_coins(game['bet'])} uwuncy`", inline=True
    )
    embed.add_field(
        name="Rung", value=f"`{game['rung']}/{LADDER_MAX_RUNGS}`", inline=True
    )
    banked = ladder_return(game["rung"]) if game["rung"] else 0.0
    embed.add_field(
        name="Banked",
        value=(
            f"`{banked:.2f}x` ({format_coins(int(game['bet'] * banked))} uwuncy)"
            if game["rung"]
            else "`—`"
        ),
        inline=True,
    )
    if game["rung"] < LADDER_MAX_RUNGS and not game.get("over"):
        step = ladder_return(game["rung"] + 1)
        embed.add_field(
            name="Next rung",
            value=f"`{step:.2f}x` ({format_coins(int(game['bet'] * step))} uwuncy)",
            inline=True,
        )
    if game.get("shield_notice"):
        embed.add_field(
            name="Loss Shield", value=game["shield_notice"], inline=False
        )
    if status:
        embed.add_field(name="Status", value=status, inline=False)
    embed.set_footer(text="Higher or lower than the card shown • Aces are low")
    return embed

class LadderView(discord.ui.View):
    """A high/low chain where every correct call compounds the multiplier."""

    def __init__(self, owner_id, game):
        super().__init__(timeout=180)
        self.owner_id = owner_id
        self.game = game
        self.message = None
        self.closed = False

        self.higher_button = discord.ui.Button(
            label="⬆️ Higher", style=discord.ButtonStyle.primary, row=0
        )
        self.higher_button.callback = self.guess_higher
        self.add_item(self.higher_button)

        self.lower_button = discord.ui.Button(
            label="⬇️ Lower", style=discord.ButtonStyle.primary, row=0
        )
        self.lower_button.callback = self.guess_lower
        self.add_item(self.lower_button)

        self.cashout_button = discord.ui.Button(
            label="💰 Cash Out",
            style=discord.ButtonStyle.success,
            row=1,
            disabled=True,
        )
        self.cashout_button.callback = self.cash_out
        self.add_item(self.cashout_button)
        self.sync_buttons()

    def sync_buttons(self):
        """A 13 can never go higher and an ace can never go lower."""
        self.higher_button.disabled = self.game["card"] >= 13
        self.lower_button.disabled = self.game["card"] <= 1

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "This is not your Ladder run.", ephemeral=True
            )
            return False
        if self.closed:
            await interaction.response.send_message(
                "This Ladder run is already finished.", ephemeral=True
            )
            return False
        return True

    def disable_all(self):
        for child in self.children:
            child.disabled = True

    async def guess_higher(self, interaction):
        await self.guess(interaction, "higher")

    async def guess_lower(self, interaction):
        await self.guess(interaction, "lower")

    async def guess(self, interaction, direction):
        survived = survive_step("ladder", LADDER_BASE_SURVIVAL, self.owner_id)
        previous = self.game["card"]
        self.game["card"] = ladder_next_card(previous, direction, survived)
        self.game["suit"] = random.choice(CARD_SUITS)
        reveal = (
            f"{card_face(previous)} → **{self.game['suit']} "
            f"{card_face(self.game['card'])}**"
        )

        if not survived:
            self.closed = True
            self.game["over"] = True
            self.disable_all()
            loss_result = settle_cashout_loss(
                self.owner_id, "ladder", self.game["bet"]
            )
            await interaction.response.edit_message(
                embed=ladder_embed(
                    self.game,
                    describe_loss(
                        loss_result,
                        self.game["bet"],
                        f"❌ {reveal} — wrong call",
                    ),
                    discord.Color.red(),
                ),
                view=self,
            )
            self.stop()
            return

        self.game["rung"] += 1
        self.cashout_button.disabled = False
        if self.game["rung"] >= LADDER_MAX_RUNGS:
            return await self.pay_out(
                interaction, "🏆 Ladder cleared", jackpot=True
            )

        self.sync_buttons()
        await interaction.response.edit_message(
            embed=ladder_embed(
                self.game,
                f"✅ {reveal} — rung {self.game['rung']} banked at "
                f"**{ladder_return(self.game['rung']):.2f}x**.",
            ),
            view=self,
        )

    async def pay_out(self, interaction, label, jackpot=False):
        self.closed = True
        self.game["over"] = True
        self.disable_all()
        bet = self.game["bet"]
        multiplier = ladder_return(self.game["rung"])
        total_payout, bonus, boosted = settle_cashout_win(
            self.owner_id, "ladder", bet, multiplier
        )
        status = (
            f"{label} at **{multiplier:.2f}x**.\n"
            f"{payout_line(total_payout, bonus, boosted)}"
        )
        if jackpot:
            status += claim_round_jackpot(self.owner_id, "ladder", bet)
        await interaction.response.edit_message(
            embed=ladder_embed(self.game, status, discord.Color.green()),
            view=self,
        )
        self.stop()
        await offer_double_or_nothing(
            self.message, self.owner_id, "ladder", total_payout
        )

    async def cash_out(self, interaction):
        if self.game["rung"] < 1:
            return await interaction.response.send_message(
                "Win at least one rung before cashing out.", ephemeral=True
            )
        await self.pay_out(interaction, "💰 Cashed out")

    async def on_timeout(self):
        if self.closed:
            return
        self.closed = True
        self.game["over"] = True
        self.disable_all()
        refund_reserved_bet(self.owner_id, self.game["bet"])
        if self.message:
            try:
                await self.message.edit(
                    embed=ladder_embed(
                        self.game, "Run expired. Your bet was returned."
                    ),
                    view=self,
                )
            except discord.HTTPException:
                pass

@bot.command(name="ladder", aliases=["chain"])
async def ladder(ctx, bet_text: str = None):
    """Chain high/low calls for a compounding multiplier, cashing out any time."""
    if bet_text is None:
        return await ctx.send(
            "Use `uwu ladder <bet>` — example: `uwu ladder 50,000`."
        )
    bet, error = resolve_gambling_bet(ctx, bet_text, "ladder", "uwu ladder 50,000")
    if error:
        return await ctx.send(error)

    user = get_user(ctx.author.id)
    game = {
        "player_name": ctx.author.display_name,
        "bet": bet,
        "rung": 0,
        "card": random.randint(2, 12),
        "suit": random.choice(CARD_SUITS),
        "shield_notice": shield_notice(user, bet),
    }
    begin_game(user, "ladder", bet, reserve_bet=True)
    save_data(DATA)
    view = LadderView(ctx.author.id, game)
    view.message = await ctx.send(
        embed=ladder_embed(game, "Higher or lower?"), view=view
    )

# ---------- 🎟️ SCRATCH ----------
SCRATCH_TILES = 9
SCRATCH_PICKS = 3
SCRATCH_SYMBOLS = ("🍒", "🍀", "🔔", "7️⃣", "💎")
SCRATCH_TABLE = balance_payout_table(
    ((1.2, 50), (2.0, 28), (3.0, 14), (6.0, 6), (20.0, 2))
)

def draw_scratch_symbol():
    """Pick a prize symbol and its multiplier from the weighted table."""
    index = random.choices(
        range(len(SCRATCH_TABLE)),
        weights=[weight for _, weight in SCRATCH_TABLE],
        k=1,
    )[0]
    return SCRATCH_SYMBOLS[index], SCRATCH_TABLE[index][0]

def scratch_multiplier(symbol):
    return SCRATCH_TABLE[SCRATCH_SYMBOLS.index(symbol)][0]

def scratch_embed(game, status=None, color=None):
    rows = []
    for row in range(3):
        cells = []
        for column in range(3):
            tile = row * 3 + column
            cells.append(game["faces"].get(tile, "🎟️"))
        rows.append(" ".join(cells))
    prize_lines = " • ".join(
        f"{symbol} `{multiplier:g}x`"
        for symbol, (multiplier, _) in zip(SCRATCH_SYMBOLS, SCRATCH_TABLE)
    )
    embed = discord.Embed(
        title="🎟️ SCRATCH",
        description="\n".join(rows) + f"\n\n{prize_lines}",
        color=color or discord.Color.purple(),
    )
    embed.add_field(name="Player", value=game["player_name"], inline=True)
    embed.add_field(
        name="Bet", value=f"`{format_coins(game['bet'])} uwuncy`", inline=True
    )
    embed.add_field(
        name="Scratched",
        value=f"`{len(game['picks'])}/{SCRATCH_PICKS}`",
        inline=True,
    )
    if game.get("shield_notice"):
        embed.add_field(
            name="Loss Shield", value=game["shield_notice"], inline=False
        )
    if status:
        embed.add_field(name="Status", value=status, inline=False)
    embed.set_footer(text="Scratch three tiles • Match all three to win")
    return embed

class ScratchView(discord.ui.View):
    """A nine-tile scratch card: three matching symbols pay the prize."""

    def __init__(self, owner_id, game):
        super().__init__(timeout=120)
        self.owner_id = owner_id
        self.game = game
        self.message = None
        self.closed = False

        for index in range(SCRATCH_TILES):
            button = discord.ui.Button(
                label="\u200b",
                emoji="🎟️",
                style=discord.ButtonStyle.secondary,
                row=index // 3,
            )

            async def tile_callback(interaction, tile=index):
                await self.scratch(interaction, tile)

            button.callback = tile_callback
            self.add_item(button)

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "This is not your scratch card.", ephemeral=True
            )
            return False
        if self.closed:
            await interaction.response.send_message(
                "This scratch card is already finished.", ephemeral=True
            )
            return False
        return True

    def next_face(self):
        """Choose the symbol under the next tile from the decided outcome."""
        revealed = [self.game["faces"][tile] for tile in self.game["picks"]]
        if self.game["target_win"]:
            return self.game["prize_symbol"]
        remaining = SCRATCH_PICKS - len(revealed)
        if remaining > 1:
            # Near misses are allowed while a losing card is still possible.
            return random.choice(SCRATCH_SYMBOLS)
        blocked = revealed[0] if len(set(revealed)) == 1 else None
        return random.choice(
            [symbol for symbol in SCRATCH_SYMBOLS if symbol != blocked]
        )

    def fill_remaining(self):
        """Reveal the untouched tiles without showing a second winning line."""
        counts = {}
        for symbol in self.game["faces"].values():
            counts[symbol] = counts.get(symbol, 0) + 1
        for tile in range(SCRATCH_TILES):
            if tile in self.game["faces"]:
                continue
            allowed = [
                symbol
                for symbol in SCRATCH_SYMBOLS
                if counts.get(symbol, 0) < 2
            ] or list(SCRATCH_SYMBOLS)
            symbol = random.choice(allowed)
            counts[symbol] = counts.get(symbol, 0) + 1
            self.game["faces"][tile] = symbol
        for tile, button in enumerate(self.children):
            button.emoji = self.game["faces"][tile]
            button.disabled = True

    async def scratch(self, interaction, tile):
        if tile in self.game["faces"]:
            return await interaction.response.send_message(
                "That tile is already scratched.", ephemeral=True
            )
        symbol = self.next_face()
        self.game["faces"][tile] = symbol
        self.game["picks"].append(tile)
        button = self.children[tile]
        button.emoji = symbol
        button.disabled = True
        button.style = discord.ButtonStyle.primary

        if len(self.game["picks"]) < SCRATCH_PICKS:
            revealed = [self.game["faces"][pick] for pick in self.game["picks"]]
            teaser = (
                f"{symbol} — two of a kind, one more to go!"
                if len(set(revealed)) == 1 and len(revealed) == 2
                else f"{symbol} — keep scratching."
            )
            return await interaction.response.edit_message(
                embed=scratch_embed(self.game, teaser), view=self
            )

        self.closed = True
        bet = self.game["bet"]
        self.fill_remaining()
        if self.game["target_win"]:
            multiplier = scratch_multiplier(self.game["prize_symbol"])
            total_payout, bonus, boosted = settle_cashout_win(
                self.owner_id, "scratch", bet, multiplier
            )
            status = (
                f"🎉 Three {self.game['prize_symbol']} — **{multiplier:g}x**.\n"
                f"{payout_line(total_payout, bonus, boosted)}"
            )
            color = discord.Color.green()
        else:
            total_payout = 0
            loss_result = settle_cashout_loss(self.owner_id, "scratch", bet)
            status = describe_loss(loss_result, bet, "No match")
            color = discord.Color.red()

        await interaction.response.edit_message(
            embed=scratch_embed(self.game, status, color), view=self
        )
        self.stop()
        await offer_double_or_nothing(
            self.message, self.owner_id, "scratch", total_payout
        )

    async def on_timeout(self):
        if self.closed:
            return
        self.closed = True
        for child in self.children:
            child.disabled = True
        refund_reserved_bet(self.owner_id, self.game["bet"])
        if self.message:
            try:
                await self.message.edit(
                    embed=scratch_embed(
                        self.game, "Card expired. Your bet was returned."
                    ),
                    view=self,
                )
            except discord.HTTPException:
                pass

@bot.command(name="scratch", aliases=["sc"])
async def scratch(ctx, bet_text: str = None):
    """Scratch three of nine tiles and match them all to win the symbol prize."""
    if bet_text is None:
        return await ctx.send(
            "Use `uwu scratch <bet>` — example: `uwu scratch 50,000`."
        )
    bet, error = resolve_gambling_bet(
        ctx, bet_text, "scratch", "uwu scratch 50,000"
    )
    if error:
        return await ctx.send(error)

    user = get_user(ctx.author.id)
    prize_symbol, _ = draw_scratch_symbol()
    game = {
        "player_name": ctx.author.display_name,
        "bet": bet,
        "faces": {},
        "picks": [],
        "prize_symbol": prize_symbol,
        "target_win": chance_roll("scratch", user_id=ctx.author.id),
        "shield_notice": shield_notice(user, bet),
    }
    begin_game(user, "scratch", bet, reserve_bet=True)
    save_data(DATA)
    view = ScratchView(ctx.author.id, game)
    view.message = await ctx.send(
        embed=scratch_embed(game, "Scratch any three tiles."), view=view
    )

# ---------- 🎲 DOUBLE OR NOTHING ----------
# Offered on every gambling win. It reuses the source game's configured win
# chance, so at the 40% baseline it is a 20% house edge and the strongest
# uwuncy sink in the economy.
DOUBLE_OR_NOTHING_MAX_CHAIN = 5
DOUBLE_OR_NOTHING_TIMEOUT = 45

def double_or_nothing_line(stake, chain):
    return (
        f"🎲 **Double or Nothing** — risk `{format_coins(stake)} uwuncy` "
        f"for `{format_coins(stake * 2)}`. "
        f"Chain {chain}/{DOUBLE_OR_NOTHING_MAX_CHAIN}."
    )

class DoubleOrNothingView(discord.ui.View):
    """Risk a fresh payout for double, up to five times in a row."""

    def __init__(self, owner_id, game_name, stake, chain=1):
        super().__init__(timeout=DOUBLE_OR_NOTHING_TIMEOUT)
        self.owner_id = owner_id
        self.game_name = game_name
        self.stake = int(stake)
        self.chain = chain
        self.message = None
        self.closed = False

        self.risk_button = discord.ui.Button(
            label="🎲 Double or Nothing", style=discord.ButtonStyle.danger
        )
        self.risk_button.callback = self.risk
        self.add_item(self.risk_button)

        self.keep_button = discord.ui.Button(
            label="🏦 Keep it", style=discord.ButtonStyle.secondary
        )
        self.keep_button.callback = self.keep
        self.add_item(self.keep_button)

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "This is not your payout.", ephemeral=True
            )
            return False
        if self.closed:
            await interaction.response.send_message(
                "This offer is already closed.", ephemeral=True
            )
            return False
        return True

    def disable_all(self):
        for child in self.children:
            child.disabled = True

    async def keep(self, interaction):
        self.closed = True
        self.disable_all()
        await interaction.response.edit_message(
            content=(
                f"🏦 Kept **{format_coins(self.stake)} uwuncy**. Smart call."
            ),
            view=self,
        )
        self.stop()

    async def risk(self, interaction):
        self.closed = True
        self.disable_all()
        user = get_user(self.owner_id)
        if not debit_wallet(user, self.stake):
            await interaction.response.edit_message(
                content="❌ That payout is already spent.", view=self
            )
            return self.stop()

        begin_game(user, self.game_name, self.stake)
        won = chance_roll(self.game_name, user_id=self.owner_id)
        await interaction.response.edit_message(
            content=f"🎲 Rolling for **{format_coins(self.stake * 2)} uwuncy**…",
            view=self,
        )
        for face in ("🌀", "🎲", "✨"):
            await asyncio.sleep(0.6)
            try:
                await interaction.edit_original_response(
                    content=f"{face} Rolling for "
                    f"**{format_coins(self.stake * 2)} uwuncy**…",
                    view=self,
                )
            except discord.HTTPException:
                break

        if won:
            reward = self.stake * 2
            credit_wallet(user, reward)
            finish_game(user, self.game_name, self.stake, True, reward)
            save_data(DATA)
            content = (
                f"🎉 **Doubled!** Now holding "
                f"**{format_coins(reward)} uwuncy**."
            )
            self.stop()
            if self.chain < DOUBLE_OR_NOTHING_MAX_CHAIN:
                follow_up = DoubleOrNothingView(
                    self.owner_id, self.game_name, reward, self.chain + 1
                )
                content += (
                    f"\n{double_or_nothing_line(reward, self.chain + 1)}"
                )
                try:
                    await interaction.edit_original_response(
                        content=content, view=follow_up
                    )
                    follow_up.message = await interaction.original_response()
                except discord.HTTPException:
                    pass
                return
        else:
            finish_game(user, self.game_name, self.stake, False, self.stake)
            save_data(DATA)
            content = (
                f"💀 **Gone.** Lost **{format_coins(self.stake)} uwuncy**."
            )
            self.stop()

        try:
            await interaction.edit_original_response(content=content, view=self)
        except discord.HTTPException:
            pass

    async def on_timeout(self):
        if self.closed:
            return
        self.closed = True
        self.disable_all()
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass

async def offer_double_or_nothing(message, user_id, game, stake):
    """Post a Double or Nothing offer under a payout, when there is one."""
    stake = int(stake or 0)
    if stake <= 0 or message is None:
        return
    view = DoubleOrNothingView(user_id, game, stake)
    try:
        view.message = await message.channel.send(
            content=double_or_nothing_line(stake, 1), view=view
        )
    except discord.HTTPException:
        pass

# ==============================================
# 📉 HOUSE EDGE REPORTING
# ==============================================
# `uwu odds` reports each game's real house edge at its current setting, so a
# game can never quietly become a money printer again. "instant" games pay a
# fixed return on a win; "steps" games pay a multiplier that compounds per
# surviving step, and a player who is losing value per step stops at one.
MINES_REFERENCE_BOMBS = 3
GAME_ECONOMICS = {
    "slots": {"kind": "instant", "table": SLOT_TABLE},
    "coinflip": {"kind": "instant", "win_return": INSTANT_WIN_RETURN},
    "blackjack": {"kind": "instant", "win_return": INSTANT_WIN_RETURN},
    "colorgame": {"kind": "instant", "win_return": INSTANT_WIN_RETURN},
    "dice": {"kind": "instant", "win_return": INSTANT_WIN_RETURN},
    "highlow": {"kind": "instant", "win_return": INSTANT_WIN_RETURN},
    "roulette": {"kind": "instant", "win_return": INSTANT_WIN_RETURN},
    "wheel": {"kind": "instant", "win_return": INSTANT_WIN_RETURN},
    "scratch": {"kind": "instant", "table": SCRATCH_TABLE},
    "crash": {
        "kind": "steps",
        "survival": CRASH_BASE_SURVIVAL,
        "max_steps": CRASH_MAX_TICKS,
    },
    "tower": {
        "kind": "steps",
        "survival": tower_survival("normal"),
        "max_steps": TOWER_FLOORS,
    },
    "ladder": {
        "kind": "steps",
        "survival": LADDER_BASE_SURVIVAL,
        "max_steps": LADDER_MAX_RUNGS,
    },
    "mines": {
        "kind": "steps",
        "survival": mines_tile_survival(MINES_REFERENCE_BOMBS, 0),
        "max_steps": 16 - MINES_REFERENCE_BOMBS,
    },
}

def game_house_edge(game, chance=None):
    """The house's expected cut of one round at the configured win chance."""
    spec = GAME_ECONOMICS.get(game)
    if spec is None:
        return None
    win_chance = get_game_win_chance(game) if chance is None else float(chance)
    if spec["kind"] == "instant":
        win_return = spec.get("win_return") or table_mean_return(spec["table"])
        return 1.0 - (win_chance / 100.0) * win_return
    base_survival = spec["survival"]
    if base_survival <= 0:
        return 1.0
    ratio = scaled_step_survival(base_survival, win_chance) / base_survival
    # Below the baseline every extra step loses value, so the best a player can
    # do is stop at one; above it, riding to the cap is best.
    steps = 1 if ratio <= 1.0 else spec["max_steps"]
    return 1.0 - (1.0 - HOUSE_EDGE) * (ratio ** steps)

async def send_with_double_or_nothing(ctx, content, game, stake):
    """Send a text result and attach the Double or Nothing offer to it."""
    stake = int(stake or 0)
    if stake <= 0:
        return await ctx.send(content)
    view = DoubleOrNothingView(ctx.author.id, game, stake)
    view.message = await ctx.send(
        content=f"{content}\n{double_or_nothing_line(stake, 1)}", view=view
    )
    return view.message

# ==============================================
# 🐓 SABONG — POOLED CROWD BETTING
# ==============================================
# Sabong is the only game here that is not played against the house. Everyone
# stakes into a MERON or WALA pool and the winning side splits the losing side's
# money, so a player's multiplier is decided by how lopsided the crowd is rather
# than by a fixed payout table:
#
#     payout = your bet x (winning_pool + losing_pool x (1 - rake)) / winning_pool
#
# Betting the unpopular rooster is what pays. If nobody backs the loser there is
# no money to share, so the winners simply get their stake back — the rake only
# ever touches the losing pool, never a winner's own stake.
SABONG_RAKE = 0.05
SABONG_ODDS_NOTE = (
    "ℹ️ `sabong` is player-versus-player, so its percentage is the chance "
    "**MERON** wins, not a house win rate — `50` is an even fight, and the "
    f"house only ever takes a {SABONG_RAKE:.0%} rake of the losing pool."
)
SABONG_LOBBY_SECONDS = 300
SABONG_FIGHT_SECONDS = 180
SABONG_FIGHT_TICKS = 30
SABONG_ROOSTER_HP = 100
SABONG_SIDES = ("meron", "wala")
SABONG_SIDE_LABELS = {"meron": "MERON", "wala": "WALA"}
SABONG_SIDE_EMOJI = {"meron": "🔴", "wala": "🔵"}
SABONG_SIDE_ALIASES = {
    "meron": "meron",
    "m": "meron",
    "red": "meron",
    "wala": "wala",
    "w": "wala",
    "blue": "wala",
}

# One live match per channel, so two crowds can never bet into the same pool.
SABONG_MATCHES = {}

SABONG_ROOSTER_NAMES = (
    "Bakunawa", "Haring Uwak", "Kidlat", "Bagyo", "Talim", "Asero",
    "Dugong Bughaw", "Panday", "Lakay", "Sunog", "Buwaya", "Higante",
    "Anino", "Tigre", "Bulkan", "Kamandag",
)

SABONG_STRIKES = (
    "{a} launches off the ground and rakes {b} across the chest!",
    "{a} lands a clean heel strike on {b}!",
    "{a} drives {b} back toward the edge of the ring!",
    "{a} slips under {b} and comes up slashing!",
    "{a} catches {b} mid-air — feathers everywhere!",
    "{a} pins {b} down and hammers with the beak!",
    "{a} feints left and buries a spur into {b}!",
    "{a} explodes out of the corner and floors {b}!",
    "{a} counters and sends {b} tumbling!",
    "{a} rips a low blow across {b}'s legs!",
)
SABONG_LULLS = (
    "Both roosters circle, sizing each other up…",
    "They lock eyes. The crowd goes quiet.",
    "Hackles up on both sides — neither one blinks.",
    "A tense stand-off in the middle of the ring.",
    "They break apart, breathing hard.",
)
SABONG_CROWD = (
    "🗣️ *MERON! MERON! MERON!*",
    "🗣️ *WALA NAMAN! WALA!*",
    "🗣️ The crowd is on its feet!",
    "🗣️ Somebody just doubled down at ringside!",
    "🗣️ *SUUUUGOD!*",
)


def sabong_side(text):
    """Resolve a side name or alias, or None when it is not a side."""
    return SABONG_SIDE_ALIASES.get(str(text or "").casefold())


def sabong_pool(match, side):
    return sum(bet["amount"] for bet in match["bets"].values() if bet["side"] == side)


def sabong_multiplier(winning_pool, losing_pool):
    """Total return per unit staked on the winning side."""
    if winning_pool <= 0:
        return 0.0
    return (winning_pool + losing_pool * (1.0 - SABONG_RAKE)) / winning_pool


def sabong_odds_board(match):
    """Live payout preview for both sides, as the crowd's money stands."""
    lines = []
    for side in SABONG_SIDES:
        pool = sabong_pool(match, side)
        other = sabong_pool(match, SABONG_SIDES[1 - SABONG_SIDES.index(side)])
        backers = sum(1 for bet in match["bets"].values() if bet["side"] == side)
        if pool <= 0:
            payout = "no bets yet"
        else:
            payout = f"pays **{sabong_multiplier(pool, other):.2f}x**"
        lines.append(
            f"{SABONG_SIDE_EMOJI[side]} **{SABONG_SIDE_LABELS[side]}** — "
            f"`{format_coins(pool)}` uwuncy from **{backers}** "
            f"{'bettor' if backers == 1 else 'bettors'} • {payout}"
        )
    return "\n".join(lines)


def sabong_hp_bar(hp):
    filled = max(0, min(10, round(hp / 10)))
    return "█" * filled + "░" * (10 - filled)


def sabong_lobby_embed(match, status=None):
    total = sum(bet["amount"] for bet in match["bets"].values())
    embed = discord.Embed(
        title="🐓 SABONG — BET BET BET!",
        description=(
            status
            or f"**{match['host_name']}** started a sabong!\n"
            "Stake with `uwu sabong <amount>`, then pick your rooster below."
        ),
        color=discord.Color.orange(),
    )
    embed.add_field(name="Ringside money", value=sabong_odds_board(match), inline=False)
    waiting = [bet for bet in match["bets"].values() if bet["side"] is None]
    if waiting:
        embed.add_field(
            name="Staked, still choosing",
            value=", ".join(bet["name"] for bet in waiting),
            inline=False,
        )
    embed.add_field(
        name="Total pot",
        value=f"**{format_coins(total)} uwuncy**",
        inline=False,
    )
    embed.set_footer(
        text=(
            f"{match['host_name']} runs `uwu sabong start` to begin • "
            f"the losing pool is shared out minus a {SABONG_RAKE:.0%} rake"
        )
    )
    return embed


def sabong_fight_embed(match, headline, color=None):
    embed = discord.Embed(
        title="🐓 SABONG — LIVE",
        description=headline,
        color=color or discord.Color.red(),
    )
    for side in SABONG_SIDES:
        hp = match["hp"][side]
        embed.add_field(
            name=(
                f"{SABONG_SIDE_EMOJI[side]} {SABONG_SIDE_LABELS[side]} — "
                f"{match['names'][side]}"
            ),
            value=f"`{sabong_hp_bar(hp)}` {max(0, int(hp))}/100",
            inline=False,
        )
    embed.add_field(name="Ringside money", value=sabong_odds_board(match), inline=False)
    if match["log"]:
        embed.add_field(
            name="Play by play",
            inline=False,
        )
    return embed


def build_sabong_script(winner):
    """Damage per tick that always leaves `winner` standing at the end.

    The outcome is rolled from the configured odds before the fight starts, so
    the animation has to be scripted backwards from it rather than emerging
    from the damage rolls.
    """
    loser = SABONG_SIDES[1 - SABONG_SIDES.index(winner)]
    script = []
    for tick in range(SABONG_FIGHT_TICKS):
        progress = (tick + 1) / SABONG_FIGHT_TICKS
        # The loser slips behind gradually so the crowd sees it coming, but the
        # winner still takes real damage and can look in trouble early on.
        if random.random() < 0.30 - 0.15 * progress:
            attacker, defender = loser, winner
        else:
            attacker, defender = winner, loser
        script.append((attacker, defender, random.randint(3, 11)))
    return script, loser


def resolve_sabong_winner(match):
    """Pick the winning rooster, honouring per-user then global odds."""
    # A per-user override is about one player's result, so it decides the whole
    # match: the earliest such bettor's roll picks the side that wins.
    for user_id, bet in match["bets"].items():
        if bet["side"] is None:
            continue
        override = get_user_game_win_chance(user_id, "sabong")
        if override is None:
            continue
        backed = bet["side"]
        other = SABONG_SIDES[1 - SABONG_SIDES.index(backed)]
        chance = max(0.0, min(100.0, override))
        if chance >= 100:
            return backed
        if chance <= 0:
            return other
        return backed if random.random() < (chance / 100.0) else other
    meron_chance = get_game_win_chance("sabong")
    return "meron" if random.random() < (meron_chance / 100.0) else "wala"


def settle_sabong(match, winner):
    """Pay the winning pool and report each player's result."""
    loser = SABONG_SIDES[1 - SABONG_SIDES.index(winner)]
    winning_pool = sabong_pool(match, winner)
    losing_pool = sabong_pool(match, loser)
    multiplier = sabong_multiplier(winning_pool, losing_pool)
    winners, losers = [], []

    for user_id, bet in match["bets"].items():
        if bet["side"] is None:
            # Never chose a rooster, so the stake was never at risk.
            refund_reserved_bet(user_id, bet["amount"])
            continue
        user = get_user(user_id)
        if bet["side"] == winner:
            payout = int(bet["amount"] * multiplier)
            total_payout, bonus, boosted = settle_win(user, payout)
            finish_game(user, "sabong", bet["amount"], True, total_payout)
            winners.append((bet["name"], bet["amount"], total_payout, bonus, boosted))
        else:
            loss_result = settle_loss(user, bet["amount"], bet_reserved=True)
            finish_game(user, "sabong", bet["amount"], False, loss_result["remaining_loss"])
            losers.append((bet["name"], bet["amount"], loss_result))

    jackpot_note = ""
    if winning_pool <= 0 and losing_pool > 0:
        # Nobody backed the winning rooster, so the whole pot seeds the jackpot
        # instead of vanishing.
        ECONOMY_SETTINGS["jackpot"] += losing_pool
        save_economy_settings()
        jackpot_note = (
            f"\n🎰 Nobody backed {SABONG_SIDE_LABELS[winner]} — "
            f"**{format_coins(losing_pool)} uwuncy** rolls into the global jackpot."
        )

    save_data(DATA)
    return {
        "winner": winner,
        "multiplier": multiplier,
        "winning_pool": winning_pool,
        "losing_pool": losing_pool,
        "winners": winners,
        "losers": losers,
        "jackpot_note": jackpot_note,
    }


def sabong_result_text(match, result):
    winner = result["winner"]
    lines = [
        f"# {SABONG_SIDE_EMOJI[winner]} {SABONG_SIDE_LABELS[winner]} WINS!",
        f"**{match['names'][winner]}** is left standing.",
        "",
        f"Pot: **{format_coins(result['winning_pool'] + result['losing_pool'])} uwuncy** • "
        f"{SABONG_SIDE_LABELS[winner]} pays **{result['multiplier']:.2f}x**",
    ]
    if result["winners"]:
        lines.append("")
        lines.append("**💰 Winners**")
        for name, amount, payout, bonus, boosted in result["winners"]:
            entry = (
                f"• {name} — staked `{format_coins(amount)}` → "
                f"**+{format_coins(payout)} uwuncy**"
            )
            if boosted:
                entry += f" (Lucky Potion +{format_coins(bonus)})"
            lines.append(entry)
    else:
        lines.append("")
        lines.append(f"**No one backed {SABONG_SIDE_LABELS[winner]}.**")
    if result["losers"]:
        lines.append("")
        lines.append("**💸 Lost their stake**")
        for name, amount, loss_result in result["losers"]:
            entry = f"• {name} — `-{format_coins(loss_result['remaining_loss'])} uwuncy`"
            if loss_result["shielded"]:
                entry += (
                    f" (Loss Shield returned "
                    f"{format_coins(loss_result['protected_amount'])})"
                )
            lines.append(entry)
    lines.append(result["jackpot_note"])
    return "\n".join(line for line in lines if line is not None)


class SabongLobbyView(discord.ui.View):
    """MERON / WALA buttons that assign each staked player to a side."""

    def __init__(self, match):
        super().__init__(timeout=SABONG_LOBBY_SECONDS)
        self.match = match
        self.message = None
        for side in SABONG_SIDES:
            button = discord.ui.Button(
                label=SABONG_SIDE_LABELS[side],
                emoji=SABONG_SIDE_EMOJI[side],
                style=(
                    discord.ButtonStyle.danger
                    if side == "meron"
                    else discord.ButtonStyle.primary
                ),
            )
            button.callback = self.make_pick(side)
            self.add_item(button)

    def make_pick(self, side):
        async def pick(interaction):
            if self.match["state"] != "betting":
                return await interaction.response.send_message(
                    "Betting is closed for this sabong.", ephemeral=True
                )
            bet = self.match["bets"].get(interaction.user.id)
            if bet is None:
                return await interaction.response.send_message(
                    "Stake first with `uwu sabong <amount>`, then pick a rooster.",
                    ephemeral=True,
                )
            if bet["side"] is not None:
                return await interaction.response.send_message(
                    f"You are already on **{SABONG_SIDE_LABELS[bet['side']]}** "
                    f"for `{format_coins(bet['amount'])}` uwuncy.",
                    ephemeral=True,
                )
            bet["side"] = side
            await interaction.response.send_message(
                f"{SABONG_SIDE_EMOJI[side]} You are on **{SABONG_SIDE_LABELS[side]}** "
                f"for `{format_coins(bet['amount'])}` uwuncy.",
                ephemeral=True,
            )
            await self.refresh()

        return pick

    async def refresh(self):
        if not self.message:
            return
        try:
            await self.message.edit(embed=sabong_lobby_embed(self.match), view=self)
        except discord.HTTPException:
            pass

    async def close(self):
        for child in self.children:
            child.disabled = True
        await self.refresh()
        self.stop()

    async def on_timeout(self):
        if self.match["state"] != "betting":
            return
        await cancel_sabong(
            self.match,
            f"⌛ Nobody started the sabong within {SABONG_LOBBY_SECONDS // 60} minutes.",
        )


async def cancel_sabong(match, reason):
    """Abandon a match and hand every staked player their money back."""
    if match["state"] == "done":
        return
    match["state"] = "done"
    SABONG_MATCHES.pop(match["channel_id"], None)
    refunded = 0
    for user_id, bet in match["bets"].items():
        refund_reserved_bet(user_id, bet["amount"])
        refunded += bet["amount"]
    view = match.get("view")
    if view:
        await view.close()
    note = (
        f"\nRefunded **{format_coins(refunded)} uwuncy** to "
        f"**{len(match['bets'])}** bettors."
        if refunded
        else ""
    )
    try:
        await match["channel"].send(f"{reason}{note}")
    except discord.HTTPException:
        pass


async def run_sabong_fight(match):
    """Play the 3-minute fight out tick by tick, then pay everyone.

    Settlement is wrapped so a mid-fight Discord failure can never leave the
    crowd's stakes reserved or the channel stuck on a match that never ends.
    """
    winner = resolve_sabong_winner(match)
    try:
        await animate_sabong_fight(match, winner)
    except Exception:
        traceback.print_exc()
    finally:
        if match["state"] != "done":
            match["state"] = "done"
            SABONG_MATCHES.pop(match["channel_id"], None)
            result = settle_sabong(match, winner)
            try:
                await match["channel"].send(sabong_result_text(match, result))
            except discord.HTTPException:
                pass


async def animate_sabong_fight(match, winner):
    """Edit one message tick by tick, then settle and announce the result."""
    script, loser = build_sabong_script(winner)
    match["hp"] = {side: SABONG_ROOSTER_HP for side in SABONG_SIDES}
    match["log"] = []
    interval = SABONG_FIGHT_SECONDS / SABONG_FIGHT_TICKS

    message = await match["channel"].send(
        embed=sabong_fight_embed(match, "🔔 **The referee releases them — FIGHT!**")
    )

    for tick, (attacker, defender, damage) in enumerate(script, start=1):
        await asyncio.sleep(interval)
        if tick == SABONG_FIGHT_TICKS:
            match["hp"][loser] = 0
            line = (
                f"💀 **{match['names'][winner]}** puts "
                f"**{match['names'][defender if defender != winner else loser]}** down!"
            )
        else:
            # Keep the loser alive until the scripted finish so the ending lands
            # on the rolled winner rather than on the damage rolls.
            floor = 6 if defender == loser else 1
            match["hp"][defender] = max(floor, match["hp"][defender] - damage)
            if random.random() < 0.18:
                line = random.choice(SABONG_LULLS)
            else:
                line = "⚔️ " + random.choice(SABONG_STRIKES).format(
                    a=match["names"][attacker], b=match["names"][defender]
                )
        match["log"].append(line)
        if tick % 6 == 0:
            match["log"].append(random.choice(SABONG_CROWD))

        remaining = int((SABONG_FIGHT_TICKS - tick) * interval)
        headline = (
            f"Round **{tick}** of {SABONG_FIGHT_TICKS} • ~{remaining}s left"
            if tick < SABONG_FIGHT_TICKS
            else "🔔 **The fight is over!**"
        )
        try:
            await message.edit(embed=sabong_fight_embed(match, headline))
        except discord.HTTPException:
            pass

    match["state"] = "done"
    SABONG_MATCHES.pop(match["channel_id"], None)
    result = settle_sabong(match, winner)
    try:
        await message.edit(
            embed=sabong_fight_embed(
                match,
                f"🏆 **{SABONG_SIDE_LABELS[winner]} — {match['names'][winner]} wins!**",
                discord.Color.gold(),
            )
        )
    except discord.HTTPException:
        pass
    await match["channel"].send(sabong_result_text(match, result))


@bot.command(name="sabong", aliases=["cockfight", "tari"])
async def sabong(ctx, action: str = None, side: str = None):
    """Stake into a pooled cockfight, then back MERON or WALA."""
    match = SABONG_MATCHES.get(ctx.channel.id)
    keyword = str(action or "").casefold()

    if keyword in {"start", "simula"}:
        if match is None:
            return await ctx.send("No sabong is open here. Start one with `uwu sabong <amount>`.")
        if match["state"] != "betting":
            return await ctx.send("This sabong has already started.")
        if match["host_id"] != ctx.author.id and not is_owner(ctx):
            return await ctx.send(
                f"Only **{match['host_name']}** can start this sabong."
            )
        placed = [bet for bet in match["bets"].values() if bet["side"] is not None]
        if not placed:
            return await ctx.send("Nobody has picked a rooster yet.")
        match["state"] = "fighting"
        await match["view"].close()
        pools = [sabong_pool(match, name) for name in SABONG_SIDES]
        if not all(pools):
            await ctx.send(
                "⚠️ Everyone is on one side, so there is no losing pool to share — "
                "winners will only get their stake back."
            )
        await ctx.send(
            f"🔔 **{match['host_name']}** rings the bell! Betting is closed.\n"
            f"{sabong_odds_board(match)}"
        )
        return await run_sabong_fight(match)

    if keyword in {"cancel", "stop"}:
        if match is None:
            return await ctx.send("No sabong is open here.")
        if match["host_id"] != ctx.author.id and not is_owner(ctx):
            return await ctx.send(f"Only **{match['host_name']}** can cancel this sabong.")
        if match["state"] != "betting":
            return await ctx.send("The fight is already under way.")
        return await cancel_sabong(match, "🚫 Sabong cancelled.")

    if action is None:
        if match is None:
            return await ctx.send(
                "🐓 **Sabong** — pooled cockfight betting.\n"
                "`uwu sabong <amount>` to stake, then click **MERON** or **WALA** "
                "(or `uwu sabong <amount> meron` in one go).\n"
                "The host runs `uwu sabong start` to begin the 3-minute fight.\n"
                "Winners split the losing pool, so backing the unpopular rooster "
                "pays the most."
            )
        return await ctx.send(embed=sabong_lobby_embed(match))

    user = get_user(ctx.author.id)
    bet = parse_coins(action, user.get("wallet", 0))
    if bet is None:
        return await ctx.send(
            "❌ Invalid amount. Use `uwu sabong 1,000,000`, `uwu sabong start`, "
            "or `uwu sabong cancel`."
        )

    chosen_side = None
    if side is not None:
        chosen_side = sabong_side(side)
        if chosen_side is None:
            return await ctx.send("❌ Pick a side: `meron` or `wala`.")

    if match is not None and match["state"] != "betting":
        return await ctx.send("Betting is closed — a fight is already running here.")

    user = get_user(ctx.author.id)
    validation_error = validate_bet(user, bet, "sabong")
    if validation_error:
        return await ctx.send(f"❌ {validation_error}")

    if match is not None and ctx.author.id in match["bets"]:
        existing = match["bets"][ctx.author.id]
        placed_on = (
            f" on **{SABONG_SIDE_LABELS[existing['side']]}**"
            if existing["side"]
            else " (still choosing a rooster)"
        )
        return await ctx.send(
            f"You already staked `{format_coins(existing['amount'])}` uwuncy{placed_on}."
        )

    if not begin_game(user, "sabong", bet, reserve_bet=True):
        return await ctx.send("❌ Not enough uwuncy.")
    save_data(DATA)

    if match is None:
        match = {
            "channel_id": ctx.channel.id,
            "channel": ctx.channel,
            "host_id": ctx.author.id,
            "host_name": ctx.author.display_name,
            "state": "betting",
            "bets": {},
            "hp": {name: SABONG_ROOSTER_HP for name in SABONG_SIDES},
            "log": [],
            "names": {
                "meron": random.choice(SABONG_ROOSTER_NAMES),
                "wala": random.choice(SABONG_ROOSTER_NAMES),
            },
        }
        while match["names"]["wala"] == match["names"]["meron"]:
            match["names"]["wala"] = random.choice(SABONG_ROOSTER_NAMES)
        SABONG_MATCHES[ctx.channel.id] = match
        match["bets"][ctx.author.id] = {
            "name": ctx.author.display_name,
            "amount": bet,
            "side": chosen_side,
        }
        view = SabongLobbyView(match)
        match["view"] = view
        view.message = await ctx.send(
            content=(
                f"@here **{ctx.author.display_name} STARTED A SABONG! BET BET BET!** 🐓"
            ),
            embed=sabong_lobby_embed(match),
            view=view,
        )
        return

    match["bets"][ctx.author.id] = {
        "name": ctx.author.display_name,
        "amount": bet,
        "side": chosen_side,
    }
    await match["view"].refresh()
    if chosen_side:
        return await ctx.send(
            f"{SABONG_SIDE_EMOJI[chosen_side]} **{ctx.author.display_name}** backs "
            f"**{SABONG_SIDE_LABELS[chosen_side]}** for "
            f"`{format_coins(bet)}` uwuncy!"
        )
    await ctx.send(
        f"🐓 **{ctx.author.display_name}** staked "
        f"`{format_coins(bet)}` uwuncy — pick **MERON** or **WALA** above!"
    )

@bot.command(name="8ball", aliases=["magic8"])
async def eightball(ctx,*,q=None):
    if not q: return await ctx.send("❌ Ask me something!")
    await ctx.send(f"🔮: {random.choice(['Yes!','No.','Maybe...','Definitely!','Absolutely not.'])}")

@bot.command(name="hug")
async def hug(ctx,m:discord.Member=None):
    if not m or m==ctx.author: await ctx.send(f"🤗 {ctx.author.mention} hugs everyone!")
    else: await ctx.send(f"🤗 {ctx.author.mention} hugs {m.mention}!")

@bot.command(name="pat")
async def pat(ctx,m:discord.Member=None):
    if not m or m==ctx.author: await ctx.send(f"🖐️ {ctx.author.mention} pats themselves~")
    else: await ctx.send(f"🖐️ {ctx.author.mention} pats {m.mention}!")

@bot.command(name="kiss")
async def kiss(ctx,m:discord.Member=None):
    if not m or m==ctx.author: await ctx.send(f"😘 {ctx.author.mention} blows a kiss~")
    else: await ctx.send(f"😘 {ctx.author.mention} kisses {m.mention}!")

@bot.command(name="slap")
async def slap(ctx,m:discord.Member=None):
    if not m or m==ctx.author: await ctx.send(f"🖐️ {ctx.author.mention} slaps air!")
    else: await ctx.send(f"🖐️ {ctx.author.mention} slaps {m.mention}!")

@bot.command(name="create")
async def create_command(
    ctx,
    target: str = None,
    size: int = None,
    amount_text: str = None,
):
    """Create an arena with a creator-selected total commitment per player."""
    if ctx.guild is None:
        return await ctx.send("Arenas can only be created inside a Discord server.")
    total_required = parse_coins(amount_text)
    if (
        str(target or "").casefold() != "arena"
        or size not in {1, 2, 3, 4, 5}
        or total_required is None
        or total_required <= 0
        or total_required % 10 != 0
    ):
        return await ctx.send(
            "Use `uwu create arena <1-5> <total-per-player>` — for example, "
            "`uwu create arena 1 1,000,000`.\n"
            "The total is the one-time bet per player. The winner pool is "
            "all player bets multiplied by 2 and split equally among the winning team."
        )
    active_guild_arena_id, _active_guild_arena = get_active_arena_for_guild(
        ctx.guild.id
    )
    if active_guild_arena_id:
        return await ctx.send(
            f"This server already has active arena `{active_guild_arena_id}`. "
            "Only one arena can exist at a time per Discord server."
        )
    if get_active_arena_for_user(ctx.author.id)[0]:
        return await ctx.send("You already have an active arena. Finish or cancel it first.")
    entry_fee = total_required
    match_reserve = 0
    round_bet = 0
    creator = get_user(ctx.author.id)
    if user_total_balance(creator) < total_required:
        return await ctx.send(
            f"You need at least **{format_coins(total_required)} uwuncy** "
            "to create an arena. Crypto holdings do not count."
        )
    if not debit_available_balance(creator, total_required):
        return await ctx.send("You could not pay the configured arena bet.")

    current_id = arena_id()
    required_players = size * 2
    ARENAS[current_id] = {
        "creator_id": str(ctx.author.id),
        "guild_id": str(ctx.guild.id),
        "team_size": int(size),
        "player_requirement": total_required,
        "bet_per_player": total_required,
        "bet_charge_mode": "single_bet",
        "entry_fee": entry_fee,
        "match_reserve": match_reserve,
        "round_bet": round_bet,
        "reserve_charge_mode": "single_bet",
        "status": "lobby",
        "created_at": int(time.time()),
        "players": {
            str(ctx.author.id): {
                "fee_paid": True,
                "bet_paid": total_required,
                "entry_paid": total_required,
                "match_reserve_total": 0,
                "match_reserve_remaining": 0,
                "display_name": ctx.author.display_name,
            }
        },
        "groups": [[str(ctx.author.id)]] if size > 1 else [],
        "teams": [],
        "unpaired": [],
        "pairs": [],
        "bets": {},
        "rounds": [],
        "round_index": 0,
        "team_wins": {"1": 0, "2": 0},
        "required_players": required_players,
    }
    arena_rebuild_teams(ARENAS[current_id])
    save_data(DATA)
    save_arenas()
    await ctx.send(
        f"🏟️ **Arena created!**\n"
        f"ID: `{current_id}` • **{arena_team_size_label(size)}**\n"
        f"Bet paid: **{format_coins(total_required)} uwuncy**\n"
        "No additional round charges will be taken. "
        "The winner payout is the total bet pool ×2, split equally among the winning team.\n"
        f"Players needed: **{required_players}**\n"
        f"Others can join with `uwu arena join {current_id}`.\n"
        f"Use `uwu arena status {current_id}` to view it.",
        embed=arena_embed(current_id, ARENAS[current_id]),
    )

@bot.command(name="arena")
async def arena_command(
    ctx,
    action: str = None,
    arena_code: str = None,
    amount_text: str = None,
    *choice_parts,
):
    """Manage arena lobbies, seven-round matches, status, and cancellation."""
    action = str(action or "").casefold()
    if action == "channel":
        if ctx.guild is None:
            return await ctx.send("Arena channels can only be configured inside a server.")
        if ctx.guild.owner_id != ctx.author.id:
            return await ctx.send("Only the server owner can set the arena channel.")
        channel_action = str(arena_code or "").casefold()
        if channel_action == "setup":
            channel = ctx.channel
            if not isinstance(channel, discord.TextChannel):
                return await ctx.send("Run channel setup from a normal text channel.")
        elif channel_action == "redo":
            _restored, response = await redo_arena_channel(ctx.guild)
            return await ctx.send(response)
        else:
            channel = resolve_arena_channel(ctx.guild, arena_code)
        if channel is None:
            return await ctx.send(
                "Use `uwu arena channel setup` in the channel you want, "
                "or `uwu arena channel #channel`."
            )
        active_id, active_arena = active_arena_for_channel(channel.id)
        if active_arena is not None:
            return await ctx.send(
                f"Arena `{active_id}` is already active in that channel. "
                "Wait for it to finish before changing the setting."
            )
        ARENA_CHANNELS[str(ctx.guild.id)] = str(channel.id)
        save_arena_channels()
        return await ctx.send(
            f"✅ Arena channel set to {channel.mention}. "
            "Future matches will lock it to registered contestants and the bot. "
            "Use `uwu channel redo` to restore the last saved permission change."
        )
    requested_id = str(arena_code or "").upper() or None
    if action not in {"join", "status", "start", "cancel"}:
        return await ctx.send(
            "Arena commands: `uwu create arena <1-5> <total-per-player>`, "
            "`uwu arena join <id>`, `uwu arena status <id>`, "
            f"`uwu arena start <id>` ({ARENA_ROUNDS} games using the configured bet), "
            f"`uwu arena cancel <id>`, or "
            "`uwu arena channel setup` / `uwu channel redo` "
            "(server owner only)."
        )

    if requested_id:
        arena = ARENAS.get(requested_id)
        if not arena:
            return await ctx.send("That arena does not exist.")
        current_id = requested_id
    else:
        current_id, arena = get_active_arena_for_user(ctx.author.id)
        if not arena:
            return await ctx.send("You are not in an active arena. Provide an arena ID.")

    user_id = str(ctx.author.id)
    players = arena_players(arena)
    required_players = int(arena["team_size"]) * 2

    if action == "status":
        return await ctx.send(embed=arena_embed(current_id, arena))

    if action == "join":
        if arena.get("status") != "lobby":
            return await ctx.send("This arena is no longer accepting registrations.")
        if user_id in players:
            return await ctx.send("You are already registered in this arena.")
        if get_active_arena_for_user(ctx.author.id)[0]:
            return await ctx.send("You already have another active arena.")
        if len(players) >= required_players:
            return await ctx.send("This arena is full.")
        user = get_user(ctx.author.id)
        bet_amount = arena_player_bet(arena)
        entry_fee = arena_entry_fee(arena)
        match_reserve = arena_match_reserve(arena)
        charge_amount = bet_amount if arena_uses_single_bet(arena) else entry_fee
        if user_total_balance(user) < charge_amount:
            return await ctx.send(
                f"You need **{format_coins(charge_amount)} uwuncy** "
                "to join. Crypto holdings do not count."
            )
        if not debit_available_balance(user, charge_amount):
            return await ctx.send(
                "You could not pay the configured arena bet."
                if arena_uses_single_bet(arena)
                else "You could not pay the configured arena entry fee."
            )
        arena.setdefault("players", {})[user_id] = {
            "fee_paid": True,
            "bet_paid": charge_amount if arena_uses_single_bet(arena) else None,
            "entry_paid": charge_amount if arena_uses_single_bet(arena) else entry_fee,
            "match_reserve_total": match_reserve,
            "match_reserve_remaining": match_reserve,
            "display_name": ctx.author.display_name,
        }
        arena_rebuild_teams(arena)
        save_data(DATA)
        save_arenas()
        registration_details = (
            f"**{format_coins(charge_amount)} uwuncy bet**. "
            "Winner payout is the total pool ×2, split equally among the winning team.\n"
            if arena_uses_single_bet(arena)
            else (
                f"**{format_coins(entry_fee)} uwuncy entry**. "
                f"Keep **{format_coins(match_reserve)} uwuncy available** for the "
                f"seven rounds (**{format_coins(arena_round_bet(arena))} per round**).\n"
            )
        )
        return await ctx.send(
            f"✅ **Registration successful!** {ctx.author.mention} paid "
            f"{registration_details}"
            "Use `uwu paired @user` to choose a teammate.",
            embed=arena_embed(current_id, arena),
        )

    if user_id not in players:
        return await ctx.send("You must register for this arena first.")

    if action == "start":
        if user_id != str(arena.get("creator_id")):
            return await ctx.send("Only the arena creator can start the arena.")
        if arena_start_is_stale(current_id, arena):
            print(f"⚠️ Resetting stale pre-lock arena start `{current_id}`.")
            reset_stale_arena_start(arena)
        if arena.get("status") != "lobby":
            return await ctx.send("This arena has already started or ended.")
        if len(players) != required_players:
            return await ctx.send(f"Waiting for all **{required_players}** players to register.")
        arena_rebuild_teams(arena)
        if not arena_ready(arena):
            return await ctx.send(
                "The teams are not full yet. Use `uwu paired @user` until both teams "
                f"have **{arena['team_size']}** players."
            )
        arena["rounds"] = []
        rotating_game_pool = list(ARENA_GAME_POOL)
        random.shuffle(rotating_game_pool)
        selected_games = rotating_game_pool[:ARENA_ROUNDS]
        for round_number, (game_key, game_name) in enumerate(selected_games, start=1):
            round_state = {
                "number": round_number,
                "game_key": game_key,
                "game_name": game_name,
            }
            if game_key == "arena_mines":
                round_state["defender_team"] = 1 if round_number % 2 else 2
                round_state["attacker_team"] = 2 if round_number % 2 else 1
            elif game_key == "bugtong":
                arena_prepare_bugtong_round(round_state, arena)
            elif game_key == "uno":
                arena_prepare_uno_round(round_state, arena)
            elif game_key == "lucky9":
                arena_prepare_lucky9_round(round_state, arena)
            elif game_key == "deal_or_no_deal":
                arena_prepare_deal_round(round_state)
            arena["rounds"].append(round_state)
        arena["round_index"] = 0
        arena["team_wins"] = {"1": 0, "2": 0}
        arena["status"] = "match"
        arena["guild_id"] = str(ctx.guild.id)
        arena_channel = await fetch_arena_channel(ctx.guild)
        if arena_channel is None:
            arena["status"] = "lobby"
            save_arenas()
            return await ctx.send(
                "Set an arena channel first with `uwu arena channel #channel`."
            )
        if not await lock_arena_channel(current_id, arena, arena_channel):
            arena["status"] = "lobby"
            save_arenas()
            return await ctx.send(
                "I couldn't lock the configured arena channel. "
                "Check that I have Manage Channels permission."
            )
        try:
            save_arenas()
            await arena_channel.send(
                "🏟️ **Seven-round arena match started!**\n"
                + (
                    f"Each player paid **{format_coins(arena_player_bet(arena))} uwuncy**. "
                    "No additional round charges will be taken. "
                    "The winner pool is the total bets ×2, split among the winning team.\n"
                    if arena_uses_single_bet(arena)
                    else (
                        f"Each player paid **{format_coins(arena_entry_fee(arena))} uwuncy** entry. "
                        f"Keep **{format_coins(arena_match_reserve(arena))} uwuncy available** "
                        f"for seven round charges.\n"
                        f"Rounds cost **{format_coins(arena_round_bet(arena))} per player** and "
                    )
                )
                + "resolve "
                "only after every player acts or the 60-second timer expires.",
                embed=arena_embed(current_id, arena),
            )
            return await continue_arena_match(current_id, arena, arena_channel)
        except Exception:
            print(f"❌ Arena `{current_id}` failed while starting; rolling back the channel lock.")
            traceback.print_exc()
            await unlock_arena_channel(current_id, arena)
            arena["status"] = "lobby"
            arena["round_index"] = 0
            for round_state in arena.get("rounds", []):
                if isinstance(round_state, dict):
                    round_state.pop("reserve_spent", None)
                    round_state.pop("winner_team", None)
            save_arenas()
            raise

    if action == "cancel":
        if user_id != str(arena.get("creator_id")):
            return await ctx.send("Only the arena creator can cancel the arena.")
        if arena.get("status") == "completed":
            return await ctx.send("A completed arena cannot be cancelled.")
        await unlock_arena_channel(current_id, arena)
        arena["status"] = "cancelled"
        save_data(DATA)
        save_arenas()
        if arena_uses_deferred_reserve(arena):
            cancellation_message = (
                "Entry fees already paid remain forfeited; future round charges "
                "were not taken."
            )
        else:
            cancellation_message = (
                "All committed entry fees and unused match reserves were forfeited; "
                "no uwuncy was refunded."
            )
        return await ctx.send(
            f"🛑 Arena `{current_id}` cancelled. {cancellation_message} "
            "Crypto was unchanged."
        )

@bot.command(name="channel", aliases=["arenachannel"])
async def channel_command(ctx, action: str = None):
    """Restore the last arena channel permission snapshot."""
    if ctx.guild is None:
        return await ctx.send("Channel redo can only be used inside a server.")
    if ctx.guild.owner_id != ctx.author.id:
        return await ctx.send("Only the server owner can redo the arena channel permissions.")
    if str(action or "").casefold() != "redo":
        return await ctx.send("Use `uwu channel redo` to restore the last saved arena channel permissions.")
    _restored, response = await redo_arena_channel(ctx.guild)
    return await ctx.send(response)

@bot.command(name="paired")
async def paired(ctx, member: discord.Member = None, arena_code: str = None):
    """Pair a registered player into the same protected team."""
    if member is None:
        return await ctx.send(
            "Use `uwu paired @user` while both players are registered in the same arena."
        )
    if member.id == ctx.author.id:
        return await ctx.send("You cannot pair with yourself.")

    current_id, arena = find_arena_for_pair(
        ctx.author.id,
        member.id,
        arena_code,
    )
    if not arena:
        return await ctx.send(
            "Both players must be registered in the same active arena. "
            "You can add the arena ID after the mention if needed."
        )
    if arena.get("status") != "lobby":
        return await ctx.send("Pairing is only available before the arena starts.")

    team_size = int(arena["team_size"])
    if team_size == 1:
        return await ctx.send(
            "A 1v1 arena does not need pairing; each player is automatically on a separate team."
        )

    first_group = arena_group_for_user(arena, ctx.author.id)
    second_group = arena_group_for_user(arena, member.id)
    if first_group is not None and second_group is first_group:
        return await ctx.send("You are already paired on the same team.")
    if second_group is not None and first_group is not None:
        return await ctx.send(
            f"{member.mention} is already paired with another team. "
            "Paired teammates cannot be attacked or reassigned."
        )
    if first_group is None and second_group is not None:
        first_group = second_group
    elif first_group is None:
        open_groups = [
            group for group in arena.get("groups", [])
            if len(group) < team_size
        ]
        if len(open_groups) == 1:
            first_group = open_groups[0]
        elif len(arena.get("groups", [])) >= 2:
            return await ctx.send(
                "Both teams already have a group. Pair with a registered player "
                "from an open team."
            )
        else:
            first_group = [str(ctx.author.id)]
            arena.setdefault("groups", []).append(first_group)
    if len(first_group) >= team_size:
        return await ctx.send(
            f"Your team is already full at **{team_size}** players."
        )
    if str(ctx.author.id) not in first_group:
        first_group.append(str(ctx.author.id))
    if str(member.id) not in first_group:
        first_group.append(str(member.id))
    arena_rebuild_teams(arena)
    save_arenas()

    team_number = arena_team_index(arena, ctx.author.id)
    await ctx.send(
        f"✅ **Paired successful!** {ctx.author.mention} and {member.mention} "
        f"are protected teammates on **Team {team_number}**.\n"
        "You can enter the arena now when both teams are full.",
        embed=arena_embed(current_id, arena),
    )

@bot.command(name="prestige")
async def prestige(ctx, confirmation: str = None):
    """Reset spendable wealth for a permanent prestige level."""
    user = get_user(ctx.author.id)
    prestige_cost = 1_000_000_000_000
    if str(confirmation or "").casefold() != "confirm":
        return await ctx.send(
            f"Prestige costs **{format_coins(prestige_cost)} uwuncy** from your wallet/bank "
            "and resets both to zero. Crypto, inventory, properties, collectibles, "
            "achievements, and XP are preserved.\n"
            "Use `uwu prestige confirm` to continue."
        )
    if user_total_balance(user) < prestige_cost:
        return await ctx.send(
            f"You need **{format_coins(prestige_cost)} uwuncy** in wallet + bank to prestige."
        )
    user["wallet"] = 0
    user["bank"] = 0
    user["prestige"] += 1
    user["prestige_points"] += 1
    user["season_score"] += 250
    save_data(DATA)
    await ctx.send(
        f"🌟 **Prestige {user['prestige']} unlocked!**\n"
        "Wallet and bank were reset, but your crypto and permanent progress stayed safe."
    )

@bot.command(name="properties", aliases=["property"])
async def properties(ctx):
    user = get_user(ctx.author.id)
    owned = set(user.get("properties", []))
    lines = ["🏠 **Luxury Properties**"]
    for key, item in PROPERTY_SHOP.items():
        marker = "✅ OWNED" if key in owned else f"`{format_coins(item['price'])}` uwuncy"
        lines.append(f"- `{key}` — **{item['name']}** — {marker}\n  {item['description']}")
    lines.append("\nBuy with `uwu buyproperty <name>`.")
    return await ctx.send("\n".join(lines))

@bot.command(name="buyproperty")
async def buy_property(ctx, property_name: str = None):
    key = str(property_name or "").casefold()
    item = PROPERTY_SHOP.get(key)
    if not item:
        return await ctx.send(
            f"Choose a property: `{', '.join(PROPERTY_SHOP)}`. Use `uwu properties` to browse."
        )
    user = get_user(ctx.author.id)
    if key in user["properties"]:
        return await ctx.send("You already own that property.")
    if not debit_available_balance(user, item["price"]):
        return await ctx.send(
            f"You need **{format_coins(item['price'])} wallet + bank uwuncy**. "
            "Crypto holdings cannot pay for properties."
        )
    user["properties"].append(key)
    user["season_score"] += 50
    save_data(DATA)
    await ctx.send(
        f"🏠 Purchased **{item['name']}** for **{format_coins(item['price'])} uwuncy**.\n"
        f"{item['description']}"
    )

@bot.command(name="myproperty", aliases=["myproperties"])
async def my_property(ctx):
    user = get_user(ctx.author.id)
    owned = user.get("properties", [])
    if not owned:
        return await ctx.send("You do not own any properties yet. Use `uwu properties`.")
    names = [PROPERTY_SHOP[key]["name"] for key in owned if key in PROPERTY_SHOP]
    await ctx.send("🏠 **Your Properties**\n" + "\n".join(f"- {name}" for name in names))

@bot.command(name="collection", aliases=["collectibles", "museum"])
async def collection(ctx):
    user = get_user(ctx.author.id)
    owned = set(user.get("collection", []))
    lines = ["🏆 **Uwuncy Collection**"]
    for key, item in COLLECTIBLE_SHOP.items():
        marker = "✅ OWNED" if key in owned else f"`{format_coins(item['price'])}` uwuncy"
        lines.append(f"- `{key}` — **{item['name']}** — {marker}\n  {item['description']}")
    lines.append("\nBuy with `uwu buycollectible <name>`.")
    await ctx.send("\n".join(lines))

@bot.command(name="buycollectible")
async def buy_collectible(ctx, collectible_name: str = None):
    key = str(collectible_name or "").casefold()
    item = COLLECTIBLE_SHOP.get(key)
    if not item:
        return await ctx.send(
            f"Choose a collectible: `{', '.join(COLLECTIBLE_SHOP)}`. Use `uwu collection` to browse."
        )
    user = get_user(ctx.author.id)
    if key in user["collection"]:
        return await ctx.send("You already own that collectible.")
    if not debit_available_balance(user, item["price"]):
        return await ctx.send(
            f"You need **{format_coins(item['price'])} wallet + bank uwuncy**. "
            "Crypto holdings cannot pay for collectibles."
        )
    user["collection"].append(key)
    user["season_score"] += 75
    save_data(DATA)
    await ctx.send(
        f"🏆 Collected **{item['name']}** for **{format_coins(item['price'])} uwuncy**."
    )

@bot.command(name="season")
async def season(ctx):
    season_key = current_season_key()
    rows = season_rows()[:10]
    lines = [f"🌎 **Uwuncy Season {season_key}**", "Earn score by playing, winning, buying, and prestiging."]
    if not rows:
        lines.append("No season score yet.")
    else:
        for index, (user_id, score) in enumerate(rows, start=1):
            lines.append(f"**{index}.** <@{user_id}> — `{score}` season points")
    lines.append("Use `uwu seasonclaim` after the season closes or `uwu seasonrank` to see your rank.")
    await ctx.send("\n".join(lines))

@bot.command(name="seasonrank")
async def season_rank(ctx):
    rows = season_rows()
    user_id = str(ctx.author.id)
    rank = next((index for index, row in enumerate(rows, start=1) if row[0] == user_id), None)
    score = next((score for row_id, score in rows if row_id == user_id), 0)
    await ctx.send(
        f"🌎 **Season {current_season_key()} rank**\n"
        f"Rank: **{rank or 'Unranked'}**\n"
        f"Season points: **{score}**"
    )

@bot.command(name="seasonclaim")
async def season_claim(ctx):
    user = get_user(ctx.author.id)
    rows = season_rows()
    rank = next((index for index, row in enumerate(rows, start=1) if row[0] == str(ctx.author.id)), None)
    if rank not in {1, 2, 3}:
        return await ctx.send("Only the current Top 3 can claim a season podium reward.")
    if user.get("season_claimed"):
        return await ctx.send("You already claimed this season's reward.")
    reward, title = next((amount, title) for place, amount, title in SEASON_REWARDS if place == rank)
    credit_wallet(user, reward)
    user["season_claimed"] = True
    user["collection"].append(f"season-{current_season_key()}-{rank}")
    save_data(DATA)
    await ctx.send(
        f"🏅 Claimed **{title}** for rank **{rank}**: "
        f"**+{format_coins(reward)} uwuncy** and a permanent season collectible."
    )

@bot.command(name="clan")
async def clan_command(
    ctx,
    action: str = None,
    target: Union[discord.Member, str] = None,
    amount_text: str = None,
):
    action = str(action or "").casefold()
    user_id = str(ctx.author.id)
    user = get_user(ctx.author.id)
    clan_id = user.get("clan_id")
    clan = CLANS.get(clan_id) if clan_id else None

    if action == "create":
        if clan:
            return await ctx.send("You are already in a clan.")
        name = str(target or "").strip()
        if not name or len(name) > 24:
            return await ctx.send("Use `uwu clan create <name>` with a name up to 24 characters.")
        new_id = "CLAN-" + uuid.uuid4().hex[:6].upper()
        CLANS[new_id] = {
            "name": name,
            "owner_id": user_id,
            "members": [user_id],
            "invites": [],
            "treasury": 0,
            "upgrades": [],
        }
        user["clan_id"] = new_id
        save_data(DATA)
        save_clans()
        return await ctx.send(f"🛡️ Clan **{name}** created. Clan ID: `{new_id}`.")

    if action == "join":
        requested_clan = CLANS.get(str(target or "").upper())
        if not requested_clan:
            return await ctx.send("That clan ID does not exist.")
        if clan:
            return await ctx.send("Leave your current clan before joining another.")
        if user_id not in requested_clan.get("invites", []):
            return await ctx.send("You need an invite before joining this clan.")
        requested_clan["invites"].remove(user_id)
        requested_clan.setdefault("members", []).append(user_id)
        user["clan_id"] = str(target).upper()
        save_data(DATA)
        save_clans()
        return await ctx.send(f"✅ You joined clan **{requested_clan['name']}**.")

    if action == "invite":
        if not clan:
            return await ctx.send("Create or join a clan first.")
        if str(clan.get("owner_id")) != user_id:
            return await ctx.send("Only the clan owner can invite members.")
        if not isinstance(target, discord.Member):
            return await ctx.send("Use `uwu clan invite @user`.")
        invited = get_user(target.id)
        if invited.get("clan_id"):
            return await ctx.send("That user is already in a clan.")
        clan.setdefault("invites", []).append(str(target.id))
        save_clans()
        return await ctx.send(
            f"✅ Invited {target.mention}. They can use `uwu clan join {clan_id}`."
        )

    if action == "deposit":
        if not clan:
            return await ctx.send("Create or join a clan first.")
        amount = parse_coins(amount_text)
        if amount is None or amount <= 0:
            return await ctx.send("Use `uwu clan deposit <amount>`.")
        if not debit_available_balance(user, amount):
            return await ctx.send("You do not have enough wallet + bank uwuncy.")
        clan["treasury"] = int(clan.get("treasury", 0)) + amount
        save_data(DATA)
        save_clans()
        return await ctx.send(f"🏦 Deposited **{format_coins(amount)} uwuncy** into the clan treasury.")

    if action == "shop":
        if not clan:
            return await ctx.send("Create or join a clan first.")
        lines = [f"🛡️ **{clan['name']} Clan Upgrades**"]
        for key, upgrade in CLAN_UPGRADES.items():
            marker = "✅ OWNED" if key in clan.get("upgrades", []) else f"`{format_coins(upgrade['price'])}`"
            lines.append(f"- `{key}` — {marker} — {upgrade['description']}")
        lines.append("Clan owner purchases with `uwu clan buy <upgrade>`.")
        return await ctx.send("\n".join(lines))

    if action == "buy":
        if not clan:
            return await ctx.send("Create or join a clan first.")
        if str(clan.get("owner_id")) != user_id:
            return await ctx.send("Only the clan owner can buy clan upgrades.")
        key = str(target or "").casefold()
        upgrade = CLAN_UPGRADES.get(key)
        if not upgrade:
            return await ctx.send(f"Choose an upgrade: `{', '.join(CLAN_UPGRADES)}`.")
        if key in clan.get("upgrades", []):
            return await ctx.send("That clan upgrade is already owned.")
        if int(clan.get("treasury", 0)) < upgrade["price"]:
            return await ctx.send("The clan treasury cannot afford that upgrade.")
        clan["treasury"] -= upgrade["price"]
        clan.setdefault("upgrades", []).append(key)
        save_clans()
        return await ctx.send(f"🛡️ Clan upgrade **{key}** unlocked.")

    if action == "leave":
        if not clan:
            return await ctx.send("You are not in a clan.")
        if str(clan.get("owner_id")) == user_id:
            return await ctx.send("The clan owner must transfer ownership or disband the clan first.")
        clan["members"] = [member for member in clan_members(clan) if member != user_id]
        user["clan_id"] = ""
        save_data(DATA)
        save_clans()
        return await ctx.send("You left the clan.")

    if action in {"info", "status"}:
        if not clan:
            return await ctx.send("You are not in a clan.")
        members = ", ".join(f"<@{member}>" for member in clan_members(clan))
        return await ctx.send(
            f"🛡️ **{clan['name']}** (`{clan_id}`)\n"
            f"Owner: <@{clan['owner_id']}>\n"
            f"Members: {members}\n"
            f"Treasury: **{format_coins(clan.get('treasury', 0))} uwuncy**\n"
            f"Upgrades: {', '.join(clan.get('upgrades', [])) or 'None'}"
        )

    await ctx.send(
        "Clan commands: `uwu clan create <name>`, `invite @user`, `join <id>`, "
        "`deposit <amount>`, `shop`, `buy <upgrade>`, `info`, or `leave`."
    )

@bot.command(name="economystats", aliases=["economy", "econ"])
async def economy_stats(ctx, view: str = None):
    if not is_owner(ctx):
        return await ctx.send("Owner only.")
    if str(view or "").casefold() in {"users", "all", "accounts", "balances"}:
        rows = []
        for user_id, record in DATA.items():
            if not isinstance(record, dict):
                continue
            user = normalize_user(record)
            wallet = int(user.get("wallet", 0))
            bank = int(user.get("bank", 0))
            rows.append((str(user_id), wallet, bank, wallet + bank))
        rows.sort(key=lambda item: (-item[3], item[0]))
        if not rows:
            return await ctx.send("No economy accounts found.")
        chunks = []
        current = ["👑 **All User Economy Balances**"]
        for index, (user_id, wallet, bank, total) in enumerate(rows, start=1):
            line = (
                f"`{index}.` <@{user_id}> — "
                f"Wallet `{format_coins(wallet)}` • "
                f"Bank `{format_coins(bank)}` • "
                f"Total `{format_coins(total)}` uwuncy"
            )
            if sum(len(item) + 1 for item in current) + len(line) > 1800:
                chunks.append("\n".join(current))
                current = ["👑 **All User Economy Balances (continued)**"]
            current.append(line)
        if len(current) > 1:
            chunks.append("\n".join(current))
        for chunk in chunks:
            await ctx.send(chunk)
        return

    if str(view or "").casefold() in {"earnings", "income", "payouts", "profits", "wins"}:
        rows = []
        for user_id, record in DATA.items():
            if not isinstance(record, dict):
                continue
            user = normalize_user(record)
            _crypto_rows, crypto_invested, crypto_value, crypto_profit = crypto_portfolio(user)
            total_won = int(user.get("total_won", 0))
            total_lost = int(user.get("total_lost", 0))
            rows.append(
                (
                    str(user_id),
                    int(user.get("games_played", 0)),
                    int(user.get("games_won", 0)),
                    int(user.get("games_lost", 0)),
                    int(user.get("total_wagered", 0)),
                    total_won,
                    total_lost,
                    total_won - total_lost,
                    crypto_invested,
                    crypto_value,
                    crypto_profit,
                )
            )
        rows.sort(key=lambda item: (-item[7], -item[5], item[0]))
        if not rows:
            return await ctx.send("No economy earnings found.")

        total_games = sum(item[1] for item in rows)
        total_wins = sum(item[2] for item in rows)
        total_wagered = sum(item[4] for item in rows)
        total_won = sum(item[5] for item in rows)
        total_lost = sum(item[6] for item in rows)
        total_crypto_invested = sum(item[8] for item in rows)
        total_crypto_value = sum(item[9] for item in rows)
        total_crypto_profit = sum(item[10] for item in rows)
        chunks = []
        current = [
            "👑 **All User Economy Earnings**",
            (
                f"Games: `{total_games:,}` • Wins: `{total_wins:,}` • "
                f"Wagered: `{format_coins(total_wagered)}` uwuncy"
            ),
            (
                f"Game payouts: `+{format_coins(total_won)}` • "
                f"Recorded losses: `-{format_coins(total_lost)}` • "
                f"Game net: `{format_coins(total_won - total_lost)}` uwuncy"
            ),
            (
                f"Crypto invested: `{total_crypto_invested:,.2f}` • "
                f"Marked value: `{total_crypto_value:,.2f}` • "
                f"Unrealized P/L: `{total_crypto_profit:+,.2f}` uwuncy"
            ),
            "",
        ]
        for index, row in enumerate(rows, start=1):
            (
                user_id,
                games_played,
                games_won,
                games_lost,
                total_wagered_user,
                total_won_user,
                total_lost_user,
                game_net,
                crypto_invested_user,
                crypto_value_user,
                crypto_profit_user,
            ) = row
            line = (
                f"`{index}.` <@{user_id}> — "
                f"Games `{games_won}/{games_played}` won • "
                f"Paid `+{format_coins(total_won_user)}` • "
                f"Lost `-{format_coins(total_lost_user)}` • "
                f"Net `{format_coins(game_net)}`\n"
                f"   Wagered `{format_coins(total_wagered_user)}` • "
                f"Crypto invested `{crypto_invested_user:,.2f}` • "
                f"value `{crypto_value_user:,.2f}` • "
                f"P/L `{crypto_profit_user:+,.2f}`"
            )
            if sum(len(item) + 1 for item in current) + len(line) > 1800:
                chunks.append("\n".join(current))
                current = ["👑 **All User Economy Earnings (continued)**"]
            current.append(line)
        if len(current) > 1:
            chunks.append("\n".join(current))
        for chunk in chunks:
            await ctx.send(chunk)
        return

    users = [normalize_user(record) for record in DATA.values() if isinstance(record, dict)]
    wallet_total = sum(int(user["wallet"]) for user in users)
    bank_total = sum(int(user["bank"]) for user in users)
    crypto_total = sum(crypto_portfolio(user)[2] for user in users)
    spent_properties = sum(len(user.get("properties", [])) for user in users)
    collectibles = sum(len(user.get("collection", [])) for user in users)
    active_arenas = sum(1 for arena in ARENAS.values() if active_arena_status(arena))
    await ctx.send(
        "📊 **Uwuncy Economy Statistics**\n"
        f"Users: `{len(users):,}`\n"
        f"Wallet total: `{format_coins(wallet_total)}` uwuncy\n"
        f"Bank total: `{format_coins(bank_total)}` uwuncy\n"
        f"Crypto marked value: `{crypto_total:,.2f}` uwuncy\n"
        f"Properties owned: `{spent_properties:,}`\n"
        f"Collectibles owned: `{collectibles:,}`\n"
        f"Active arenas: `{active_arenas}`\n"
        f"Active clans: `{len(CLANS):,}`"
    )

@bot.command(name="servercount", aliases=["servers", "guildcount"])
async def server_count(ctx):
    """Show how many Discord servers the bot is currently connected to."""
    if not is_owner(ctx):
        return await ctx.send("Owner only.")
    guilds = sorted(bot.guilds, key=lambda guild: guild.name.casefold())
    if not guilds:
        return await ctx.send("The bot is currently connected to 0 servers.")

    chunks = []
    current = [f"👑 **UwU Bot Server Count: {len(guilds):,}**"]
    for index, guild in enumerate(guilds, start=1):
        member_count = guild.member_count if guild.member_count is not None else "unknown"
        line = f"`{index}.` **{guild.name}** — `{guild.id}` • `{member_count}` members"
        if sum(len(item) + 1 for item in current) + len(line) > 1800:
            chunks.append("\n".join(current))
            current = ["👑 **UwU Bot Servers (continued)**"]
        current.append(line)
    if len(current) > 1:
        chunks.append("\n".join(current))
    for chunk in chunks:
        await ctx.send(chunk)

@bot.command(name="antinuke")
async def antinuke(ctx, action: str = None):
    """Toggle anti-nuke protection in this server."""
    return await toggle_moderation_option(ctx, "antinuke", "Anti-nuke", action)

@bot.command(name="antispam")
async def antispam(ctx, action: str = None):
    """Toggle anti-spam protection in this server."""
    return await toggle_moderation_option(ctx, "antispam", "Anti-spam", action)

@bot.command(name="antiraid")
async def antiraid(ctx, action: str = None):
    """Toggle anti-raid protection in this server."""
    return await toggle_moderation_option(ctx, "antiraid", "Anti-raid", action)

@bot.command(name="antibullying", aliases=["anti-bullying", "antibully", "anti-bully", "anti"])
async def antibullying_cmd(ctx, sub_cmd: str = None, action: str = None):
    """Toggle sensitive anti-bullying protection in this server."""
    if is_category_disabled(ctx.guild, 'moderation'):
        return await ctx.send("**Moderation commands are currently disabled.**")

    act = action if sub_cmd and sub_cmd.lower() in ["bullying", "bully"] else sub_cmd
    return await toggle_moderation_option(ctx, "antibullying", "Anti-bullying", act)

@bot.command(name="setwelcome", aliases=["set_welcome", "welcomechannel", "welcomecard"])
async def setwelcome_cmd(ctx, target: str = None, channel: discord.TextChannel = None):
    """Server owner command to set or test the welcome card channel."""
    if ctx.guild is None:
        return await ctx.send("❌ This command can only be used inside a server.")
    if is_category_disabled(ctx.guild, 'moderation'):
        return await ctx.send("**Moderation commands are currently disabled.**")
    if ctx.author.id != ctx.guild.owner_id and not is_owner(ctx):
        return await ctx.send("❌ **Server Owner Only.** Only the server owner can configure the welcome channel.")

    settings = get_guild_moderation_settings(ctx.guild)

    if target and target.lower() in ["off", "disable", "none", "remove"]:
        settings["welcome_channel"] = None
        save_guild_moderation_settings(ctx.guild)
        return await ctx.send("❌ **Welcome channel disabled.** New members will no longer receive welcome cards.")

    if target and target.lower() in ["test", "preview", "check"]:
        w_channel_id = settings.get("welcome_channel")
        target_chan = ctx.guild.get_channel(w_channel_id) if w_channel_id else ctx.channel
        embed = build_welcome_embed(ctx.guild, ctx.author)
        try:
            await target_chan.send(f"👋 **[Welcome Preview]** Welcome to {ctx.guild.name}, {ctx.author.mention}!", embed=embed)
            if target_chan.id != ctx.channel.id:
                await ctx.send(f"✅ Welcome card preview sent to {target_chan.mention}!")
            return
        except Exception as e:
            return await ctx.send(f"❌ Failed to send preview: {e}")

    target_channel = channel
    if target_channel is None and ctx.message.channel_mentions:
        target_channel = ctx.message.channel_mentions[0]
    elif target_channel is None and target:
        if target.startswith("<#") and target.endswith(">"):
            try:
                chan_id = int(target.replace("<#", "").replace(">", ""))
                target_channel = ctx.guild.get_channel(chan_id)
            except Exception:
                pass
        elif target.isdigit():
            target_channel = ctx.guild.get_channel(int(target))

    if target_channel is None:
        current_id = settings.get("welcome_channel")
        current_chan = ctx.guild.get_channel(current_id) if current_id else None
        status = f"currently set to {current_chan.mention}" if current_chan else "currently **not set**"
        return await ctx.send(
            f"ℹ️ Welcome channel is {status}.\n\n"
            f"**Usage:**\n"
            f"• `uwu setwelcome #channel` — Set welcome channel\n"
            f"• `uwu setwelcome test` — Send a test welcome card preview\n"
            f"• `uwu setwelcome off` — Disable welcome cards"
        )

    settings["welcome_channel"] = target_channel.id
    save_guild_moderation_settings(ctx.guild)

    embed = build_welcome_embed(ctx.guild, ctx.author)
    await ctx.send(
        f"✅ **Welcome channel successfully set to {target_channel.mention}!**\n"
        f"Here is a preview of what new joiners will see:",
        embed=embed
    )

@bot.command(name="set")
async def set_cmd(ctx, sub_cmd: str = None, target: str = None, channel: discord.TextChannel = None):
    """Server setting management command."""
    if not sub_cmd:
        return await ctx.send("ℹ️ Usage: `uwu set welcome #channel`, `uwu set welcome test`, or `uwu set welcome off`.")
    clean_sub = sub_cmd.lower()
    if clean_sub in ["welcome", "welcomechannel", "welcome_channel", "card"]:
        return await setwelcome_cmd(ctx, target=target, channel=channel)
    elif clean_sub in ["invite", "invites", "invitechannel", "invlog"]:
        return await invites_cmd(ctx, option="set", channel_or_member=target)
    else:
        return await ctx.send(f"Unknown setting `{sub_cmd}`. Options: `welcome`, `invites`.")


@bot.command(name="invites", aliases=["invs", "invite", "invboard", "topinvites", "invleaderboard"])
async def invites_cmd(ctx, option: str = None, channel_or_member: str = None):
    """Single unified command to view invite leaderboards, user stats, sync, or configure invite tracking channel."""
    if ctx.guild is None:
        return await ctx.send("❌ This command can only be used inside a server.")
    if is_category_disabled(ctx.guild, 'moderation'):
        return await ctx.send("**Moderation commands are currently disabled.**")

    settings = get_guild_moderation_settings(ctx.guild)

    # Subcommand 1: set channel (e.g. `uwu invites set #channel` or `uwu invites #channel`)
    if (option and option.lower() in ["set", "channel", "setup", "log"]) or (option and option.startswith("<#")):
        if not (ctx.author.guild_permissions.manage_guild or ctx.author.id == ctx.guild.owner_id or is_owner(ctx)):
            return await ctx.send("❌ You need **Manage Server** permission to configure invite tracking channel.")

        target_chan = None
        target_str = channel_or_member if (option in ["set", "channel", "setup", "log"]) else option

        if ctx.message.channel_mentions:
            target_chan = ctx.message.channel_mentions[0]
        elif target_str and target_str.startswith("<#"):
            try:
                cid = int(target_str.replace("<#", "").replace(">", ""))
                target_chan = ctx.guild.get_channel(cid)
            except Exception:
                pass
        elif target_str and target_str.isdigit():
            target_chan = ctx.guild.get_channel(int(target_str))

        if not target_chan:
            curr_id = settings.get("invite_channel")
            curr_chan = ctx.guild.get_channel(curr_id) if curr_id else None
            status_str = f"currently set to {curr_chan.mention}" if curr_chan else "currently **not configured**"
            return await ctx.send(f"ℹ️ Invite tracking log channel is {status_str}.\n**Usage:** `uwu invites set #channel` or `uwu invites off`.")

        settings["invite_channel"] = target_chan.id
        save_guild_moderation_settings(ctx.guild)
        return await ctx.send(f"✅ **Invite log channel successfully set to {target_chan.mention}!** The bot will announce who invited new members here.")

    # Subcommand 2: turn off (e.g. `uwu invites off` / `disable`)
    if option and option.lower() in ["off", "disable", "none", "remove"]:
        if not (ctx.author.guild_permissions.manage_guild or ctx.author.id == ctx.guild.owner_id or is_owner(ctx)):
            return await ctx.send("❌ You need **Manage Server** permission to disable invite tracking.")
        settings["invite_channel"] = None
        save_guild_moderation_settings(ctx.guild)
        return await ctx.send("❌ **Invite tracking log channel disabled.**")

    # Subcommand 3: sync (e.g. `uwu invites sync`)
    if option and option.lower() in ["sync", "resync"]:
        if not (ctx.author.guild_permissions.manage_guild or ctx.author.id == ctx.guild.owner_id or is_owner(ctx)):
            return await ctx.send("❌ You need **Manage Server** permission to sync invites.")
        msg = await ctx.send("🔄 **Syncing server invites with Discord API...**")
        cache = await fetch_and_cache_guild_invites(ctx.guild)
        return await msg.edit(content=f"✅ **Synced `{len(cache)}` active invite code(s) for {ctx.guild.name}!** Invite counter is live and active.")

    # Subcommand 4: Check individual member invite stats (e.g. `uwu invites @user`)
    target_member = None
    if option:
        try:
            target_member = await commands.MemberConverter().convert(ctx, option)
        except Exception:
            pass

    if target_member:
        g_store = get_invite_store(ctx.guild.id)
        inv_stats = g_store["inviters"].get(str(target_member.id), {"regular": 0, "left": 0, "fake": 0})
        regular = inv_stats.get("regular", 0)
        left = inv_stats.get("left", 0)
        fake = inv_stats.get("fake", 0)
        net = regular - left - fake

        embed = discord.Embed(
            title=f"✉️ Invite Statistics — {target_member.display_name}",
            color=discord.Color.blue()
        )
        if hasattr(target_member, "display_avatar") and target_member.display_avatar:
            embed.set_thumbnail(url=target_member.display_avatar.url)

        embed.add_field(
            name="Invite Summary",
            value=(
                f"• **Regular Joins:** {regular}\n"
                f"• **Members Left:** {left}\n"
                f"• **Fake / Alts:** {fake}\n"
                f"• **Net Total Invites:** **{net}**"
            ),
            inline=False
        )
        return await ctx.send(embed=embed)

    # Default / Leaderboard: `uwu invites` or `uwu invites leaderboard`
    g_store = get_invite_store(ctx.guild.id)
    inviters = g_store.get("inviters", {})

    leaderboard = []
    for user_id, stats in inviters.items():
        reg = stats.get("regular", 0)
        left = stats.get("left", 0)
        fake = stats.get("fake", 0)
        net = reg - left - fake
        if net != 0 or reg > 0:
            leaderboard.append((user_id, net, reg, left, fake))

    leaderboard.sort(key=lambda x: x[1], reverse=True)

    curr_id = settings.get("invite_channel")
    curr_chan = ctx.guild.get_channel(curr_id) if curr_id else None
    chan_info = f"Log Channel: {curr_chan.mention}" if curr_chan else "Log Channel: *Not set* (`uwu invites set #channel`)"

    embed = discord.Embed(
        title=f"🏆 Top Server Inviters — {ctx.guild.name}",
        description=f"📌 {chan_info}\n\n",
        color=discord.Color.gold()
    )

    if not leaderboard:
        embed.description += "No active invites tracked yet. Invite friends using a server invite link!"
    else:
        lines = []
        medals = ["🥇", "🥈", "🥉"]
        for i, (uid, net, reg, left, fake) in enumerate(leaderboard[:10], start=1):
            prefix = medals[i-1] if i <= 3 else f"`#{i}`"
            lines.append(f"{prefix} <@{uid}> — **{net}** invites (`{reg}` joined, `{left}` left)")
        embed.description += "\n".join(lines)

    embed.set_footer(text="Commands: uwu invites [@user] | uwu invites set #channel | uwu invites sync")
    await ctx.send(embed=embed)

@bot.command(name="kick")
async def kick_user(ctx, member: discord.Member = None, *, reason: str = "No reason provided"):
    """Kick a member from the server."""
    if ctx.guild is None:
        return await ctx.send("❌ This command can only be used inside a server.")
    if is_category_disabled(ctx.guild, 'moderation'):
        return await ctx.send("**Moderation commands are currently disabled.**")
    if not (ctx.author.guild_permissions.kick_members or ctx.author.id == ctx.guild.owner_id or is_owner(ctx)):
        return await ctx.send("❌ You need **Kick Members** permission to use this command.")
    if member is None:
        return await ctx.send("ℹ️ **Usage:** `uwu kick @user [reason]`")
    if member.id == ctx.guild.owner_id:
        return await ctx.send("❌ You cannot kick the server owner.")
    if member.id == ctx.author.id:
        return await ctx.send("❌ You cannot kick yourself.")
    if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id and not is_owner(ctx):
        return await ctx.send("❌ You cannot kick someone with an equal or higher role than you.")
    
    try:
        await member.kick(reason=f"Kicked by {ctx.author}: {reason}")
        await ctx.send(f"👢 **Kicked {member.mention}** (`{member.id}`). Reason: *{reason}*")
        await log_moderation_action(ctx.guild, f"Kicked: {member} ({member.id}) by {ctx.author}. Reason: {reason}")
    except discord.Forbidden:
        await ctx.send("❌ I do not have permission to kick this member.")
    except Exception as e:
        await ctx.send(f"❌ Failed to kick member: {e}")


@bot.command(name="ban")
async def ban_user(ctx, member: discord.Member = None, *, reason: str = "No reason provided"):
    """Ban a user from the server."""
    if ctx.guild is None:
        return await ctx.send("This command can only be used inside a server.")
    if is_category_disabled(ctx.guild, 'moderation'):
        return await ctx.send("**Moderation commands are currently disabled.**")
    if not (ctx.author.guild_permissions.ban_members or ctx.author.id == ctx.guild.owner_id or is_owner(ctx)):
        return await ctx.send("❌ You need **Ban Members** permission to use this command.")
    if member is None:
        return await ctx.send("Use `uwu ban @user [reason]`.")
    if member.id == ctx.guild.owner_id:
        return await ctx.send("❌ I cannot ban the server owner.")
    if member.id == ctx.author.id:
        return await ctx.send("❌ You cannot ban yourself.")
    if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id and not is_owner(ctx):
        return await ctx.send("❌ You cannot ban someone with an equal or higher role than you.")
    if await ban_user_for_moderation(ctx.guild, member, reason):
        await ctx.send(f"✅ Banned {member.mention}. Reason: {reason}")
    else:
        await ctx.send(
            "❌ Could not ban that user. Check bot permissions and target validity."
        )


@bot.command(name="unban")
async def unban_user(ctx, user_id: str = None, *, reason: str = "No reason provided"):
    """Unban a user by ID or tag."""
    if ctx.guild is None:
        return await ctx.send("This command can only be used inside a server.")
    if is_category_disabled(ctx.guild, 'moderation'):
        return await ctx.send("**Moderation commands are currently disabled.**")
    if not (ctx.author.guild_permissions.ban_members or ctx.author.id == ctx.guild.owner_id or is_owner(ctx)):
        return await ctx.send("❌ You need **Ban Members** permission to use this command.")
    if user_id is None:
        return await ctx.send("ℹ️ **Usage:** `uwu unban <user_id_or_tag> [reason]`")
    
    try:
        ban_entries = [entry async for entry in ctx.guild.bans()]
        target_user = None
        for ban_entry in ban_entries:
            u = ban_entry.user
            if str(u.id) == user_id or f"{u.name}#{u.discriminator}" == user_id or u.name == user_id:
                target_user = u
                break
        
        if target_user is None and user_id.isdigit():
            try:
                target_user = await bot.fetch_user(int(user_id))
            except Exception:
                pass
            
        if target_user:
            await ctx.guild.unban(target_user, reason=f"Unbanned by {ctx.author}: {reason}")
            await ctx.send(f"✅ **Unbanned {target_user.mention}** (`{target_user.id}`).")
            await log_moderation_action(ctx.guild, f"Unbanned: {target_user} ({target_user.id}) by {ctx.author}. Reason: {reason}")
        else:
            await ctx.send(f"❌ User `{user_id}` not found in the ban list.")
    except discord.Forbidden:
        await ctx.send("❌ I don't have Ban Members permission.")
    except Exception as e:
        await ctx.send(f"❌ Failed to unban: {e}")


@bot.command(name="mute", aliases=["timeout", "tempmute"])
async def mute_user(ctx, member: discord.Member = None, duration: str = "10m", *, reason: str = "No reason provided"):
    """Timeout / Mute a member for a specified duration (e.g. 10m, 1h, 1d)."""
    if ctx.guild is None:
        return await ctx.send("❌ This command can only be used inside a server.")
    if is_category_disabled(ctx.guild, 'moderation'):
        return await ctx.send("**Moderation commands are currently disabled.**")
    if not (ctx.author.guild_permissions.moderate_members or ctx.author.guild_permissions.kick_members or ctx.author.id == ctx.guild.owner_id or is_owner(ctx)):
        return await ctx.send("❌ You need **Timeout/Moderate Members** permission to use this command.")
    if member is None:
        return await ctx.send("ℹ️ **Usage:** `uwu mute @user [duration] [reason]` (e.g. `uwu mute @user 10m spamming`)")
    if member.id == ctx.guild.owner_id:
        return await ctx.send("❌ You cannot mute the server owner.")
    if member.id == ctx.author.id:
        return await ctx.send("❌ You cannot mute yourself.")
    if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id and not is_owner(ctx):
        return await ctx.send("❌ You cannot mute someone with an equal or higher role than you.")
    
    try:
        seconds = parse_duration_to_seconds(duration)
        if seconds <= 0:
            return await ctx.send("❌ Invalid duration. Use e.g. `10m`, `1h`, `1d`.")
        if seconds > 28 * 86400:
            return await ctx.send("❌ Timeout duration cannot exceed 28 days.")
        
        td = timedelta(seconds=seconds)
        await member.timeout(td, reason=f"Muted by {ctx.author}: {reason}")
        await ctx.send(f"🔇 **Timed out {member.mention}** for **{duration}**. Reason: *{reason}*")
        await log_moderation_action(ctx.guild, f"Muted: {member} ({member.id}) for {duration} by {ctx.author}. Reason: {reason}")
    except discord.Forbidden:
        await ctx.send("❌ I do not have permission to timeout this member.")
    except Exception as e:
        await ctx.send(f"❌ Failed to timeout member: {e}")


@bot.command(name="unmute", aliases=["untimeout"])
async def unmute_user(ctx, member: discord.Member = None, *, reason: str = "No reason provided"):
    """Remove timeout / unmute a member."""
    if ctx.guild is None:
        return await ctx.send("❌ This command can only be used inside a server.")
    if is_category_disabled(ctx.guild, 'moderation'):
        return await ctx.send("**Moderation commands are currently disabled.**")
    if not (ctx.author.guild_permissions.moderate_members or ctx.author.guild_permissions.kick_members or ctx.author.id == ctx.guild.owner_id or is_owner(ctx)):
        return await ctx.send("❌ You need **Timeout/Moderate Members** permission to use this command.")
    if member is None:
        return await ctx.send("ℹ️ **Usage:** `uwu unmute @user [reason]`")
    
    try:
        await member.timeout(None, reason=f"Unmuted by {ctx.author}: {reason}")
        await ctx.send(f"🔊 **Removed timeout from {member.mention}**.")
        await log_moderation_action(ctx.guild, f"Unmuted: {member} ({member.id}) by {ctx.author}. Reason: {reason}")
    except discord.Forbidden:
        await ctx.send("❌ I do not have permission to remove timeout from this member.")
    except Exception as e:
        await ctx.send(f"❌ Failed to unmute member: {e}")


@bot.command(name="purge", aliases=["clear", "clean"])
async def purge_messages(ctx, amount: int = None):
    """Purge / clear messages from the current channel."""
    if ctx.guild is None:
        return await ctx.send("❌ This command can only be used inside a server.")
    if is_category_disabled(ctx.guild, 'moderation'):
        return await ctx.send("**Moderation commands are currently disabled.**")
    if not (ctx.author.guild_permissions.manage_messages or ctx.author.id == ctx.guild.owner_id or is_owner(ctx)):
        return await ctx.send("❌ You need **Manage Messages** permission to use this command.")
    if amount is None or amount <= 0:
        return await ctx.send("ℹ️ **Usage:** `uwu purge <amount>` (e.g. `uwu purge 20`)")
    if amount > 100:
        amount = 100
    
    try:
        deleted = await ctx.channel.purge(limit=amount + 1)
        count = max(0, len(deleted) - 1)
        confirm = await ctx.send(f"🧹 **Cleared {count} message(s).**")
        await asyncio.sleep(4)
        try:
            await confirm.delete()
        except Exception:
            pass
        await log_moderation_action(ctx.guild, f"Purged {count} messages in #{ctx.channel.name} by {ctx.author}")
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to manage/delete messages in this channel.")
    except Exception as e:
        await ctx.send(f"❌ Failed to purge messages: {e}")


@bot.command(name="warn")
async def warn_user(ctx, member: discord.Member = None, *, reason: str = "No reason provided"):
    """Issue a warning to a server member."""
    if ctx.guild is None:
        return await ctx.send("❌ This command can only be used inside a server.")
    if is_category_disabled(ctx.guild, 'moderation'):
        return await ctx.send("**Moderation commands are currently disabled.**")
    if not (ctx.author.guild_permissions.manage_messages or ctx.author.guild_permissions.kick_members or ctx.author.id == ctx.guild.owner_id or is_owner(ctx)):
        return await ctx.send("❌ You need **Manage Messages** or **Kick Members** permission to warn members.")
    if member is None:
        return await ctx.send("ℹ️ **Usage:** `uwu warn @user [reason]`")
    if member.id == ctx.guild.owner_id or member.id == ctx.author.id or member.bot:
        return await ctx.send("❌ Cannot warn this user.")
    
    settings = get_guild_moderation_settings(ctx.guild)
    warns = settings.setdefault("warnings", {})
    user_warns = warns.setdefault(str(member.id), [])
    
    warn_entry = {
        "reason": reason,
        "moderator": ctx.author.display_name,
        "moderator_id": ctx.author.id,
        "timestamp": int(datetime.now(timezone.utc).timestamp())
    }
    user_warns.append(warn_entry)
    save_guild_moderation_settings(ctx.guild)
    
    total = len(user_warns)
    embed = discord.Embed(
        title="⚠️ Member Warned",
        description=f"{member.mention} has received a warning.",
        color=discord.Color.orange()
    )
    embed.add_field(name="User", value=f"{member.display_name} (`{member.id}`)", inline=True)
    embed.add_field(name="Total Warnings", value=f"**{total}**", inline=True)
    embed.add_field(name="Reason", value=reason, inline=False)
    embed.set_footer(text=f"Warned by {ctx.author.display_name}")
    
    await ctx.send(embed=embed)
    await log_moderation_action(ctx.guild, f"Warned: {member} ({member.id}) by {ctx.author}. Total warns: {total}. Reason: {reason}")


@bot.command(name="clearwarns", aliases=["rmwarn", "delwarns"])
async def clearwarns_cmd(ctx, member: discord.Member = None):
    """Clear all warnings for a member."""
    if ctx.guild is None:
        return await ctx.send("❌ This command can only be used inside a server.")
    if is_category_disabled(ctx.guild, 'moderation'):
        return await ctx.send("**Moderation commands are currently disabled.**")
    if not (ctx.author.guild_permissions.manage_messages or ctx.author.id == ctx.guild.owner_id or is_owner(ctx)):
        return await ctx.send("❌ You need **Manage Messages** permission to clear warnings.")
    if member is None:
        return await ctx.send("ℹ️ **Usage:** `uwu clearwarns @user`")
    
    settings = get_guild_moderation_settings(ctx.guild)
    warns = settings.setdefault("warnings", {})
    if str(member.id) in warns and warns[str(member.id)]:
        count = len(warns[str(member.id)])
        warns[str(member.id)] = []
        save_guild_moderation_settings(ctx.guild)
        await ctx.send(f"✅ **Cleared `{count}` warning(s) for {member.mention}.**")
        await log_moderation_action(ctx.guild, f"Cleared {count} warnings for {member} ({member.id}) by {ctx.author}")
    else:
        await ctx.send(f"ℹ️ {member.mention} has no warnings to clear.")


@bot.command(name="nick", aliases=["nickname", "setnick"])
async def nickname_cmd(ctx, member: discord.Member = None, *, new_nick: str = None):
    """Change or reset a member's nickname."""
    if ctx.guild is None:
        return await ctx.send("❌ This command can only be used inside a server.")
    if is_category_disabled(ctx.guild, 'moderation'):
        return await ctx.send("**Moderation commands are currently disabled.**")
    if not (ctx.author.guild_permissions.manage_nicknames or ctx.author.id == ctx.guild.owner_id or is_owner(ctx)):
        return await ctx.send("❌ You need **Manage Nicknames** permission to use this command.")
    if member is None:
        return await ctx.send("ℹ️ **Usage:** `uwu nick @user [new nickname]`")
    
    try:
        await member.edit(nick=new_nick, reason=f"Nickname changed by {ctx.author}")
        if new_nick:
            await ctx.send(f"🏷️ Changed nickname for {member.mention} to **{new_nick}**.")
        else:
            await ctx.send(f"🏷️ Reset nickname for {member.mention}.")
        await log_moderation_action(ctx.guild, f"Changed nickname for {member} ({member.id}) to '{new_nick}' by {ctx.author}")
    except discord.Forbidden:
        await ctx.send("❌ I do not have permission to change this member's nickname.")
    except Exception as e:
        await ctx.send(f"❌ Failed to change nickname: {e}")

@bot.command(name="rollback")
async def rollback(ctx):
    """Rollback recent suspicious activity by deleting tracked messages."""
    if ctx.guild is None:
        return await ctx.send("This command can only be used inside a server.")
    if ctx.author.id != ctx.guild.owner_id and not is_owner(ctx):
        return await ctx.send("Owner only.")
    suspects = build_suspicious_user_ids(ctx.guild)
    if not suspects:
        return await ctx.send("No suspicious users are currently tracked for rollback.")
    deleted, cleanup = delete_suspicious_messages(ctx.guild, suspects)
    await cleanup
    suspect_names = format_suspect_names(ctx.guild, suspects)
    await ctx.send(
        f"🔁 Rollback complete. Deleted messages from {len(suspects)} suspect accounts: {', '.join(suspect_names)}."
    )

@bot.command(name="prefix")
async def change_prefix(ctx,new=None):
    await ctx.send("The bot prefix is fixed at `uwu`.")

@bot.command(name="off")
async def disable_category_cmd(ctx, category: str):
    """Owner-only command to disable a command category for all users."""
    if not is_owner(ctx):
        return await ctx.send("Owner only.")
    normalized, display = normalize_category(category)
    if not normalized:
        return await ctx.send("Use `uwu off <category>` such as `socials` or `gambling`.")
    await set_category_state(ctx, normalized, False)
    embed = discord.Embed(
        title="🔒 Category Disabled",
        description=f"**{display}** commands have been turned **off** by **{ctx.author.display_name}**.",
        color=discord.Color.gold(),
    )
    await ctx.send(embed=embed)

@bot.command(name="on")
async def enable_category_cmd(ctx, category: str):
    """Owner-only command to re-enable a disabled command category."""
    if not is_owner(ctx):
        return await ctx.send("Owner only.")
    normalized, display = normalize_category(category)
    if not normalized:
        return await ctx.send("Use `uwu on <category>` such as `socials` or `gambling`.")
    await set_category_state(ctx, normalized, True)
    embed = discord.Embed(
        title="✅ Category Enabled",
        description=f"**{display}** commands have been turned **on** by **{ctx.author.display_name}**.",
        color=discord.Color.green(),
    )
    await ctx.send(embed=embed)

@bot.command(name="help")
async def help_cmd(ctx, category: str = None):
    p = get_prefix()
    user_data = get_user(ctx.author.id)
    is_booster = booster_utils.is_server_booster(ctx.author, user_data, guild=ctx.guild)
    if is_booster and not user_data.get("is_booster"):
        user_data["is_booster"] = True
        save_data(DATA)
    guild_name = ctx.guild.name if ctx.guild else "our server"

    HELP_CATEGORIES = {
        "booster": {
            "title": "💎 Server Booster Exclusive Commands",
            "aliases": ["boost", "boosters", "serverbooster", "boosterhelp"],
            "items": [
                ("booster", "claim daily 5T uwuncy reward & view booster multipliers"),
                ("boosters", "view active server boosters & server boost tier level"),
                ("booster shop", "browse exclusive booster items & passes catalog"),
                ("booster buy <item_id>", "purchase booster items with uwuncy"),
            ],
            "desc": "Commands and daily benefits reserved exclusively for Server Boosters."
        },
        "economy": {
            "title": "💰 Economy",
            "aliases": ["econ", "wallet", "bank"],
            "items": [
                ("claim", "claim hourly uwuncy reward"),
                ("daily", "claim daily uwuncy streak"),
                ("money", "bal / balance — check wallet & bank"),
                ("info", "userinfo — check user profile & stats"),
                ("deposit", "dep <amount|all> — deposit into bank"),
                ("withdraw", "with <amount|all> — withdraw from bank"),
                ("give", "pay @user <amount> — transfer uwuncy"),
                ("history", "bets / recent — transaction history"),
                ("achievements", "ach / badges — view unlocked badges"),
                ("quests", "quest / missions — daily & weekly quests"),
                ("jackpot", "view server jackpot pool & entries"),
                ("hunt", "hunt for wild animals & rewards"),
                ("huntinfo", "huntlevel / huntstats — hunting level"),
                ("leaderboard", "lb / top — view global rankings"),
                ("crypwuncy", "crypto / market — live crypto prices"),
                ("invest", "invest in crypto coins"),
                ("sell", "cashout / sellcrypto — sell investments"),
                ("investments", "portfolio / invested — view holdings"),
                ("shop", "store — view global shop catalog"),
                ("buy", "buy item from shop"),
                ("inventory", "inv — view inventory items"),
            ],
        },
        "gambling": {
            "title": "🎰 Gambling & Games",
            "aliases": ["games", "casino", "betting"],
            "items": [
                ("cf", "coinflip <amount> <heads|tails>"),
                ("slot", "slots <amount>"),
                ("bj", "blackjack <amount>"),
                ("colorgame", "cg <amount> <red|blue|yellow|etc>"),
                ("mines", "m <amount> [mines_count]"),
                ("dice", "roll <amount> <over|under> <number>"),
                ("highlow", "hl <amount>"),
                ("rr", "roulette <amount> <red|black|number>"),
                ("crash", "rocket <amount>"),
                ("tower", "climb <amount>"),
                ("wheel", "spin <amount>"),
                ("ladder", "chain <amount>"),
                ("scratch", "sc <amount>"),
                ("sabong", "cockfight / tari <amount> <wala|meron>"),
            ],
        },
        "social": {
            "title": "💬 Social & Marriage",
            "aliases": ["profile", "socials"],
            "items": [
                ("profile", "[@user] — view custom social profile"),
                ("avatar", "av [@user] — view high-res avatar"),
                ("banner", "[@user] — view server/user banner"),
                ("ig", ",ig — view linked Instagram"),
                ("tt", ",tt — view linked TikTok"),
                ("fb", ",fb — view linked Facebook"),
                ("marry", "@user — propose marriage to user"),
                ("divorce", "end marriage status"),
                ("ship", "@user @user — check love compatibility"),
            ],
        },
        "music": {
            "title": "🎵 Music & Voice",
            "aliases": ["audio", "dj"],
            "items": [
                ("!play", "<link|search> — play music in voice channel"),
                ("pause", "pause playback"),
                ("resume", "resume playback"),
                ("skip", "skip current track"),
                ("stop", "stop music & disconnect"),
                ("volume", "[1-100] — set music volume"),
                ("lyrics", "[song name] — search song lyrics"),
                ("save", "[name] — save track to playlist"),
            ],
        },
        "moderation": {
            "title": "🛡️ Moderation & Server Protection",
            "aliases": ["mod"],
            "items": [
                ("kick", "@user [reason] — kick member"),
                ("ban", "@user [reason] — ban member"),
                ("unban", "<user_id_or_tag> [reason] — unban member"),
                ("mute", "@user [duration] [reason] — mute member"),
                ("unmute", "@user [reason] — unmute member"),
                ("purge", "<amount> — bulk delete messages"),
                ("warn", "@user [reason] — warn member"),
                ("clearwarns", "@user — clear warnings"),
                ("nick", "@user [nickname] — change nickname"),
                ("setwelcome", "#channel / test / off — welcome logs"),
                ("invites", "[@user | set #channel | sync] — invite tracking"),
                ("antinuke", "on/off — antinuke protection"),
                ("antispam", "on/off — antispam filter"),
                ("antiraid", "on/off — antiraid shield"),
                ("antibullying", "on/off — antibullying filter"),
                ("rollback", "restore recent server actions"),
                ("lock", "lock channel"),
                ("unlock", "unlock channel"),
                ("modlog set", "clear — set mod logging channel"),
                ("whitelist add", "remove — manage admin whitelist"),
            ],
        },
        "admin": {
            "title": "👑 Admin & Owner",
            "aliases": ["owner", "admin"],
            "items": [
                ("setclaim", "claimamount / claiminfo"),
                ("economystats", "economy / econ"),
                ("cryptocontrol", "cryptoset / cryptoadmin"),
                ("cryptopause", "marketpause"),
                ("odds", "setodds / chance"),
                ("userodds", "userchance / setuserodds"),
                ("betlimits", "setbetlimits / gamebets"),
                ("betcap", "maxbet"),
                ("setjackpot", ""),
                ("addcoins", "giveadmin"),
                ("removecoins", "takecoins"),
                ("setcoins", "setbal"),
                ("resetuser", "wipeuser"),
                ("resetstreak", ""),
                ("resetuwuncy", "clearuwuncy / wipeuwuncy"),
                ("apify", "apifybalance / apifystats"),
            ],
        },
    }

    def format_command(name, alias_text):
        if alias_text:
            return f"- `{p}{name}` ({alias_text})"
        return f"- `{p}{name}`"

    def format_category(name, category_dict):
        lines = [f"__{category_dict['title']}__"]
        lines.extend(format_command(cmd, alias) for cmd, alias in category_dict['items'])
        return lines

    def split_chunks(lines):
        chunks = []
        current = ""
        for line in lines:
            if len(current) + len(line) + 1 > 1900:
                chunks.append(current)
                current = line
            else:
                current = f"{current}\n{line}" if current else line
        if current:
            chunks.append(current)
        return chunks

    requested = category.strip().lower() if category else None
    available_categories = []
    
    order = ["booster", "economy", "gambling", "social", "music", "moderation", "admin"]
    for key in order:
        if key in HELP_CATEGORIES:
            if key == "admin":
                if is_owner(ctx):
                    available_categories.append(key)
            else:
                available_categories.append(key)

    if not requested:
        if is_booster:
            lines = [
                f"💎 ════════════════════════════════════════ 💎",
                f"⚡ **VIP SERVER BOOSTER HELP MENU** ⚡",
                f"Thank you {ctx.author.mention} for boosting **{guild_name}**!",
                f"💎 ════════════════════════════════════════ 💎",
                f"",
                f"✨ **YOUR ACTIVE BOOSTER ADVANTAGES & PERKS:**",
                f"• 🎁 **Daily Reward:** `+5,000,000,000,000 (5T) uwuncy` (`{p}booster`)",
                f"• ⚡ **Command Cooldowns:** `BYPASSED (0s cooldowns on all commands)`",
                f"• 🖼️ **Links & Media:** `BYPASSED` in restricted channels",
                f"• 🛒 **Booster Shop Catalog:** `UNLOCKED` (`{p}booster shop`)",
                f"• 💎 **Server Boost Count:** `{booster_utils.get_user_boost_count(ctx.author)} Boost(s)`",
                f"",
                f"Use `{p}help <category>` to view a specific section.",
                f""
            ]
        else:
            lines = [
                f"🤖 **UwU Bot Help Menu** for {ctx.author.display_name}",
                f"Prefix: `{p}`",
                f"",
                f"💎 **BOOST OUR SERVER FOR EXCLUSIVE PERKS!**",
                f"Boost **{guild_name}** to unlock **5T daily uwuncy**, **0s command cooldowns**, and the **VIP Booster Help Menu**! (`{p}boosters` / `{p}booster`)",
                f"",
                f"Use `{p}help <category>` to view a specific section.",
                f""
            ]

        for key in available_categories:
            cat_obj = HELP_CATEGORIES[key]
            if is_booster and key == "booster":
                lines.append("⚡ **SERVER BOOSTER EXCLUSIVE COMMANDS**")
                for cmd, alias in cat_obj['items']:
                    lines.append(f"• `{p}{cmd}` — {alias}")
                lines.append("")
            else:
                lines.extend(format_category(key, cat_obj))
                lines.append("")

        for chunk in split_chunks(lines):
            await ctx.send(chunk)
        return

    matched_key = None
    for key, cat_obj in HELP_CATEGORIES.items():
        if requested == key or requested in cat_obj["aliases"]:
            matched_key = key
            break

    if matched_key is None or matched_key not in available_categories:
        valid = ", ".join(HELP_CATEGORIES[key]["title"] for key in available_categories)
        return await ctx.send(
            f"Unknown help category `{category}`. Valid categories: {valid}."
        )

    cat_obj = HELP_CATEGORIES[matched_key]
    if is_booster and matched_key == "booster":
        lines = [
            f"💎 **VIP SERVER BOOSTER COMMANDS & BENEFITS** 💎",
            f"Special perks unlocked for boosting **{guild_name}**:",
            f"",
            f"• `{p}booster` (or `{p}booster claim`) — Claim your daily **5T uwuncy** + stacking boost multipliers.",
            f"• `{p}boosters` (or `{p}boosterlist`) — View all server boosters & current server boost level.",
            f"• `{p}booster shop` — Browse the booster shop catalog (Cooldown Skips, Auto-Claim Passes, 2x Earnings).",
            f"• `{p}booster buy <item_id>` — Buy exclusive booster items with uwuncy.",
            f"",
            f"⚡ **Booster Passive Perks:**",
            f"• **0 Command Cooldowns**: Bypasses all standard command cooldown limits.",
            f"• **Auto-Claim Pass**: Automatically collects your 5T daily reward when chatting.",
            f"• **Filter Bypass**: Bypasses link and image filters in restricted channels."
        ]
    else:
        lines = [f"UwU Help — {cat_obj['title']}", ""]
        if is_booster:
            lines.append("⚡ *As a Server Booster, all command cooldowns are 0 seconds for you!*")
            lines.append("")
        lines.extend(format_category(matched_key, cat_obj))

    for chunk in split_chunks(lines):
        await ctx.send(chunk)


# ==============================================
# 👑 ADMIN COMMANDS
# ==============================================
@bot.command(name="cryptocontrol", aliases=["cryptoset", "cryptoadmin"])
async def crypto_control(ctx, crypto: str = None, trend: str = None, percent: str = None):
    """Owner controls for the crypto market."""
    if not is_owner(ctx):
        return await ctx.send("Owner only.")
    if crypto is None:
        return await ctx.send(
            "Use `uwu cryptocontrol <crypto|all> <up|down|random|freeze|unfreeze> [percent]`."
        )

    target_symbols = list(CRYPTO_SYMBOLS) if crypto.casefold() == "all" else [resolve_crypto(crypto)]
    if target_symbols[0] is None:
        return await ctx.send(
            f"Unknown crypto. Choose one of: `{', '.join(CRYPTO_SYMBOLS)}`."
        )
    action = str(trend or "").casefold()
    valid_actions = {"up", "down", "random", "freeze", "unfreeze"}
    if action not in valid_actions:
        return await ctx.send(
            "Choose a control: `up`, `down`, `random`, `freeze`, or `unfreeze`."
        )

    movement = None
    if percent is not None:
        try:
            movement = float(percent.replace("%", ""))
        except ValueError:
            return await ctx.send("Movement must be a percentage from 0.1 to 50.")
        if not 0.1 <= movement <= 50:
            return await ctx.send("Movement must be between 0.1% and 50%.")

    for symbol in target_symbols:
        state = CRYPTO_MARKET["symbols"][symbol]
        if action in {"up", "down", "random"}:
            state["trend"] = action
        elif action == "freeze":
            state["frozen"] = True
        elif action == "unfreeze":
            state["frozen"] = False
        if movement is not None:
            state["tick_percent"] = movement
    save_crypto_market()

    names = ", ".join(CRYPTO_DISPLAY_NAMES[symbol] for symbol in target_symbols)
    details = f" at {movement:.1f}% per tick" if movement is not None else ""
    await ctx.send(
        f"👑 Updated **{names}**: `{action}`{details}.\n"
        "This market change is saved to Firebase."
    )

@bot.command(name="cryptopause", aliases=["marketpause"])
async def crypto_pause(ctx, state: str = None):
    """Owner pause/resume control for the crypto market."""
    if not is_owner(ctx):
        return await ctx.send("Owner only.")
    if state is None:
        current = "paused" if CRYPTO_MARKET.get("paused") else "live"
        return await ctx.send(f"UWUCRYPTO market is currently **{current}**.")
    value = state.casefold()
    if value not in {"on", "off", "pause", "resume"}:
        return await ctx.send("Use `uwu cryptopause on` to pause or `uwu cryptopause off` to resume.")
    CRYPTO_MARKET["paused"] = value in {"on", "pause"}
    save_crypto_market()
    await ctx.send(
        f"👑 UWUCRYPTO market **{'paused' if CRYPTO_MARKET['paused'] else 'resumed'}**."
    )
# ========== NEW ODDS HELPER — DO NOT MOVE ==========
def get_effective_win_chance(user_id: str, game_name: str) -> float:
    # Normalize game names so aliases work
    game_key = game_name.lower().strip()
    game_key = GAME_ODDS_ALIASES.get(game_key, game_key)

    # 🟢 FIRST CHECK: PER-USER ODDS (HIGHEST PRIORITY)
    user_odds = USER_GAME_ODDS.get(str(user_id), {})
    user_setting = user_odds.get(game_key)
    if user_setting and isinstance(user_setting, dict):
        mode = user_setting.get("mode", "win").lower()
        pct = float(user_setting["percent"])

        if mode == "win":
            if pct >= 100:
                return 100.0  # ✅ ALWAYS WIN
            if pct <= 0:
                return 0.0    # ❌ ALWAYS LOSE
            return max(0.0, min(100.0, pct))

        elif mode == "lose":
            if pct >= 100:
                return 0.0    # ❌ LOSE 100% = NEVER WIN
            if pct <= 0:
                return 100.0  # ✅ LOSE 0% = ALWAYS WIN
            win_from_lose = 100.0 - pct
            return max(0.0, min(100.0, win_from_lose))

    # 🟡 FALLBACK: GLOBAL ODDS IF NO USER RULE
    return float(GAME_WIN_CHANCES.get(game_key, DEFAULT_GAME_WIN_CHANCES.get(game_key, 50.0)))
# ==================================================
@bot.command(name="odds", aliases=["setodds", "chance"])
async def odds(ctx, game: str = None, percent: str = None):
    """View or change the developer-controlled win chance for supported games."""
    if not is_owner(ctx):
        return await ctx.send("Owner only.")

    if game is None:
        lines = []
        for name in DEFAULT_GAME_WIN_CHANCES:
            edge = game_house_edge(name)
            lines.append(
                f"- `{name}`: **{get_game_win_chance(name):.1f}%** {game_odds_meaning(name)}"
                + ("" if edge is None else f" • house edge `{edge:+.1%}`")
            )
        return await ctx.send(
            "**Game win chances**\n"
            + "\n".join(lines)
            + "\n\nA positive house edge drains uwuncy; a negative one prints it."
            + f"\n{SABONG_ODDS_NOTE}"
            + "\nUse `uwu odds <game> <percent>` or `uwu odds all <percent>`."
        )

    normalized_game = game.lower()
    if normalized_game == "all":
        target_games = list(DEFAULT_GAME_WIN_CHANCES)
    else:
        canonical_game = GAME_ODDS_ALIASES.get(normalized_game)
        if canonical_game is None:
            supported = ", ".join(sorted(GAME_ODDS_ALIASES))
            return await ctx.send(
                f"Unknown game. Supported names and aliases: `{supported}`."
            )
        target_games = [canonical_game]

    if percent is None:
        if len(target_games) == 1:
            game_name = target_games[0]
            edge = game_house_edge(game_name)
            return await ctx.send(
                f"**{game_name}** {game_odds_meaning(game_name)}: "
                f"`{get_game_win_chance(game_name):.1f}%`"
                + ("" if edge is None else f" • house edge `{edge:+.1%}`")
                + (f"\n{SABONG_ODDS_NOTE}" if game_name == "sabong" else "")
            )
        return await ctx.send(
            "Add a percentage, for example: `uwu odds all 40`."
        )

    try:
        value = float(percent.replace("%", ""))
    except ValueError:
        return await ctx.send("Percentage must be a number from 0 to 100.")
    if not 0 <= value <= 100:
        return await ctx.send("Percentage must be between 0 and 100.")

    for game_name in target_games:
        GAME_WIN_CHANCES[game_name] = value
    save_game_win_chances(GAME_WIN_CHANCES)

    if len(target_games) == 1:
        return await ctx.send(
            f"Set **{target_games[0]}** {game_odds_meaning(target_games[0])} "
            f"to **{value:.1f}%**."
            + (f"\n{SABONG_ODDS_NOTE}" if target_games[0] == "sabong" else "")
        )
    await ctx.send(
        f"Set win chance to **{value:.1f}%** for: "
        f"{', '.join(target_games)}."
        + (f"\n{SABONG_ODDS_NOTE}" if "sabong" in target_games else "")
    )


async def start_help_paginator(ctx, embeds, timeout=120):
    """Send a paginated help message controlled by reactions."""
    if not embeds:
        return
    message = await ctx.send(embed=embeds[0])
    controls = ["◀️", "▶️", "⏹️"]
    for r in controls:
        try:
            await message.add_reaction(r)
        except Exception:
            pass

    index = 0

    def check(reaction, user):
        return (
            reaction.message.id == message.id
            and user.id != bot.user.id
            and str(reaction.emoji) in controls
        )

    while True:
        try:
            reaction, user = await bot.wait_for("reaction_add", timeout=timeout, check=check)
        except asyncio.TimeoutError:
            try:
                await message.clear_reactions()
            except Exception:
                pass
            return

        emoji = str(reaction.emoji)
        try:
            await message.remove_reaction(emoji, user)
        except Exception:
            pass

        if emoji == "⏹️":
            try:
                await message.clear_reactions()
            except Exception:
                pass
            return
        elif emoji == "▶️":
            index = (index + 1) % len(embeds)
        elif emoji == "◀️":
            index = (index - 1) % len(embeds)
        try:
            await message.edit(embed=embeds[index])
        except Exception:
            pass

@bot.command(name="userodds", aliases=["userchance", "setuserodds"])
async def user_odds(
    ctx,
    member: discord.Member = None,
    game: str = None,
    mode: str = None,
    percent: str = None,
):
    """Set or view an owner-controlled win/lose chance for one user and game."""
    if not is_owner(ctx):
        return await ctx.send("Owner only.")
    if member is None:
        return await ctx.send(
            "Use `uwu userodds @user <game> <win|lose> <percent>`.\n"
            "Example: `uwu userodds @User slots win 75`."
        )

    user_key = str(member.id)
    user_settings = USER_GAME_ODDS.setdefault(user_key, {})

    if game is None:
        configured = user_settings
        if not configured:
            return await ctx.send(f"No custom gambling odds are set for {member.mention}.")
        lines = []
        for game_name, setting in sorted(configured.items()):
            if not isinstance(setting, dict):
                continue
            lines.append(
                f"- `{game_name}`: **{setting.get('mode', 'win')} "
                f"{float(setting.get('percent', 0)):.1f}%**"
            )
        return await ctx.send(
            f"**Custom gambling odds for {member.mention}**\n"
            + ("\n".join(lines) if lines else "No custom gambling odds are set.")
        )

    normalized_game = game.casefold()
    if normalized_game == "all":
        target_games = list(DEFAULT_GAME_WIN_CHANCES)
    else:
        canonical_game = GAME_ODDS_ALIASES.get(normalized_game)
        if canonical_game is None:
            supported = ", ".join(sorted(GAME_ODDS_ALIASES))
            return await ctx.send(
                f"Unknown gambling game. Supported names and aliases: `{supported}`."
            )
        target_games = [canonical_game]

    if mode is None:
        configured = [
            (game_name, user_settings.get(game_name))
            for game_name in target_games
            if isinstance(user_settings.get(game_name), dict)
        ]
        if not configured:
            return await ctx.send(
                f"{member.mention} has no custom odds for {normalized_game}."
            )
        lines = [
            f"- `{game_name}`: **{setting.get('mode', 'win')} "
            f"{float(setting.get('percent', 0)):.1f}%**"
            for game_name, setting in configured
        ]
        return await ctx.send("\n".join(lines))

    if mode.casefold() in {"clear", "reset", "off"}:
        for game_name in target_games:
            user_settings.pop(game_name, None)
        if user_settings:
            USER_GAME_ODDS[user_key] = user_settings
        else:
            USER_GAME_ODDS.pop(user_key, None)
        save_user_game_odds()
        return await ctx.send(
            f"Cleared custom gambling odds for {member.mention}: "
            f"{', '.join(target_games)}."
        )

    normalized_mode = mode.casefold()
    if normalized_mode not in {"win", "lose"}:
        return await ctx.send(
            "Chance mode must be `win`, `lose`, or `clear`."
        )
    if percent is None:
        return await ctx.send(
            "Add a percentage, for example: `uwu userodds @User slots win 75`."
        )
    try:
        value = float(percent.replace("%", ""))
    except ValueError:
        return await ctx.send("Percentage must be a number from 0 to 100.")
    if not 0 <= value <= 100:
        return await ctx.send("Percentage must be between 0 and 100.")

    for game_name in target_games:
        user_settings[game_name] = {
            "mode": normalized_mode,
            "percent": value,
        }
    USER_GAME_ODDS[user_key] = user_settings
    save_user_game_odds()
    await ctx.send(
        f"Set {member.mention}'s {normalized_mode} chance to **{value:.1f}%** "
        f"for: {', '.join(target_games)}."
    )

@bot.command(name="betlimits", aliases=["setbetlimits", "gamebets"])
async def bet_limits(
    ctx,
    game: str = None,
    minimum: str = None,
    maximum: str = None,
):
    """View or set min/max bets for non-Arena gambling games."""
    if not is_owner(ctx):
        return await ctx.send("Owner only.")

    if game is None:
        lines = []
        for game_name in GAMBLING_GAME_NAMES:
            limits = GAME_BET_LIMITS.get(game_name, DEFAULT_GAME_BET_LIMITS[game_name])
            max_value = int(limits.get("max", 0))
            max_label = format_coins(max_value) if max_value else "unlimited"
            lines.append(
                f"- `{game_name}`: min `{format_coins(int(limits.get('min', 1)))}` "
                f"• max `{max_label}`"
            )
        return await ctx.send(
            "**Non-Arena gambling bet limits**\n"
            + "\n".join(lines)
            + "\n\nUse `uwu betlimits <game> <min> <max>`."
        )

    normalized_game = game.casefold()
    if normalized_game == "all":
        target_games = list(GAMBLING_GAME_NAMES)
    else:
        canonical_game = GAME_ODDS_ALIASES.get(normalized_game)
        if canonical_game not in GAMBLING_GAME_NAMES:
            supported = ", ".join(sorted(GAME_ODDS_ALIASES))
            return await ctx.send(
                f"Unknown gambling game. Supported names and aliases: `{supported}`."
            )
        target_games = [canonical_game]

    if minimum is None and maximum is None:
        lines = []
        for game_name in target_games:
            limits = GAME_BET_LIMITS[game_name]
            max_value = int(limits.get("max", 0))
            max_label = format_coins(max_value) if max_value else "unlimited"
            lines.append(
                f"`{game_name}`: min `{format_coins(int(limits.get('min', 1)))}` "
                f"• max `{max_label}`"
            )
        return await ctx.send("\n".join(lines))

    if minimum is None or maximum is None:
        return await ctx.send(
            "Provide both limits: `uwu betlimits <game> <min> <max>`.\n"
            "Use max `0` for no maximum, or `clear` to restore defaults."
        )

    if minimum.casefold() in {"clear", "reset", "off"} or maximum.casefold() in {
        "clear",
        "reset",
        "off",
    }:
        for game_name in target_games:
            GAME_BET_LIMITS[game_name] = DEFAULT_GAME_BET_LIMITS[game_name].copy()
        save_game_bet_limits()
        return await ctx.send(
            f"Reset bet limits for: {', '.join(target_games)}."
        )

    minimum_value = parse_coins(minimum)
    maximum_value = parse_coins(maximum)
    if minimum_value is None or minimum_value < 1:
        return await ctx.send("Minimum bet must be at least 1.")
    if maximum_value is None or maximum_value < 0:
        return await ctx.send("Maximum bet must be 0 or greater.")
    if maximum_value and maximum_value < minimum_value:
        return await ctx.send("Maximum bet must be greater than or equal to the minimum.")

    for game_name in target_games:
        GAME_BET_LIMITS[game_name] = {
            "min": minimum_value,
            "max": maximum_value,
        }
    save_game_bet_limits()
    max_label = format_coins(maximum_value) if maximum_value else "unlimited"
    await ctx.send(
        f"Set bet limits for {', '.join(target_games)}: "
        f"minimum **{format_coins(minimum_value)}** • maximum **{max_label}**."
    )

@bot.command(name="betcap", aliases=["maxbet"])
async def betcap(ctx, percent: str = None):
    """View or change the owner-controlled maximum bet percentage."""
    if not is_owner(ctx):
        return await ctx.send("Owner only.")
    if percent is None:
        status = "enabled" if ECONOMY_SETTINGS.get("bet_cap_enabled", True) else "disabled"
        return await ctx.send(
            f"**Maximum bet cap:** {status}\n"
            f"Current limit: **{ECONOMY_SETTINGS.get('max_bet_percent', 0):.1f}%** of wallet\n"
            "Use `uwu betcap <percent>` or `uwu betcap off`."
        )
    if percent.lower() == "off":
        ECONOMY_SETTINGS["bet_cap_enabled"] = False
        save_economy_settings()
        return await ctx.send("Maximum bet cap disabled.")
    try:
        value = float(percent.replace("%", ""))
    except ValueError:
        return await ctx.send("Bet cap must be a percentage from 1 to 100, or `off`.")
    if not 1 <= value <= 100:
        return await ctx.send("Bet cap must be between 1% and 100%.")
    ECONOMY_SETTINGS["max_bet_percent"] = value
    ECONOMY_SETTINGS["bet_cap_enabled"] = True
    save_economy_settings()
    await ctx.send(f"Maximum bet cap set to **{value:.1f}%** of each player's wallet.")

@bot.command(name="setjackpot")
async def setjackpot(ctx, amount_text: str = None):
    """Set the global jackpot seed amount."""
    if not is_owner(ctx):
        return await ctx.send("Owner only.")
    amount = parse_coins(amount_text)
    if amount is None or amount < 0:
        return await ctx.send("Jackpot amount must be zero or more.")
    ECONOMY_SETTINGS["jackpot"] = amount
    save_economy_settings()
    await ctx.send(f"Global jackpot set to **{format_coins(amount)} uwuncy**.")

@bot.command(name="addcoins", aliases=["giveadmin"])
async def addcoins(ctx, *args):
    if not is_owner(ctx):
        return await ctx.send("❌ **Owner only!**")

    if not args:
        return await ctx.send("❌ **Usage:** `uwu addcoins <user/role/all> <amount>`")

    amount = None
    target_arg = None

    for arg in args:
        cleaned = arg.replace(",", "").lower()
        if cleaned.endswith("k") and cleaned[:-1].isdigit():
            val = int(cleaned[:-1]) * 1000
            if amount is None:
                amount = val
                continue
        elif cleaned.endswith("m") and cleaned[:-1].isdigit():
            val = int(cleaned[:-1]) * 1000000
            if amount is None:
                amount = val
                continue
        elif cleaned.endswith("b") and cleaned[:-1].isdigit():
            val = int(cleaned[:-1]) * 1000000000
            if amount is None:
                amount = val
                continue
        elif cleaned.isdigit():
            if amount is None:
                amount = int(cleaned)
                continue

        if target_arg is None:
            target_arg = arg

    if amount is None or amount <= 0:
        return await ctx.send("❌ **Please specify a positive coin amount.** (e.g. `uwu addcoins @role 1000` or `uwu addcoins @user 50k`)")

    if not target_arg:
        target = ctx.author
    else:
        target_lower = target_arg.lower()
        if target_lower in ["all", "everyone", "@everyone"]:
            members = [m for m in ctx.guild.members if not m.bot] if ctx.guild else []
            if not members:
                return await ctx.send("❌ No members found to receive coins.")
            for m in members:
                credit_wallet(get_user(m.id), amount)
            save_data(DATA)
            total = amount * len(members)
            return await ctx.send(
                f"👑 Added **{format_coins(amount)} uwuncy** to **{len(members)}** members in this server.\n"
                f"Total distributed: **{format_coins(total)} uwuncy**."
            )

        target = None
        # Try RoleConverter
        try:
            target = await commands.RoleConverter().convert(ctx, target_arg)
        except Exception:
            pass

        # Try MemberConverter
        if not target:
            try:
                target = await commands.MemberConverter().convert(ctx, target_arg)
            except Exception:
                pass

        # Try UserConverter
        if not target:
            try:
                target = await commands.UserConverter().convert(ctx, target_arg)
            except Exception:
                pass

        if not target:
            return await ctx.send(f"❌ Could not find user or role `{target_arg}`.")

    if isinstance(target, discord.Role):
        members = [m for m in target.members if not m.bot]
        if not members:
            return await ctx.send(f"❌ No members currently have the {target.mention} role.")
        for member in members:
            credit_wallet(get_user(member.id), amount)
        save_data(DATA)
        total = amount * len(members)
        return await ctx.send(
            f"👑 Added **{format_coins(amount)} uwuncy** to **{len(members)}** members with role {target.mention}.\n"
            f"Total distributed: **{format_coins(total)} uwuncy**."
        )

    credit_wallet(get_user(target.id), amount)
    save_data(DATA)
    await ctx.send(f"👑 Admin: Added **{format_coins(amount)} uwuncy** to {target.mention}.")

@bot.command(name="removecoins", aliases=["takecoins"])
async def removecoins(ctx, member: discord.Member, amount: int):
    if not is_owner(ctx): return await ctx.send("❌ **Owner only!**")
    if amount <= 0: return await ctx.send("❌ Amount must be positive!")
    u = get_user(member.id)
    debit_wallet(u, amount)
    save_data(DATA)
    await ctx.send(f"Admin: removed **{format_coins(amount)} uwuncy** from {member.mention}.")

@bot.command(name="setcoins", aliases=["setbal"])
async def setcoins(ctx, member: discord.Member, amount: int):
    if not is_owner(ctx): return await ctx.send("❌ **Owner only!**")
    if amount < 0: return await ctx.send("❌ Can't set negative!")
    u = get_user(member.id)
    u["wallet"] = max(0, int(amount))
    save_data(DATA)
    await ctx.send(f"Admin: set {member.mention}'s wallet to **{format_coins(amount)} uwuncy**.")

@bot.command(name="resetuser", aliases=["wipeuser"])
async def resetuser(ctx, member: discord.Member):
    if not is_owner(ctx): return await ctx.send("❌ **Owner only!**")
    uid = str(member.id)
    if uid in DATA: del DATA[uid]
    save_data(DATA)
    await ctx.send(f"👑 **ADMIN:** Wiped all data for {member.mention}")

@bot.command(name="resetstreak")
async def resetstreak(ctx, member: discord.Member):
    if not is_owner(ctx): return await ctx.send("❌ **Owner only!**")
    get_user(member.id)["streak"] = 0
    save_data(DATA)
    await ctx.send(f"👑 **ADMIN:** Reset streak for {member.mention}")

@bot.command(name="resetuwuncy", aliases=["clearuwuncy", "wipeuwuncy"])
async def reset_all_uwuncy(ctx, confirmation: str = None):
    """Owner-only destructive reset of wallets and banks, not crypto holdings."""
    if not is_owner(ctx):
        return await ctx.send("Owner only.")
    if str(confirmation or "").casefold() != "confirm":
        return await ctx.send(
            "⚠️ This will set every user's wallet and bank to **0 uwuncy** "
            "without removing crypto investments or other profile data.\n"
            "To continue, use `uwu resetuwuncy confirm`."
        )

    affected_users = 0
    cleared_uwuncy = 0
    for record in DATA.values():
        if not isinstance(record, dict):
            continue
        user = normalize_user(record)
        previous_total = int(user.get("wallet", 0)) + int(user.get("bank", 0))
        if previous_total or user.get("wallet") != 0 or user.get("bank") != 0:
            affected_users += 1
            cleared_uwuncy += previous_total
        user["wallet"] = 0
        user["bank"] = 0

    save_data(DATA)
    await ctx.send(
        f"👑 Cleared wallet and bank uwuncy for **{affected_users}** users.\n"
        f"Removed from spendable balances: **{format_coins(cleared_uwuncy)} uwuncy**.\n"
        "Crypto investments and all other user data were preserved."
    )

# ==============================================
# 🚀 RUN
# ==============================================
def run_bot():
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_BOT_TOKEN secret is not configured")
    acquire_bot_lease()
    heartbeat = threading.Thread(target=refresh_bot_lease, daemon=True)
    heartbeat.start()
    try:
        bot.run(token)
    finally:
        release_bot_lease()

def start_keep_alive():
    """Serve the health endpoint on the port the host assigned, if enabled."""
    if os.environ.get("DISABLE_KEEPALIVE"):
        return
    port = int(os.environ.get("PORT") or os.environ.get("SERVER_PORT") or "8000")

    def serve():
        try:
            app.run(host="0.0.0.0", port=port, use_reloader=False)
        except OSError as exc:
            # The bot itself does not need this endpoint, so a busy or
            # unavailable port must not take the process down.
            print(f"⚠️ Keep-alive server disabled: {exc}")

    threading.Thread(target=serve, daemon=True).start()

if __name__ == "__main__":
    start_keep_alive()
    run_bot()