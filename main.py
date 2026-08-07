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
import random, json, time, os, asyncio, socket, uuid, re, traceback
from typing import Union
from datetime import datetime, timezone
from threading import Lock
import firebase_admin
from firebase_admin import credentials, db
from dotenv import load_dotenv

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
    return PREFIX_VARIANTS

# --- INTENTS ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(
    command_prefix=lambda b, m: get_prefixes(),
    intents=intents,
    case_insensitive=True,
    help_command=None
)

# --- OWNER CHECK ---
def is_owner(ctx):
    return str(ctx.author.id) == BOT_OWNER_ID
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

GAMBLING_GAME_NAMES = (
    "slots",
    "coinflip",
    "blackjack",
    "mines",
    "colorgame",
    "dice",
    "highlow",
    "roulette",
)

DEFAULT_GAME_WIN_CHANCES = {
    game: 40.0
    for game in GAMBLING_GAME_NAMES
}

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
}

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
    user["level"] = max(int(user.get("level", 1)), 1 + int(user.get("xp", 0)) // 1_000)
    inventory = user.get("inventory")
    if not isinstance(inventory, list):
        user["inventory"] = []
    if not isinstance(user.get("crypto_positions"), dict):
        user["crypto_positions"] = {}
    return user

def get_user(uid):
    uid = str(uid) # ✅ GLOBAL DISCORD USER ID — shared across all servers
    if uid not in DATA:
        DATA[uid] = {
            "wallet": 0,
            "bank": 0,
            "last_daily": 0,
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

def parse_coins(value):
    """Parse a user-entered coin amount, including comma formatting."""
    try:
        text = str(value).strip().replace(",", "").replace("_", "").casefold()
        multiplier = 1
        if text.endswith(("k", "m", "b", "t")):
            suffix = text[-1]
            multiplier = {
                "k": 1_000,
                "m": 1_000_000,
                "b": 1_000_000_000,
                "t": 1_000_000_000_000,
            }[suffix]
            text = text[:-1]
        return int(float(text) * multiplier)
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
            value="\n".join(uno_card_text(card) for card in hand) or "No cards — you win!",
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
            multiplier = 3
            # Bet is reserved (already deducted); payout returns the stake + profit.
            payout = self.game["bet"] * multiplier + self.game["bet"]
            outcome = (
                f"Three {COLOR_CHOICES[selected]} **{selected.title()}** slots. "
                f"Profit: **+{format_coins(self.game['bet'] * multiplier)} uwuncy**"
            )
        elif matching == 2:
            multiplier = 2
            payout = self.game["bet"] * multiplier + self.game["bet"]
            outcome = (
                f"Two {COLOR_CHOICES[selected]} **{selected.title()}** slots. "
                f"Profit: **+{format_coins(self.game['bet'] * multiplier)} uwuncy**"
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

def mines_multiplier(bombs, found):
    """Fair progressive multiplier for a 4x4 Mines board."""
    multiplier = 1.0
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

        # Apply the configured round odds to the first tile while preserving
        # a normal-looking board for every later interaction.
        if not self.game["revealed"]:
            bombs = self.game["bomb_locations"]
            if self.game["target_win"] and tile in bombs:
                safe_replacements = [
                    index for index in range(16)
                    if index != tile and index not in bombs
                ]
                if safe_replacements:
                    bombs.remove(tile)
                    bombs.add(random.choice(safe_replacements))
            elif not self.game["target_win"] and tile not in bombs:
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


@bot.command(name="info", aliases=["userinfo", "profile"])
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
async def on_message(message):
    if message.author.bot:
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

@bot.event
async def on_command_error(ctx, error):
    """Keep command mistakes readable without hiding real persistence failures."""
    if isinstance(error, commands.CommandNotFound):
        return
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
    await ctx.send(
        f"🍁 **{ctx.author.display_name}**, you currently have "
        f"**{format_coins(user['wallet'])} uwuncy**!\n"
        f"{crypto_line}"
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


@bot.command(name="off")
async def crypto_off(ctx, feature: str = None):
    if str(feature or "").casefold() != "crypto":
        return await ctx.send("Use `uwu off crypto` to hide your crypto details.")
    await set_crypto_privacy(ctx, True)


@bot.command(name="on")
async def crypto_on(ctx, feature: str = None):
    if str(feature or "").casefold() != "crypto":
        return await ctx.send("Use `uwu on crypto` to show your crypto details.")
    await set_crypto_privacy(ctx, False)

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
    try:
        bet = int(bet_text.replace(",", ""))
    except ValueError:
        return await ctx.send(
            "The bet must be a whole number. Example: `uwu cf h 20,000`."
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
        total_payout, bonus, boosted = settle_win(user, bet)
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
    await ctx.send(msg)

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
async def slot(ctx, bet: int):
    user = get_user(ctx.author.id)
    validation_error = validate_bet(user, bet, "slots")
    if validation_error:
        return await ctx.send(f"❌ {validation_error}")
    begin_game(user, "slots", bet)
    symbols = ["🍒", "🍋", "🍊", "🍇", "💎", "7️⃣"]

    protection_notice = shield_notice(user, bet)
    if chance_roll("slots", user_id=ctx.author.id):
        winning_symbol = random.choice(symbols)
        final = [winning_symbol] * 3
    else:
        final = random.sample(symbols, 3)
    res = f"🎰 **RESULT** 🎰\n| {final[0]} | {final[1]} | {final[2]} |\n"

    if final[0]==final[1]==final[2]:
        payout = bet*(10 if final[0]=="💎" else 5 if final[0]=="7️⃣" else 3)
        total_payout, bonus, boosted = settle_win(user, payout)
        jackpot_amount = jackpot_payout(user, "slots", bet) if final[0] == "💎" else 0
        finish_game(user, "slots", bet, True, total_payout + jackpot_amount)
        res += f"**Jackpot:** +{format_coins(total_payout)} uwuncy"
        if jackpot_amount:
            res += f"\n🎰 Global jackpot claimed: **+{format_coins(jackpot_amount)} uwuncy**"
        if boosted:
            res += f" (includes Lucky Potion bonus of +{format_coins(bonus)} uwuncy)"
    elif final[0]==final[1] or final[1]==final[2]:
        payout = bet*2
        total_payout, bonus, boosted = settle_win(user, payout)
        finish_game(user, "slots", bet, True, total_payout)
        res += f"**Pair:** +{format_coins(total_payout)} uwuncy"
        if boosted:
            res += f" (includes Lucky Potion bonus of +{format_coins(bonus)} uwuncy)"
    else:
        loss_result = settle_loss(user, bet)
        finish_game(user, "slots", bet, False, loss_result["remaining_loss"])
        res += describe_loss(loss_result, bet, "No match")

    if protection_notice:
        res += f"\n{protection_notice}"
    save_data(DATA)
    await ctx.send(res)

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
async def blackjack(ctx, bet_text: str):
    user = get_user(ctx.author.id)
    bet = parse_coins(bet_text)
    if bet is None:
        return await ctx.send("Invalid bet or not enough uwuncy.")
    validation_error = validate_bet(user, bet, "blackjack")
    if validation_error:
        return await ctx.send(validation_error)
    begin_game(user, "blackjack", bet)

    def show(hand):
        return " ".join(f"`{card[0]}`" for card in hand)

    target_win = chance_roll("blackjack", user_id=ctx.author.id)
    player_initial, dealer_initial, player, dealer = build_blackjack_round(target_win)

    p, d = blackjack_score(player), blackjack_score(dealer)
    if p == 21 and len(player) == 2 and not (d == 21 and len(dealer) == 2):
        payout = int(bet * 1.5)
        total_payout, bonus, boosted = settle_win(user, payout)
        finish_game(user, "blackjack", bet, True, total_payout)
        result = f"Blackjack. Profit: **+{format_coins(total_payout)} uwuncy**"
        if boosted:
            result += f" (includes Lucky Potion bonus of +{format_coins(bonus)} uwuncy)"
    elif p > 21:
        loss_result = settle_loss(user, bet)
        finish_game(user, "blackjack", bet, False, loss_result["remaining_loss"])
        result = describe_loss(loss_result, bet, "Bust")
    elif d > 21 or p > d:
        total_payout, bonus, boosted = settle_win(user, bet)
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
    await ctx.send(
        f"**Blackjack — Final**\n"
        f"Your hand: {show(player)} → **{p}**\n"
        f"Dealer: {show(dealer)} → **{d}**\n"
        f"{result}\n"
        f"Wallet: `{format_coins(user['wallet'])}` uwuncy"
    )

@bot.command(name="colorgame", aliases=["cg"])
async def colorgame(ctx, first: str, bet_text: str = None):
    user = get_user(ctx.author.id)
    requested_color = None
    if bet_text is None:
        # Interactive form: `uwu cg 500`
        bet = parse_coins(first)
    else:
        # Direct form: `uwu cg r 500` (full color names remain supported).
        requested_color = COLOR_SHORTCUTS.get(first.lower(), first.lower())
        bet = parse_coins(bet_text)
        if requested_color not in COLOR_CHOICES:
            return await ctx.send(
                "Choose one color: `r` red, `b` blue, `g` green, or `y` yellow."
            )
    if bet is None:
        return await ctx.send("Invalid bet or not enough uwuncy.")
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
async def mines(ctx, bombs: int, bet_text: str):
    user = get_user(ctx.author.id)
    bet = parse_coins(bet_text)
    if bombs < 1 or bombs > 15:
        return await ctx.send("Bombs must be between 1 and 15.")
    if bet is None:
        return await ctx.send("Invalid bet or not enough uwuncy.")
    validation_error = validate_bet(user, bet, "mines")
    if validation_error:
        return await ctx.send(validation_error)

    # Reserve the bet while the board is active. Safe reveals pay the
    # multiplier, while a bomb leaves the reserved bet lost.
    begin_game(user, "mines", bet, reserve_bet=True)
    save_data(DATA)
    game = {
        "player_name": ctx.author.display_name,
        "bet": bet,
        "bombs": bombs,
        "revealed": set(),
        "bomb_locations": set(random.sample(range(16), bombs)),
        "target_win": chance_roll("mines", user_id=ctx.author.id),
        "shield_notice": shield_notice(user, bet),
    }
    view = MinesView(ctx.author.id, game)
    message = await ctx.send(embed=mines_embed(game), view=view)
    view.message = message

@bot.command(name="dice", aliases=["roll"])
async def dice(ctx, bet: int, guess: int):
    user = get_user(ctx.author.id)
    validation_error = validate_bet(user, bet, "dice")
    if validation_error:
        return await ctx.send(f"❌ {validation_error}")
    if guess <1 or guess >6:
        return await ctx.send("❌ Guess 1–6 only!")

    begin_game(user, "dice", bet)
    protection_notice = shield_notice(user, bet)
    if chance_roll("dice", user_id=ctx.author.id):
        num = guess
    else:
        num = random.choice([value for value in range(1, 7) if value != guess])
    if num == guess:
        payout = bet*6
        total_payout, bonus, boosted = settle_win(user, payout)
        finish_game(user, "dice", bet, True, total_payout)
        res = f"Result: **{num}** — Win: **+{format_coins(total_payout)} uwuncy**"
        if boosted:
            res += f" (includes Lucky Potion bonus of +{format_coins(bonus)} uwuncy)"
    else:
        loss_result = settle_loss(user, bet)
        finish_game(user, "dice", bet, False, loss_result["remaining_loss"])
        res = f"Result: **{num}** — {describe_loss(loss_result, bet, 'Loss')}"

    if protection_notice:
        res += f"\n{protection_notice}"
    save_data(DATA)
    await ctx.send(res)

@bot.command(name="highlow", aliases=["hl"])
async def highlow(ctx, bet: int, pick: str):
    user = get_user(ctx.author.id)
    validation_error = validate_bet(user, bet, "highlow")
    if validation_error:
        return await ctx.send(f"❌ {validation_error}")
    pick = pick.lower()
    if pick not in ["high","low"]:
        return await ctx.send("❌ Use: `uwu hl 50 high` / `uwu hl 50 low`")

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
        total_payout, bonus, boosted = settle_win(user, bet)
        finish_game(user, "highlow", bet, True, total_payout)
        res = f"Number: **{num}** — Win: **+{format_coins(total_payout)} uwuncy**"
        if boosted:
            res += f" (includes Lucky Potion bonus of +{format_coins(bonus)} uwuncy)"
    else:
        loss_result = settle_loss(user, bet)
        finish_game(user, "highlow", bet, False, loss_result["remaining_loss"])
        res = f"Number: **{num}** — {describe_loss(loss_result, bet, 'Loss')}"

    if protection_notice:
        res += f"\n{protection_notice}"
    save_data(DATA)
    await ctx.send(res)

@bot.command(name="rr", aliases=["roulette"])
async def rr(ctx, bet: int):
    user = get_user(ctx.author.id)
    validation_error = validate_bet(user, bet, "roulette")
    if validation_error:
        return await ctx.send(f"❌ {validation_error}")

    begin_game(user, "roulette", bet)
    protection_notice = shield_notice(user, bet)
    if chance_roll("roulette", user_id=ctx.author.id):
        payout = bet*5
        total_payout, bonus, boosted = settle_win(user, payout)
        finish_game(user, "roulette", bet, True, total_payout)
        res = f"Click. You survived. Profit: **+{format_coins(total_payout)} uwuncy**"
        if boosted:
            res += f" (includes Lucky Potion bonus of +{format_coins(bonus)} uwuncy)"
    else:
        loss_result = settle_loss(user, bet)
        finish_game(user, "roulette", bet, False, loss_result["remaining_loss"])
        res = describe_loss(loss_result, bet, "Bang. Loss")

    if protection_notice:
        res += f"\n{protection_notice}"
    save_data(DATA)
    await ctx.send(res)

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

@bot.command(name="prefix")
async def change_prefix(ctx,new=None):
    await ctx.send("The bot prefix is fixed at `uwu`.")

@bot.command(name="help")
async def help_cmd(ctx):
    p = get_prefix()
    help_text = f"""📖 **UwU Bot**
┏ 📊 Economy
┃ `{p}daily` `{p}bal` `{p}info [user]` `{p}hunt` `{p}huntinfo`
┃ `{p}deposit` `{p}withdraw <amount>` `{p}withdraw crypto <crypto> <amount|all>` `{p}give <@user> <amount> | {p}give role <@Role> <amount> | {p}give role <@Role> split <total>` `{p}slot` `{p}lb`
┃ `{p}history` `{p}quests` `{p}achievements` `{p}jackpot`
┃ `{p}crypwuncy` `{p}invest <crypto> <amount>` `{p}investments` `{p}sell <crypto> all`
┃ `{p}top crypto` — highest crypto profit
┃ `{p}off crypto` / `{p}on crypto` — hide/show crypto in balance and profile
┃ `{p}prestige confirm` `{p}properties` `{p}buyproperty <name>`
┃ `{p}collection` `{p}buycollectible <name>` `{p}season` `{p}seasonrank` `{p}seasonclaim`
┣ 🛒 Shop
 ┃ `{p}shop` `{p}buy <item> [quantity]` `{p}inv`
┣ 🎲 Games
┃ `{p}cf h <bet>` `{p}bj <bet>` `{p}cg <bet>` (choose color)
┃ `{p}cg r <bet>` (r/b/g/y) `{p}colorgame <color> <bet>`
┃ `{p}mines <bombs> <bet>` `{p}dice` `{p}hl` `{p}rr`
┃ `{p}create arena <1-5> <total-per-player>` `{p}arena join/status/start/cancel <id>`
┃ `{p}paired @user [arena-id]` — protected teammates for 2v2–5v5
┃ Server owner: `{p}arena channel setup` • restore with `{p}channel redo`
┃ Arena games are bot-selected from: Dice, High/Low, Color, Roulette, Number, Mines, Coin Rush, Card Draw, Treasure Hunt, Battle Power, Math Sprint, BUGTONG-BUGTONG, UNO, LUCKY 9, DEAL OR NO DEAL
┃ Math Sprint: type only the numeric answer directly in the locked arena channel
┃ UNO: open your private hand, select one or more matching cards, then drop them on your turn
┃ LUCKY 9: bot-selected RED/BLUE representatives reveal cards; stand or draw one optional third card
┃ DEAL OR NO DEAL: find the public target number behind 20 shared briefcase tiles; each team gets 3 flips
┃ Only one active arena is allowed per Discord server
┃ `{p}clan create/invite/join/deposit/shop/buy/info/leave`
┣ 😜 Fun
┃ `{p}8ball` `{p}hug` `{p}pat` `{p}kiss` `{p}slap`
┗ ⚙️ `{p}prefix` `{p}help`
"""
    if is_owner(ctx):
        help_text += f"""
┣ 👑 **OWNER ONLY**
┃ `{p}economystats` — economy totals and active systems
┃ `{p}addcoins @user|@role <amount>` `{p}removecoins` `{p}setcoins` `{p}resetuser`
┃ `{p}resetstreak` `{p}resetuwuncy` `{p}odds [game] [percent]`
┃ `{p}userodds @user <game|all> <win|lose> <percent|clear>`
┃ `{p}betlimits [game] [min] [max]` — gambling games only, never Arena
┃ `{p}betcap [percent|off]` `{p}setjackpot <amount>`
┃ `{p}cryptocontrol <crypto|all> <up|down|random|freeze|unfreeze> [percent]`
┃ `{p}cryptopause <on|off>`
┃ `{p}economy users` — every user's wallet, bank, and total balance
┃ `{p}economy earnings` — every user's game payouts and crypto P/L
┃ `{p}servercount` — number of servers and each server's member count
"""
    # Discord rejects messages over 2,000 characters. Send the complete help
    # menu in safe chunks so `uwu help` never falls into the generic error path.
    lines = help_text.splitlines()
    chunks = []
    current = []
    current_length = 0
    for line in lines:
        line_length = len(line) + 1
        if current and current_length + line_length > 1900:
            chunks.append("\n".join(current))
            current = []
            current_length = 0
        current.append(line)
        current_length += line_length
    if current:
        chunks.append("\n".join(current))
    for chunk in chunks:
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
        lines = [
            f"- `{name}`: **{get_game_win_chance(name):.1f}%**"
            for name in DEFAULT_GAME_WIN_CHANCES
        ]
        return await ctx.send(
            "**Game win chances**\n"
            + "\n".join(lines)
            + "\n\nUse `uwu odds <game> <percent>` or `uwu odds all <percent>`."
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
            return await ctx.send(
                f"**{game_name}** win chance: "
                f"`{get_game_win_chance(game_name):.1f}%`"
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
            f"Set **{target_games[0]}** win chance to **{value:.1f}%**."
        )
    await ctx.send(
        f"Set win chance to **{value:.1f}%** for: "
        f"{', '.join(target_games)}."
    )

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
async def addcoins(ctx, target: Union[discord.Member, discord.Role], amount: int):
    if not is_owner(ctx):
        return await ctx.send("❌ **Owner only!**")
    if amount <= 0:
        return await ctx.send("❌ Amount must be positive!")

    if isinstance(target, discord.Role):
        members = list(target.members)
        if not members:
            return await ctx.send(f"❌ No members currently have the {target.mention} role.")
        for member in members:
            credit_wallet(get_user(member.id), amount)
        save_data(DATA)
        total = amount * len(members)
        return await ctx.send(
            f"👑 Added **{format_coins(amount)} uwuncy** to "
            f"**{len(members)}** members with {target.mention}.\n"
            f"Total distributed: **{format_coins(total)} uwuncy**."
        )

    credit_wallet(get_user(target.id), amount)
    save_data(DATA)
    await ctx.send(f"Admin: added **{format_coins(amount)} uwuncy** to {target.mention}.")

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