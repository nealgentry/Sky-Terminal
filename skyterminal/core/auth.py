"""Authentication and permission management."""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Permission(Enum):
    VIEW = "view"
    FULL = "full"


@dataclass
class ConnectionToken:
    token: str
    label: str
    permission: Permission
    session_name: Optional[str] = None  # None = access all sessions
    telegram_user_id: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "token": self.token,
            "label": self.label,
            "permission": self.permission.value,
            "session_name": self.session_name,
            "telegram_user_id": self.telegram_user_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ConnectionToken":
        return cls(
            token=data["token"],
            label=data["label"],
            permission=Permission(data["permission"]),
            session_name=data.get("session_name"),
            telegram_user_id=data.get("telegram_user_id"),
        )


class AuthManager:
    def __init__(self, config):
        self.config = config
        self._tokens: dict[str, ConnectionToken] = {}
        self._load_tokens()

    def _load_tokens(self):
        connections = self.config.get("connections") or []
        for conn in connections:
            ct = ConnectionToken.from_dict(conn)
            self._tokens[ct.token] = ct

    def _save_tokens(self):
        self.config.set("connections", [t.to_dict() for t in self._tokens.values()])

    def create_token(
        self,
        label: str,
        permission: Permission,
        session_name: str | None = None,
        telegram_user_id: int | None = None,
    ) -> ConnectionToken:
        token = secrets.token_hex(16)
        ct = ConnectionToken(
            token=token,
            label=label,
            permission=permission,
            session_name=session_name,
            telegram_user_id=telegram_user_id,
        )
        self._tokens[token] = ct
        self._save_tokens()
        return ct

    def verify_token(self, token: str) -> ConnectionToken | None:
        return self._tokens.get(token)

    def verify_telegram_user(self, user_id: int) -> ConnectionToken | None:
        for ct in self._tokens.values():
            if ct.telegram_user_id == user_id:
                return ct
        return None

    def list_tokens(self) -> list[ConnectionToken]:
        return list(self._tokens.values())

    def revoke_token(self, token: str) -> bool:
        if token in self._tokens:
            del self._tokens[token]
            self._save_tokens()
            return True
        return False
