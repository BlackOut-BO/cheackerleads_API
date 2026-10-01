from typing import Literal

from fastapi import APIRouter, File, Header, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel, Field

from . import service as svc
from . import store

router = APIRouter(prefix="/leads")

T_MAIN = "Чекер лидов"
T_PARSE = "Чекер лидов · распознавание"
T_TOOLS = "Чекер лидов · отдельные проверки"
T_HIST = "Чекер лидов · история и файлы"
T_AUDIT = "Чекер лидов · журнал действий"


def uid(x_user_id: int | None) -> int:
    return x_user_id or 1  # пользователь из панели (авторизация хаба); в витрине — demo (id=1)


def _wrap(fn, *a):
    try:
        return fn(*a)
    except svc.FlowError as e:
        raise HTTPException(e.status, e.message) from e


class TextIn(BaseModel):
    text: str = Field(..., description="Лиды в любом формате, как сообщение боту: «email=… | ip=… | phone=…», через пробел или просто текст; несколько — с новой строки")


class LeadIn(BaseModel):
    email: str | None = None
    ip: str | None = None
    phone: str | None = None


class ValueIn(BaseModel):
    value: str = Field(..., description="email / IP / телефон")


class ScoreIn(BaseModel):
    ip_score: float | None = None
    email_score: float | None = None
    phone_score: float | None = None


def _view(c: dict) -> dict:
    c = dict(c)
    c["stats"] = store.verdict_stats(c.get("results") or [])
    c["has_output"] = bool(c.get("output_name"))
    return c


# ── меню бота ────────────────────────────────────────────────────
@router.get("/meta", tags=[T_MAIN], summary="Тексты меню бота (/start, 📖 Справка, ℹ️ О боте), форматы, пороги и какие сервисы настроены")
def meta():
    return {
        "welcome": svc.WELCOME, "help": svc.HELP, "about": svc.ABOUT,
        "upload_hint": svc.UPLOAD_HINT, "input_hint": svc.INPUT_HINT,
        "formats": svc.SUPPORTED, "max_file_mb": svc.MAX_FILE // 1024 // 1024,
        "thresholds": {"risky": svc.config.RISKY_THRESHOLD, "spam": svc.config.SPAM_THRESHOLD},
        "weights": {"ip": svc.config.IP_WEIGHT, "email": svc.config.EMAIL_WEIGHT, "phone": svc.config.PHONE_WEIGHT},
        "services": svc.services_status(),
    }


# ── проверка (✍️ Ввести данные / 📤 Загрузить файл) ─────────────
@router.post("/checks/text", tags=[T_MAIN], status_code=status.HTTP_202_ACCEPTED, summary="✍️ Ввести данные: распознать лиды в тексте и запустить проверку в фоне")
async def check_text(body: TextIn, x_user_id: int | None = Header(None)):
    user = uid(x_user_id)
    return _view(store.get_check(_wrap(svc.start_text, user, body.text)))


@router.post("/checks/file", tags=[T_MAIN], status_code=status.HTTP_202_ACCEPTED, summary="📤 Загрузить файл (CSV / XLSX / XLS / TXT / JSON) и запустить проверку в фоне")
async def check_file(file: UploadFile = File(...), x_user_id: int | None = Header(None)):
    user = uid(x_user_id)
    content = await file.read()
    return _view(store.get_check(_wrap(svc.start_file, user, content, file.filename or "unknown")))


@router.post("/checks/single", tags=[T_MAIN], status_code=status.HTTP_202_ACCEPTED, summary="Проверить один лид по полям email / IP / телефон")
async def check_single(body: LeadIn, x_user_id: int | None = Header(None)):
    user = uid(x_user_id)
    return _view(store.get_check(_wrap(svc.start_single, user, body.model_dump())))


@router.get("/checks/{check_id}", tags=[T_MAIN], summary="Статус и прогресс проверки, сводка clean / risky / spam, результаты по лидам")
def get_check(check_id: int, x_user_id: int | None = Header(None)):
    c = store.get_check(check_id, uid(x_user_id))
    if not c:
        raise HTTPException(404, "Проверка не найдена.")
    return _view(c)


@router.get("/checks/{check_id}/leads/{lead_number}", tags=[T_MAIN], summary="📋 #N — полный JSON результата лида (кнопка под сводкой)")
def get_lead(check_id: int, lead_number: int, x_user_id: int | None = Header(None)):
    c = store.get_check(check_id, uid(x_user_id))
    if not c:
        raise HTTPException(404, "Результаты проверки не найдены. Пожалуйста, выполните проверку снова.")
    for r in c["results"] or []:
        if r and r.get("lead_number") == lead_number:
            return r
    raise HTTPException(404, "Лид не найден.")


@router.post("/checks/{check_id}/cancel", tags=[T_MAIN], summary="Остановить проверку")
async def cancel(check_id: int, x_user_id: int | None = Header(None)):
    return {"cancelled": _wrap(svc.cancel, uid(x_user_id), check_id)}


@router.post("/checks/{check_id}/retry", tags=[T_MAIN], status_code=status.HTTP_202_ACCEPTED, summary="Проверить те же данные ещё раз")
async def retry(check_id: int, x_user_id: int | None = Header(None)):
    user = uid(x_user_id)
    return _view(store.get_check(_wrap(svc.retry, user, check_id)))


# ── распознавание без проверки ───────────────────────────────────
@router.post("/parse/text", tags=[T_PARSE], summary="Какие лиды бот распознает в тексте (без проверки и без трат)")
def parse_text(body: TextIn):
    leads = svc.parse_text(body.text)
    return {"count": len(leads), "leads": leads, "error": None if leads else svc.NO_DATA_TEXT}


