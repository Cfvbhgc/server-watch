# Server Watch Bot

Telegram bot for real-time server monitoring. Tracks CPU, RAM, disk usage, and network I/O. Generates matplotlib charts and sends them as photos. Supports configurable alert thresholds.

## Features

- `/status` - full system overview (CPU, RAM, disk, uptime, top processes)
- `/cpu` - detailed CPU info with per-core breakdown + usage chart
- `/ram` - memory usage details + chart
- `/disk` - disk partitions with visual usage bars
- `/alerts` - enable/disable threshold notifications

Inline keyboards for quick refresh and navigation between views.

## Setup

1. Copy `.env.example` to `.env` and fill in your values:
   ```
   cp .env.example .env
   ```

2. Get a bot token from [@BotFather](https://t.me/BotFather)

3. Set your Telegram user ID as `ADMIN_ID`

## Run with Docker

```bash
docker-compose up -d --build
```

## Run locally

```bash
pip install -r requirements.txt
python main.py
```

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `BOT_TOKEN` | Telegram bot token | required |
| `ADMIN_ID` | Admin user ID for alerts | - |
| `ALERT_CPU_THRESHOLD` | CPU alert threshold (%) | 80 |
| `ALERT_RAM_THRESHOLD` | RAM alert threshold (%) | 90 |
| `CHECK_INTERVAL` | Metrics collection interval (sec) | 60 |

## Architecture

- `main.py` - entry point, bot setup, background collector task
- `handlers/commands.py` - command handlers (/start, /status, /cpu, /ram, /disk, /alerts)
- `handlers/callbacks.py` - inline button callback handlers
- `monitoring/collector.py` - ServerCollector class with psutil metrics and history
- `monitoring/charts.py` - matplotlib chart generation (CPU, RAM, overview)
- `keyboards.py` - inline keyboard builders
- `middleware.py` - AlertMiddleware for proactive threshold notifications
