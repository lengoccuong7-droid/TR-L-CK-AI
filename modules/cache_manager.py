import json
import time
import hashlib
from pathlib import Path
from config import CACHE_DIR, DEFAULT_CACHE_TTL_MINUTES

def _get_cache_path(key: str) -> Path:
    hashed_key = hashlib.md5(key.encode('utf-8')).hexdigest()
    return CACHE_DIR / f"{hashed_key}.json"

def get_cache(key: str, ttl_minutes: int = DEFAULT_CACHE_TTL_MINUTES):
    path = _get_cache_path(key)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        timestamp = data.get("_cached_at", 0)
        if time.time() - timestamp > ttl_minutes * 60:
            return None
        return data.get("payload")
    except Exception:
        return None

def set_cache(key: str, payload: dict):
    path = _get_cache_path(key)
    try:
        data = {
            "_cached_at": time.time(),
            "payload": payload
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Lỗi ghi cache: {e}")
