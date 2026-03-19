"""Sky Terminal - main entry point."""

from __future__ import annotations

import argparse
import asyncio
import sys

from .config import Config
from .core.auth import AuthManager, Permission
from .core.session import SessionManager
from .core.connection import ConnectionManager


def setup_telegram(config, auth, connection):
    bot_token = config.get("telegram.bot_token")
    if not bot_token:
        return None
    from .interfaces.telegram import TelegramInterface
    return TelegramInterface(bot_token, auth, connection)


def cmd_tui(args, config, auth, sessions, connection):
    """Launch the TUI."""
    from .interfaces.tui import SkyTerminalTUI
    telegram = setup_telegram(config, auth, connection)
    app = SkyTerminalTUI(config, auth, sessions, connection, telegram)
    app.run()


def cmd_setup(args, config, auth, sessions, connection):
    """Interactive first-time setup."""
    print("=== Sky Terminal Setup ===\n")

    # Telegram
    bot_token = config.get("telegram.bot_token")
    if bot_token:
        print(f"Telegram bot token: {bot_token[:8]}...{bot_token[-4:]}")
        change = input("Change it? [y/N] ").strip().lower()
        if change == "y":
            bot_token = None
    if not bot_token:
        bot_token = input("Telegram bot token (from @BotFather): ").strip()
        if bot_token:
            config.set("telegram.bot_token", bot_token)
            print("Saved.\n")

    # Create a connection token
    print("\nCreate a connection token for Telegram?")
    tg_id = input("Your Telegram user ID (send /start to @userinfobot): ").strip()
    if tg_id.isdigit():
        label = input("Label for this connection [my-terminal]: ").strip() or "my-terminal"
        perm = input("Permission (full/view) [full]: ").strip().lower() or "full"
        permission = Permission.FULL if perm == "full" else Permission.VIEW

        ct = auth.create_token(
            label=label,
            permission=permission,
            telegram_user_id=int(tg_id),
        )
        print(f"\nToken created: {ct.token}")
        print(f"  Label: {ct.label}")
        print(f"  Permission: {ct.permission.value}")
        print(f"  Telegram User ID: {ct.telegram_user_id}")

    print(f"\nConfig saved to: {config.path}")
    print("Run 'skyterminal' or 'python -m skyterminal' to launch the TUI.")


def cmd_headless(args, config, auth, sessions, connection):
    """Run headless (Telegram bot only, no TUI)."""
    telegram = setup_telegram(config, auth, connection)
    if not telegram:
        print("Error: No Telegram bot token configured. Run setup first.")
        sys.exit(1)

    async def run():
        print("Sky Terminal - Headless Mode")
        print("Telegram bot starting...")
        await telegram.start()
        print("Bot is running. Press Ctrl+C to stop.")
        try:
            while True:
                await asyncio.sleep(1)
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
        finally:
            await telegram.stop()
            print("\nStopped.")

    asyncio.run(run())


def cmd_token(args, config, auth, sessions, connection):
    """Manage connection tokens from CLI."""
    if args.token_action == "list":
        tokens = auth.list_tokens()
        if not tokens:
            print("No connection tokens.")
            return
        for ct in tokens:
            print(f"  {ct.label:20s}  {ct.permission.value:5s}  "
                  f"tg:{ct.telegram_user_id or '-':>12s}  "
                  f"session:{ct.session_name or 'default':>15s}  "
                  f"{ct.token[:16]}...")

    elif args.token_action == "create":
        perm = Permission.FULL if args.permission == "full" else Permission.VIEW
        tg_id = int(args.telegram_id) if args.telegram_id else None
        ct = auth.create_token(
            label=args.label,
            permission=perm,
            session_name=args.session,
            telegram_user_id=tg_id,
        )
        print(f"Created token: {ct.token}")

    elif args.token_action == "revoke":
        if auth.revoke_token(args.token_value):
            print("Token revoked.")
        else:
            print("Token not found.")


def main():
    parser = argparse.ArgumentParser(
        prog="skyterminal",
        description="Sky Terminal - Connect to tmux sessions from anywhere",
    )
    parser.add_argument("--config", help="Config file path")

    sub = parser.add_subparsers(dest="command")

    # TUI (default)
    sub.add_parser("tui", help="Launch the TUI (default)")

    # Setup
    sub.add_parser("setup", help="Interactive setup")

    # Headless
    sub.add_parser("headless", help="Run headless (Telegram bot only)")

    # Token management
    token_parser = sub.add_parser("token", help="Manage connection tokens")
    token_sub = token_parser.add_subparsers(dest="token_action")
    token_sub.add_parser("list", help="List tokens")

    create_p = token_sub.add_parser("create", help="Create a token")
    create_p.add_argument("label", help="Token label")
    create_p.add_argument("--permission", choices=["full", "view"], default="full")
    create_p.add_argument("--telegram-id", help="Telegram user ID")
    create_p.add_argument("--session", help="Tmux session name")

    revoke_p = token_sub.add_parser("revoke", help="Revoke a token")
    revoke_p.add_argument("token_value", help="Token to revoke")

    args = parser.parse_args()

    # Initialize core
    config = Config(args.config)
    sessions = SessionManager(config.get("default_shell", "/bin/bash"))
    auth = AuthManager(config)
    connection = ConnectionManager(auth, sessions)

    commands = {
        "setup": cmd_setup,
        "tui": cmd_tui,
        "headless": cmd_headless,
        "token": cmd_token,
    }

    handler = commands.get(args.command or "tui")
    if handler:
        handler(args, config, auth, sessions, connection)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
