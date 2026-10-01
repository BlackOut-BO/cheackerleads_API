# Buying · Чекер лидов (веб)

Проект отдела **Buying** в Blackout Hub: перенос Telegram-бота **Checkerleads** (@cheackerleadsbot) в веб.
Все функции и флоу бота сохранены, меняется только интерфейс: вместо Telegram — раздел «Чекер лидов» в хабе и REST API.
Боевой бот работает на своём сервере и не трогается.

## Безопасность (как требует ТЗ)

- Код бота **не запускается как есть**: `bot.py` не импортируется, Telegram-токен не используется (иначе второй экземпляр перехватит обновления боевого бота).
- Веб берёт из бота только модули проверки (`leads_checker/services`, `leads_checker/utils`) через мост `app/leads/legacy.py`.
- Все секреты — только в переменных окружения веба (`.env`, см. `.env.example`), **отдельные от боевых**. В репозитории и логах ключей нет; `.env` и `authorized_users.json` бота в копию не попадают.
- Боевая база не используется: у веба своя SQLite (таблицы `leads_checks`, `leads_files`, `leads_audit`).
- Без ключа соответствующая проверка возвращает «API key not configured» (как бот без ключей) — страница при этом не падает, оценка считается по остальным проверкам.

## Карта исходного бота

| Что | Где | Комментарий |
|---|---|---|
| Точка входа | `main.py` → `bot.main()` | aiogram 3, long polling, токен `TELEGRAM_BOT_TOKEN` |
| Команды | `/start`, `/help` | меню из 5 кнопок |
| Кнопки (callback) | `help`, `about`, `upload_file`, `input_data`, `refresh`, `detail_<N>` | |
| Сообщения | документ → `handle_document`, текст → `handle_text` | |
| Доступ | `utils/auth.py` | только `ADMIN_IDS`; пароль и `authorized_users.json` больше не дают доступа |
| Проверка лида | `services/lead_checker.py` | параллельно email / IP / телефон / WhatsApp, соцсети по email; батчи по 3 лида, пауза 1 с |
| Email | `services/email_checker.py` | Abstract API Email Reputation |
| IP | `services/ip_checker.py` | ipdata.co; приватные IP не отправляются |
| Телефон | `services/phone_checker.py` | numverify; < 7 цифр — ошибка без запроса |
| WhatsApp | `services/whatsapp_checker.py` | RapidAPI, ретраи на 429, пауза 1.05 с, прокси `PROXY_URL` |
| Соцсети | `services/social_checkers.py` | Facebook, Google (только @gmail.com), Instagram, Snapchat, X — RapidAPI |
| Оценка | `utils/risk_scorer.py` | баллы 0–100 по email / IP / телефону, веса 0.4 / 0.4 / 0.2, risky ≥ 50, spam ≥ 75 |
| Разбор ввода | `utils/data_parser.py`, `utils/file_processor.py`, `utils/csv_processor.py` | текст, CSV (любой разделитель), Excel, TXT, JSON |
| База | — | бот хранит результаты только в памяти (для кнопок «📋 #N») |

## Флоу бота → веб

| Шаг в боте | Вход | Выход в боте | В вебе |
|---|---|---|---|
| `/start`, «🔄 Обновить меню» | — | приветствие + меню | экран раздела, приветствие в пустом результате |
| «📖 Справка» / `/help` | — | форматы, пороги, сервисы | кнопка «Справка» |
| «ℹ️ О боте» | — | описание | кнопка «О боте» |
| «✍️ Ввести данные» → текст | лиды в любом формате, по строке | «✅ Распознано лидов: N»; 1 лид → `lead_N_result.txt` (текст + JSON), несколько → `checked_leads.csv` | вкладка «✍️ Ввести данные»: предпросмотр распознавания, проверка в фоне с прогрессом, тот же файл |
| Нераспознанный текст | — | «❌ Не удалось распознать данные…» | тот же текст, кнопка неактивна |
| «📤 Загрузить файл» → CSV / Excel | таблица с любыми колонками | «✅ Найдено лидов: N» → `<имя>_checked.csv` (исходные колонки + Validity, Verdict, Score, IP/Email/Phone Score, Description) | вкладка «📤 Файл» (drag & drop), тот же файл |
| … → TXT / JSON | лиды | 1 лид → `lead_N_result.txt`; несколько → сводка SPAM → RISKY → CLEAN с кнопками «📋 #N» | то же: сводка, фильтры, «📋 #N» |
| Неподдерживаемый формат / пустой файл | — | «❌ Неподдерживаемый формат…» / «❌ Не удалось найти данные в файле.» | те же тексты |
| «📋 #N» | — | JSON результата лида | карточка лида (оценки, WhatsApp, соцсети, причины) + JSON |
| Ошибки внешних сервисов | — | «Не проверено» / текст ошибки в оценках | то же в карточке; страница не падает |

Дополнительно в вебе (бот этого не умел, но ничего не убрано): «Один лид» по полям, история проверок, повтор, остановка,
CSV / JSON выгрузка любой проверки, исходный файл, отдельная ручка на каждый внешний сервис, расчёт оценки, **журнал действий** (кто, что, когда; админ из `LEADS_ADMIN_IDS` видит всех).

## Swagger — общий на отдел

В Blackout Hub проект подключён в общий сервис `Buying API` вместе с [CelebritySearch_API](https://github.com/BlackOut-BO/CelebritySearch_API)
и [CreativeBot_API](https://github.com/BlackOut-BO/CreativeBot_API): один Swagger `/api/buying/docs`, проекты разделены группами тегов («Чекер лидов · …»).
`app/main.py` одинаковый во всех проектах отдела и подключает пакеты `app/<проект>/project.py`, которые лежат рядом; здесь — только «Чекер лидов».

## Состав

| Путь | Что это |
|---|---|
| `app/leads/` | веб-слой: `router.py` (ручки), `service.py` (флоу бота), `store.py` (SQLite + журнал), `formatting.py` (TXT 1:1 с ботом), `legacy.py` (мост), `project.py` |
| `leads_checker/` | копия кода бота без `.env` и списка пользователей; используется только логика проверки |
| `tests/` | 10 тестов API (внешние API подменены; текст TXT сверяется с функцией из `bot.py`) |
| `web/lead-checker/` | UI для Blackout Hub (React 19 + TS + daisyUI; использует kit хаба `views/../kit`) |

## Запуск

```bash
cp .env.example .env          # свои ключи; TELEGRAM_BOT_TOKEN не нужен
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --port 8100   # Swagger: http://127.0.0.1:8100/api/buying/docs
python -m pytest -q tests
```
Docker: `docker build -t cheackerleads-api . && docker run --env-file .env -p 8100:8000 -v $PWD/data:/srv/buying/data cheackerleads-api`.

Пользователь передаётся заголовком `X-User-Id` (в хабе его проставляет панель — авторизация хаба).

## Ручки API

### Чекер лидов

| Метод | Путь | Что делает |
|---|---|---|
| `GET` | `/api/buying/leads/meta` | Тексты меню бота (/start, 📖 Справка, ℹ️ О боте), форматы, пороги и какие сервисы настроены |
| `POST` | `/api/buying/leads/checks/text` | ✍️ Ввести данные: распознать лиды в тексте и запустить проверку в фоне |
| `POST` | `/api/buying/leads/checks/file` | 📤 Загрузить файл (CSV / XLSX / XLS / TXT / JSON) и запустить проверку в фоне |
| `POST` | `/api/buying/leads/checks/single` | Проверить один лид по полям email / IP / телефон |
| `GET` | `/api/buying/leads/checks/{check_id}` | Статус и прогресс проверки, сводка clean / risky / spam, результаты по лидам |
| `GET` | `/api/buying/leads/checks/{check_id}/leads/{lead_number}` | 📋 #N — полный JSON результата лида (кнопка под сводкой) |
| `POST` | `/api/buying/leads/checks/{check_id}/cancel` | Остановить проверку |
| `POST` | `/api/buying/leads/checks/{check_id}/retry` | Проверить те же данные ещё раз |

### Чекер лидов · распознавание

| Метод | Путь | Что делает |
|---|---|---|
| `POST` | `/api/buying/leads/parse/text` | Какие лиды бот распознает в тексте (без проверки и без трат) |
| `POST` | `/api/buying/leads/parse/file` | Какие лиды бот найдёт в файле (без проверки и без трат) |

### Чекер лидов · отдельные проверки

| Метод | Путь | Что делает |
|---|---|---|
| `POST` | `/api/buying/leads/tools/{kind}` | Одна проверка: email (Abstract API), ip (ipdata), phone (numverify), whatsapp (RapidAPI), social (5 соцсетей по email) |
| `POST` | `/api/buying/leads/score` | Итоговая оценка и вердикт по оценкам IP / email / телефона (веса и пороги бота) |

### Чекер лидов · история и файлы

| Метод | Путь | Что делает |
|---|---|---|
| `DELETE` | `/api/buying/leads/checks/{check_id}` | Удалить проверку из истории |
| `GET` | `/api/buying/leads/checks` | История проверок пользователя |
| `GET` | `/api/buying/leads/checks/{check_id}/download` | Файл, который прислал бы бот: <имя>_checked.csv / checked_leads.csv / lead_N_result.txt |
| `GET` | `/api/buying/leads/checks/{check_id}/export.csv` | CSV с результатами (для любой проверки) |
| `GET` | `/api/buying/leads/checks/{check_id}/export.json` | Все результаты в JSON |
| `GET` | `/api/buying/leads/checks/{check_id}/source` | Исходный загруженный файл |

### Чекер лидов · журнал действий

| Метод | Путь | Что делает |
|---|---|---|
| `GET` | `/api/buying/leads/audit` | Кто, что и когда делал. Пользователь видит свои действия, админ (LEADS_ADMIN_IDS) — все |

Всего ручек: 19
