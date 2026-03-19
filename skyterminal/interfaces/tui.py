"""TUI interface for Sky Terminal using Textual."""

from __future__ import annotations

import asyncio
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import (
    Header,
    Footer,
    Static,
    Input,
    Button,
    DataTable,
    Label,
    Log,
)
from textual.screen import ModalScreen
from textual.binding import Binding

from ..config import Config
from ..core.auth import AuthManager, Permission
from ..core.session import SessionManager
from ..core.connection import ConnectionManager


class AddTokenScreen(ModalScreen[dict | None]):
    """Modal for creating a new connection token."""

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def compose(self) -> ComposeResult:
        with Container(id="add-token-dialog"):
            yield Label("Create Connection Token", id="dialog-title")
            yield Input(placeholder="Label (e.g. 'my-phone')", id="token-label")
            yield Input(placeholder="Telegram User ID (optional)", id="token-telegram-id")
            yield Input(placeholder="Session name (blank = default)", id="token-session")
            with Horizontal(id="permission-row"):
                yield Button("Full Access", id="btn-full", variant="warning")
                yield Button("View Only", id="btn-view", variant="default")
            with Horizontal(id="button-row"):
                yield Button("Cancel", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.dismiss(None)
            return

        label = self.query_one("#token-label", Input).value.strip()
        if not label:
            label = "unnamed"

        tg_id_str = self.query_one("#token-telegram-id", Input).value.strip()
        tg_id = int(tg_id_str) if tg_id_str.isdigit() else None

        session = self.query_one("#token-session", Input).value.strip() or None

        permission = Permission.FULL if event.button.id == "btn-full" else Permission.VIEW

        self.dismiss({
            "label": label,
            "permission": permission,
            "session_name": session,
            "telegram_user_id": tg_id,
        })

    def action_cancel(self) -> None:
        self.dismiss(None)


class SkyTerminalTUI(App):
    """Sky Terminal management TUI."""

    CSS = """
    #main-container {
        height: 100%;
    }
    #status-bar {
        dock: top;
        height: 3;
        background: $primary-background;
        padding: 1;
    }
    #tokens-table {
        height: 1fr;
        margin: 1;
    }
    #sessions-panel {
        height: auto;
        max-height: 12;
        margin: 1;
        border: solid $primary;
        padding: 1;
    }
    #log-panel {
        height: 10;
        margin: 1;
        border: solid $secondary;
    }
    #add-token-dialog {
        width: 60;
        height: auto;
        padding: 2;
        background: $surface;
        border: thick $primary;
        align: center middle;
    }
    #dialog-title {
        text-align: center;
        padding-bottom: 1;
        text-style: bold;
    }
    #permission-row {
        height: 3;
        align: center middle;
        margin-top: 1;
    }
    #button-row {
        height: 3;
        align: center middle;
        margin-top: 1;
    }
    """

    TITLE = "Sky Terminal"
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("a", "add_token", "Add Token"),
        Binding("d", "delete_token", "Delete Token"),
        Binding("r", "refresh", "Refresh"),
        Binding("t", "toggle_telegram", "Telegram On/Off"),
    ]

    def __init__(self, config: Config, auth: AuthManager, sessions: SessionManager,
                 connection: ConnectionManager, telegram_iface=None):
        super().__init__()
        self.config = config
        self.auth = auth
        self.session_mgr = sessions
        self.connection = connection
        self.telegram_iface = telegram_iface
        self.telegram_running = False

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="main-container"):
            yield Static("", id="status-bar")
            yield Static("Sessions", classes="section-title")
            yield Static("", id="sessions-panel")
            yield Static("Connection Tokens", classes="section-title")
            yield DataTable(id="tokens-table")
            yield Log(id="log-panel")
        yield Footer()

    def on_mount(self) -> None:
        self._update_status()
        self._update_sessions()
        self._setup_tokens_table()
        self._refresh_tokens()
        self._log("Sky Terminal started.")

        bot_token = self.config.get("telegram.bot_token")
        if bot_token:
            self._log(f"Telegram bot token configured.")
        else:
            self._log("No Telegram bot token configured. Use config to set one.")

    def _log(self, msg: str):
        log = self.query_one("#log-panel", Log)
        log.write_line(msg)

    def _update_status(self):
        tg_status = "ON" if self.telegram_running else "OFF"
        sessions = self.session_mgr.list_sessions()
        tokens = self.auth.list_tokens()
        status = self.query_one("#status-bar", Static)
        status.update(
            f"  Sessions: {len(sessions)}  |  "
            f"Tokens: {len(tokens)}  |  "
            f"Telegram: {tg_status}"
        )

    def _update_sessions(self):
        sessions = self.session_mgr.list_sessions()
        panel = self.query_one("#sessions-panel", Static)
        if not sessions:
            panel.update("  No active tmux sessions")
            return
        lines = []
        for s in sessions:
            status = "attached" if s.attached else "detached"
            lines.append(f"  {s.name:20s} {s.windows} windows  [{status}]")
        panel.update("\n".join(lines))

    def _setup_tokens_table(self):
        table = self.query_one("#tokens-table", DataTable)
        table.add_columns("Label", "Permission", "Session", "Telegram ID", "Token")

    def _refresh_tokens(self):
        table = self.query_one("#tokens-table", DataTable)
        table.clear()
        for ct in self.auth.list_tokens():
            table.add_row(
                ct.label,
                ct.permission.value,
                ct.session_name or "(default)",
                str(ct.telegram_user_id or "-"),
                ct.token[:12] + "...",
            )

    def action_refresh(self) -> None:
        self._update_status()
        self._update_sessions()
        self._refresh_tokens()
        self._log("Refreshed.")

    def action_add_token(self) -> None:
        def on_result(result: dict | None) -> None:
            if result:
                ct = self.auth.create_token(**result)
                self._refresh_tokens()
                self._update_status()
                self._log(f"Created token '{ct.label}' ({ct.permission.value}) -> {ct.token}")

        self.push_screen(AddTokenScreen(), callback=on_result)

    def action_delete_token(self) -> None:
        table = self.query_one("#tokens-table", DataTable)
        if table.cursor_row is not None:
            tokens = self.auth.list_tokens()
            if 0 <= table.cursor_row < len(tokens):
                ct = tokens[table.cursor_row]
                self.auth.revoke_token(ct.token)
                self._refresh_tokens()
                self._update_status()
                self._log(f"Revoked token '{ct.label}'")

    async def action_toggle_telegram(self) -> None:
        if not self.telegram_iface:
            self._log("No Telegram bot token configured.")
            return

        if self.telegram_running:
            await self.telegram_iface.stop()
            self.telegram_running = False
            self._log("Telegram bot stopped.")
        else:
            try:
                await self.telegram_iface.start()
                self.telegram_running = True
                self._log("Telegram bot started!")
            except Exception as e:
                self._log(f"Failed to start Telegram bot: {e}")

        self._update_status()
