"""Connection point management."""

from __future__ import annotations

from dataclasses import dataclass
from .auth import AuthManager, ConnectionToken, Permission
from .session import SessionManager


@dataclass
class ConnectionPoint:
    token: ConnectionToken
    session_name: str


class ConnectionManager:
    """Manages connection points between interfaces and tmux sessions."""

    def __init__(self, auth: AuthManager, sessions: SessionManager):
        self.auth = auth
        self.sessions = sessions

    async def handle_command(
        self, token: ConnectionToken, command: str,
        session_override: str | None = None,
    ) -> str:
        """Process a command from an authenticated connection."""
        session = session_override or token.session_name or "skyterminal"

        if token.permission == Permission.VIEW:
            return await self.sessions.read_pane(session)

        self.sessions.ensure_session(session)
        return await self.sessions.execute_command(session, command)

    async def read_output(
        self, token: ConnectionToken,
        session_override: str | None = None,
    ) -> str:
        """Read current terminal output for any permission level."""
        session = session_override or token.session_name or "skyterminal"
        return await self.sessions.read_pane(session)
