<p align="center">
  <h1 align="center">Sky Terminal</h1>
  <p align="center">Connect to your terminal from anywhere. Use Telegram, Discord, or any messaging app as a remote shell.</p>
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> •
  <a href="#features">Features</a> •
  <a href="#setup">Setup</a> •
  <a href="#usage">Usage</a> •
  <a href="#faq">FAQ</a> •
  <a href="#roadmap">Roadmap</a> •
  <a href="#license">License</a>
</p>

---

## What is Sky Terminal?

Sky Terminal is a serverless, open-source tool that lets you control your machine's terminal from messaging apps. It runs on your host machine, connects to tmux sessions, and bridges them to services like Telegram — so you can run commands on your server from your phone, tablet, or any device with a messaging app.

No cloud servers. No port forwarding. No SSH keys on your phone. Just message your bot and get terminal output back.

```
You (Telegram)              Your Machine
┌──────────────┐           ┌──────────────────┐           ┌────────────┐
│  "ls -la"    │ ────────▶ │   Sky Terminal    │ ────────▶ │   tmux     │
│              │           │                   │           │  session   │
│  ┌────────┐  │ ◀──────── │  • Auth manager   │ ◀──────── │            │
│  │output  │  │           │  • Session mgr    │           │ $ ls -la   │
│  │here    │  │           │  • Permissions     │           │ > file.txt │
│  └────────┘  │           └──────────────────┘           └────────────┘
└──────────────┘
```

## Features

- **Telegram Bot** — Send commands from Telegram, get output back in code blocks
- **TUI Dashboard** — Manage sessions, tokens, and connections from a rich terminal interface
- **Headless Mode** — Run as a background service with no UI required
- **Token-Based Auth** — Each connection gets its own token with configurable permissions
- **Permission Levels** — Grant full access or view-only per connection
- **tmux Integration** — Commands execute in real tmux sessions you can also attach to locally
- **Multi-Session** — Create and manage multiple tmux sessions, assign connections to specific ones
- **Serverless** — Runs entirely on your machine, no cloud infrastructure needed
- **Async Core** — Built on asyncio for responsive, non-blocking operation

## Quick Start

```bash
# Clone the repo
git clone https://github.com/nealgentry/Sky-Terminal.git
cd Sky-Terminal

# Install dependencies
pip install -r requirements.txt

# Run interactive setup
python -m skyterminal setup

# Start Sky Terminal
python -m skyterminal headless
```

That's it. Message your Telegram bot and start running commands.

## Setup

### Prerequisites

- **Python 3.9+**
- **tmux** installed on your machine
- **A Telegram bot token**

### Step 1: Install tmux (if needed)

```bash
# Debian/Ubuntu
sudo apt install tmux

# Fedora/RHEL
sudo dnf install tmux

# macOS
brew install tmux
```

### Step 2: Create a Telegram Bot

