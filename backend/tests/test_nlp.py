# backend/tests/test_nlp.py
from app.services.parsing.ner_extractor import extract_entities


def test_extract_name():
    # Natasha лучше работает с полными ФИО
    text = "Меня зовут Иван Иванов, телефон +79001234567."
    entities = extract_entities(text)

    names = [e for e in entities if e["type"] == "NAME"]
    assert len(names) > 0
    assert "Иван" in names[0]["normal"]


def test_extract_phone():
    text = "Мой номер 8 900 123 45 67"
    entities = extract_entities(text)

    phones = [e for e in entities if e["type"] == "PHONE"]
    assert len(phones) > 0
    # Теперь проверяем очищенный номер
    assert phones[0]["normal"] == "89001234567"
