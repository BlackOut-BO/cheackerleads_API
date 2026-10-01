"""Утилиты для управления авторизацией пользователей"""
import json
import os
from typing import Set, Optional
from pathlib import Path


class AuthManager:
    """Менеджер авторизации пользователей"""
    
    def __init__(self, auth_file: str = "authorized_users.json"):
        """
        Инициализирует менеджер авторизации
        
        Args:
            auth_file: Путь к файлу с авторизованными пользователями
        """
        self.auth_file = Path(auth_file)
        self._authorized_users: Set[int] = set()
        self._load_authorized_users()
        self._admin_ids: Set[int] = self._load_admin_ids()

    def _load_admin_ids(self) -> Set[int]:
        """
        Загружает список администраторов из переменной окружения `ADMIN_IDS`.
        Формат: "id1,id2,id3" (разделитель - запятая).
        """
        admin_ids_raw = os.getenv("ADMIN_IDS", "") or ""
        if not admin_ids_raw.strip():
            return set()

        ids: Set[int] = set()
        for part in admin_ids_raw.split(","):
            part = part.strip()
            if not part:
                continue
            try:
                ids.add(int(part))
            except ValueError:
                continue
        return ids
    
    def _load_authorized_users(self):
        """Загружает список авторизованных пользователей из файла"""
        if self.auth_file.exists():
            try:
                with open(self.auth_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._authorized_users = set(data.get('users', []))
            except (json.JSONDecodeError, IOError) as e:
                # Если файл поврежден, создаем новый
                self._authorized_users = set()
                self._save_authorized_users()
        else:
            self._authorized_users = set()
            self._save_authorized_users()
    
    def _save_authorized_users(self):
        """Сохраняет список авторизованных пользователей в файл"""
        try:
            data = {'users': list(self._authorized_users)}
            with open(self.auth_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Ошибка при сохранении авторизованных пользователей: {e}")
    
    def is_authorized(self, user_id: int) -> bool:
        """
        Проверяет, авторизован ли пользователь
        
        Args:
            user_id: ID пользователя Telegram
            
        Returns:
            bool: True если пользователь авторизован
        """
        # Разрешаем только админам. Пароль и файл `authorized_users.json` больше
        # не должны давать доступ.
        return user_id in self._admin_ids
    
    def authorize_user(self, user_id: int) -> bool:
        """
        Авторизует пользователя
        
        Args:
            user_id: ID пользователя Telegram
            
        Returns:
            bool: True если пользователь успешно авторизован
        """
        if user_id not in self._authorized_users:
            self._authorized_users.add(user_id)
            self._save_authorized_users()
        return True
    
    def deauthorize_user(self, user_id: int) -> bool:
        """
        Деавторизует пользователя
        
        Args:
            user_id: ID пользователя Telegram
            
        Returns:
            bool: True если пользователь успешно деавторизован
        """
        if user_id in self._authorized_users:
            self._authorized_users.remove(user_id)
            self._save_authorized_users()
        return True
    
    def check_password(self, password: str, correct_password: str) -> bool:
        """
        Проверяет правильность пароля
        
        Args:
            password: Введенный пароль
            correct_password: Правильный пароль
            
        Returns:
            bool: True если пароль правильный
        """
        return password.strip() == correct_password.strip()
