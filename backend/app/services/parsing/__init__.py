# app/services/parsing/__init__.py
def extract_entities(text: str) -> dict:
    # Здесь будет вызов Natasha и regex
    return {
        'full_name': 'Иванов Иван',
        'object': 'ООО Газпром',
        'phone_num': '+79991234567',
        'device_num': 'SN123456',
        'device_type': 'СИГНАЛ-4',
    }

def analyze_sentiment(text: str) -> str:
    return "negative"  # Dostoevsky

def summarize(text: str) -> str:
    return text[:200]  # Sumy