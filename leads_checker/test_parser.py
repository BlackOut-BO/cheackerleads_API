"""Тестовый скрипт для проверки парсера данных"""
from utils.data_parser import LeadParser

def test_parser():
    """Тестирует парсер данных"""
    parser = LeadParser()
    
    # Тест 1: Простой текст
    print("Тест 1: Простой текст")
    text1 = "email=test@example.com | ip=192.168.1.1 | phone=+1234567890"
    result1 = parser.parse_text(text1)
    print(f"  Результат: {result1}")
    assert result1["email"] == "test@example.com"
    assert result1["ip"] == "192.168.1.1"
    assert result1["phone"] == "+1234567890"
    print("  ✅ OK\n")
    
    # Тест 2: Текст без разделителей
    print("Тест 2: Текст без разделителей")
    text2 = "test@example.com 192.168.1.1 +1234567890"
    result2 = parser.parse_text(text2)
    print(f"  Результат: {result2}")
    assert result2["email"] == "test@example.com"
    assert result2["ip"] == "192.168.1.1"
    print("  ✅ OK\n")
    
    # Тест 3: Множественные лиды
    print("Тест 3: Множественные лиды")
    text3 = """test1@example.com 192.168.1.1 +1234567890
test2@example.com 192.168.1.2 +1234567891"""
    results3 = parser.parse_multiple_text(text3)
    print(f"  Найдено лидов: {len(results3)}")
    assert len(results3) == 2
    print("  ✅ OK\n")
    
    # Тест 4: CSV (симуляция)
    print("Тест 4: CSV формат")
    csv_content = b"email,ip,phone\ntest@example.com,192.168.1.1,+1234567890"
    results4 = parser.parse_csv(csv_content)
    print(f"  Найдено лидов: {len(results4)}")
    assert len(results4) == 1
    assert results4[0]["email"] == "test@example.com"
    print("  ✅ OK\n")
    
    print("✅ Все тесты парсера пройдены успешно!")

if __name__ == '__main__':
    test_parser()
