from typing import Optional, Union

import discord

__NICK_CACHE: dict[int, str] = {}


def fetch_nickname_from_cache(user_id: int) -> Optional[str]:
    return __NICK_CACHE.get(user_id)


def update_nickname_cache(user: Union[discord.Member, discord.abc.User]):
    __NICK_CACHE[user.id] = get_guild_display_name(user)


def get_guild_display_name(user: Union[discord.Member, discord.abc.User]):
    return (
            # 1: return nick if set (server-specific nickname)
            getattr(user, 'nick', None) or
            # 2: return global_name if set (global display name)
            getattr(user, 'global_name', None) or
            # 3: return name (user's username - this should always exist)
            # 4: return 'unknown name' just in case getting everything else fails
            getattr(user, 'name', 'unknown name')
    )
