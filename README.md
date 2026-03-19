# Sky Terminal

Connect to tmux sessions from anywhere. Use Telegram, Discord, or any messaging app as your terminal.

## Features

- **TUI Dashboard** — Manage sessions, tokens, and connections from a rich terminal UI
- **Telegram Bot** — Send commands and get output via Telegram
- **Auth & Permissions** — Token-based auth with view-only or full access per connection
- **tmux Integration** — Connects to real tmux sessions on your machine
- **Headless Mode** — Run as a background service without a UI

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# First-time setup (configures Telegram bot token + creates your first auth token)
python -m skyterminal setup

# Launch the TUI
python -m skyterminal

# Or run headless (Telegram bot only)
python -m skyterminal headless
```

## Setup

1. Create a Telegram bot via [@BotFather](https://t.me/BotFather) and get your bot token
2. Get your Telegram user ID from [@userinfobot](https://t.me/userinfobot)
3. Run `python -m skyterminal setup` and enter both values
4. Start Sky Terminal and press `t` in the TUI to activate the Telegram bot
5. Message your bot — every message is executed as a command

## Usage

### TUI Keybindings

| Key | Action |
|-----|--------|
| `a` | Add connection token |
| `d` | Delete selected token |
| `r` | Refresh sessions/tokens |
| `t` | Toggle Telegram bot on/off |
| `q` | Quit |

### CLI Token Management

```bash
# List tokens
python -m skyterminal token list

# Create a full-access token for Telegram user
python -m skyterminal token create my-phone --telegram-id 123456789 --permission full

# Create a view-only token
python -m skyterminal token create viewer --telegram-id 987654321 --permission view

# Revoke a token
python -m skyterminal token revoke <token>
```

### Telegram Bot Commands

- `/start` — Check connection status
- `/sessions` — List active tmux sessions
- `/view` — View current terminal output
- Any other message is executed as a shell command

## Requirements

- Python 3.11+
- tmux installed on the host machine
- A Telegram bot token (from @BotFather)

## License

MIT
