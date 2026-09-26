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
    nebesna: int
    svaroja: int
    fragment: int
    armor_scroll: int
    weapon_scroll: int


def clean_number(value_str: str) -> int:
    """Очищает строку от пробелов и точек перед конвертацией в число."""
    if not value_str:
        return 0
    clean_str = re.sub(r'[^\d]', '', value_str)
    return int(clean_str) if clean_str else 0


def parse_report(text: str) -> Optional[GameReport]:
    try:
        text_lower = text.lower()

        # 1. Жесткая привязка базовых метрик (Опыт только ✨, Золото только 💰/🪙)
        gold_match = re.search(r'(?:💰|🪙)[ \t]*\+?[ \t]*(\d[\d\s.,]*)|(\d[\d\s.,]*)[ \t]*\+?[ \t]*(?:💰|🪙)', text)
        exp_match = re.search(r'✨[ \t]*\+?[ \t]*(\d[\d\s.,]*)|(\d[\d\s.,]*)[ \t]*\+?[ \t]*✨', text)

        gold_str = gold_match.group(1) or gold_match.group(2) if gold_match else ""
        exp_str = exp_match.group(1) or exp_match.group(2) if exp_match else ""

        gold = clean_number(gold_str)
        exp = clean_number(exp_str)

        # 2. Безопасный поиск материалов (с поддержкой получения без явной цифры)
        def extract_item(pattern: str) -> int:
            match = re.search(rf'{pattern}(?:[ \t]*\+?[ \t]*(\d+))?', text, re.IGNORECASE)
            if not match:
                return 0
            return int(match.group(1)) if match.group(1) else 1

        nebesna = extract_item(r'Небесна криця')
        svaroja = extract_item(r'Сварожа криця')
        fragment = extract_item(r'Фрагмент заповіту')
        armor_scroll = extract_item(r'Сувій обладунку')
        weapon_scroll = extract_item(r'Сувій зброї')

        # Если вообще ничего не найдено — это мусор
        if sum([gold, exp, nebesna, svaroja, fragment, armor_scroll, weapon_scroll]) == 0:
            return None

        # 3. Строгая маршрутизация
        if "справи громади" in text_lower:
            activity = "Справи громади"
        elif "сонячне стояння" in text_lower:
            activity = "Стояння"
        elif any(trigger in text_lower for trigger in ["твоя ватага зняла"]):
            activity = "Бос"
        elif any(trigger in text_lower for trigger in
                 ["стежки повертають тебе додому", "винесено з печери", "ти виходиш"]):
            activity = "Похід"
        elif any(trigger in text_lower for trigger in ["лови:", "катакомби", "завдано сторожу", "загін поліг"]):
            activity = "Лови"
        else:
            return None

        return GameReport(
            activity=activity,
            gold=gold,
            exp=exp,
            nebesna=nebesna,
            svaroja=svaroja,
            fragment=fragment,
            armor_scroll=armor_scroll,
            weapon_scroll=weapon_scroll
        )

    except Exception as e:
        logger.error(f"Критический сбой парсера: {e}\nТекст: {text[:50]}...", exc_info=True)
        return None