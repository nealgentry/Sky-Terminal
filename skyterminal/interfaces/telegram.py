"""Telegram bot interface for Sky Terminal."""

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

    def _get_token(self, user_id: int):
        return self.auth.verify_telegram_user(user_id)

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        token = self._get_token(user_id)
        if token:
            await update.message.reply_text(
                f"Connected to Sky Terminal.\n"
                f"Session: {token.session_name or 'skyterminal'}\n"
                f"Permission: {token.permission.value}\n\n"
                f"Send any command to execute it."
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

        sessions = self.connection.sessions.list_sessions()
        if not sessions:
            await update.message.reply_text("No active tmux sessions.")
            return

        text = "Active sessions:\n\n"
        for s in sessions:
            status = "attached" if s.attached else "detached"
            text += f"  {s.name} ({s.windows} windows, {status})\n"
        await update.message.reply_text(f"```\n{text}```", parse_mode="Markdown")

    async def cmd_view(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        token = self._get_token(user_id)
        if not token:
            await update.message.reply_text("Not authorized.")
            return

        output = await self.connection.read_output(token)
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
            output = await self.connection.handle_command(token, command)
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
