import os
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
    db_name: str


@dataclass
class Config:
    instances: Dict[int, InstanceConfig]
    db_host: str
    db_password: str
    db_user: str
    token: str
    master_admin_user_id: int


def load_config() -> Config:
    """Environment variables override db_host, db_password and db_user"""
    config_dict = yaml.safe_load(open(LOCAL_SETTINGS_FILENAME))
    instance_configs = {}
    for _id, values in config_dict["instances"].items():
        instance_configs[_id] = InstanceConfig(_id, **values)

    return Config(
        instances=instance_configs,
        db_host=os.getenv("DATABASE_HOST") or config_dict["db_host"],
        db_password=os.getenv("DATABASE_PASSWORD") or config_dict["db_password"],
        db_user=os.getenv("DATABASE_USER") or config_dict["db_user"],
        token=config_dict["token"],
        master_admin_user_id=config_dict["master_admin_user_id"],
    )
