"""Проект отдела Buying «Чекер лидов» — перенос бота Checkerleads (@cheackerleadsbot) в веб."""
from . import router as _router
from . import store

NAME = "🛡 Чекер лидов"
PREFIX = "/leads"
router = _router.router
TAGS = [
    {"name": "Чекер лидов", "description": "Перенос бота Checkerleads: лиды текстом или файлом (CSV / Excel / TXT / JSON) → проверка email (Abstract API), "
     "IP (ipdata), телефона (numverify), WhatsApp и 5 соцсетей (RapidAPI) → оценка риска 0–100 и вердикт clean / risky / spam. Проверка идёт в фоне."},
    {"name": "Чекер лидов · распознавание", "description": "Что бот распознает в тексте или файле — без проверки и без трат на API."},
    {"name": "Чекер лидов · отдельные проверки", "description": "Каждый внешний сервис бота отдельной ручкой и расчёт итоговой оценки."},
    {"name": "Чекер лидов · история и файлы", "description": "История проверок, файл как от бота, CSV / JSON выгрузка, исходный файл."},
    {"name": "Чекер лидов · журнал действий", "description": "Логи действий пользователей: кто, что, когда."},
]


async def startup() -> None:
    store.init()


async def shutdown() -> None:
    return None
