import time
import discord

# --- BOOSTER SHOP ITEMS CATALOG ---
BOOSTER_SHOP_ITEMS = {
    # Category 1: Economy & Multipliers
    "2x_earnings_pass": {
        "id": "2x_earnings_pass",
        "name": "2× Earnings Pass",
        "category": "Economy & Multipliers",
        "price": 15_000_000_000_000, # 15T
        "desc": "Doubles ALL money you earn for 7 days",
        "icon": "📈",
        "duration_days": 7
    },
    "tax_exemption_token": {
        "id": "tax_exemption_token",
        "name": "Tax Exemption Token",
        "category": "Economy & Multipliers",
        "price": 8_000_000_000_000, # 8T
        "desc": "Pay 0% tax on all transactions for 30 days",
        "icon": "📜",
        "duration_days": 30
    },
    "cooldown_skip": {
        "id": "cooldown_skip",
        "name": "Cooldown Skip",
        "category": "Economy & Multipliers",
        "price": 5_000_000_000_000, # 5T
        "desc": "Instantly reset your `uwu booster` cooldown (claim again now!)",
        "icon": "⏱️",
        "instant": True
    },
    "daily_cap_bypass": {
        "id": "daily_cap_bypass",
        "name": "Daily Cap Bypass",
        "category": "Economy & Multipliers",
        "price": 10_000_000_000_000, # 10T
        "desc": "Remove daily earning limits for 24 hours",
        "icon": "📊",
        "duration_days": 1
    },
    "permanent_1_5x_boost": {
        "id": "permanent_1_5x_boost",
        "name": "Permanent 1.5× Boost",
        "category": "Economy & Multipliers",
        "price": 150_000_000_000_000, # 150T
        "desc": "Permanent +50% bonus on all earnings forever!",
        "icon": "💎",
        "permanent": True
    },
    "lump_sum_bonus": {
        "id": "lump_sum_bonus",
        "name": "Lump Sum Bonus",
        "category": "Economy & Multipliers",
        "price": 3_000_000_000_000, # 3T
        "desc": "Instant +5T cash (one-time purchase every 7 days)",
        "icon": "💵",
        "instant": True,
        "cooldown_days": 7
    },

    # Category 2: Command & Utility Perks
    "priority_queue": {
        "id": "priority_queue",
        "name": "Priority Queue",
        "category": "Command & Utility Perks",
        "price": 20_000_000_000_000, # 20T
        "desc": "Your commands process first; bypass slowdowns",
        "icon": "🚀",
        "permanent": True
    },
    "extra_storage_slot": {
        "id": "extra_storage_slot",
        "name": "Extra Storage Slot",
        "category": "Command & Utility Perks",
        "price": 15_000_000_000_000, # 15T
        "desc": "Unlock extra inventory space for collectibles/items",
        "icon": "📦",
        "permanent": True
    },
    "exclusive_command_pack": {
        "id": "exclusive_command_pack",
        "name": "Exclusive Command Pack",
        "category": "Command & Utility Perks",
        "price": 30_000_000_000_000, # 30T
        "desc": "Unlock fun booster-only mini-commands (8ball, hug, meme, etc.)",
        "icon": "🎯",
        "permanent": True
    },
    "stealth_mode": {
        "id": "stealth_mode",
        "name": "Stealth Mode",
        "category": "Command & Utility Perks",
        "price": 12_000_000_000_000, # 12T
        "desc": "Command outputs hidden from others; anonymous leaderboard entries",
        "icon": "🤫",
        "permanent": True
    },
    "auto_claim_pass": {
        "id": "auto_claim_pass",
        "name": "Auto-Claim Pass",
        "category": "Command & Utility Perks",
        "price": 25_000_000_000_000, # 25T
        "desc": "Auto-collect your daily `uwu booster` reward while offline/online for 30 days",
        "icon": "📅",
        "duration_days": 30
    },

    # Category 3: Limited / One-Time / Stackable
    "permanent_shop_access": {
        "id": "permanent_shop_access",
        "name": "Permanent Shop Access",
        "category": "Limited / One-Time / Stackable",
        "price": 80_000_000_000_000, # 80T
        "desc": "Keep shopping here even if you stop boosting (rare perk!)",
        "icon": "🔒",
        "permanent": True
    },
    "birthday_bonus_multiplier": {
        "id": "birthday_bonus_multiplier",
        "name": "Birthday Bonus Multiplier",
        "category": "Limited / One-Time / Stackable",
        "price": 10_000_000_000_000, # 10T
        "desc": "On your birthday: 5× daily reward that day",
        "icon": "🎂",
        "permanent": True
    },
    "lucky_enchant": {
        "id": "lucky_enchant",
        "name": "Lucky Enchant",
        "category": "Limited / One-Time / Stackable",
        "price": 45_000_000_000_000, # 45T
        "desc": "+20% chance for bonus rewards from all mini-games (permanent)",
        "icon": "🪄",
        "permanent": True
    },
    "gift_token": {
        "id": "gift_token",
        "name": "Gift Token",
        "category": "Limited / One-Time / Stackable",
        "price": 6_000_000_000_000, # 6T
        "desc": "Buy a reward to gift to a friend (nice gesture!)",
        "icon": "🕹️",
        "instant": True
    },
    "boost_count_multiplier": {
        "id": "boost_count_multiplier",
        "name": "Boost Count Multiplier",
        "category": "Limited / One-Time / Stackable",
        "price": 60_000_000_000_000, # 60T
        "desc": "Your boost count counts double for reward scaling (permanent)",
        "icon": "💥",
        "permanent": True
    }
}


