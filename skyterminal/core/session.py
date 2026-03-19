"""Tmux session management."""

from __future__ import annotations

import asyncio
import os
import subprocess
import tempfile
import uuid
from dataclasses import dataclass


@dataclass
class TmuxSession:
    name: str
    windows: int
    created: str
    attached: bool


class SessionManager:
    """Manages tmux sessions and command execution."""

    def __init__(self, default_shell: str = "/bin/bash"):
        self.default_shell = default_shell

    @staticmethod
    def _run_tmux(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["tmux", *args],
            capture_output=True,
            text=True,
            timeout=10,
        )

    def is_tmux_available(self) -> bool:
        try:
            result = self._run_tmux("list-sessions")
            return result.returncode in (0, 1)  # 1 = no sessions
        except FileNotFoundError:
            return False

    def list_sessions(self) -> list[TmuxSession]:
        result = self._run_tmux(
            "list-sessions", "-F",
            "#{session_name}|#{session_windows}|#{session_created}|#{session_attached}"
        )
        if result.returncode != 0:
            return []

        sessions = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("|")
            sessions.append(TmuxSession(
                name=parts[0],
                windows=int(parts[1]),
                created=parts[2],
                attached=parts[3] == "1",
            ))
        return sessions

    def create_session(self, name: str) -> bool:
        result = self._run_tmux(
            "new-session", "-d", "-s", name, "-x", "200", "-y", "50"
        )
        return result.returncode == 0

    def kill_session(self, name: str) -> bool:
        result = self._run_tmux("kill-session", "-t", name)
        return result.returncode == 0

    def ensure_session(self, name: str = "skyterminal") -> str:
        sessions = self.list_sessions()
        for s in sessions:
            if s.name == name:
                return name
        self.create_session(name)
        return name

    async def execute_command(
        self, session_name: str, command: str, timeout: float = 30
    ) -> str:
        """Send a command to a tmux session and capture the output."""
        self.ensure_session(session_name)

        # Write output to a temp file to avoid pane-scraping issues
        uid = uuid.uuid4().hex[:12]
        out_file = f"/tmp/sky_{uid}.out"
        done_file = f"/tmp/sky_{uid}.done"

        # Run command, redirect output to file, then touch done marker
        full_cmd = (
            f"{{ {command}; }} > {out_file} 2>&1; "
            f"touch {done_file}"
        )
        self._run_tmux("send-keys", "-t", session_name, full_cmd, "Enter")

        # Poll for the done file
        elapsed = 0.0
        interval = 0.3

        while elapsed < timeout:
            await asyncio.sleep(interval)
            elapsed += interval

            if os.path.exists(done_file):
                try:
                    with open(out_file, "r") as f:
                        output = f.read().strip()
                finally:
                    # Clean up temp files
                    for f in (out_file, done_file):
                        try:
                            os.remove(f)
                        except OSError:
                            pass
                return output

        # Clean up on timeout
        for f in (out_file, done_file):
            try:
                os.remove(f)
            except OSError:
                pass
        return "[Command timed out after {:.0f}s]".format(timeout)

    async def read_pane(self, session_name: str, lines: int = 50) -> str:
        """Read the current pane content (for view-only connections)."""
        self.ensure_session(session_name)
        result = self._run_tmux(
            "capture-pane", "-t", session_name, "-p", "-S", f"-{lines}"
        )
        if result.returncode == 0:
            return result.stdout.rstrip()
        return "[Error reading pane]"
