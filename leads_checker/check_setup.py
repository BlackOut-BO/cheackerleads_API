#!/usr/bin/env python3
"""Скрипт для проверки готовности проекта к запуску"""
import os
import sys

def check_files():
    """Проверяет наличие всех необходимых файлов"""
    required_files = [
        "main.py",
        "bot.py",
        "config.py",
        "requirements.txt",
        "services/email_checker.py",
        "services/ip_checker.py",
        "services/phone_checker.py",
        "services/whatsapp_checker.py",
        "services/social_checkers.py",
        "services/lead_checker.py",
        "utils/data_parser.py",
        "utils/risk_scorer.py"
    ]
    
    missing = []
    for file in required_files:
        if not os.path.exists(file):
            missing.append(file)
    
    if missing:
        print("❌ Отсутствуют файлы:")
        for file in missing:
            print(f"  - {file}")
        return False
    else:
        print("✅ Все необходимые файлы на месте")
        return True

def check_env():
    """Проверяет наличие .env файла"""
    if os.path.exists(".env"):
        print("✅ Файл .env найден")
        return True
    else:
        print("⚠️  Файл .env не найден")
        print("   Создайте его на основе env.example и заполните API ключи")
        return False

def check_imports():
    """Проверяет импорты"""
    try:
        from config import TELEGRAM_BOT_TOKEN
        print("✅ Импорты работают")
        return True
    except Exception as e:
        print(f"❌ Ошибка импорта: {e}")
        return False

def main():
    """Основная функция проверки"""
    print("🔍 Проверка готовности проекта...\n")
    
    all_ok = True
    
    print("1. Проверка файлов:")
    if not check_files():
        all_ok = False
    
    print("\n2. Проверка конфигурации:")
    if not check_env():
        all_ok = False
    
    print("\n3. Проверка импортов:")
    if not check_imports():
        all_ok = False
    
    print("\n" + "="*50)
    if all_ok:
        print("✅ Проект готов к запуску!")
        print("\nСледующие шаги:")
        print("1. Убедитесь, что все API ключи заполнены в .env")
        print("2. Запустите: python main.py")
    else:
        print("❌ Проект не готов. Исправьте ошибки выше.")
        sys.exit(1)

if __name__ == '__main__':
    main()
