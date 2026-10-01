"""Модуль оценки рисков"""
from config import RISKY_THRESHOLD, SPAM_THRESHOLD, IP_WEIGHT, EMAIL_WEIGHT, PHONE_WEIGHT


class EmailRiskScorer:
    """Оценка риска для email"""
    
    @staticmethod
    def score(email_data: dict) -> float:
        """
        Оценивает риск email адреса (0-100)
        
        Args:
            email_data: Данные от EmailChecker (Email Reputation API)
            
        Returns:
            float: Оценка риска 0-100
        """
        if email_data.get("error"):
            error_msg = email_data.get("error", "").lower()
            # Если это ошибка квоты или rate limit, не увеличиваем риск
            if "quota" in error_msg or "rate limit" in error_msg or "too many" in error_msg:
                return None  # Не можем оценить из-за лимитов API
            return 50.0  # Средний риск при других ошибках
        
        score = 0.0
        
        # Deliverability - самый важный фактор
        deliverability = email_data.get("deliverability", "UNKNOWN").upper()
        if deliverability == "UNDELIVERABLE":
            score += 50.0
        elif deliverability == "DELIVERABLE":
            score += 0.0
        elif deliverability == "UNKNOWN":
            score += 20.0
        
        # Risk status - прямое указание на риск
        address_risk_status = email_data.get("address_risk_status") or "unknown"
        address_risk = str(address_risk_status).lower() if address_risk_status else "unknown"
        if address_risk == "high":
            score += 60.0
        elif address_risk == "medium":
            score += 30.0
        elif address_risk == "low":
            score += 0.0
        
        domain_risk_status = email_data.get("domain_risk_status") or "unknown"
        domain_risk = str(domain_risk_status).lower() if domain_risk_status else "unknown"
        if domain_risk == "high":
            score += 40.0
        elif domain_risk == "medium":
            score += 20.0
        
        # Disposable email - высокий риск
        if email_data.get("disposable", False):
            score += 40.0
        
        # Quality score (0.01-0.99, чем ниже, тем выше риск)
        quality_score = email_data.get("quality_score", 0.0)
        if quality_score is not None and isinstance(quality_score, (int, float)):
            try:
                quality_score = float(quality_score)
                if quality_score < 0.3:
                    score += 30.0
                elif quality_score < 0.5:
                    score += 15.0
                elif quality_score < 0.7:
                    score += 5.0
            except (ValueError, TypeError):
                pass
        
        # Breaches - утечки данных
        total_breaches = email_data.get("total_breaches", 0) or 0
        if total_breaches is None:
            total_breaches = 0
        try:
            total_breaches = int(total_breaches)
        except (ValueError, TypeError):
            total_breaches = 0
        
        if total_breaches > 5:
            score += 25.0
        elif total_breaches > 2:
            score += 15.0
        elif total_breaches > 0:
            score += 10.0
        
        # Suspicious username
        if email_data.get("is_username_suspicious", False):
            score += 20.0
        
        # Risky TLD
        if email_data.get("is_risky_tld", False):
            score += 15.0
        
        # Catchall email - средний риск
        if email_data.get("is_catchall_email", False):
            score += 10.0
        
        # Role email - низкий риск, но учитываем
        if email_data.get("is_role_email", False):
            score += 5.0
        
        # Free email - небольшой риск
        if email_data.get("free", False):
            score += 3.0
        
        # SMTP/MX validation
        if not email_data.get("is_smtp_valid", False):
            score += 10.0
        if not email_data.get("is_mx_valid", False):
            score += 10.0
        
        # Format validation
        if not email_data.get("valid_format", False):
            score += 50.0
        
        return min(score, 100.0)


class IPRiskScorer:
    """Оценка риска для IP"""
    
    @staticmethod
    def score(ip_data: dict) -> float:
        """
        Оценивает риск IP адреса (0-100)
        
        Args:
            ip_data: Данные от IPChecker
            
        Returns:
            float: Оценка риска 0-100
        """
        if ip_data.get("error"):
            return 50.0  # Средний риск при ошибке
        
        score = 0.0
        
        # Критические угрозы
        if ip_data.get("is_known_attacker", False):
            score += 60.0
        if ip_data.get("is_known_abuser", False):
            score += 50.0
        if ip_data.get("is_threat", False):
            score += 40.0
        
        # Анонимность и прокси
        if ip_data.get("is_tor", False):
            score += 50.0
        if ip_data.get("is_proxy", False):
            score += 30.0
        if ip_data.get("is_anonymous", False):
            score += 25.0
        
        # Bogon IP
        if ip_data.get("is_bogon", False):
            score += 20.0
        
        return min(score, 100.0)


class PhoneRiskScorer:
    """Оценка риска для телефона"""
    
    @staticmethod
    def score(phone_data: dict) -> float:
        """
        Оценивает риск телефонного номера (0-100)
        
        Args:
            phone_data: Данные от PhoneChecker
            
        Returns:
            float: Оценка риска 0-100
        """
        if phone_data.get("error"):
            return 50.0  # Средний риск при ошибке
        
        score = 0.0
        
        # Невалидный номер - высокий риск
        if not phone_data.get("valid", False):
            score += 60.0
            return min(score, 100.0)
        
        # Тип линии
        line_type = phone_data.get("line_type") or ""
        if line_type:
            line_type = str(line_type).upper()
            if line_type == "VOIP":
                score += 30.0
            elif line_type == "LANDLINE":
                score += 5.0
            elif line_type == "MOBILE":
                score += 0.0
        
        return min(score, 100.0)


class RiskAggregator:
    """Агрегация оценок рисков"""
    
    def __init__(self, ip_weight=IP_WEIGHT, email_weight=EMAIL_WEIGHT, phone_weight=PHONE_WEIGHT):
        self.ip_weight = ip_weight
        self.email_weight = email_weight
        self.phone_weight = phone_weight
    
    def aggregate(self, ip_score: float = None, email_score: float = None, phone_score: float = None) -> float:
        """
        Объединяет оценки рисков в итоговую
        
        Args:
            ip_score: Оценка риска IP (0-100)
            email_score: Оценка риска email (0-100)
            phone_score: Оценка риска телефона (0-100)
            
        Returns:
            float: Итоговая оценка риска (0-100)
        """
        scores = []
        weights = []
        
        if ip_score is not None:
            scores.append(ip_score)
            weights.append(self.ip_weight)
        
        if email_score is not None:
            scores.append(email_score)
            weights.append(self.email_weight)
        
        if phone_score is not None:
            scores.append(phone_score)
            weights.append(self.phone_weight)
        
        if not scores:
            return 0.0
        
        # Нормализуем веса
        total_weight = sum(weights)
        if total_weight == 0:
            return sum(scores) / len(scores) if scores else 0.0
        
        normalized_weights = [w / total_weight for w in weights]
        
        # Взвешенное среднее
        final_score = sum(score * weight for score, weight in zip(scores, normalized_weights))
        
        return round(final_score, 2)


class VerdictMapper:
    """Определение вердикта по оценке риска"""
    
    def __init__(self, risky_threshold=RISKY_THRESHOLD, spam_threshold=SPAM_THRESHOLD):
        self.risky_threshold = risky_threshold
        self.spam_threshold = spam_threshold
    
    def get_verdict(self, score: float) -> str:
        """
        Определяет вердикт по оценке риска
        
        Args:
            score: Итоговая оценка риска (0-100)
            
        Returns:
            str: Вердикт (clean/risky/spam)
        """
        if score >= self.spam_threshold:
            return "spam"
        elif score >= self.risky_threshold:
            return "risky"
        else:
            return "clean"
