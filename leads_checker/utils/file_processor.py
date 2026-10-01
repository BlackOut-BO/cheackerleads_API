"""Утилиты для обработки различных форматов файлов"""
import csv
import io
import json
import pandas as pd
from typing import List, Dict, Tuple, Optional


class FileProcessor:
    """Обработчик различных форматов файлов с преобразованием в единый формат"""
    
    @staticmethod
    def detect_file_type(file_name: str) -> str:
        """
        Определяет тип файла по расширению
        
        Args:
            file_name: Имя файла
            
        Returns:
            str: Тип файла (csv, excel, txt, json, unknown)
        """
        file_name_lower = file_name.lower()
        
        if file_name_lower.endswith('.csv'):
            return 'csv'
        elif file_name_lower.endswith(('.xlsx', '.xls')):
            return 'excel'
        elif file_name_lower.endswith('.txt'):
            return 'txt'
        elif file_name_lower.endswith('.json'):
            return 'json'
        else:
            return 'unknown'
    
    @staticmethod
    def parse_file(file_content: bytes, file_name: str) -> Tuple[List[Dict], List[str], List[Dict], str]:
        """
        Парсит файл любого формата и преобразует в единый формат
        
        Args:
            file_content: Содержимое файла в байтах
            file_name: Имя файла
            
        Returns:
            tuple: (leads, fieldnames, original_rows, delimiter)
        """
        file_type = FileProcessor.detect_file_type(file_name)
        
        if file_type == 'csv':
            from utils.csv_processor import CSVProcessor
            return CSVProcessor.parse_csv_with_structure(file_content)
        
        elif file_type == 'excel':
            return FileProcessor._parse_excel(file_content)
        
        elif file_type == 'json':
            return FileProcessor._parse_json(file_content)
        
        elif file_type == 'txt':
            # Для TXT используем обычный парсинг текста
            text = file_content.decode('utf-8')
            from utils.data_parser import LeadParser
            leads = LeadParser.parse_multiple_text(text)
            return leads, [], [], ','
        
        else:
            # Пробуем как CSV по умолчанию
            try:
                from utils.csv_processor import CSVProcessor
                return CSVProcessor.parse_csv_with_structure(file_content)
            except:
                # Если не получилось, пробуем как TXT
                text = file_content.decode('utf-8')
                from utils.data_parser import LeadParser
                leads = LeadParser.parse_multiple_text(text)
                return leads, [], [], ','
    
    @staticmethod
    def _parse_excel(file_content: bytes) -> Tuple[List[Dict], List[str], List[Dict], str]:
        """
        Парсит Excel файл (.xlsx, .xls)
        
        Args:
            file_content: Содержимое файла в байтах
            
        Returns:
            tuple: (leads, fieldnames, original_rows, delimiter)
        """
        leads = []
        original_rows = []
        fieldnames = []
        
        try:
            # Читаем Excel файл
            excel_file = io.BytesIO(file_content)
            
            # Пробуем прочитать как xlsx
            try:
                df = pd.read_excel(excel_file, engine='openpyxl')
            except:
                # Если не получилось, пробуем xls
                excel_file.seek(0)
                df = pd.read_excel(excel_file, engine='xlrd')
            
            # Получаем названия колонок
            fieldnames = [str(col) for col in df.columns.tolist() if col is not None]
            
            # Преобразуем DataFrame в список словарей
            for index, row in df.iterrows():
                row_dict = {}
                for col in fieldnames:
                    value = row.get(col)
                    # Преобразуем NaN в None
                    if pd.isna(value):
                        value = None
                    else:
                        value = str(value).strip() if value else None
                    row_dict[col] = value
                
                original_rows.append(row_dict.copy())
                
                # Извлекаем лид из строки
                lead = {
                    "email": None,
                    "ip": None,
                    "phone": None
                }
                
                # Ищем данные в разных колонках
                import re
                from utils.data_parser import LeadParser
                
                for key, value in row_dict.items():
                    if key is None or value is None:
                        continue
                    
                    key_str = str(key).strip().lower()
                    value_str = str(value).strip() if value else ""
                    
                    if not value_str or value_str.lower() in ['none', 'null', 'nan', '']:
                        continue
                    
                    # Email
                    if 'email' in key_str or '@' in value_str:
                        if re.match(LeadParser.EMAIL_PATTERN, value_str):
                            lead["email"] = value_str
                    
                    # IP - проверяем по ключу (ip, address, login ip) или содержимому
                    if not lead.get("ip"):
                        # Проверяем по ключу (учитываем пробелы в названии, например "Login Ip")
                        if ('ip' in key_str or 'address' in key_str or 'login' in key_str):
                            # Проверяем IPv4 (пропускаем IPv6, они содержат :)
                            if ':' not in value_str and re.match(LeadParser.IP_PATTERN, value_str):
                                parts = value_str.split('.')
                                if len(parts) == 4 and all(part.isdigit() and 0 <= int(part) <= 255 for part in parts):
                                    lead["ip"] = value_str
                        # Если не нашли по ключу, проверяем по содержимому (только IPv4)
                        elif ':' not in value_str and re.match(LeadParser.IP_PATTERN, value_str):
                            parts = value_str.split('.')
                            if len(parts) == 4 and all(part.isdigit() and 0 <= int(part) <= 255 for part in parts):
                                lead["ip"] = value_str
                    
                    # Phone - проверяем по ключу или содержимому
                    if not lead.get("phone"):
                        # Проверяем по ключу
                        if ('phone' in key_str or 'tel' in key_str or 'mobile' in key_str):
                            # Обрабатываем научную нотацию Excel
                            phone_value = value_str
                            if 'E+' in phone_value.upper() or 'E-' in phone_value.upper():
                                try:
                                    phone_value = phone_value.replace(',', '.').replace(' ', '')
                                    phone_float = float(phone_value)
                                    phone_value = str(int(phone_float))
                                except (ValueError, OverflowError):
                                    pass
                            
                            phone_clean = phone_value.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
                            phone_clean = re.sub(r'[^\d+]', '', phone_clean)
                            if len(phone_clean) >= 7:
                                # Если нет + в начале и это длинный номер, добавляем +
                                if not phone_clean.startswith('+') and len(phone_clean) >= 10:
                                    lead["phone"] = '+' + phone_clean
                                else:
                                    lead["phone"] = phone_clean
                        # Если не нашли по ключу, проверяем по содержимому (только если это похоже на телефон)
                        elif value_str and (value_str.replace(' ', '').replace('-', '').replace('+', '').replace('(', '').replace(')', '').isdigit()):
                            phone_clean = value_str.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
                            phone_clean = re.sub(r'[^\d+]', '', phone_clean)
                            if len(phone_clean) >= 7:
                                # Если нет + в начале и это длинный номер, добавляем +
                                if not phone_clean.startswith('+') and len(phone_clean) >= 10:
                                    lead["phone"] = '+' + phone_clean
                                else:
                                    lead["phone"] = phone_clean
                
                # Добавляем лид если есть хотя бы одно поле
                if lead["email"] or lead["ip"] or lead["phone"]:
                    leads.append(lead)
                else:
                    # Если нет данных, добавляем пустой лид для сохранения структуры
                    leads.append(lead)
            
            return leads, fieldnames, original_rows, ','
            
        except Exception as e:
            raise ValueError(f"Ошибка при парсинге Excel файла: {str(e)}")
    
    @staticmethod
    def _parse_json(file_content: bytes) -> Tuple[List[Dict], List[str], List[Dict], str]:
        """
        Парсит JSON файл
        
        Args:
            file_content: Содержимое файла в байтах
            
        Returns:
            tuple: (leads, fieldnames, original_rows, delimiter)
        """
        leads = []
        original_rows = []
        fieldnames = []
        
        try:
            # Декодируем и парсим JSON
            text = file_content.decode('utf-8')
            data = json.loads(text)
            
            # Если это список
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        original_rows.append(item.copy())
                        
                        # Извлекаем лид
                        lead = {
                            "email": item.get("email") or item.get("Email") or item.get("EMAIL"),
                            "ip": item.get("ip") or item.get("IP") or item.get("Ip"),
                            "phone": item.get("phone") or item.get("Phone") or item.get("PHONE") or item.get("tel") or item.get("Tel")
                        }
                        
                        # Очищаем значения
                        for key in lead:
                            if lead[key]:
                                lead[key] = str(lead[key]).strip()
                                if lead[key].lower() in ['none', 'null', 'nan', '']:
                                    lead[key] = None
                            else:
                                lead[key] = None
                        
                        leads.append(lead)
                        
                        # Определяем fieldnames из первого элемента
                        if not fieldnames:
                            fieldnames = list(item.keys())
            
            # Если это словарь с массивом данных
            elif isinstance(data, dict):
                # Ищем массив данных
                data_list = None
                for key in ['data', 'leads', 'items', 'results']:
                    if key in data and isinstance(data[key], list):
                        data_list = data[key]
                        break
                
                if data_list:
                    for item in data_list:
                        if isinstance(item, dict):
                            original_rows.append(item.copy())
                            
                            lead = {
                                "email": item.get("email") or item.get("Email") or item.get("EMAIL"),
                                "ip": item.get("ip") or item.get("IP") or item.get("Ip"),
                                "phone": item.get("phone") or item.get("Phone") or item.get("PHONE") or item.get("tel") or item.get("Tel")
                            }
                            
                            for key in lead:
                                if lead[key]:
                                    lead[key] = str(lead[key]).strip()
                                    if lead[key].lower() in ['none', 'null', 'nan', '']:
                                        lead[key] = None
                                else:
                                    lead[key] = None
                            
                            leads.append(lead)
                            
                            if not fieldnames:
                                fieldnames = list(item.keys())
            
            return leads, fieldnames, original_rows, ','
            
        except Exception as e:
            raise ValueError(f"Ошибка при парсинге JSON файла: {str(e)}")
