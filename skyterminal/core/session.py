"""Tmux session management."""

import asyncio
import subprocess
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

        # Clear the pane, send the command with a unique marker
        marker = f"__SKY_END_{id(command)}__"

        # Send command and echo marker when done
        full_cmd = f"{command}; echo '{marker}'"
        self._run_tmux("send-keys", "-t", session_name, full_cmd, "Enter")

        # Poll for the marker in pane output
        output = ""
        elapsed = 0.0
        interval = 0.3

        while elapsed < timeout:
            await asyncio.sleep(interval)
            elapsed += interval

            result = self._run_tmux("capture-pane", "-t", session_name, "-p", "-S", "-100")
            if result.returncode != 0:
                continue

            pane_content = result.stdout
            if marker in pane_content:
                # Extract output between command and marker
                lines = pane_content.split("\n")
                output_lines = []
                capturing = False
                for line in lines:
                    if marker in line:
                        break
                    if capturing:
                        output_lines.append(line)
                    if command in line and not capturing:
                        capturing = True

                output = "\n".join(output_lines).strip()
                # Clean up marker from pane
                break

        if not output and elapsed >= timeout:
            output = "[Command timed out after {:.0f}s]".format(timeout)

        return output

    async def read_pane(self, session_name: str, lines: int = 50) -> str:
        """Read the current pane content (for view-only connections)."""
        self.ensure_session(session_name)
        result = self._run_tmux(
            "capture-pane", "-t", session_name, "-p", "-S", f"-{lines}"
        )
        if result.returncode == 0:
            return result.stdout.rstrip()
        return "[Error reading pane]"
