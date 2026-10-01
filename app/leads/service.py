"""Флоу бота Checkerleads без Telegram: те же шаги, проверки и файлы на выходе.

Бот (bot.py):
  ✍️ «Ввести данные» → текст → LeadParser.parse_multiple_text → фильтр пустых →
     «✅ Распознано лидов: N» → LeadChecker.check_leads(check_social=True) →
     1 лид — TXT «lead_N_result.txt» (текст + JSON), несколько — CSV «checked_leads.csv».
  📤 «Загрузить файл» → CSV/XLSX/XLS/TXT/JSON → FileProcessor.parse_file → «✅ Найдено лидов: N» →
     таблица (CSV/Excel) — «<имя>_checked.csv» с колонками результатов; иначе 1 лид — TXT,
     несколько — сводка SPAM/RISKY/CLEAN с кнопками «📋 #N» (JSON лида).
Здесь то же самое, только долгая проверка идёт в фоне, а прогресс и результат видны в вебе.
"""
import asyncio
import json
import logging
import os
from typing import Any

from . import store
from .formatting import format_check_result_technical, strip_html
from .legacy import CSVProcessor, FileProcessor, LeadChecker, LeadParser, RiskAggregator, VerdictMapper, config

log = logging.getLogger("leads")

SUPPORTED = [".csv", ".xlsx", ".xls", ".txt", ".json"]
MAX_FILE = 10 * 1024 * 1024

WELCOME = """Я помогаю проверять лиды на валидность и риски.

Возможности:
✅ Проверка email, IP и телефона
✅ Проверка WhatsApp
✅ Проверка социальных сетей (Facebook, Google, Instagram, Snapchat, X)
✅ Оценка рисков и вердикт (clean/risky/spam)

Как использовать:
1. Нажмите кнопку "Загрузить файл" для загрузки файла
2. Или нажмите "Ввести данные" и отправьте текст с лидами

Примеры формата:
• email=test@example.com | ip=192.168.1.1 | phone=+1234567890
• test@example.com 192.168.1.1 +1234567890
• Просто текст с данными - я распознаю автоматически"""

HELP = """Форматы данных:

1. CSV файл - загрузите файл с колонками:
   - email, ip, phone (или любые другие названия)
   - Бот автоматически распознает данные

2. Ручной ввод - отправьте текст в любом формате:
   • email=test@example.com | ip=192.168.1.1 | phone=+1234567890
   • test@example.com 192.168.1.1 +1234567890
   • Просто текст - бот распознает автоматически

Результаты проверки:
• clean - выглядит нормально (score < 50)
• risky - есть заметные риски (score 50-74)
• spam - очень похоже на спам/мошенничество (score >= 75)

Проверяемые данные:
✅ Email (Abstract API)
✅ IP (ipdata.co)
✅ Телефон (numverify)
✅ WhatsApp (RapidAPI)
✅ Facebook, Google, Instagram, Snapchat, X (RapidAPI)"""

ABOUT = """Этот бот предназначен для комплексной проверки лидов на валидность и риски.

Что проверяется:
• Email адреса на валидность и качество
• IP адреса на угрозы и анонимность
• Телефонные номера на валидность и тип линии
• Наличие WhatsApp на номере
• Наличие аккаунтов в социальных сетях

Оценка рисков:
Бот автоматически оценивает каждый лид по шкале 0-100 и выдает вердикт:
• clean - безопасный лид
• risky - есть риски
• spam - подозрительный лид"""