@router.post("/parse/file", tags=[T_PARSE], summary="Какие лиды бот найдёт в файле (без проверки и без трат)")
async def parse_file(file: UploadFile = File(...)):
    p = _wrap(svc.parse_file, await file.read(), file.filename or "unknown")
    return {"count": len(p["leads"]), "leads": p["leads"], "file_type": p["file_type"], "is_table": p["is_table"],
            "columns": p["fieldnames"], "error": None if p["leads"] else svc.NO_DATA_FILE}


# ── отдельные проверки ───────────────────────────────────────────
@router.post("/tools/{kind}", tags=[T_TOOLS], summary="Одна проверка: email (Abstract API), ip (ipdata), phone (numverify), whatsapp (RapidAPI), social (5 соцсетей по email)")
async def tool(kind: Literal["email", "ip", "phone", "whatsapp", "social"], body: ValueIn, x_user_id: int | None = Header(None)):
    user = uid(x_user_id)
    try:
        res = await svc.check_one(kind, body.value)
    except svc.FlowError as e:
        raise HTTPException(e.status, e.message) from e
    store.audit(user, f"tool.{kind}", {"value": body.value})
    return res


@router.post("/score", tags=[T_TOOLS], summary="Итоговая оценка и вердикт по оценкам IP / email / телефона (веса и пороги бота)")
def score(body: ScoreIn):
    return svc.score(body.ip_score, body.email_score, body.phone_score)


# ── история и файлы ──────────────────────────────────────────────
@router.get("/checks", tags=[T_HIST], summary="История проверок пользователя")
def list_checks(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), x_user_id: int | None = Header(None)):
    return store.list_checks(uid(x_user_id), limit, offset)


@router.get("/checks/{check_id}/download", tags=[T_HIST], summary="Файл, который прислал бы бот: <имя>_checked.csv / checked_leads.csv / lead_N_result.txt")
def download(check_id: int, x_user_id: int | None = Header(None)):
    user = uid(x_user_id)
    if not store.get_check(check_id, user):
        raise HTTPException(404, "Проверка не найдена.")
    kind, name, data = store.get_output(check_id)
    if not data:
        raise HTTPException(404, "Для этой проверки бот отвечает сводкой без файла — используй CSV или JSON выгрузку.")
    store.audit(user, "check.download", {"check_id": check_id, "file": name})
    media = "text/csv; charset=utf-8" if kind == "csv" else "text/plain; charset=utf-8"
    return Response(data, media_type=media, headers={"Content-Disposition": _cd(name)})


@router.get("/checks/{check_id}/export.csv", tags=[T_HIST], summary="CSV с результатами (для любой проверки)")
def export_csv(check_id: int, x_user_id: int | None = Header(None)):
    user = uid(x_user_id)
    c = store.get_check(check_id, user)
    if not c or c["status"] != "done":
        raise HTTPException(404, "Готовых результатов нет.")
    store.audit(user, "check.export", {"check_id": check_id, "format": "csv"})
    return Response(svc.export_csv(c), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": _cd(f"leads_check_{check_id}.csv")})


@router.get("/checks/{check_id}/export.json", tags=[T_HIST], summary="Все результаты в JSON")
def export_json(check_id: int, x_user_id: int | None = Header(None)):
    user = uid(x_user_id)
    c = store.get_check(check_id, user)
    if not c or c["status"] != "done":
        raise HTTPException(404, "Готовых результатов нет.")
    store.audit(user, "check.export", {"check_id": check_id, "format": "json"})
    return Response(svc.json.dumps(c["results"], ensure_ascii=False, indent=2, default=str), media_type="application/json",
                    headers={"Content-Disposition": _cd(f"leads_check_{check_id}.json")})


@router.get("/checks/{check_id}/source", tags=[T_HIST], summary="Исходный загруженный файл")
def source(check_id: int, x_user_id: int | None = Header(None)):
    c = store.get_check(check_id, uid(x_user_id))
    data = store.get_file(check_id) if c else None
    if not data:
        raise HTTPException(404, "Исходного файла нет.")
    return Response(data, media_type="application/octet-stream", headers={"Content-Disposition": _cd(c["file_name"])})


@router.delete("/checks/{check_id}", tags=[T_HIST], status_code=204, summary="Удалить проверку из истории")
def delete(check_id: int, x_user_id: int | None = Header(None)):
    user = uid(x_user_id)
    if not store.get_check(check_id, user):
        raise HTTPException(404, "Проверка не найдена.")
    store.delete_check(check_id)
    store.audit(user, "check.delete", {"check_id": check_id})


# ── журнал действий ──────────────────────────────────────────────
@router.get("/audit", tags=[T_AUDIT], summary="Кто, что и когда делал. Пользователь видит свои действия, админ (LEADS_ADMIN_IDS) — все")
def audit(all_users: bool = False, limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0), x_user_id: int | None = Header(None)):
    user = uid(x_user_id)
    is_admin = user in svc.admin_ids()
    if all_users and not is_admin:
        raise HTTPException(403, "Журнал всех пользователей доступен только админам.")
    return {"is_admin": is_admin, "items": store.list_audit(None if all_users else user, limit, offset)}


def _cd(name: str) -> str:
    from urllib.parse import quote  # pylint: disable=import-outside-toplevel
    ascii_name = name.encode("ascii", "ignore").decode() or "file"
    return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(name)}"
