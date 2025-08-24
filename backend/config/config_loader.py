"""Configuration loader for model registry and runtime settings."""
from __future__ import annotations
import os
import threading
from pathlib import Path
from typing import Any, Dict, List

try:
    import yaml  # type: ignore
except Exception:  # fallback minimal parser if pyyaml absent
    yaml = None

_lock = threading.Lock()
_cache: Dict[str, Any] = {}
_mtime = 0.0

def load_model_registry(path: str | None = None, force: bool = False) -> Dict[str, Any]:
    global _cache, _mtime
    path = path or os.getenv("MODEL_REGISTRY_PATH", str(Path(__file__).parent / "model_registry.yml"))
    p = Path(path)
    if not p.exists():
        return {"models": [], "routing_rules": []}
    stat = p.stat()
    with _lock:
        if not force and _cache and stat.st_mtime == _mtime:
            return _cache
        text = p.read_text(encoding="utf-8")
        if yaml:
            data = yaml.safe_load(text) or {}
        else:
            data = {"raw": text}
        _cache = data
        _mtime = stat.st_mtime
        return data

def list_models() -> List[Dict[str, Any]]:
    reg = load_model_registry()
    return reg.get("models", [])

def get_model(model_id: str) -> Dict[str, Any] | None:
    for m in list_models():
        if m.get("id") == model_id:
            return m
    return None

def get_routing_rules() -> List[Dict[str, Any]]:
    reg = load_model_registry()
    return reg.get("routing_rules", [])

def reload_registry() -> Dict[str, Any]:
    return load_model_registry(force=True)

def get_env_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.lower() in {"1", "true", "yes", "on"}

def get_env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default
