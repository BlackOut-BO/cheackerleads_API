"""Blackout Hub · Buying API — единый Swagger отдела Buying.

Каждый проект отдела — пакет `app/<проект>/` с `project.py` (роутер, теги, старт/стоп).
Сервис подключает все проекты, которые есть рядом: в Blackout Hub это «Поиск селеб» и «Креативы»
в одном Swagger с разделением по проектам. Репозиторий отдельного проекта содержит только его пакет
и поднимает тот же сервис с одним проектом (для разработки).
"""
import importlib
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
logging.basicConfig(level=logging.INFO)

# Порядок = порядок групп в Swagger
_PROJECT_PACKAGES = [
    ("celebs", "Telegram-бот поиска селеб (@Test_Creos_Bot)"),
    ("creatives", "креатив-бот TgCreativeBot2"),
    ("leads", "бот Checkerleads (@cheackerleadsbot)"),
]
PROJECTS = []
for _pkg, _origin in _PROJECT_PACKAGES:
    if (Path(__file__).parent / _pkg / "project.py").exists():
        _mod = importlib.import_module(f".{_pkg}.project", __package__)
        _mod.ORIGIN = _origin
        PROJECTS.append(_mod)

SERVICE_TAG = {"name": "Сервис", "description": "Состояние сервиса."}
TAGS = [t for p in PROJECTS for t in p.TAGS] + [SERVICE_TAG]


@asynccontextmanager
async def lifespan(_: FastAPI):
    for p in PROJECTS:
        await p.startup()
    yield
    for p in PROJECTS:
        await p.shutdown()


_rows = "".join(f"| **{p.NAME}** | {p.ORIGIN} | `/api/buying{p.PREFIX}` | «{p.TAGS[0]['name'].split(' · ')[0]} · …» |\n" for p in PROJECTS)
app = FastAPI(
    title="Blackout Hub · Buying API",
    version="0.2.0",
    description=(
        "Единый API отдела **Buying** для Blackout Hub. Один Swagger на отдел, проекты разделены группами тегов:\n\n"
        "| Проект | Откуда перенесён | Префикс ручек | Группы |\n|---|---|---|---|\n" + _rows +
        "\nПользователь передаётся заголовком `X-User-Id` (его проставляет панель). Боты продолжают работать параллельно."
    ),
    openapi_tags=TAGS,
    docs_url="/api/buying/docs",
    redoc_url="/api/buying/redoc",
    openapi_url="/api/buying/openapi.json",
    lifespan=lifespan,
)
for _p in PROJECTS:
    app.include_router(_p.router, prefix="/api/buying")


@app.get("/api/buying/health", tags=["Сервис"], summary="Проверка, что сервис жив")
def health():
    return {"status": "ok", "projects": [p.NAME for p in PROJECTS]}


def _openapi():
    # группы проектов для ReDoc (/api/buying/redoc); в Swagger UI — порядок и префиксы тегов
    if not app.openapi_schema:
        schema = get_openapi(title=app.title, version=app.version, description=app.description, routes=app.routes, tags=TAGS)
        schema["x-tagGroups"] = [{"name": p.NAME, "tags": [t["name"] for t in p.TAGS]} for p in PROJECTS] + [{"name": "Сервис", "tags": ["Сервис"]}]
        app.openapi_schema = schema
    return app.openapi_schema


app.openapi = _openapi
