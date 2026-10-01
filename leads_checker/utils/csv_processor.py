"""Утилиты для обработки CSV файлов с результатами проверки"""
import csv
import io
import re
from typing import List, Dict, Optional, Tuple


class CSVProcessor:
    """Обработчик CSV файлов с добавлением результатов проверки"""
    
    @staticmethod
    def _format_result_for_csv(result: Dict, lead_num: int) -> str:
        """
        Форматирует результат проверки для CSV файла (без HTML тегов)
        
        Args:
            result: Результат проверки лида
            lead_num: Номер лида
            
        Returns:
            str: Отформатированный текст без HTML тегов
        """
        lead = result.get("lead", {}) or {}
        lead_info = []
        if lead.get("ip"):
            lead_info.append(f"ip={lead['ip']}")
        if lead.get("email"):
            lead_info.append(f"email={lead['email']}")
        if lead.get("phone"):
            lead_info.append(f"phone={lead['phone']}")
        
        # Если нет данных лида, пробуем получить из результата напрямую
        if not lead_info:
            if result.get("ip_data"):
                ip_data = result.get("ip_data", {})
                if isinstance(ip_data, dict) and ip_data.get("ip"):
                    lead_info.append(f"ip={ip_data['ip']}")
            if result.get("email_data"):
                email_data = result.get("email_data", {})
                if isinstance(email_data, dict) and email_data.get("email"):
                    lead_info.append(f"email={email_data['email']}")
            if result.get("phone_data"):
                phone_data = result.get("phone_data", {})
                if isinstance(phone_data, dict) and phone_data.get("number"):
                    lead_info.append(f"phone={phone_data['number']}")
        
        lead_str = " | ".join(lead_info) if lead_info else "N/A"
        lead_num_str = f"Lead #{lead_num}: " if lead_num else ""
        
        verdict = result.get("verdict", "unknown")
        score = result.get("final_score", 0) or 0
        
        # Формируем текст в старом формате (без HTML)
        text = f"{lead_num_str}{lead_str}\n"
        text += f"Verdict: {verdict.upper()} (score: {score:.2f})\n\n"
        
        # Checks
        text += "Checks:\n"
        ip_score = result.get('ip_score')
        email_score = result.get('email_score')
        phone_score = result.get('phone_score')
        
        if ip_score is not None:
            text += f"• IP: {ip_score:.1f}\n"
        else:
            ip_data = result.get('ip_data') or {}
            ip_error = ip_data.get('error', 'Not checked') if isinstance(ip_data, dict) else 'Not checked'
            text += f"• IP: ❌ {ip_error}\n"
        
        if email_score is not None:
            text += f"• Email: {email_score:.1f}\n"
        else:
            email_data = result.get('email_data') or {}
            email_error = email_data.get('error', 'Not checked') if isinstance(email_data, dict) else 'Not checked'
            text += f"• Email: ❌ {email_error}\n"
        
        if phone_score is not None:
            text += f"• Phone: {phone_score:.1f}\n"
        else:
            phone_data = result.get('phone_data') or {}
            phone_error = phone_data.get('error', 'Not checked') if isinstance(phone_data, dict) else 'Not checked'
            text += f"• Phone: ❌ {phone_error}\n"
        
        text += f"\nThresholds: risky>=50, spam>=75\n"
        
        # WhatsApp проверка
        if result.get("whatsapp_data"):
            whatsapp_data = result["whatsapp_data"]
            if whatsapp_data.get("error"):
                whatsapp_error = whatsapp_data.get("error", "Not checked")
                text += f"WhatsApp: ❌ {whatsapp_error}\n"
            else:
                whatsapp_valid = whatsapp_data.get("valid", False)
                # Показываем результат проверки (даже если Invalid, это означает, что проверка была выполнена)
                status_text = "✓ Valid" if whatsapp_valid else "✗ Invalid (checked)"
                text += f"WhatsApp: {status_text}\n"
        
        # Социальные сети
        social_data = result.get("social_data", {})
        if social_data:
            text += f"\nSocial networks:\n"
            for social_name, social_result in social_data.items():
                if not social_result.get("error"):
                    exists = social_result.get("exists", False)
                    text += f"  {social_name.capitalize()}: {'✓ Found' if exists else '✗ Not found'}\n"
        
        # Причины
        reasons = result.get("reasons", [])
        if reasons:
            text += f"\n- Reasons:\n"
            for reason in reasons[:30]:  # Ограничиваем количество причин для CSV
                text += f"  • {reason}\n"
        
        return text
    
    @staticmethod
    def parse_csv_with_structure(file_content: bytes) -> Tuple[List[Dict], List[str], List[Dict], str]:
        """
        Парсит CSV файл, сохраняя структуру и оригинальные строки
        
        Args:
            file_content: Содержимое CSV файла в байтах
            
        Returns:
            tuple: (leads, fieldnames, original_rows)
        """
        leads = []
        fieldnames = []
        original_rows = []
        
        try:
            # Декодируем файл
            try:
                text = file_content.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    text = file_content.decode('utf-8-sig')
                except UnicodeDecodeError:
                    text = file_content.decode('latin-1')
            
            # Определяем разделитель CSV (точка с запятой или запятая)
            delimiter = ';' if ';' in text.split('\n')[0] else ','
            
            csv_reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
            fieldnames = csv_reader.fieldnames or []
            
            # Фильтруем None из fieldnames
            fieldnames = [f for f in fieldnames if f is not None]
            
            for row in csv_reader:
                original_rows.append(row.copy())
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
                    # Безопасная проверка на пустые значения
                    try:
                        if value_str.lower() in ['none', 'null', 'nan', '']:
                            continue
                    except AttributeError:
                        continue
                    
                    # Определяем тип данных
                    try:
                        import re
                        from utils.data_parser import LeadParser
                        
                        # Email - проверяем по ключу или содержимому
                        if 'email' in key_lower or '@' in value_str:
                            if re.match(LeadParser.EMAIL_PATTERN, value_str):
                                lead["email"] = value_str
                        
                        # IP - проверяем по ключу (ip, address, login ip) или содержимому
                        if ('ip' in key_lower or 'address' in key_lower) and not lead.get("ip"):
                            # Проверяем IPv4
                            if re.match(LeadParser.IP_PATTERN, value_str):
                                parts = value_str.split('.')
                                if len(parts) == 4 and all(part.isdigit() and 0 <= int(part) <= 255 for part in parts):
                                    lead["ip"] = value_str
                            # Пропускаем IPv6 адреса (они начинаются с цифр или букв и содержат :)
                        
                        # Phone - проверяем по ключу или содержимому
                        if ('phone' in key_lower or 'tel' in key_lower or 'mobile' in key_lower) and not lead.get("phone"):
                            # Обрабатываем научную нотацию Excel (например, "9,73596E+11")
                            phone_value = value_str
                            if 'E+' in phone_value.upper() or 'E-' in phone_value.upper():
                                try:
                                    # Заменяем запятую на точку для float
                                    phone_value = phone_value.replace(',', '.').replace(' ', '')
                                    # Преобразуем из научной нотации
                                    phone_float = float(phone_value)
                                    phone_value = str(int(phone_float))
                                except (ValueError, OverflowError):
                                    pass
                            
                            # Очищаем телефон от пробелов и других символов для проверки
                            # Сначала убираем все пробелы, затем оставляем только цифры и +
                            phone_clean = phone_value.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
                            phone_clean = re.sub(r'[^\d+]', '', phone_clean)
                            if len(phone_clean) >= 7:  # Минимум 7 цифр
                                # Сохраняем очищенный формат телефона
                                lead["phone"] = phone_clean
                        
                        # Если еще не определили тип, пробуем по содержимому
                        if not lead.get("email") and '@' in value_str and re.match(LeadParser.EMAIL_PATTERN, value_str):
                            lead["email"] = value_str
                        
                        if not lead.get("ip") and re.match(LeadParser.IP_PATTERN, value_str):
                            parts = value_str.split('.')
                            if len(parts) == 4 and all(part.isdigit() and 0 <= int(part) <= 255 for part in parts):
                                lead["ip"] = value_str
                        
                        # Дополнительная проверка телефона по содержимому (если не найден по ключу)
                        if not lead.get("phone"):
                            # Обрабатываем научную нотацию
                            phone_value = value_str
                            if 'E+' in phone_value.upper() or 'E-' in phone_value.upper():
                                try:
                                    phone_value = phone_value.replace(',', '.').replace(' ', '')
                                    phone_float = float(phone_value)
                                    phone_value = str(int(phone_float))
                                except (ValueError, OverflowError):
                                    pass
                            
                            # Очищаем телефон от пробелов и других символов
                            phone_clean = phone_value.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
                            phone_clean = re.sub(r'[^\d+]', '', phone_clean)
                            if len(phone_clean) >= 7:
                                lead["phone"] = phone_clean
                    except Exception as e:
                        # Пропускаем ошибки парсинга отдельных значений
                        continue
                
                # Добавляем лид даже если есть хотя бы одно поле
                if lead["email"] or lead["ip"] or lead["phone"]:
                    leads.append(lead)
                else:
                    # Если нет данных, добавляем пустой лид для сохранения структуры CSV
                    leads.append(lead)
        
        except Exception as e:
            raise ValueError(f"Ошибка при парсинге CSV: {str(e)}")
        
        return leads, fieldnames, original_rows, delimiter
    
    @staticmethod
    def create_csv_with_results(
        original_rows: List[Dict],
        fieldnames: List[str],
        results: List[Dict],
        file_name: str = "results.csv",
        delimiter: str = ","
    ) -> bytes:
        """
        Создает CSV файл с добавленными колонками результатов
        
        Args:
            original_rows: Оригинальные строки CSV
            fieldnames: Названия колонок
            results: Результаты проверки лидов
            file_name: Имя файла
            
        Returns:
            bytes: Содержимое CSV файла
        """
        output = io.StringIO()
        
        # Добавляем новые колонки
        new_fieldnames = list(fieldnames) + ["Validity", "Verdict", "Score", "IP Score", "Email Score", "Phone Score", "Description"]
        writer = csv.DictWriter(output, fieldnames=new_fieldnames)
        writer.writeheader()
        
        # Записываем строки с результатами
        for i, row in enumerate(original_rows):
            # Фильтруем None ключи из row
            clean_row = {k: v for k, v in row.items() if k is not None}
            
            if i < len(results):
                result = results[i]
                verdict = result.get("verdict", "unknown") or "unknown"
                score = result.get("final_score", 0) or 0
                ip_score = result.get("ip_score")
                email_score = result.get("email_score")
                phone_score = result.get("phone_score")
                
                # Безопасное преобразование score
                try:
                    score = float(score) if score is not None else 0.0
                except (ValueError, TypeError):
                    score = 0.0
                
                # Определяем валидность
                if verdict == "clean":
                    valid_status = "✅ Valid"
                elif verdict == "risky":
                    valid_status = "⚠️ Risky"
                else:
                    valid_status = "❌ Invalid"
                
                # Добавляем результаты
                clean_row["Validity"] = valid_status
                clean_row["Verdict"] = str(verdict).upper() if verdict else "UNKNOWN"
                clean_row["Score"] = f"{score:.2f}" if score is not None else "N/A"
                clean_row["IP Score"] = f"{ip_score:.2f}" if ip_score is not None else "N/A"
                clean_row["Email Score"] = f"{email_score:.2f}" if email_score is not None else "N/A"
                clean_row["Phone Score"] = f"{phone_score:.2f}" if phone_score is not None else "N/A"
                
                # Форматируем полное описание для CSV
                full_description = CSVProcessor._format_result_for_csv(result, lead_num=i+1)
                clean_row["Description"] = full_description
            else:
                # Если нет результата для этой строки, оставляем пустым
                clean_row["Validity"] = ""
                clean_row["Verdict"] = ""
                clean_row["Score"] = ""
                clean_row["IP Score"] = ""
                clean_row["Email Score"] = ""
                clean_row["Phone Score"] = ""
                clean_row["Description"] = ""
            
            writer.writerow(clean_row)
        
        output.seek(0)
        return output.getvalue().encode('utf-8-sig')  # UTF-8 с BOM для Excel
