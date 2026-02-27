from typing import Dict

from dostoevsky.models import FastTextSocialNetworkModel
from dostoevsky.tokenization import RegexTokenizer

# Инициализация
tokenizer = RegexTokenizer()
model = FastTextSocialNetworkModel(tokenizer=tokenizer)


def analyze_sentiment(text: str) -> Dict:
    """
    Возвращает тональность текста.
    """
    results = model.predict([text], k=2)
    # results: [{'negative': 0.8, 'positive': 0.1, ...}]
    if results:
        top_sentiment = max(results[0], key=results[0].get)
        return {"label": top_sentiment, "score": results[0][top_sentiment]}
    return {"label": "neutral", "score": 0.0}
