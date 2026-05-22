# Telegram Reminder Bot

A personal Telegram bot for one-time reminders, recurring reminders, reminder lists, and repeated notifications until the reminder is marked done.

## Tech stack

- Python 3.12+
- python-telegram-bot
- APScheduler
- MongoDB Atlas free tier
- Railway worker deploy

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env`:

```env
BOT_TOKEN=your-telegram-bot-token
MONGODB_URI=your-mongodb-atlas-uri
MONGODB_DB=telegram_reminder_bot
STORAGE_BACKEND=mongo
TIMEZONE=Asia/Bangkok
ADMIN_USER_IDS=123456789
```

Run locally:

```powershell
python -m app.main
```

For quick local testing without MongoDB, set:

```env
STORAGE_BACKEND=memory
```

Memory storage is not persistent and should not be used for Railway deployment.

## Railway deploy

1. Push this folder to GitHub.
2. Create a Railway project from the repo.
3. Add these variables in Railway:
   - `BOT_TOKEN`
   - `MONGODB_URI`
   - `MONGODB_DB`
   - `TIMEZONE`
   - `ADMIN_USER_IDS`
4. Railway can use `Procfile` or `railway.json` to start the worker.

## Bot commands

```text
/start
/help
/remind <time> | <content> [--every Nh] [--repeat daily|weekly|monthly|hourly|Nh]
/list
/done <id>
/delete <id>
/snooze <id> [hours]
/admin
```

Examples:

```text
/remind 2026-05-23 09:00 | pay electricity bill --every 1h
/remind 23/05/2026 08:30 | send report --repeat daily --every 2h
/remind sau 2h | check deployment --every 3h
/remind mai 07:00 | drink medicine --repeat daily
```

Without `--every`, the bot sends one notification only. `--every Nh` controls how often the bot sends the same notification after the due time until you press `Done` or use `/done <id>`.

`--repeat` controls recurrence after the reminder is completed. For example, a daily reminder will be scheduled again for the next day after you mark it done.

## Supported time formats

```text
YYYY-MM-DD HH:MM
DD/MM/YYYY HH:MM
HH:MM
today HH:MM
tomorrow HH:MM
hom nay HH:MM
mai HH:MM
sau 30m
sau 2h
sau 1d
```

The default timezone is configured with `TIMEZONE`.
