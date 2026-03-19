"""Telegram bot interface for Sky Terminal."""

from __future__ import annotations

import asyncio
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from ..core.auth import AuthManager, Permission
from ..core.connection import ConnectionManager

logger = logging.getLogger("skyterminal.telegram")


class TelegramInterface:
    def __init__(
        self,
        bot_token: str,
        auth: AuthManager,
        connection: ConnectionManager,
    ):
        self.bot_token = bot_token
        self.auth = auth
        self.connection = connection
        self.app: Application | None = None
        # Runtime session overrides per user (not persisted)
        self._user_sessions: dict[int, str] = {}

    def _get_token(self, user_id: int):
        return self.auth.verify_telegram_user(user_id)

    def _get_session(self, user_id: int, token) -> str:
        """Get the active session for a user (runtime override or token default)."""
        return self._user_sessions.get(user_id, token.session_name or "skyterminal")

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        token = self._get_token(user_id)
        if token:
            current = self._get_session(user_id, token)
            await update.message.reply_text(
                f"Connected to Sky Terminal.\n"
                f"Session: {current}\n"
                f"Permission: {token.permission.value}\n\n"
                f"Commands:\n"
                f"/sessions - list sessions\n"
                f"/switch <name> - switch session\n"
                f"/newsession <name> - create session\n"
                f"/killsession <name> - kill session\n"
                f"/view - view pane output\n\n"
                f"Send any text to execute as a command."
            )
        else:
            await update.message.reply_text(
                f"Not authorized.\n"
                f"Your Telegram user ID: {user_id}\n\n"
                f"Ask the host to create a connection token for your user ID."
            )

    async def cmd_sessions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        token = self._get_token(user_id)
        if not token:
            await update.message.reply_text("Not authorized.")
            return

        current = self._get_session(user_id, token)
        sessions = self.connection.sessions.list_sessions()
        if not sessions:
            await update.message.reply_text("No active tmux sessions.")
            return

        text = "Active sessions:\n\n"
        for s in sessions:
            status = "attached" if s.attached else "detached"
            marker = " <-- active" if s.name == current else ""
            text += f"  {s.name} ({s.windows} windows, {status}){marker}\n"
        text += f"\nUse /switch <name> to change session."
        await update.message.reply_text(f"```\n{text}```", parse_mode="Markdown")

    async def cmd_switch(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        token = self._get_token(user_id)
        if not token:
            await update.message.reply_text("Not authorized.")
            return

        if not context.args:
            current = self._get_session(user_id, token)
            await update.message.reply_text(
                f"Current session: {current}\n"
                f"Usage: /switch <session-name>"
            )
            return

        name = context.args[0]
        sessions = self.connection.sessions.list_sessions()
        session_names = [s.name for s in sessions]

        if name not in session_names:
            await update.message.reply_text(
                f"Session '{name}' not found.\n"
                f"Available: {', '.join(session_names) or '(none)'}\n\n"
                f"Use /newsession {name} to create it."
            )
            return

        self._user_sessions[user_id] = name
        await update.message.reply_text(f"Switched to session: {name}")

    async def cmd_newsession(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        token = self._get_token(user_id)
        if not token:
            await update.message.reply_text("Not authorized.")
            return

        if token.permission != Permission.FULL:
            await update.message.reply_text("Full access required to create sessions.")
            return

        if not context.args:
            await update.message.reply_text("Usage: /newsession <name>")
            return

        name = context.args[0]
        if self.connection.sessions.create_session(name):
            self._user_sessions[user_id] = name
            await update.message.reply_text(
                f"Created and switched to session: {name}"
            )
        else:
            await update.message.reply_text(
                f"Failed to create session '{name}'. It may already exist."
            )

    async def cmd_killsession(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        token = self._get_token(user_id)
        if not token:
            await update.message.reply_text("Not authorized.")
            return

        if token.permission != Permission.FULL:
            await update.message.reply_text("Full access required to kill sessions.")
            return

        if not context.args:
            await update.message.reply_text("Usage: /killsession <name>")
            return

        name = context.args[0]
        if name == "skyterminal":
            await update.message.reply_text("Cannot kill the default session.")
            return

        if self.connection.sessions.kill_session(name):
            # If user was on this session, switch back to default
            if self._user_sessions.get(user_id) == name:
                del self._user_sessions[user_id]
            await update.message.reply_text(f"Killed session: {name}")
        else:
            await update.message.reply_text(f"Session '{name}' not found.")

    async def cmd_view(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        token = self._get_token(user_id)
        if not token:
            await update.message.reply_text("Not authorized.")
            return

        session = self._get_session(user_id, token)
        output = await self.connection.read_output(token, session_override=session)
        if output:
            # Telegram has a 4096 char limit
            if len(output) > 4000:
                output = output[-4000:]
            await update.message.reply_text(f"```\n{output}\n```", parse_mode="Markdown")
        else:
            await update.message.reply_text("(empty pane)")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        token = self._get_token(user_id)

        if not token:
            await update.message.reply_text(
                f"Not authorized. Your ID: {user_id}"
            )
            return

        command = update.message.text.strip()
        if not command:
            return

        if token.permission == Permission.VIEW:
            await update.message.reply_text(
                "View-only access. Use /view to see the terminal."
            )
            return

        # Send typing indicator
        await update.message.chat.send_action("typing")

        try:
            session = self._get_session(user_id, token)
            output = await self.connection.handle_command(token, command, session_override=session)
            if not output:
                output = "(no output)"
            # Telegram message limit
            if len(output) > 4000:
                output = output[-4000:]
            await update.message.reply_text(f"```\n{output}\n```", parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Command execution error: {e}")
            await update.message.reply_text(f"Error: {e}")

    async def start(self):
        self.app = Application.builder().token(self.bot_token).build()

        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("sessions", self.cmd_sessions))
        self.app.add_handler(CommandHandler("switch", self.cmd_switch))
        self.app.add_handler(CommandHandler("newsession", self.cmd_newsession))
        self.app.add_handler(CommandHandler("killsession", self.cmd_killsession))
        self.app.add_handler(CommandHandler("view", self.cmd_view))
        self.app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, self.handle_message
        ))

        logger.info("Telegram bot starting...")
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()

    async def stop(self):
        if self.app:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
