"""Чекер лидов: флоу бота Checkerleads через веб. Внешние API подменены, логика бота — настоящая."""
import ast
import io
import json
import time
from pathlib import Path

import pytest
from openpyxl import Workbook

API = "/api/buying/leads"
BOT = Path(__file__).resolve().parents[1] / "leads_checker" / "bot.py"


def _email(email):
    bad = "spam" in email
    return {"deliverability": "UNDELIVERABLE" if bad else "DELIVERABLE", "valid_format": True, "is_smtp_valid": not bad, "is_mx_valid": True,
            "quality_score": 0.1 if bad else 0.9, "free": True, "disposable": bad, "address_risk_status": "high" if bad else "low",
            "domain_risk_status": "low", "total_breaches": 0, "is_risky_tld": False, "error": None}


def _ip(ip):
    tor = ip.startswith("185.")
    return {"is_tor": tor, "is_proxy": tor, "is_anonymous": tor, "is_known_attacker": False, "is_known_abuser": False, "is_threat": tor,
            "is_bogon": False, "country_code": "DE", "country_name": "Germany", "city": "Berlin", "asn": "AS1", "asn_name": "x", "error": None}


def _phone(phone):
    return {"valid": not phone.endswith("000"), "number": phone, "line_type": "mobile", "carrier": "T", "country_code": "DE", "error": None}


@pytest.fixture(autouse=True)
def no_real_keys(monkeypatch):
    """Тесты никогда не ходят во внешние API: ключи из .env (в т.ч. рабочие) обнуляются."""
    from app.leads import service as svc
    from app.leads.legacy import config
    for k in ("ABSTRACT_API_KEY", "IPDATA_API_KEY", "NUMVERIFY_API_KEY", "RAPIDAPI_KEY", "PROXY_URL", "CHECKNUMBER_API_KEY"):
        monkeypatch.setattr(config, k, "" if k in ("PROXY_URL", "CHECKNUMBER_API_KEY") else None)
    lc = svc.lead_checker
    for name in ("email_checker", "ip_checker", "phone_checker", "whatsapp_checker", "facebook_checker", "google_checker",
                 "instagram_checker", "snapchat_checker", "x_checker"):
        monkeypatch.setattr(getattr(lc, name), "api_key", None)
    monkeypatch.setattr(lc.whatsapp_checker, "proxy_url", None)


@pytest.fixture()
def lx(client, monkeypatch):
    from app.leads import service as svc
    lc = svc.lead_checker
    calls = []

    async def wrap(fn, name, v):
        calls.append((name, v))
        return fn(v)

    monkeypatch.setattr(lc.email_checker, "check", lambda v: wrap(_email, "email", v))
    monkeypatch.setattr(lc.ip_checker, "check", lambda v: wrap(_ip, "ip", v))
    monkeypatch.setattr(lc.phone_checker, "check", lambda v: wrap(_phone, "phone", v))

    async def wa(v, max_retries=3):
        calls.append(("whatsapp", v))
        return {"valid": True, "error": None}
    monkeypatch.setattr(lc.whatsapp_checker, "check", wa)
    for n in ("facebook", "google", "instagram", "snapchat", "x"):
        async def soc(v, n=n):
            calls.append((n, v))
            return {"exists": n in ("facebook", "instagram"), "error": None}
        monkeypatch.setattr(getattr(lc, f"{n}_checker"), "check", soc)
    client.calls = calls
    return client


def wait(c, cid, user=None, timeout=30):
    h = {"X-User-Id": str(user)} if user else {}
    end = time.time() + timeout
    while time.time() < end:
        j = c.get(f"{API}/checks/{cid}", headers=h).json()
        if j["status"] in ("done", "error", "cancelled"):
            return j
        time.sleep(0.1)
    raise AssertionError(j)


def test_meta_texts_and_services(lx):
    m = lx.get(f"{API}/meta").json()
    assert "проверять лиды" in m["welcome"] and "score < 50" in m["help"] and "clean - безопасный лид" in m["about"]
    assert m["formats"] == [".csv", ".xlsx", ".xls", ".txt", ".json"] and m["thresholds"] == {"risky": 50, "spam": 75}
    assert set(m["services"].values()) == {False}  # ключей веба нет — боевые не подхватываются