def is_server_booster(member, user=None, guild=None):
    """Check if member is a Server Booster or has Permanent Shop Access."""
    if user is not None:
        if user.get("is_booster") or user.get("booster"):
            return True
        inventory = user.get("inventory", [])
        if "permanent_shop_access" in inventory:
            return True

    if member is None:
        return False

    member_id = getattr(member, "id", None)
    target_guild = guild or getattr(member, "guild", None)

    # If member is a User object or cached separately, fetch guild member object if available
    guild_member = member
    if target_guild is not None and member_id is not None:
        found_member = target_guild.get_member(member_id)
        if found_member is not None:
            guild_member = found_member

    # 1. Check premium_since timestamp set by Discord
    if getattr(guild_member, "premium_since", None) is not None or getattr(member, "premium_since", None) is not None:
        return True

    # 2. Check guild premium subscribers list by ID matching
    if target_guild is not None and member_id is not None:
        try:
            premium_subs = getattr(target_guild, "premium_subscribers", []) or []
            if any(getattr(sub, "id", None) == member_id for sub in premium_subs):
                return True
        except Exception:
            pass

        # 3. Check official guild.premium_subscriber_role
        try:
            booster_role = getattr(target_guild, "premium_subscriber_role", None)
            if booster_role and hasattr(guild_member, "roles") and booster_role in guild_member.roles:
                return True
        except Exception:
            pass

    # 4. Check roles on guild_member or member for nitro booster flags and role names
    roles_to_check = getattr(guild_member, "roles", []) or getattr(member, "roles", []) or []
    for role in roles_to_check:
        try:
            if getattr(role, "is_premium_subscriber", lambda: False)():
                return True
            r_name = getattr(role, "name", "").lower()
            if any(kw in r_name for kw in ("booster", "server booster", "nitro booster", "boost")):
                return True
        except Exception:
            pass

    return False


def get_guild_boosters(guild):
    """Return list of members currently boosting the given guild."""
    if not isinstance(guild, discord.Guild):
        return []

    boosters = []
    # Primary check across guild members
    for member in guild.members:
        if is_server_booster(member):
            boosters.append(member)

    # Fallback to guild.premium_subscribers
    if not boosters and hasattr(guild, "premium_subscribers"):
        for sub in getattr(guild, "premium_subscribers", []):
            if sub not in boosters:
                boosters.append(sub)

    return boosters


def get_user_boost_count(member, user=None):
    """Calculate effective boost count for member."""
    count = 1
    if isinstance(member, discord.Member):
        boost_roles = [r for r in member.roles if "booster" in r.name.lower() or getattr(r, "is_premium_subscriber", lambda: False)()]
        if len(boost_roles) > 1:
            count = len(boost_roles)

    if user is not None:
        inventory = user.get("inventory", [])
        if "boost_count_multiplier" in inventory:
            count *= 2

    return max(1, count)


def calculate_booster_daily_reward(user, boost_count=1, is_birthday=False):
    """Calculate total daily booster reward with multipliers and perks."""
    base_amount = 5_000_000_000_000  # 5 Trillion uwuncy base

    count_mult = max(1, boost_count)
    inventory = user.get("inventory", [])

    perm_mult = 1.5 if "permanent_1_5x_boost" in inventory else 1.0

    pass_expiry = user.get("booster_passes", {}).get("2x_earnings_pass", 0)
    pass_mult = 2.0 if time.time() < pass_expiry else 1.0

    bday_mult = 1.0
    if is_birthday or "birthday_bonus_multiplier" in inventory:
        bday_mult = 5.0 if is_birthday else 1.25

    total = int(base_amount * count_mult * perm_mult * pass_mult * bday_mult)
    return total, {
        "base": base_amount,
        "count_mult": count_mult,
        "perm_mult": perm_mult,
        "pass_mult": pass_mult,
        "bday_mult": bday_mult
    }


def format_trillion(amount):
    """Format large numbers into clean T/B/M or comma format."""
    if amount >= 1_000_000_000_000:
        val = amount / 1_000_000_000_000
        return f"{val:.2f}".rstrip('0').rstrip('.') + "T"
    elif amount >= 1_000_000_000:
        val = amount / 1_000_000_000
        return f"{val:.2f}".rstrip('0').rstrip('.') + "B"
    elif amount >= 1_000_000:
        val = amount / 1_000_000
        return f"{val:.2f}".rstrip('0').rstrip('.') + "M"
    return f"{amount:,}"
