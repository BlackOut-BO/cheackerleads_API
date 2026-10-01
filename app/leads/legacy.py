"""Подключение логики бота Checkerleads (копия в `buying/leads_checker`) без Telegram-части.

Боевой бот работает на своём сервере и не трогается. Здесь используются только его модули
проверки: парсер лидов, разбор файлов, чекеры (Abstract API, ipdata, numverify, RapidAPI),
оценка риска и CSV с результатами. `bot.py` не импортируется и не запускается.

Ключи берутся из окружения веба (`buying/.env`), отдельные от боевых: без ключа сервис
проверки штатно возвращает «API key not configured», как в боте.
"""
import sys
from pathlib import Path

LEADS_DIR = Path(__file__).resolve().parents[2] / "leads_checker"
if str(LEADS_DIR) not in sys.path:
    sys.path.insert(0, str(LEADS_DIR))

import config  # noqa: E402
from services.lead_checker import LeadChecker  # noqa: E402
from utils.csv_processor import CSVProcessor  # noqa: E402
from utils.data_parser import LeadParser  # noqa: E402
from utils.file_processor import FileProcessor  # noqa: E402
from utils.risk_scorer import RiskAggregator, VerdictMapper  # noqa: E402

__all__ = ["config", "LeadChecker", "CSVProcessor", "LeadParser", "FileProcessor", "RiskAggregator", "VerdictMapper", "LEADS_DIR"]
