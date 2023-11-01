from dataclasses import dataclass
from typing import Dict

import yaml

LOCAL_SETTINGS_FILENAME = "config_local.yaml"


@dataclass
class InstanceConfig:
    guild_id: int
    admin_user_id: int
    bot_channel_id: int
    midnight_channel_id: int
    db_host: str
    db_name: str
    db_password: str
    db_user: str


@dataclass
class Config:
    instances: Dict[int, InstanceConfig]
    token: str
    master_admin_user_id: int


def load_config() -> Config:
    config_dict = yaml.safe_load(open(LOCAL_SETTINGS_FILENAME))
    instance_configs = {}
    for _id, values in config_dict["instances"].items():
        instance_configs[_id] = InstanceConfig(_id, **values)

    return Config(
        instances=instance_configs,
        token=config_dict["token"],
        master_admin_user_id=config_dict["master_admin_user_id"],
    )


if __name__ == '__main__':
    print(load_config())
