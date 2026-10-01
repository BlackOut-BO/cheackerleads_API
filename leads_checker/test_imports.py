"""Тестовый скрипт для проверки всех импортов"""
import sys

def test_imports():
    """Проверяет все импорты проекта"""
    errors = []
    
    try:
        from config import (
            TELEGRAM_BOT_TOKEN, ABSTRACT_API_KEY, IPDATA_API_KEY,
            NUMVERIFY_API_KEY, RAPIDAPI_KEY
        )
        print("✅ config.py - OK")
    except Exception as e:
        errors.append(f"config.py: {e}")
        print(f"❌ config.py - ОШИБКА: {e}")
    
    try:
        from services.email_checker import EmailChecker
        from services.ip_checker import IPChecker
        from services.phone_checker import PhoneChecker
        from services.whatsapp_checker import WhatsAppChecker
        from services.social_checkers import (
            FacebookChecker, GoogleChecker, InstagramChecker,
            SnapchatChecker, XChecker
        )
        from services.lead_checker import LeadChecker
        print("✅ services - OK")
    except Exception as e:
        errors.append(f"services: {e}")
        print(f"❌ services - ОШИБКА: {e}")
    
    try:
        from utils.data_parser import LeadParser
        from utils.risk_scorer import (
            EmailRiskScorer, IPRiskScorer, PhoneRiskScorer,
            RiskAggregator, VerdictMapper
        )
        print("✅ utils - OK")
    except Exception as e:
        errors.append(f"utils: {e}")
        print(f"❌ utils - ОШИБКА: {e}")
    
    try:
        from bot import format_check_result, start, help_command, handle_document, handle_text, main
        print("✅ bot.py - OK")
    except Exception as e:
        errors.append(f"bot.py: {e}")
        print(f"❌ bot.py - ОШИБКА: {e}")
    
    if errors:
        print("\n❌ Обнаружены ошибки импорта!")
        for error in errors:
            print(f"  - {error}")
        return False
    else:
        print("\n✅ Все импорты успешны!")
        return True

if __name__ == '__main__':
    success = test_imports()
    sys.exit(0 if success else 1)
