import copy


def censor_config(config: dict) -> dict:
    unsafe_keys = ("db_password", "token")
    config_copy = copy.deepcopy(config)

    for key, value in config_copy.items():
        if key in unsafe_keys:
            config_copy[key] = '***'
            continue

        if isinstance(value, dict):
            config_copy[key] = censor_config(value)

    return config_copy