def test_parse_preview_and_errors(lx):
    r = lx.post(f"{API}/parse/text", json={"text": "email=a@b.com | ip=8.8.8.8 | phone=+491511234567\nc@d.com 1.1.1.1"}).json()
    assert r["count"] == 2 and r["leads"][0] == {"email": "a@b.com", "ip": "8.8.8.8", "phone": "+491511234567"}
    assert lx.post(f"{API}/parse/text", json={"text": "привет"}).json()["error"].startswith("❌ Не удалось распознать")
    bad = lx.post(f"{API}/checks/text", json={"text": "привет"})
    assert bad.status_code == 422 and "Не удалось распознать данные" in bad.json()["detail"]
    pdf = lx.post(f"{API}/checks/file", files={"file": ("a.pdf", b"%PDF", "application/pdf")})
    assert pdf.status_code == 422 and "Неподдерживаемый формат" in pdf.json()["detail"]
    empty = lx.post(f"{API}/checks/file", files={"file": ("a.txt", b"nothing here", "text/plain")})
    assert empty.status_code == 422 and empty.json()["detail"] == "❌ Не удалось найти данные в файле."
    assert lx.calls == []  # распознавание ничего не тратит


def test_text_many_leads_csv_like_bot(lx):
    text = "email=good@ok.com | ip=8.8.8.8 | phone=+491511234567\nemail=spam@bad.com | ip=185.1.1.1 | phone=+491510000000"
    c = lx.post(f"{API}/checks/text", json={"text": text}).json()
    assert c["message"].startswith("✅ Распознано лидов: 2")
    j = wait(lx, c["id"])
    assert j["status"] == "done" and j["output_kind"] == "csv" and j["output_name"] == "checked_leads.csv" and j["done"] == 2
    assert j["stats"]["clean"] == 1 and j["stats"]["spam"] + j["stats"]["risky"] == 1
    r1 = j["results"][0]
    assert r1["whatsapp_data"]["valid"] and r1["social_data"]["facebook"]["exists"] and "ip.country_code=DE" in r1["reasons"]
    d = lx.get(f"{API}/checks/{c['id']}/download")
    assert d.headers["content-disposition"].endswith("checked_leads.csv") and d.content.startswith(b"\xef\xbb\xbf")
    rows = d.content.decode("utf-8-sig").splitlines()
    assert rows[0] == "Email,IP,Phone,Validity,Verdict,Score,IP Score,Email Score,Phone Score,Description" and len(rows) > 2
    detail = lx.get(f"{API}/checks/{c['id']}/leads/2").json()
    assert detail["lead"]["email"] == "spam@bad.com" and detail["lead_number"] == 2
    assert lx.get(f"{API}/checks/{c['id']}/leads/9").status_code == 404
    assert len(json.loads(lx.get(f"{API}/checks/{c['id']}/export.json").content)) == 2
    assert lx.get(f"{API}/checks/{c['id']}/export.csv").status_code == 200


def test_single_lead_txt_matches_bot_format(lx):
    c = lx.post(f"{API}/checks/single", json={"email": "good@ok.com", "ip": "8.8.8.8", "phone": "+491511234567"}).json()
    j = wait(lx, c["id"])
    assert j["output_kind"] == "txt" and j["output_name"] == "lead_1_result.txt" and j["message"] == "📄 Результат проверки Lead #1"
    txt = lx.get(f"{API}/checks/{c['id']}/download").content.decode()
    # эталон — функция из bot.py (извлекаем исходник, бот не запускаем)
    tree = ast.parse(BOT.read_text())
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "format_check_result")
    ns = {"Dict": dict}
    exec(compile(ast.Module([fn], []), "bot_format", "exec"), ns)  # noqa: S102
    import re
    expected = re.sub(r"<[^>]+>", "", ns["format_check_result"](j["results"][0], 1, detailed=True, friendly=False))
    assert txt.startswith(expected) and "=" * 60 + "\n\nJSON Result:" in txt


def test_csv_file_keeps_columns_and_delimiter(lx):
    csv = "Name;E-mail;Phone number;User IP\nAnn;good@ok.com;+491511234567;8.8.8.8\nBob;spam@bad.com;+491510000000;185.2.2.2\n"
    c = lx.post(f"{API}/checks/file", files={"file": ("leads.csv", csv.encode(), "text/csv")}).json()
    assert c["message"].startswith("✅ Найдено лидов: 2")
    j = wait(lx, c["id"])
    assert j["output_name"] == "leads_checked.csv"
    out = lx.get(f"{API}/checks/{c['id']}/download").content.decode("utf-8-sig").splitlines()
    assert out[0].startswith("Name,E-mail,Phone number,User IP,Validity") and out[1].startswith("Ann,")


