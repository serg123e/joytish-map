"""Конвейер разбора карты Джйотиш: сбор данных, производные расчёты, экспорт.

Методика — в `prompts/`. Здесь только то, что должно считаться кодом, а не
языковой моделью: сбор данных с vedic-horo, арифметика, проверки и вёрстка.

Функции сбора живут в `jyotish.collect`, а не здесь: реэкспорт функции с
именем `collect` затенил бы одноимённый модуль.
"""

from .client import Client, ConfigError
from .derive import arudha_padas, chara_karakas, derive_all, dispositors

__all__ = [
    "Client", "ConfigError",
    "derive_all", "arudha_padas", "chara_karakas", "dispositors",
]
