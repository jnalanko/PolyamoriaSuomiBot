import unittest
from typing import Iterable, NamedTuple

from config import censor_config

VALID_CONFIG = {
    'instances': {
        123456789012345678: {
            'admin_user_id': 987654321098765432,
            'bot_channel_id': 1231231231231231231,
            'midnight_channel_id': 4564564564564564564,
            'db_name': 'mydb',
            'db_password': 'very-secure-password',
            'db_user': 'root',
            'osallistuja_role_id': 12345,
            'lukija_role_id': 12354,
            'aktiivi_role_id': 23523
        }
    },
    'token': 'NOTREAL.X00o05XB9aNcYTgU7S3H6rKi6QRfaNI7qVZ0Kq5wYNKA1pLeIRmb3Hk0jzTd3XemSk8',
    'master_admin_user_id': 987654321098765432,
}


class DictCompareResult(NamedTuple):
    result: bool
    message: str

class TestConfig(unittest.TestCase):
    def test_censor_config_password(self):
        config = {"db_password": "very secret"}
        censored_config = censor_config(config)
        self.assertNotIn(config["db_password"],
                         censored_config["db_password"],
                         "db_password should be censored")

    def test_censor_config_token(self):
        config = {"token": "very secret token"}
        censored_config = censor_config(config)
        self.assertNotIn(config["token"],
                         censored_config["token"],
                         "token should be censored")

    def test_censor_config_deep_level(self):
        config = {"deeper": {"deeper": {"deeper": {"deeper": {"db_password": "very secret"}}}}}
        censored_config = censor_config(config)
        self.assertNotIn(config["deeper"]["deeper"]["deeper"]["deeper"]["db_password"],
                         censored_config["deeper"]["deeper"]["deeper"]["deeper"]["db_password"],
                         "censoring should work on deeply nested configs")

    def test_censor_config_contents_match(self):
        censored_config = censor_config(VALID_CONFIG)
        compare_result = self._dict_contents_equal(
            VALID_CONFIG,
            censored_config,
            skip_keys=("db_password", "token"),
        )
        self.assertTrue(
            compare_result.result,
            f"config should not be modified (other than censoring defined keys): {compare_result.message}"
        )

    def _dict_contents_equal(self, dict1: dict, dict2: dict, skip_keys: Iterable = None) -> DictCompareResult:
        """Check if two dicts' values are equal. Recurse nested dicts. Optionally, skip keys."""
        if len(dict1) != len(dict2):
            return DictCompareResult(False, "lengths not equal")

        if dict1.keys() != dict2.keys():
            return DictCompareResult(False, "keys don't match")

        for (key1, value1), (key2, value2) in zip(sorted(dict1.items()), sorted(dict2.items())):
            if skip_keys is not None and key1 in skip_keys:
                continue
            if key1 != key2:
                return DictCompareResult(False, f"keys don't match: {key1} != {key2}")
            if isinstance(value1, dict):
                sub_dict_result = self._dict_contents_equal(value1, value2, skip_keys=skip_keys)
                if not sub_dict_result.result:
                    return sub_dict_result
                continue
            if value1 != value2:
                return DictCompareResult(False, f"values don't match: {value1} != {value2}")
        return DictCompareResult(True, "")


if __name__ == '__main__':
    unittest.main()