def test_excel_and_txt_and_json_files(lx):
    wb = Workbook(); ws = wb.active; ws.append(["email", "ip", "phone"]); ws.append(["good@ok.com", "8.8.8.8", "+491511234567"]); ws.append(["x@y.com", "9.9.9.9", "+491511111111"])
    b = io.BytesIO(); wb.save(b)
    j = wait(lx, lx.post(f"{API}/checks/file", files={"file": ("base.xlsx", b.getvalue(), "application/octet-stream")}).json()["id"])
    assert j["output_kind"] == "csv" and j["output_name"] == "base_checked.csv" and j["total"] == 2
    t = "good@ok.com 8.8.8.8 +491511234567\nspam@bad.com 185.1.1.1 +491510000000\nz@z.com 7.7.7.7 +491512222222"
    j = wait(lx, lx.post(f"{API}/checks/file", files={"file": ("l.txt", t.encode(), "text/plain")}).json()["id"])
    assert j["output_kind"] == "summary" and j["output_name"] is None and j["message"] == "✅ Проверка завершена! Обработано лидов: 3"
    assert lx.get(f"{API}/checks/{j['id']}/download").status_code == 404
    js = json.dumps([{"email": "good@ok.com", "ip": "8.8.8.8"}]).encode()
    j = wait(lx, lx.post(f"{API}/checks/file", files={"file": ("one.json", js, "application/json")}).json()["id"])
    assert j["total"] == 1 and j["output_kind"] in ("txt", "csv")


def test_external_errors_do_not_break(lx, monkeypatch):
    from app.leads import service as svc

    async def boom(v):
        raise RuntimeError("ipdata down")
    monkeypatch.setattr(svc.lead_checker.ip_checker, "check", boom)
    j = wait(lx, lx.post(f"{API}/checks/single", json={"email": "good@ok.com", "ip": "8.8.8.8"}).json()["id"])
    assert j["status"] == "done" and j["results"][0]["ip_score"] is None and "ip.error=ipdata down" in j["results"][0]["reasons"]


def test_no_keys_behaves_like_bot(client):
    j = wait(client, client.post(f"{API}/checks/single", json={"email": "a@b.com"}).json()["id"])
    r = j["results"][0]
    assert r["email_data"]["error"] == "API key not configured" and r["verdict"] == "clean" and "email.error=API key not configured" in r["reasons"]


def test_tools_and_score(lx):
    e = lx.post(f"{API}/tools/email", json={"value": "spam@bad.com"}).json()
    assert e["score"] >= 75 and e["data"]["disposable"]
    assert lx.post(f"{API}/tools/ip", json={"value": "185.1.1.1"}).json()["score"] > 0
    assert lx.post(f"{API}/tools/phone", json={"value": "+491511234567"}).json()["score"] == 0
    assert lx.post(f"{API}/tools/whatsapp", json={"value": "+491511234567"}).json()["data"]["valid"] is True
    s = lx.post(f"{API}/tools/social", json={"value": "a@gmail.com"}).json()["data"]
    assert set(s) == {"facebook", "google", "instagram", "snapchat", "x"}
    assert lx.post(f"{API}/score", json={"ip_score": 100, "email_score": 100}).json()["verdict"] == "spam"
    assert lx.post(f"{API}/score", json={"phone_score": 60}).json() == {**lx.post(f"{API}/score", json={"phone_score": 60}).json(), "verdict": "risky"}


def test_history_cancel_retry_delete_isolation_audit(lx, monkeypatch):
    from app.leads import service as svc
    import asyncio

    async def slow(v):
        await asyncio.sleep(5)
        return _email(v)
    monkeypatch.setattr(svc.lead_checker.email_checker, "check", slow)
    c = lx.post(f"{API}/checks/text", json={"text": "a@b.com\n\nc@d.com\n\ne@f.com\n\ng@h.com"}).json()
    time.sleep(0.3)
    assert lx.post(f"{API}/checks/{c['id']}/cancel").json()["cancelled"] is True
    assert wait(lx, c["id"])["status"] == "cancelled"
    monkeypatch.setattr(svc.lead_checker.email_checker, "check", lambda v: _async(_email(v)))
    r = lx.post(f"{API}/checks/{c['id']}/retry").json()
    assert wait(lx, r["id"])["total"] == 4
    hist = lx.get(f"{API}/checks").json()
    assert [h["id"] for h in hist][:2] == [r["id"], c["id"]] and hist[0]["stats"]["clean"] == 4
    assert lx.get(f"{API}/checks/{r['id']}", headers={"X-User-Id": "77"}).status_code == 404
    assert lx.get(f"{API}/checks", headers={"X-User-Id": "77"}).json() == []
    assert lx.delete(f"{API}/checks/{c['id']}").status_code == 204 and lx.get(f"{API}/checks/{c['id']}").status_code == 404
    acts = [a["action"] for a in lx.get(f"{API}/audit").json()["items"]]
    assert {"check.start", "check.cancel", "check.retry", "check.done", "check.delete"} <= set(acts)
    assert lx.get(f"{API}/audit?all_users=true").status_code == 403
    monkeypatch.setenv("LEADS_ADMIN_IDS", "1")
    lx.post(f"{API}/tools/phone", json={"value": "+491511234567"}, headers={"X-User-Id": "77"})
    allu = lx.get(f"{API}/audit?all_users=true").json()
    assert allu["is_admin"] and {a["user_id"] for a in allu["items"]} >= {1, 77}


async def _async(v):
    return v
