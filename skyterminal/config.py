"""Configuration management for Sky Terminal."""

from __future__ import annotations

import json
import os
import secrets
from pathlib import Path
from typing import Optional

DEFAULT_CONFIG_PATH = Path.home() / ".skyterminal" / "config.json"

DEFAULT_CONFIG = {
    "host_token": None,
    "telegram": {
        "bot_token": None,
        "allowed_users": []
    },
    "connections": [],
    "default_shell": os.environ.get("SHELL", "/bin/bash"),
    "max_output_length": 4000,
}


class Config:
    def __init__(self, path: str | None = None):
        self.path = Path(path) if path else DEFAULT_CONFIG_PATH
        self.data = {}
        self.load()

    def load(self):
        if self.path.exists():
            with open(self.path, "r") as f:
                self.data = json.load(f)
        else:
            self.data = DEFAULT_CONFIG.copy()
            if not self.data["host_token"]:
                self.data["host_token"] = secrets.token_hex(32)
            self.save()

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w") as f:
            json.dump(self.data, f, indent=2)

    def get(self, key: str, default=None):
        keys = key.split(".")
        val = self.data
        for k in keys:
            if isinstance(val, dict):
                val = val.get(k)
            else:
                return default
        return val if val is not None else default

    def set(self, key: str, value):
        keys = key.split(".")
        d = self.data
        for k in keys[:-1]:
            if k not in d or not isinstance(d[k], dict):
                d[k] = {}
            d = d[k]
        d[keys[-1]] = value
        self.save()
