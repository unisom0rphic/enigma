import re
from typing import Dict, List

from natasha import (
    PER,
    Doc,
    MorphVocab,
    NewsEmbedding,
    NewsMorphTagger,
    NewsNERTagger,
    NewsSyntaxParser,
    Segmenter,
)
from pymorphy2 import MorphAnalyzer

# Инициализация тяжелых объектов (Singleton style)
segmenter = Segmenter()
morph_vocab = MorphVocab()
emb = NewsEmbedding()
morph_tagger = NewsMorphTagger(emb)
syntax_parser = NewsSyntaxParser(emb)
ner_tagger = NewsNERTagger(emb)

# Pymorphy для определения пола
pymorphy_analyzer = MorphAnalyzer()


def extract_entities(text: str) -> List[Dict]:
    """
    Извлекает ФИО (Natasha) и Технические данные (Regex).
    """
    entities = []

    # --- 1. Natasha NER (ФИО) ---
    doc = Doc(text)
    doc.segment(segmenter)
    doc.tag_morph(morph_tagger)
    doc.parse_syntax(syntax_parser)
    doc.tag_ner(ner_tagger)

    for span in doc.spans:
        if span.type == PER:
            # Нормализация ФИО
            span.normalize(morph_vocab)
            normal_form = span.normal

            # Определение пола через Pymorphy
            gender = "masc"  # Дефолт мужской
            if normal_form:
                first_word = normal_form.split()[0]
                parsed = pymorphy_analyzer.parse(first_word)[0]
                if "femn" in parsed.tag:
                    gender = "femn"

            entities.append(
                {
                    "type": "NAME",
                    "text": span.text,
                    "normal": normal_form,
                    "gender": gender,
                }
            )

    # --- 2. Regex (Заводской номер ГН-xxxxx) ---
    # Паттерн: ГН- и 5 цифр
    device_pattern = re.compile(r"ГН-\d{5}")
    for match in device_pattern.finditer(text):
        entities.append(
            {"type": "DEVICE", "text": match.group(), "normal": match.group()}
        )

    # --- 3. Другие regex (Телефон, Email) ---
    # Простые примеры:
    phone_pattern = re.compile(r"\+7\d{10}")
    for match in phone_pattern.finditer(text):
        entities.append(
            {"type": "PHONE", "text": match.group(), "normal": match.group()}
        )

    return entities
