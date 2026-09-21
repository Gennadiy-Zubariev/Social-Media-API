# Social Media API

RESTful API соціальної мережі на Django REST framework: профілі, підписки, пости з хештегами, лайки, коментарі та відкладені пости (Celery).

## Стек

- Python 3.14, Django 6.1, Django REST framework
- PostgreSQL 17
- Celery + Redis (відкладені пости)
- Token-автентифікація (`rest_framework.authtoken`)
- drf-spectacular (Swagger / ReDoc)
- Docker Compose

## Можливості

- Реєстрація за email і паролем, логін (отримання токена), логаут (видалення токена)
- Профіль користувача: нікнейм, біографія, дата народження, стать, фото; пошук профілів за нікнеймом
- Підписки: підписатися / відписатися, мої підписки, мої підписники
- Пости з текстом і зображенням; хештеги додаються автоматично з тексту (`#django`)
- Мої пости, стрічка підписок, фільтр за хештегом
- Лайки (toggle), список вподобаних постів
- Коментарі до постів
- Відкладені пости: публікуються Celery-таскою в задений час
- Оновлювати й видаляти можна лише власні пости, коментарі та профіль

## Швидкий старт (Docker)

```bash
cp .env.sample .env      # заповніть SECRET_KEY і POSTGRES_PASSWORD
docker compose up --build
```

Піднімаються сервіси: `web` (API на порту 8000), `db` (PostgreSQL), `redis`, `celery` (воркер) і `celery-beat` (планувальник). Міграції застосовуються автоматично при старті `web`.

Створити адміністратора:

```bash
docker compose exec web python manage.py createsuperuser
```

Зупинити: `docker compose down` (дані Postgres і медіафайли лишаються в томах; `-v` видалить і їх).

## Запуск без Docker

Потрібні запущені PostgreSQL і Redis (можна підняти лише їх: `docker compose up -d db redis`; порт Redis назовні не публікується, тож для Celery поза Docker потрібен власний Redis на `localhost:6379`).

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.sample .env      # POSTGRES_HOST=localhost
python manage.py migrate
python manage.py runserver
```

Celery (в окремих терміналах):

```bash
celery -A social_media_api worker -l info
celery -A social_media_api beat -l info
```

## Наповнення бази тестовими даними

Команда `seed_db` створює користувачів, профілі, підписки, пости з хештегами, лайки, коментарі та відкладені пости.

```bash
# у Docker
docker compose exec web python manage.py seed_db

# без Docker
python manage.py seed_db
```

Параметри:

| Параметр | Опис |
|---|---|
| `--users N` | кількість користувачів (за замовчуванням 10) |
| `--posts N` | постів на користувача (за замовчуванням 3) |
| `--clear` | спершу видалити раніше створені seed-дані |

Приклад: `python manage.py seed_db --clear --users 20 --posts 5`.

Seed-користувачі мають email `seed1@seed.example.com`, `seed2@seed.example.com`, ... і пароль `password123`. Для входу використовуйте `POST /api/user/auth/login/`. Команда видаляє (`--clear`) лише користувачів із доменом `seed.example.com`, ваші власні акаунти вона не чіпає.

## Змінні середовища (`.env`)

| Змінна | Опис |
|---|---|
| `SECRET_KEY` | секретний ключ Django |
| `DEBUG` | `True` / `False` |
| `ALLOWED_HOSTS` | хости через кому |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | доступ до БД (ті самі значення використовує контейнер `db`) |
| `POSTGRES_HOST`, `POSTGRES_PORT` | адреса БД (`localhost` поза Docker; у compose підміняється на `db`) |
| `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | адреса Redis (у compose підміняється на `redis`) |

## Документація API

Після запуску:

- Swagger UI: http://localhost:8000/api/doc/swagger/
- ReDoc: http://localhost:8000/api/doc/redoc/
- OpenAPI-схема: http://localhost:8000/api/schema/

Для авторизації у Swagger: отримайте токен через `POST /api/user/auth/login/`, натисніть **Authorize** і введіть `Token <ваш_токен>`. Усі запити, крім реєстрації та логіну, вимагають заголовок `Authorization: Token <токен>`.

## Ендпоінти

**Auth** (`/api/user/auth/`)

| Метод | URL | Опис |
|---|---|---|
| POST | `register/` | реєстрація, повертає токен |
| POST | `login/` | логін, повертає токен |
| POST | `logout/` | видаляє токен |

**Профілі** (`/api/user/profiles/`)

| Метод | URL | Опис |
|---|---|---|
| GET | `/` | список профілів, пошук `?nickname=` |
| GET | `{id}/` | профіль користувача |
| PUT, PATCH | `{id}/` | оновити (лише власник) |
| GET, PUT, PATCH, DELETE | `me/` | мій профіль |

**Підписки** (`/api/user/follows/`)

| Метод | URL | Опис |
|---|---|---|
| GET | `/` | на кого я підписаний |
| POST | `/` | підписатися (`{"following": <user_id>}`) |
| DELETE | `{id}/` | відписатися |
| GET | `followers/` | мої підписники |

**Пости** (`/api/posts/`)

| Метод | URL | Опис |
|---|---|---|
| GET | `/` | усі пости, фільтр `?hashtag=django` |
| POST | `/` | створити пост (`content`, `image`) |
| GET | `{id}/` | пост з коментарями |
| PUT, PATCH, DELETE | `{id}/` | змінити / видалити (лише автор) |
| GET | `my/` | мої пости |
| GET | `feed/` | стрічка підписок |
| POST | `{id}/like/` | лайк / зняти лайк |

**Коментарі** (`/api/posts/{post_id}/comments/`)

| Метод | URL | Опис |
|---|---|---|
| GET, POST | `/` | список / додати |
| PUT, PATCH, DELETE | `{id}/` | змінити / видалити (лише автор) |

**Інше**

| Метод | URL | Опис |
|---|---|---|
| GET | `/api/liked/` | пости, які я вподобав |
| GET, POST | `/api/scheduled/` | мої відкладені пости / створити |
| GET, PUT, PATCH, DELETE | `/api/scheduled/{id}/` | керування відкладеним постом |

Приклад відкладеного посту (`publish_at` має бути в майбутньому, `hashtags` через кому):

```json
{
  "content": "Привіт із майбутнього",
  "hashtags": "python,django",
  "publish_at": "2030-01-01T12:00:00Z"
}
```

Celery Beat щохвилини запускає таску `publish_scheduled_posts`, яка публікує всі пости, чий час настав.

## Тести

Потрібен запущений PostgreSQL (`docker compose up -d db`):

```bash
python manage.py test
```
