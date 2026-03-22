import json
import os
from pathlib import Path


DEFAULT_CONFIG = {
    "mongodb": {
        "uri": "mongodb://localhost:27017/",
    },
    "cors": {
        "allow_origins": ["http://localhost:3000", "http://localhost:5173"],
    },
}


def _merge_dicts(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(merged.get(key), dict) and isinstance(value, dict):
            merged[key] = _merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_config() -> dict:
    config_path = Path(__file__).with_name("config.json")
    try:
        with config_path.open("r", encoding="utf-8") as config_file:
            loaded_config = json.load(config_file)
    except FileNotFoundError:
        return DEFAULT_CONFIG

    if not isinstance(loaded_config, dict):
        return DEFAULT_CONFIG

    return _merge_dicts(DEFAULT_CONFIG, loaded_config)


def _load_local_env() -> None:
    env_path = Path(__file__).with_name(".env.local")
    try:
        lines = env_path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue

        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_local_env()
CONFIG = _load_config()


def get_mongodb_uri() -> str:
    return os.environ.get("MONGODB_URI", CONFIG["mongodb"]["uri"])


def get_mongodb_with_cred_uri() -> str | None:
    return os.environ.get("MONGODB_WITH_CRED_URI") or os.environ.get("MONGODB_URI")


def get_cors_allow_origins() -> list[str]:
    env_value = os.environ.get("CORS_ALLOW_ORIGINS")
    if env_value:
        return [origin.strip() for origin in env_value.split(",") if origin.strip()]

    configured_origins = CONFIG["cors"].get("allow_origins", [])
    if isinstance(configured_origins, list):
        return [str(origin) for origin in configured_origins]

    return []