UPLOAD_HINT = "Отправьте файл с лидами в любом формате: CSV (.csv), Excel (.xlsx, .xls), TXT (.txt), JSON (.json). Данные и формат распознаются автоматически."
INPUT_HINT = "Отправьте данные лидов в любом формате:\n• email=test@example.com | ip=192.168.1.1 | phone=+1234567890\n• test@example.com 192.168.1.1 +1234567890\n• Просто текст - распознается автоматически"
UNSUPPORTED = "❌ Неподдерживаемый формат файла.\n\nПоддерживаемые форматы:\n• CSV (.csv)\n• Excel (.xlsx, .xls)\n• TXT (.txt)\n• JSON (.json)"
NO_DATA_FILE = "❌ Не удалось найти данные в файле."
NO_DATA_TEXT = "❌ Не удалось распознать данные. Пожалуйста, укажите email, IP или телефон.\n\nПример: email=test@example.com | ip=192.168.1.1 | phone=+1234567890"


class FlowError(Exception):
    def __init__(self, message: str, status: int = 422):
        super().__init__(message)
        self.message = message
        self.status = status


# Один экземпляр на сервис, как глобальный `lead_checker` в боте (общая пауза между WhatsApp-запросами)
lead_checker = LeadChecker()
parser = LeadParser()
_tasks: dict[int, asyncio.Task] = {}


def admin_ids() -> set[int]:
    raw = os.environ.get("LEADS_ADMIN_IDS", "")
    return {int(x) for x in raw.replace(" ", "").split(",") if x.strip().isdigit()}


def services_status() -> dict[str, bool]:
    """Какие внешние сервисы настроены (только факт наличия ключа, значения не отдаются)."""
    return {
        "email (Abstract API)": bool(config.ABSTRACT_API_KEY),
        "ip (ipdata.co)": bool(config.IPDATA_API_KEY),
        "phone (numverify)": bool(config.NUMVERIFY_API_KEY),
        "whatsapp (RapidAPI)": bool(config.RAPIDAPI_KEY) and config.ENABLE_WHATSAPP_CHECK,
        "соцсети (RapidAPI)": bool(config.RAPIDAPI_KEY),
        "прокси для WhatsApp": bool(config.PROXY_URL),
    }


# ── разбор ввода (как handle_text / handle_document) ─────────────
def parse_text(text: str) -> list[dict]:
    leads = parser.parse_multiple_text((text or "").strip())
    return [lead for lead in leads if lead.get("email") or lead.get("ip") or lead.get("phone")]


def parse_file(content: bytes, file_name: str) -> dict:
    name = file_name or "unknown"
    if not any(name.lower().endswith(ext) for ext in SUPPORTED):
        raise FlowError(UNSUPPORTED)
    if len(content) > MAX_FILE:
        raise FlowError("❌ Файл больше 10 МБ.")
    try:
        leads, fieldnames, original_rows, delimiter = FileProcessor.parse_file(content, name)
    except Exception as e:  # noqa: BLE001 — как в боте: текст ошибки пользователю
        raise FlowError(f"❌ Ошибка при обработке файла: {e}") from e
    file_type = FileProcessor.detect_file_type(name)
    return {"leads": leads, "fieldnames": fieldnames, "original_rows": original_rows, "delimiter": delimiter,
            "file_type": file_type, "is_table": file_type in ("csv", "excel")}


# ── запуск проверки ──────────────────────────────────────────────
def start_text(user: int, text: str) -> int:
    leads = parse_text(text)
    if not leads:
        raise FlowError(NO_DATA_TEXT)
    cid = store.create_check(user, "text", leads, text=text)
    store.update_check(cid, message=f"✅ Распознано лидов: {len(leads)}\n🔄 Начинаю проверку...")
    store.audit(user, "check.start", {"check_id": cid, "source": "text", "leads": len(leads)})
    _spawn(cid, user)
    return cid


def start_file(user: int, content: bytes, file_name: str) -> int:
    parsed = parse_file(content, file_name)
    if not parsed["leads"]:
        raise FlowError(NO_DATA_FILE)
    cid = store.create_check(user, "file", parsed["leads"], file_name=file_name, file_type=parsed["file_type"], file_bytes=content)
    store.update_check(cid, message=f"✅ Найдено лидов: {len(parsed['leads'])}\n🔄 Начинаю проверку...")
    store.audit(user, "check.start", {"check_id": cid, "source": "file", "file": file_name, "leads": len(parsed["leads"])})
    _spawn(cid, user)
    return cid


