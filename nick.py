import threading
from typing import Optional, Union, Dict

import discord

__NICK_CACHE: Dict[int, str] = {}
__CACHE_LOCK = threading.Lock()


# TODO: BUG IN MULTI-BOT ENVIRONMENT - WILL RETURN WRONG NICK SOMETIMES
def fetch_nickname_from_cache(user_id: int) -> Optional[str]:
    return __NICK_CACHE.get(user_id)


def update_nickname_cache(user: Union[discord.Member, discord.abc.User]):
    __NICK_CACHE[user.id] = get_guild_display_name(user)


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
