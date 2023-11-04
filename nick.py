import threading
from collections import defaultdict
from typing import Optional, Union, Dict

import discord


# Key: user id
GuildSpecificCache = Dict[int, str]

# Key: guild id
__NICK_CACHE: Dict[int, GuildSpecificCache] = defaultdict(dict)
__CACHE_LOCK = threading.Lock()


def fetch_nickname_from_cache(user_id: int, guild_id: int) -> Optional[str]:
    with __CACHE_LOCK:
        return __NICK_CACHE.get(guild_id, {}).get(user_id)


def update_nickname_cache(user: Union[discord.Member, discord.abc.User],
                          guild_id: int):
    with __CACHE_LOCK:
        __NICK_CACHE[guild_id][user.id] = get_guild_display_name(user)


def clear_nickname_cache():
    with __CACHE_LOCK:
        __NICK_CACHE.clear()


def get_guild_display_name(user: Union[discord.Member, discord.abc.User]) -> str:
    return (
        # 1: return nick if set (server-specific nickname)
        getattr(user, 'nick', '') or
        # 2: return global_name if set (global display name)
        getattr(user, 'global_name', '') or
        # 3: return name (user's username - this should always exist)
        # 4: return 'unknown name' just in case getting everything else fails
        getattr(user, 'name', 'unknown name')
    )


def get_nick(user_id: int, guild: discord.Guild) -> str:
    from_cache = fetch_nickname_from_cache(user_id, guild_id=guild.id)
    if from_cache is not None:
        return from_cache
    member: Optional[discord.Member] = guild.get_member(user_id)
    # None == has left the guild
    if member is None:
        return 'unknown name'
    nick = get_guild_display_name(member)
    update_nickname_cache(member, guild_id=guild.id)
    return nick
