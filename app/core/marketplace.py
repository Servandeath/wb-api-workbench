"""
Общий словарь маркетплейсов и типов ключей.

Используется как метаданные для ApiKey (app/db/models.py): какой это
маркетплейс и как ключ устроен — чтобы GUI/репозиторий знали, каким
декодером/чекером его обрабатывать (wb_token/wb_ping vs ozon_ping).

Значения — обычные строки (StrEnum), без DB-уровневого CHECK constraint
на колонке: добавление нового маркетплейса (Lamoda, Деловые линии,
МойСклад, МоЕх...) не должно требовать миграции схемы.
"""

from enum import StrEnum


class Marketplace(StrEnum):
    WB = "WB"
    OZON = "OZON"


class KeyKind(StrEnum):
    # WB: единый JWT-токен, права зашиты в bitmask (wb_token.py).
    JWT = "jwt"
    # Ozon Seller API: Client-Id + Api-Key (ozon_ping.check_seller_key).
    SELLER = "seller"
    # Ozon Performance API: Client ID + Client Secret, OAuth2
    # (ozon_ping.check_performance_key).
    PERFORMANCE = "performance"
