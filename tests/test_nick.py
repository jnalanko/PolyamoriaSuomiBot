from unittest import TestCase
from unittest.mock import Mock

from nick import (
    update_nickname_cache,
    fetch_nickname_from_cache,
    get_guild_display_name,
    clear_nickname_cache,
    get_nick,
)


class TestNick(TestCase):
    def setUp(self):
        clear_nickname_cache()

    def test_update_nickname_from_global_name(self):
        user_id = 123
        user_global_name = "Erkki"
        user_nick = None
        mock_user = Mock(id=user_id, global_name=user_global_name, nick=user_nick)
        update_nickname_cache(mock_user)
        self.assertEqual(fetch_nickname_from_cache(user_id), user_global_name)

    def test_update_nickname_from_nick(self):
        user_id = 456
        user_global_name = "Pentti"
        user_nick = "PenttiOnlyOnThisServer"
        mock_user = Mock(id=user_id, global_name=user_global_name, nick=user_nick)
        update_nickname_cache(mock_user)
        self.assertEqual(fetch_nickname_from_cache(user_id), user_nick)

    def test_fetch_nonexistent_nickname(self):
        self.assertEqual(fetch_nickname_from_cache(99999), None)

    def test_clear_cache(self):
        user_id = 789
        user_global_name = "CacheGuy"
        mock_user = Mock(id=user_id, global_name=user_global_name, nick=None)
        update_nickname_cache(mock_user)
        clear_nickname_cache()
        self.assertIsNone(fetch_nickname_from_cache(user_id))

    def test_get_guild_display_name_no_nick_attr(self):
        # Create a mock user that doesn't have 'nick'.
        # Needed to test a case where Message.author is abc.User instead of Member
        # https://docs.pycord.dev/en/stable/api/models.html#discord.Message.author
        class NoNickMock(Mock):
            def __getattr__(self, name):
                if name == 'nick':
                    raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
                return super().__getattr__(name)

        user_global_name = 'Abstract User'
        no_nick_user = NoNickMock(global_name=user_global_name)
        self.assertEqual(get_guild_display_name(no_nick_user), user_global_name)

    def test_get_nick_cache_hit(self):
        user_id = 999
        user_global_name = "CacheHitUser"
        user_nick = None
        mock_user = Mock(id=user_id, global_name=user_global_name, nick=user_nick)
        update_nickname_cache(mock_user)
        self.assertEqual(get_nick(user_id, guild=Mock()), user_global_name)

    def test_get_nick_cache_miss(self):
        user_id = 888
        user_global_name = "CacheMissUser"
        user_nick = None
        mock_user = Mock(id=user_id, global_name=user_global_name, nick=user_nick)
        mock_guild = Mock()
        mock_guild.get_member = Mock(return_value=mock_user)
        self.assertEqual(get_nick(user_id, guild=mock_guild), user_global_name)

    def test_get_nick_cache_miss_updates_cache(self):
        user_id = 777
        user_global_name = "CacheMissUpdateUser"
        user_nick = None
        mock_user = Mock(id=user_id, global_name=user_global_name, nick=user_nick)
        mock_guild = Mock()
        mock_guild.get_member = Mock(return_value=mock_user)
        get_nick(user_id, guild=mock_guild)
        self.assertEqual(fetch_nickname_from_cache(user_id), user_global_name)
