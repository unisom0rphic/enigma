import re
from typing import Dict, List

import pymorphy3
from natasha import Doc, MorphVocab, NewsEmbedding, NewsNERTagger, Segmenter

from .serial_parser import extract_device_from_serial

# Инициализация (один раз при старте)
segmenter = Segmenter()
emb = NewsEmbedding()
ner_tagger = NewsNERTagger(emb)
morph_vocab = MorphVocab()
morph_analyzer = pymorphy3.MorphAnalyzer()


def extract_entities(text: str) -> List[Dict]:
    entities = []

    # --- 1. Natasha NER (ФИО) ---
    doc = Doc(text)
    doc.segment(segmenter)
    doc.tag_ner(ner_tagger)

    found_names = set()

    for span in doc.spans:
        if span.type == "PER":
            span.normalize(morph_vocab)
            name = span.normal or span.text

            if name not in found_names:
                # Определяем пол
                parsed = morph_analyzer.parse(name.split()[0])[0]
                gender = "femn" if "femn" in parsed.tag else "masc"

                entities.append(
                    {
                        "type": "NAME",
                        "text": span.text,
                        "normal": name,
                        "gender": gender,
                    }
                )
                found_names.add(name)

    # --- 2. Regex для Приборов (DEVICE) ---
    # Ищем явные названия
    device_pattern = re.compile(r"\b([А-ЯA-Z]{2,4}(?:\s*ЭРИС)?-\d{2,4}(?:-\d)?)\b")

    for match in device_pattern.finditer(text):
        entities.append(
            {"type": "DEVICE", "text": match.group(1), "normal": match.group(1)}
        )

    # --- 3. Телефоны и Email ---
    email_pattern = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+")
    for match in email_pattern.finditer(text):
        entities.append(
            {"type": "EMAIL", "text": match.group(0), "normal": match.group(0)}
        )

    phone_pattern = re.compile(
        r"(?:\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}"
    )
    for match in phone_pattern.finditer(text):
        raw_phone = match.group(0)
        # ИСПРАВЛЕНИЕ: Очищаем номер от всего, кроме цифр
        clean_phone = re.sub(r"[^\d]", "", raw_phone)

        entities.append({"type": "PHONE", "text": raw_phone, "normal": clean_phone})

    # --- 4. Fallback: Serial -> Device ---
    has_device = any(e["type"] == "DEVICE" for e in entities)

    if not has_device:
        serial_entity = extract_device_from_serial(text)
        if serial_entity:
            entities.append(serial_entity)

    return entities