1. Open Telegram and message [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the prompts to name your bot
3. Copy the **bot token** (looks like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### Step 3: Get Your Telegram User ID

1. Message [@userinfobot](https://t.me/userinfobot) on Telegram
2. It will reply with your **numeric user ID**

### Step 4: Run Setup

```bash
python -m skyterminal setup
```

This will prompt you for:
- Your Telegram bot token
- Your Telegram user ID
- A label for your connection
- Permission level (full or view-only)

Configuration is saved to `~/.skyterminal/config.json`.

### Step 5: Start Sky Terminal

```bash
# Headless mode (recommended for servers)
python -m skyterminal headless

# Or launch the TUI
python -m skyterminal
```

### Step 6: Test It

Open Telegram, find your bot, and send `/start`. Then try sending `whoami` or `ls`.

## Usage

### Telegram Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Check connection status and permissions |
| `/sessions` | List all active tmux sessions |
| `/view` | View the current terminal pane output |
| Any text | Executed as a shell command |

### Running Modes

#### Headless (Telegram bot only)
```bash
python -m skyterminal headless
```
Best for servers and background operation. Run with `nohup` or in a tmux/screen session for persistence:
```bash
nohup python -m skyterminal headless > /var/log/skyterminal.log 2>&1 &
```

#### TUI Dashboard
```bash
python -m skyterminal
```
Interactive terminal UI for managing everything:

| Key | Action |
|-----|--------|
| `a` | Add a new connection token |
| `d` | Delete selected token |
| `r` | Refresh sessions and tokens |
| `t` | Toggle Telegram bot on/off |
| `q` | Quit |

### Token Management (CLI)

```bash
# List all connection tokens
python -m skyterminal token list

# Create a full-access token linked to a Telegram user
python -m skyterminal token create my-phone --telegram-id 123456789 --permission full

# Create a view-only token for someone else
python -m skyterminal token create coworker --telegram-id 987654321 --permission view

# Create a token for a specific tmux session
python -m skyterminal token create deploy-monitor --telegram-id 123456789 --permission view --session deploy

# Revoke a token
python -m skyterminal token revoke <token-string>
```

### Permission Levels

| Level | Can Execute Commands | Can View Output | Use Case |
|-------|---------------------|-----------------|----------|
| `full` | Yes | Yes | Personal use, trusted access |
| `view` | No | Yes | Monitoring, sharing with teammates |

### Working with tmux Sessions

Sky Terminal auto-creates a default `skyterminal` tmux session. You can also attach to it locally to see commands come in:

```bash
# Attach to the session locally
tmux attach -t skyterminal

# List all sessions
tmux list-sessions
```

Assign different connections to different sessions to isolate workloads:
```bash
python -m skyterminal token create web-server --telegram-id 123456789 --session webserver
python -m skyterminal token create db-monitor --telegram-id 123456789 --session database --permission view
```

## Configuration

Config lives at `~/.skyterminal/config.json`:

```json
{
  "host_token": "auto-generated-host-token",
  "telegram": {
    "bot_token": "your-bot-token-here",
    "allowed_users": []
  },
  "connections": [
    {
      "token": "connection-token",
      "label": "my-phone",
      "permission": "full",
      "session_name": null,
      "telegram_user_id": 123456789
    }
  ],
  "default_shell": "/bin/bash",
  "max_output_length": 4000
}
```

## Security

- **No open ports** — Sky Terminal doesn't expose any network ports. Communication goes through Telegram's API (outbound HTTPS only).
- **Token-based auth** — Every connection requires a unique token tied to a specific Telegram user ID. Unauthorized users are rejected.
- **Permission scoping** — Tokens can be restricted to view-only and locked to specific tmux sessions.
- **Local config** — All tokens and configuration are stored locally on your machine. Nothing is sent to third-party servers.
- **Revocable access** — Revoke any token instantly from the CLI or TUI.

### Security Recommendations

- Do not run Sky Terminal as root
- Use view-only tokens when sharing access with others
- Regularly review and revoke unused tokens
- Keep your Telegram bot token secret — anyone with it can receive messages sent to your bot
- Consider running Sky Terminal in a restricted user account for additional isolation

## FAQ

### General

**Q: Do I need a server or cloud account to use Sky Terminal?**
A: No. Sky Terminal runs entirely on your local machine. It communicates through Telegram's bot API using outbound HTTPS — no incoming ports, no cloud services, no subscriptions.

**Q: Is this like SSH?**
A: Similar concept, different approach. SSH requires port forwarding, firewall rules, and key management. Sky Terminal uses messaging apps as the transport layer, so it works from any device with Telegram installed — no client setup needed.

**Q: Can I use this on a headless server?**
A: Yes. Run `python -m skyterminal headless` and it operates entirely in the background. Pair it with `nohup`, `systemd`, or run it inside its own tmux/screen session for persistence.

**Q: What happens if Sky Terminal crashes?**
A: Your tmux sessions keep running — they're independent processes. Just restart Sky Terminal and you'll reconnect to the same sessions. No work is lost.

### Setup & Configuration

**Q: How do I find my Telegram user ID?**
A: Message [@userinfobot](https://t.me/userinfobot) on Telegram. It replies instantly with your numeric ID.

**Q: Can I run multiple instances of Sky Terminal?**
A: Yes, but each needs its own Telegram bot (you can't have two processes polling the same bot). Create a separate bot via @BotFather for each instance.

**Q: Where is the config stored?**
A: `~/.skyterminal/config.json`. You can specify a different path with `--config /path/to/config.json`.

**Q: Can I change the default tmux session name?**
A: Assign tokens to specific sessions with `--session myname`. The default session is called `skyterminal`.

### Security

**Q: Is it safe to run commands over Telegram?**
A: Telegram uses end-to-end encryption for bot API traffic over HTTPS. However, Telegram's servers do process the messages. For highly sensitive operations, consider the risk. Sky Terminal is best suited for general server management, not transmitting passwords or secrets.

**Q: What if someone finds my Telegram bot?**
A: They can message it, but Sky Terminal will reject them — only Telegram user IDs with registered tokens can execute commands. Unauthorized users see a "Not authorized" message and nothing else.

**Q: Can I restrict what commands a user can run?**
A: Currently, permission levels are full access or view-only. Command-level filtering (allowlists/blocklists) is on the roadmap.

**Q: What if I lose my bot token?**
A: Revoke it via [@BotFather](https://t.me/BotFather) (`/revoke`), create a new bot, and update your config with `python -m skyterminal setup`.

### Troubleshooting

**Q: The bot responds to /start but commands return "(no output)"**
A: Make sure tmux is installed and a session exists. Run `tmux list-sessions` to check. Sky Terminal auto-creates sessions, but if tmux itself isn't installed, commands will fail silently.

**Q: The bot doesn't respond at all**
A: Check that Sky Terminal is running (`ps aux | grep skyterminal`). Verify your bot token is correct in `~/.skyterminal/config.json`. Check logs if running with output redirection.

**Q: Commands are slow to return**
A: Sky Terminal polls for command completion every 0.3 seconds with a 30-second timeout. Long-running commands will take time. Very fast commands typically return in under a second.

**Q: Can I run interactive commands (like vim or top)?**
A: No. Sky Terminal captures command output after execution completes. Interactive/TUI programs that require a live terminal won't work through the messaging interface. Use `tmux attach` locally for those.

**Q: Output is cut off**
A: Telegram has a 4096 character message limit. Sky Terminal truncates output to the last 4000 characters. For large outputs, pipe to `head`, `tail`, or redirect to a file and `cat` the relevant part.

## Roadmap

- [ ] Discord bot interface
- [ ] Web GUI (Flask-based)
- [ ] Command allowlists/blocklists per token
- [ ] Session recording and playback
- [ ] File upload/download through Telegram
- [ ] Systemd service file for auto-start
- [ ] Multi-message output for results exceeding Telegram limits
- [ ] Webhook mode (alternative to polling)
- [ ] Matrix, Slack, and other messaging platform support

## Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.

1. Fork the repo
2. Create your feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes
4. Push to the branch (`git push origin feature/my-feature`)
5. Open a pull request

## License

MIT License — see [LICENSE](LICENSE) for details.
