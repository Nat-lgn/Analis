import re
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class GameReport:
    activity: str
    gold: int
    exp: int


def parse_report(text: str) -> Optional[GameReport]:
    """
    Анализирует текст сообщения, извлекает статистику (опыт и золото),
    определяет тип активности и жестко отбрасывает мусор.
    """
    try:
        # 1. Би-направленные регулярные выражения
        gold_match = re.search(r'(?:(?:💰|🪙)\s*\+?\s*(\d+))|(?:\+?\s*(\d+)\s*(?:💰|🪙))', text)
        exp_match = re.search(r'(?:(?:⭐|⭐️|✨)\s*\+?\s*(\d+))|(?:\+?\s*(\d+)\s*(?:⭐|⭐️|✨))', text)

        # 2. Мягкая валидация: отбрасываем только если нет ни золота, ни опыта
        if not exp_match and not gold_match:
            return None

        # 3. Безопасное извлечение цифр
        gold = 0
        if gold_match:
            gold = int(gold_match.group(1) or gold_match.group(2))

        exp = 0
        if exp_match:
            exp = int(exp_match.group(1) or exp_match.group(2))

        # 4. Маршрутизация категорий
        text_lower = text.lower()

        if "справи громади" in text_lower:
            activity = "Ежедневные задания"
        elif "сонячне стояння" in text_lower:
            activity = "Стояние"
        elif "підсумок битви" in text_lower and  "хвиля" in text_lower:
            activity = "Босс"
        elif "катакомби" in text_lower or "завдано сторожу" in text_lower:
            activity = "Катакомбы"
        elif "стежки повертають тебе додому" in text_lower or "винесено з печери" in text_lower or "ти виходиш" in text_lower:
            activity = "Походы"
        elif "лови:" in text_lower:
            activity = "Ловы"
        else:
            activity = "Обычный фарм / Неизвестно"

        return GameReport(activity=activity, gold=gold, exp=exp)

    except Exception as e:
        logger.error(f"Ошибка при парсинге сообщения: {e}\nТекст: {text}", exc_info=True)
        return None