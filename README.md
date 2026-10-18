# Note — особисті нотатки в Telegram

Бот + API для зберігання акаунтів, посилань, покупок і чого завгодно — по папках,
з довільними полями в кожному записі, пошуком і спільними папками для сім'ї.

```
Telegram ──► bot (aiogram) ──HTTP──► api (FastAPI) ──► PostgreSQL
                                                  └──► backup (щоденний pg_dump у ./backups)
```

## Запуск (macOS + Docker Desktop)

1. Створи бота в [@BotFather](https://t.me/BotFather) → `/newbot` → скопіюй токен.
2. Відкрий `.env` (уже створений, секрети згенеровані) і впиши `BOT_TOKEN`.
   Якщо `.env` немає — `cp .env.example .env` і заповни.
3. Запусти:
   ```bash
   docker compose up -d --build
   ```
4. Напиши боту `/start`. Він відповість «🔒 приватний бот» і покаже **твій Telegram ID**.
   Впиши його в `ADMIN_TELEGRAM_ID` у `.env` і перезапусти бота з API:
   ```bash
   docker compose up -d --force-recreate api bot
   ```
5. Знову `/start` — ти адмін. Кнопка «🎟 Запросити» дає одноразове посилання для дружини / сім'ї.

### Щоб працювало постійно

- Docker Desktop → Settings → General → **Start Docker Desktop when you sign in**.
- Контейнери мають `restart: unless-stopped` — піднімуться самі після перезапуску Docker.
- Щоб Mac не засинав: `sudo pmset -a sleep 0` (або `sudo pmset -a disablesleep 1`, якщо кришка закрита).
- Home Assistant можна тримати поруч — порти не конфліктують (API: `127.0.0.1:8000`, HA: `8123`).

## Як користуватись

| Дія | Як |
|---|---|
| Переглянути | 📁 Папки → папка → запис |
| Новий запис | ➕ Запис → папка → назва → поля |
| Швидко | після вибору папки одним повідомленням: перший рядок — назва, далі поля |
| Пошук | просто напиши назву або частину в чат |
| Поля | `назва: значення`, кожне з нового рядка; голе посилання стане полем «посилання» |
| Секрети | поля з ключами «пароль», «PIN», «token», «cvv»… — під спойлером |
| Спільна папка | ⚙️ Папка → 👥 Доступ → вибрати людину |

Повідомлення з полями бот видаляє з чату після збереження, щоб паролі не висіли в історії.

## Розробка

```bash
python3.12 -m venv .venv            # або існуючий .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest
```

- API-документація (Swagger): http://127.0.0.1:8000/docs — запити потребують заголовків
  `X-API-Key` і `X-Telegram-Id`.
- Нова міграція після зміни `app/models.py`:
  ```bash
  docker compose exec api alembic revision --autogenerate -m "опис"
  ```
- Логи: `docker compose logs -f bot api`

### Структура

```
app/            FastAPI: моделі, схеми, роути (auth, folders, items)
bot/            aiogram-бот: handlers/, клавіатури, рендер, HTTP-клієнт до API
migrations/     Alembic
tests/          pytest (SQLite in-memory)
```

## Бекапи

Сервіс `backup` щодоби кладе `backups/note-YYYY-MM-DD.sql.gz` і тримає 14 днів.
Відновлення:
```bash
gunzip -c backups/note-2026-10-17.sql.gz | docker compose exec -T db psql -U note note
```

## Ідеї на потім

- Веб-версія поверх того ж API (вхід через Telegram Login)
- Файли й фото (взуття, документи)
- Шифрування секретних полів у БД
- Автовидалення повідомлення з паролем через N секунд
- Теги / вкладені папки