def start_single(user: int, lead: dict) -> int:
    lead = {k: (lead.get(k) or "").strip() or None for k in ("email", "ip", "phone")}
    if not any(lead.values()):
        raise FlowError(NO_DATA_TEXT)
    cid = store.create_check(user, "single", [lead])
    store.update_check(cid, message="✅ Распознано лидов: 1\n🔄 Начинаю проверку...")
    store.audit(user, "check.start", {"check_id": cid, "source": "single"})
    _spawn(cid, user)
    return cid


def retry(user: int, cid: int) -> int:
    c = store.get_check(cid, user)
    if not c:
        raise FlowError("Проверка не найдена.", 404)
    store.audit(user, "check.retry", {"check_id": cid})
    if c["source"] == "file":
        content = store.get_file(cid)
        if content is None:
            raise FlowError("Исходный файл не сохранился — загрузи его заново.", 409)
        return start_file(user, content, c["file_name"])
    if c["source"] == "text":
        return start_text(user, c["input"] or "")
    return start_single(user, c["leads"][0])


def cancel(user: int, cid: int) -> bool:
    c = store.get_check(cid, user)
    if not c:
        raise FlowError("Проверка не найдена.", 404)
    t = _tasks.get(cid)
    if t and not t.done():
        t.cancel()
        store.audit(user, "check.cancel", {"check_id": cid})
        return True
    return False


def _spawn(cid: int, user: int) -> None:
    _tasks[cid] = asyncio.create_task(_run(cid, user))


class _Tracked(LeadChecker):
    """Тот же LeadChecker бота (батчи по 3, пауза 1 с), только с отметкой прогресса после каждого лида."""

    def __init__(self, base: LeadChecker, on_lead):  # pylint: disable=super-init-not-called
        self.__dict__.update(base.__dict__)  # общие чекеры (и пауза WhatsApp) — как у глобального экземпляра
        self._on_lead = on_lead

    async def _check_lead_with_number(self, lead, lead_num, check_social):
        result = await super()._check_lead_with_number(lead, lead_num, check_social)
        self._on_lead()
        return result


async def _run(cid: int, user: int) -> None:
    c = store.get_check(cid)
    leads = c["leads"]
    progress = {"done": 0}

    def tick():
        progress["done"] += 1
        store.update_check(cid, done=progress["done"])

    try:
        store.update_check(cid, status="running")
        results = await _Tracked(lead_checker, tick).check_leads(leads, check_social=True)
        kind, name, data, msg = build_output(c, results)
        store.update_check(cid, status="done", results=results, done=len(results), output_kind=kind, output_name=name,
                           output=data, message=msg, finished_at=store.now())
        stats = store.verdict_stats(results)
        store.audit(user, "check.done", {"check_id": cid, **stats})
    except asyncio.CancelledError:
        store.update_check(cid, status="cancelled", finished_at=store.now(), message="Проверка отменена")
        raise
    except Exception as e:  # noqa: BLE001 — ошибка не роняет сервис, видна в интерфейсе
        log.exception("leads check %s failed", cid)
        store.update_check(cid, status="error", error=f"❌ Ошибка при обработке: {e}", finished_at=store.now())
        store.audit(user, "check.error", {"check_id": cid, "error": str(e)})
    finally:
        _tasks.pop(cid, None)


def txt_for(result: dict) -> tuple[str, bytes]:
    lead_num = result.get("lead_number", 0)
    text_result = strip_html(format_check_result_technical(result, lead_num))
    json_result = json.dumps(result, indent=2, ensure_ascii=False, default=str)
    content = f"{text_result}\n\n{'=' * 60}\n\nJSON Result:\n\n{json_result}"
    return f"lead_{lead_num}_result.txt", content.encode("utf-8")


