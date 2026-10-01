"""Текст результата для TXT-файла — 1:1 с bot.format_check_result(..., detailed=True, friendly=False).

Функция скопирована, а не импортирована: bot.py при импорте создаёт Telegram-объекты и файл
авторизации, а запускать код бота как есть нельзя.
"""
import re
from typing import Dict


def _err(result: Dict, key: str) -> str:
    data = result.get(key) or {}
    return data.get("error", "Не проверено") if isinstance(data, dict) else "Не проверено"


def format_check_result_technical(result: Dict, lead_num: int | None = None) -> str:
    lead = result.get("lead", {}) or {}
    lead_info = []
    if lead.get("ip"):
        lead_info.append(f"ip={lead['ip']}")
    if lead.get("email"):
        lead_info.append(f"email={lead['email']}")
    if lead.get("phone"):
        lead_info.append(f"phone={lead['phone']}")
    lead_str = " | ".join(lead_info)
    lead_num_str = f"Lead #{lead_num}: " if lead_num else ""
    verdict = result.get("verdict", "unknown")
    score = result.get("final_score", 0)

    text = f"<b>{lead_num_str}{lead_str}</b>\n"
    text += f"Verdict: <b>{verdict.upper()}</b> (score: {score:.2f})\n\n"
    text += "<b>Проверки:</b>\n"
    for key, label in (("ip", "IP"), ("email", "Email"), ("phone", "Phone")):
        s = result.get(f"{key}_score")
        text += f"• {label}: {s}\n" if s is not None else f"• {label}: ❌ {_err(result, f'{key}_data')}\n"
    text += f"\nThresholds: risky>={50}, spam>={75}\n"
    if result.get("whatsapp_data"):
        whatsapp_valid = result["whatsapp_data"].get("valid", False)
        text += f"WhatsApp: {'✓ Valid' if whatsapp_valid else '✗ Invalid'}\n"
    social_data = result.get("social_data", {})
    if social_data:
        text += "\nSocial networks:\n"
        for social_name, social_result in social_data.items():
            if not social_result.get("error"):
                exists = social_result.get("exists", False)
                text += f"  {social_name.capitalize()}: {'✓ Found' if exists else '✗ Not found'}\n"
    reasons = result.get("reasons", [])
    if reasons:
        text += "\n- Reasons:\n"
        for reason in reasons[:20]:
            text += f"  • {reason}\n"
    return text


def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)
