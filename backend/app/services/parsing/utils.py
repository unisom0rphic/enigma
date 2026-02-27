import re
from typing import Dict, List, Tuple

import pymorphy2

morph = pymorphy2.MorphAnalyzer()

# Маппинг тегов падежей от LLM -> теги Pymorphy
CASE_MAP = {
    "NOM": "nomn",  # Именительный
    "GEN": "gent",  # Родительный
    "DAT": "datv",  # Дательный
    "ACC": "accs",  # Винительный
    "INS": "ablt",  # Творительный
    "ABL": "loct",  # Предложный
}


def inflect_name(name_normal: str, case_tag: str, gender: str) -> str:
    """Склоняет ФИО."""
    py_case = CASE_MAP.get(case_tag.upper())
    if not py_case:
        return name_normal

    parts = name_normal.split()
    inflected_parts = []

    for part in parts:
        parsed = morph.parse(part)[0]
        inflected = parsed.inflect({py_case})
        if inflected:
            inflected_parts.append(inflected.word.capitalize())
        else:
            inflected_parts.append(part)

    return " ".join(inflected_parts)


def mask_pii(text: str, entities: List[Dict]) -> Tuple[str, Dict[str, Dict]]:
    """
    Замена сущностей на плейсхолдеры.
    Возвращает замаскированный текст и map.
    Ключом map теперь является строка плейсхолдера (например, "NAME_1").
    """
    entity_map = {}
    masked_text = text

    counters = {"NAME": 0, "DEVICE": 0, "PHONE": 0, "EMAIL": 0}

    # Сортируем по длине, чтобы длинные строки заменялись первыми
    sorted_entities = sorted(entities, key=lambda x: len(x["text"]), reverse=True)

    for ent in sorted_entities:
        ent_type = ent["type"]
        if ent_type in counters:
            counters[ent_type] += 1
            idx = counters[ent_type]

            placeholder_name = f"{ent_type}_{idx}"
            placeholder = f"<{placeholder_name}>"

            # ИСПРАВЛЕНИЕ: Ключ - это уникальная строка "NAME_1", "DEVICE_1"
            entity_map[placeholder_name] = {
                "type": ent_type,
                "text": ent["text"],
                "normal": ent.get("normal", ent["text"]),
                "gender": ent.get("gender", "masc"),
            }

            masked_text = masked_text.replace(ent["text"], placeholder)

    return masked_text, entity_map


def unmask_pii(text: str, entity_map: Dict[str, Dict]) -> str:
    """
    Восстановление сущностей с учетом падежей.
    """
    # Паттерн: <TYPE_ID_CASE>
    pattern = re.compile(r"<(NAME|DEVICE|PHONE|EMAIL)_(\d+)(?:_([A-Z]+))?>")

    def replacer(match):
        ent_type = match.group(1)
        idx = match.group(2)
        case = match.group(3)

        # Собираем ключ поиска: "NAME_1"
        lookup_key = f"{ent_type}_{idx}"

        if lookup_key in entity_map:
            entity = entity_map[lookup_key]

            # Если это не Имя или падеж не указан - возвращаем нормальную форму
            if ent_type != "NAME" or not case:
                return entity["normal"]

            # Если Имя и есть падеж -> склоняем
            return inflect_name(entity["normal"], case, entity["gender"])

        return match.group(0)

    return pattern.sub(replacer, text)