def build_output(c: dict, results: list[dict]) -> tuple[str, str | None, bytes | None, str]:
    """Что бот прислал бы в чат после проверки."""
    n = len(results)
    if c["source"] == "file":
        content = store.get_file(c["id"]) or b""
        parsed = parse_file(content, c["file_name"])
        if parsed["is_table"] and parsed["original_rows"]:
            fn = c["file_name"]
            out_name = fn.rsplit(".", 1)[0] + "_checked.csv" if "." in fn else f"checked_{fn}.csv"
            data = CSVProcessor.create_csv_with_results(parsed["original_rows"], parsed["fieldnames"], results, fn, parsed["delimiter"])
            return "csv", out_name, data, f"✅ Проверка завершена! Обработано: {n} лидов\n📊 Все результаты сохранены в файле"
        if n == 1:
            name, data = txt_for(results[0])
            return "txt", name, data, f"📄 Результат проверки Lead #{results[0].get('lead_number', 0)}"
        return "summary", None, None, f"✅ Проверка завершена! Обработано лидов: {n}"
    if n == 1:
        name, data = txt_for(results[0])
        return "txt", name, data, f"📄 Результат проверки Lead #{results[0].get('lead_number', 0)}"
    rows = [{"Email": l.get("email") or "", "IP": l.get("ip") or "", "Phone": l.get("phone") or ""} for l in c["leads"]]
    data = CSVProcessor.create_csv_with_results(rows, ["Email", "IP", "Phone"], results, "manual_input.csv", ",")
    return "csv", "checked_leads.csv", data, f"✅ Проверка завершена! Обработано: {n} лидов\n📊 Все результаты сохранены в файле"


def export_csv(c: dict) -> bytes:
    """CSV-выгрузка любой проверки (в вебе доступна всегда, в дополнение к файлу бота)."""
    rows = [{"Email": l.get("email") or "", "IP": l.get("ip") or "", "Phone": l.get("phone") or ""} for l in c["leads"]]
    return CSVProcessor.create_csv_with_results(rows, ["Email", "IP", "Phone"], c["results"], "export.csv", ",")


# ── отдельные проверки (каждый сервис бота своей ручкой) ─────────
async def check_one(kind: str, value: str) -> dict[str, Any]:
    lc = lead_checker
    value = (value or "").strip()
    if not value:
        raise FlowError("Пустое значение.")
    if kind == "email":
        data = await lc.email_checker.check(value)
        score = None if data.get("error") else lc.email_scorer.score(data)
    elif kind == "ip":
        data = await lc.ip_checker.check(value)
        score = None if data.get("error") else lc.ip_scorer.score(data)
    elif kind == "phone":
        data = await lc.phone_checker.check(value)
        score = None if data.get("error") else lc.phone_scorer.score(data)
    elif kind == "whatsapp":
        data, score = await lc.whatsapp_checker.check(value), None
    elif kind == "social":
        checkers = {"facebook": lc.facebook_checker, "google": lc.google_checker, "instagram": lc.instagram_checker,
                    "snapchat": lc.snapchat_checker, "x": lc.x_checker}
        res = await asyncio.gather(*[c.check(value) for c in checkers.values()], return_exceptions=True)
        data = {k: (r if not isinstance(r, Exception) else {"exists": False, "error": str(r)}) for k, r in zip(checkers, res)}
        score = None
    else:
        raise FlowError("Неизвестный тип проверки.", 404)
    return {"kind": kind, "value": value, "score": score, "data": data}


def score(ip_score: float | None, email_score: float | None, phone_score: float | None) -> dict:
    final = RiskAggregator().aggregate(ip_score=ip_score, email_score=email_score, phone_score=phone_score)
    return {"final_score": final, "verdict": VerdictMapper().get_verdict(final),
            "weights": {"ip": config.IP_WEIGHT, "email": config.EMAIL_WEIGHT, "phone": config.PHONE_WEIGHT},
            "thresholds": {"risky": config.RISKY_THRESHOLD, "spam": config.SPAM_THRESHOLD}}
