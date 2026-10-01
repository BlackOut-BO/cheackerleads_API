"""Утилиты для парсинга данных лидов"""
import re
import csv
import io
from typing import List, Dict, Optional


class LeadParser:
    """Парсер данных лидов из различных форматов"""
    
    # Регулярные выражения для распознавания
    EMAIL_PATTERN = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    IP_PATTERN = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
    # Улучшенный паттерн для телефонов - сначала ищем полные номера с +, потом остальные
    PHONE_PATTERN_FULL = r'\+?[1-9]\d{6,14}'  # Полный номер с кодом страны
    PHONE_PATTERN = r'[\+]?[(]?[0-9]{1,4}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,9}'
    
    @staticmethod
    def parse_text(text: str) -> Dict[str, Optional[str]]:
        """
        Парсит текст и извлекает email, IP и телефон
        
        Args:
            text: Текст для парсинга
            
        Returns:
            dict: Словарь с ключами email, ip, phone
        """
        result = {
            "email": None,
            "ip": None,
            "phone": None
        }
        
        # Ищем email
        email_match = re.search(LeadParser.EMAIL_PATTERN, text)
        if email_match:
            result["email"] = email_match.group(0)
        
        # Ищем IP
        ip_match = re.search(LeadParser.IP_PATTERN, text)
        if ip_match:
            ip = ip_match.group(0)
            # Проверяем, что это валидный IP
            try:
                parts = ip.split('.')
                if len(parts) == 4 and all(part.isdigit() and 0 <= int(part) <= 255 for part in parts):
                    result["ip"] = ip
            except (ValueError, AttributeError):
                pass
        
        # Ищем телефон - сначала полные номера с +, потом остальные
        phone_match = re.search(LeadParser.PHONE_PATTERN_FULL, text)
        if phone_match:
            result["phone"] = phone_match.group(0).strip()
        else:
            # Если не нашли полный номер, ищем обычный паттерн
            phone_match = re.search(LeadParser.PHONE_PATTERN, text)
            if phone_match:
                phone = phone_match.group(0).strip()
                # Проверяем, что это не слишком короткий номер
                digits = ''.join(filter(str.isdigit, phone))
                if len(digits) >= 7:  # Минимум 7 цифр
                    result["phone"] = phone
        
        return result
    
    @staticmethod
    def parse_csv(file_content: bytes) -> List[Dict[str, Optional[str]]]:
        """
        Парсит CSV файл с лидами
        
        Args:
            file_content: Содержимое CSV файла в байтах
            
        Returns:
            list: Список словарей с лидами
        """
        leads = []
        
        try:
            # Декодируем файл (пробуем разные кодировки)
            try:
                text = file_content.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    text = file_content.decode('utf-8-sig')  # BOM
                except UnicodeDecodeError:
                    text = file_content.decode('latin-1')  # Fallback
            
            csv_reader = csv.DictReader(io.StringIO(text))
            
            for row in csv_reader:
                lead = {
                    "email": None,
                    "ip": None,
                    "phone": None
                }
                
                # Ищем данные в разных колонках
                for key, value in row.items():
                    # Безопасная проверка на None
                    if key is None:
                        continue
                    
                    key_str = str(key).strip() if key else ""
                    if not key_str:
                        continue
                    
                    key_lower = key_str.lower()
                    
                    # Безопасная обработка значения
                    if value is None:
                        continue
                    
                    value_str = str(value).strip() if value else ""
                    
                    if not value_str:
                        continue
                    
                    # Определяем тип данных по названию колонки или содержимому
                    if 'email' in key_lower or '@' in value_str:
                        if re.match(LeadParser.EMAIL_PATTERN, value_str):
                            lead["email"] = value_str
                    elif 'ip' in key_lower or 'address' in key_lower:
                        if re.match(LeadParser.IP_PATTERN, value_str):
                            parts = value_str.split('.')
                            if all(part.isdigit() and 0 <= int(part) <= 255 for part in parts):
                                lead["ip"] = value_str
                    elif 'phone' in key_lower or 'tel' in key_lower or 'mobile' in key_lower:
                        lead["phone"] = value_str
                    else:
                        # Пытаемся определить тип по содержимому
                        if '@' in value_str and re.match(LeadParser.EMAIL_PATTERN, value_str):
                            lead["email"] = value_str
                        elif re.match(LeadParser.IP_PATTERN, value_str):
                            parts = value_str.split('.')
                            if all(part.isdigit() and 0 <= int(part) <= 255 for part in parts):
                                lead["ip"] = value_str
                        elif re.search(LeadParser.PHONE_PATTERN_FULL, value_str):
                            lead["phone"] = value_str
                        elif re.search(LeadParser.PHONE_PATTERN, value_str):
                            digits = ''.join(filter(str.isdigit, value_str))
                            if len(digits) >= 7:  # Минимум 7 цифр
                                lead["phone"] = value_str
                
                # Добавляем лид, если есть хотя бы одно поле
                if lead["email"] or lead["ip"] or lead["phone"]:
                    leads.append(lead)
        
        except Exception as e:
            raise ValueError(f"Ошибка при парсинге CSV: {str(e)}")
        
        return leads
    
    @staticmethod
    def parse_multiple_text(text: str) -> List[Dict[str, Optional[str]]]:
        """
        Парсит текст с несколькими лидами (разделенными переносами строк или другими разделителями)
        
        Args:
            text: Текст с несколькими лидами
            
        Returns:
            list: Список словарей с лидами
        """
        leads = []
        
        # Разделяем по строкам
        lines = text.split('\n')
        current_lead = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                if current_lead and (current_lead.get("email") or current_lead.get("ip") or current_lead.get("phone")):
                    leads.append(current_lead)
                    current_lead = {}
                continue
            
            # Парсим строку
            parsed = LeadParser.parse_text(line)
            
            # Если в строке найдены все три типа данных, это отдельный лид
            found_count = sum(1 for v in parsed.values() if v)
            if found_count >= 2:  # Если найдено 2+ типа данных, это отдельный лид
                if current_lead and (current_lead.get("email") or current_lead.get("ip") or current_lead.get("phone")):
                    leads.append(current_lead)
                current_lead = parsed
            else:
                # Объединяем с текущим лидом
                for key, value in parsed.items():
                    if value and not current_lead.get(key):
                        current_lead[key] = value
        
        # Добавляем последний лид
        if current_lead and (current_lead.get("email") or current_lead.get("ip") or current_lead.get("phone")):
            leads.append(current_lead)
        
        # Если ничего не найдено, пытаемся распарсить весь текст как один лид
        if not leads:
            single_lead = LeadParser.parse_text(text)
            if single_lead.get("email") or single_lead.get("ip") or single_lead.get("phone"):
                leads.append(single_lead)
        
        return leads
