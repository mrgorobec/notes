# Note — personal notes in Telegram

A bot + API for storing accounts, links, purchases and anything else — organized in folders,
with custom fields in every entry, search, and folders you can share with family.

```
Telegram ──► bot (aiogram) ──HTTP──► api (FastAPI) ──► PostgreSQL
                                                  └──► backup (daily pg_dump to ./backups)
```

> The bot's interface is in Ukrainian; button labels below are quoted as they appear in the bot.

## Running (macOS + Docker Desktop)

1. Create a bot with [@BotFather](https://t.me/BotFather) → `/newbot` → copy the token.
2. Create `.env` from the template and fill in `BOT_TOKEN`
   (generate `API_KEY` and `POSTGRES_PASSWORD` with `openssl rand -hex 32`):
   ```bash
   cp .env.example .env
   ```
3. Start everything:
   ```bash
   docker compose up -d --build
   ```
4. Send `/start` to the bot. It replies "🔒 private bot" and shows **your Telegram ID**.
   Put it into `ADMIN_TELEGRAM_ID` in `.env` and restart the API and the bot:
   ```bash
   docker compose up -d --force-recreate api bot
   ```
5. `/start` again — you're the admin now. The «🎟 Запросити» (Invite) button gives you a
   single-use invite link for family members.

### Keeping it running

- Docker Desktop → Settings → General → **Start Docker Desktop when you sign in**.
- All containers use `restart: unless-stopped`, so they come back after Docker restarts.
- Keep the Mac awake: `sudo pmset -a sleep 0` (or `sudo pmset -a disablesleep 1` to stay awake
  with the lid closed).
- Home Assistant can run alongside — no port conflicts (API: `127.0.0.1:8000`, HA: `8123`).

## Usage

| Action | How |
|---|---|
| Browse | «📁 Папки» (Folders) → folder → entry |
| New entry | «➕ Запис» (Entry) → folder → title → fields |
| Quick add | after picking a folder, send one message: first line is the title, the rest are fields |
| Search | just type a title or part of it into the chat |
| Fields | `key: value`, one per line; a bare URL becomes a «посилання» (link) field |
| Secrets | fields with keys like «пароль» (password), «PIN», «token», «cvv»… are shown under a spoiler |
| Edit an entry | open it → add / edit / delete fields, rename, move, delete |
| Manage a folder | open it → «⚙️ Папка» → rename, sharing, delete |
| Shared folder | «⚙️ Папка» → «👥 Доступ» (Access) → pick a person |

After saving, the bot deletes your message with the field values, so passwords don't linger in
the chat history.

## Development

```bash
python3.12 -m venv .venv            # or reuse an existing .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest
```

- API docs (Swagger): http://127.0.0.1:8000/docs — requests need the `X-API-Key` and
  `X-Telegram-Id` headers.
- New migration after changing `app/models.py`:
  ```bash
  docker compose exec api alembic revision --autogenerate -m "description"
  ```
- Logs: `docker compose logs -f bot api`

### Project layout

```
app/            FastAPI: models, schemas, routes (auth, folders, items)
bot/            aiogram bot: handlers/, keyboards, rendering, HTTP client for the API
migrations/     Alembic
tests/          pytest (in-memory SQLite)
```

## Backups

The `backup` service writes `backups/note-YYYY-MM-DD.sql.gz` once a day and keeps the last 14 days.
Restore into an empty database:
```bash
gunzip -c backups/note-2026-10-17.sql.gz | docker compose exec -T db psql -U note note
```

## Ideas for later

- Web version on top of the same API (sign in with Telegram Login)
- Files and photos (shoes, documents)
- Encryption of secret fields in the database
- Auto-delete the message with a password after N seconds
- Tags / nested folders
