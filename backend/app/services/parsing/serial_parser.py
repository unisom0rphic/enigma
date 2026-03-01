import re
from typing import Dict, Optional

# Маппинг: первые 3 цифры -> Тип прибора
DEVICE_PREFIX_MAP = {
    "230": "ДГС ЭРИС-230",
    "414": "ПГ ЭРИС-414",
    "411": "ПГ ЭРИС-411",
    "020": "СГГ-20",
    "400": "Док ЭРИС-400",
}


def extract_device_from_serial(text: str) -> Optional[Dict]:
    """
    Ищет 9-значные числа и пытается сопоставить префикс с типом прибора.
    """
    pattern = re.compile(r"\b(\d{9})\b")
    matches = pattern.findall(text)

    for serial_number in matches:
        prefix = serial_number[:3]

        if prefix in DEVICE_PREFIX_MAP:
            device_type = DEVICE_PREFIX_MAP[prefix]
            return {
                "type": "DEVICE",
                "text": serial_number,  # То, что физически в тексте (номер)
                "normal": device_type,  # То, что это значит (имя прибора)
            }

    return None
