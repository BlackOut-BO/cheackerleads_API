"""Основной сервис проверки лидов"""
import asyncio
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)
from services.email_checker import EmailChecker
from services.ip_checker import IPChecker
from services.phone_checker import PhoneChecker
from services.whatsapp_checker import WhatsAppChecker
from services.social_checkers import (
    FacebookChecker, GoogleChecker, InstagramChecker, 
    SnapchatChecker, XChecker
)
from utils.risk_scorer import (
    EmailRiskScorer, IPRiskScorer, PhoneRiskScorer,
    RiskAggregator, VerdictMapper
)


class LeadChecker:
    """Основной класс для проверки лидов"""
    
    def __init__(self):
        self.email_checker = EmailChecker()
        self.ip_checker = IPChecker()
        self.phone_checker = PhoneChecker()
        self.whatsapp_checker = WhatsAppChecker()
        self.facebook_checker = FacebookChecker()
        self.google_checker = GoogleChecker()
        self.instagram_checker = InstagramChecker()
        self.snapchat_checker = SnapchatChecker()
        self.x_checker = XChecker()
        
        self.email_scorer = EmailRiskScorer()
        self.ip_scorer = IPRiskScorer()
        self.phone_scorer = PhoneRiskScorer()
        self.aggregator = RiskAggregator()
        self.verdict_mapper = VerdictMapper()
    
    async def check_lead(self, lead: Dict[str, Optional[str]], check_social: bool = True) -> Dict:
        """
        Проверяет один лид
        
        Args:
            lead: Словарь с данными лида (email, ip, phone)
            check_social: Проверять ли социальные сети
            
        Returns:
            dict: Результаты проверки
        """
        result = {
            "lead": lead,
            "email_data": None,
            "ip_data": None,
            "phone_data": None,
            "whatsapp_data": None,
            "social_data": {},
            "email_score": None,
            "ip_score": None,
            "phone_score": None,
            "final_score": None,
            "verdict": None,
            "reasons": []
        }
        
        # Создаем список задач для параллельного выполнения
        tasks = []
        
        # Проверка email
        if lead.get("email"):
            tasks.append(("email", self.email_checker.check(lead["email"])))
        
        # Проверка IP
        if lead.get("ip"):
            tasks.append(("ip", self.ip_checker.check(lead["ip"])))
        
        # Проверка телефона
        if lead.get("phone"):
            phone_num = lead.get("phone")
            logger.debug(f"Checking phone: {phone_num}")
            tasks.append(("phone", self.phone_checker.check(phone_num)))
            if check_social:
                # Проверяем, включена ли проверка WhatsApp
                from config import ENABLE_WHATSAPP_CHECK
                if ENABLE_WHATSAPP_CHECK:
                    tasks.append(("whatsapp", self.whatsapp_checker.check(phone_num)))
        
        # Выполняем все проверки параллельно (даже если есть только одно поле)
        if tasks:
            results = await asyncio.gather(*[task[1] for task in tasks], return_exceptions=True)
            
            for (check_type, _), check_result in zip(tasks, results):
                if isinstance(check_result, Exception):
                    check_result = {"error": str(check_result)}
                
                if check_type == "email":
                    result["email_data"] = check_result
                    if check_result.get("error"):
                        # Если есть ошибка, логируем её но не устанавливаем score
                        error_msg = check_result.get('error', 'Unknown error')
                        logger.warning(f"Email check error for {lead.get('email', 'unknown')}: {error_msg}")
                        result["reasons"].append(f"email.error={error_msg}")
                    else:
                        result["email_score"] = self.email_scorer.score(check_result)
                        # Добавляем причины
                        if check_result.get("deliverability"):
                            result["reasons"].append(f"email.deliverability={check_result['deliverability']}")
                        if check_result.get("address_risk_status"):
                            result["reasons"].append(f"email.address_risk={check_result['address_risk_status']}")
                        if check_result.get("domain_risk_status"):
                            result["reasons"].append(f"email.domain_risk={check_result['domain_risk_status']}")
                        if check_result.get("valid_format") is not None:
                            result["reasons"].append(f"email.valid_format={check_result['valid_format']}")
                        if check_result.get("disposable") is not None:
                            result["reasons"].append(f"email.disposable={check_result['disposable']}")
                        if check_result.get("free") is not None:
                            result["reasons"].append(f"email.free={check_result['free']}")
                        if check_result.get("quality_score") is not None:
                            result["reasons"].append(f"email.quality_score={check_result['quality_score']}")
                        total_breaches = check_result.get("total_breaches", 0) or 0
                        try:
                            total_breaches = int(total_breaches) if total_breaches is not None else 0
                        except (ValueError, TypeError):
                            total_breaches = 0
                        if total_breaches > 0:
                            result["reasons"].append(f"email.breaches={total_breaches}")
                        if check_result.get("is_username_suspicious"):
                            result["reasons"].append(f"email.suspicious_username={check_result['is_username_suspicious']}")
                        if check_result.get("is_risky_tld"):
                            result["reasons"].append(f"email.risky_tld={check_result['is_risky_tld']}")
                        
                        # Проверка социальных сетей по email
                        if check_social:
                            social_tasks = [
                                ("facebook", self.facebook_checker.check(lead["email"])),
                                ("google", self.google_checker.check(lead["email"])),
                                ("instagram", self.instagram_checker.check(lead["email"])),
                                ("snapchat", self.snapchat_checker.check(lead["email"])),
                                ("x", self.x_checker.check(lead["email"]))
                            ]
                            social_results = await asyncio.gather(*[task[1] for task in social_tasks], return_exceptions=True)
                            for (social_type, _), social_result in zip(social_tasks, social_results):
                                if isinstance(social_result, Exception):
                                    social_result = {"exists": False, "error": str(social_result)}
                                result["social_data"][social_type] = social_result
                                if not social_result.get("error"):
                                    result["reasons"].append(f"{social_type}.exists={social_result.get('exists', False)}")
                
                elif check_type == "ip":
                    result["ip_data"] = check_result
                    if not check_result.get("error"):
                        result["ip_score"] = self.ip_scorer.score(check_result)
                        # Добавляем причины
                        for key in ["is_tor", "is_proxy", "is_anonymous", "is_known_attacker", 
                                   "is_known_abuser", "is_threat", "is_bogon"]:
                            if check_result.get(key) is not None:
                                result["reasons"].append(f"ip.{key}={check_result[key]}")
                        if check_result.get("country_code"):
                            result["reasons"].append(f"ip.country_code={check_result['country_code']}")
                        if check_result.get("country_name"):
                            result["reasons"].append(f"ip.country_name={check_result['country_name']}")
                        if check_result.get("city"):
                            result["reasons"].append(f"ip.city={check_result['city']}")
                        if check_result.get("asn"):
                            result["reasons"].append(f"ip.asn={check_result['asn']}")
                        if check_result.get("asn_name"):
                            result["reasons"].append(f"ip.asn_name={check_result['asn_name']}")
                    else:
                        result["reasons"].append(f"ip.error={check_result.get('error', 'Unknown error')}")
                
                elif check_type == "phone":
                    result["phone_data"] = check_result
                    if not check_result.get("error"):
                        result["phone_score"] = self.phone_scorer.score(check_result)
                        # Добавляем причины
                        if check_result.get("valid") is not None:
                            result["reasons"].append(f"phone.valid={check_result['valid']}")
                        if check_result.get("line_type"):
                            result["reasons"].append(f"phone.line_type={check_result['line_type']}")
                        if check_result.get("carrier"):
                            result["reasons"].append(f"phone.carrier={check_result['carrier']}")
                    else:
                        # Логируем ошибку проверки телефона
                        error_msg = check_result.get('error', 'Unknown error')
                        logger.warning(f"Phone check error for {lead.get('phone', 'unknown')}: {error_msg}")
                        result["reasons"].append(f"phone.error={error_msg}")
                        # Устанавливаем phone_score = None при ошибке (будет показано как N/A)
                        result["phone_score"] = None
                
                elif check_type == "whatsapp":
                    result["whatsapp_data"] = check_result
                    if check_result.get("error"):
                        error_msg = check_result.get('error', 'Unknown error')
                        logger.warning(f"WhatsApp check error for {lead.get('phone', 'unknown')}: {error_msg}")
                        result["reasons"].append(f"whatsapp.error={error_msg}")
                    else:
                        result["reasons"].append(f"whatsapp.valid={check_result.get('valid', False)}")
        
        # Вычисляем итоговую оценку
        result["final_score"] = self.aggregator.aggregate(
            ip_score=result["ip_score"],
            email_score=result["email_score"],
            phone_score=result["phone_score"]
        )
        
        # Определяем вердикт
        result["verdict"] = self.verdict_mapper.get_verdict(result["final_score"])
        
        return result
    
    async def check_leads(self, leads: List[Dict[str, Optional[str]]], check_social: bool = True) -> List[Dict]:
        """
        Проверяет список лидов с параллельной обработкой батчами
        
        Args:
            leads: Список лидов для проверки
            check_social: Проверять ли социальные сети
            
        Returns:
            list: Список результатов проверки
        """
        # Размер батча для параллельной обработки (3 лида одновременно для 3 RPS)
        batch_size = 3
        results = []
        total_batches = (len(leads) + batch_size - 1) // batch_size
        
        logger.info(f"Начинаю обработку {len(leads)} лидов батчами по {batch_size} (всего {total_batches} батчей)")
        
        # Обрабатываем лиды батчами
        for batch_start in range(0, len(leads), batch_size):
            batch = leads[batch_start:batch_start + batch_size]
            batch_num = (batch_start // batch_size) + 1
            
            # Создаем задачи для параллельной обработки батча
            batch_tasks = []
            for i, lead in enumerate(batch):
                lead_index = batch_start + i + 1
                task = self._check_lead_with_number(lead, lead_index, check_social)
                batch_tasks.append(task)
            
            # Выполняем батч параллельно
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Обрабатываем результаты батча
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Ошибка при проверке лида: {result}")
                    # Создаем пустой результат при ошибке
                    results.append({
                        "lead": {},
                        "verdict": "unknown",
                        "final_score": 0,
                        "reasons": [f"error={str(result)}"]
                    })
                else:
                    results.append(result)
            
            # Логируем прогресс
            logger.info(f"Обработано батч {batch_num}/{total_batches} ({len(results)}/{len(leads)} лидов)")
            
            # Задержка между батчами для соблюдения 3 RPS
            # Если обрабатываем 3 лида параллельно, задержка должна быть ~1 секунда (3 лида / 3 RPS)
            if batch_start + batch_size < len(leads):
                await asyncio.sleep(1.0)
        
        return results
    
    async def _check_lead_with_number(self, lead: Dict[str, Optional[str]], lead_num: int, check_social: bool) -> Dict:
        """Вспомогательная функция для проверки лида с номером"""
        result = await self.check_lead(lead, check_social)
        result["lead_number"] = lead_num
        return result
