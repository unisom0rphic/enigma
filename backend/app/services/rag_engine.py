import asyncio
import json
import os
from typing import List

import faiss
import numpy as np
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

from app.config import get_settings

settings = get_settings()


class RAGEngine:
    def __init__(
        self,
        index_root: str = "data/faiss_index",
        model_name: str = "intfloat/multilingual-e5-base",
    ):
        self.model = None
        self.index_root = index_root
        self.model_name = model_name
        self._model_lock = asyncio.Lock()  # Для безопасной загрузки модели

    async def load_model(self):
        """Ленивая загрузка модели в отдельном потоке."""
        async with self._model_lock:
            if self.model is None:
                print(f"Loading embedding model {self.model_name}...")
                # Загрузка модели - это IO/CPU тяжелая операция, делаем в треде
                self.model = await asyncio.to_thread(
                    SentenceTransformer, self.model_name
                )
                print("Model loaded.")

    async def get_context(
        self, query: str, device_name: str, pdf_path: str, top_k: int = 3
    ) -> List[str]:
        """
        Возвращает контекст для запроса.
        Если индекс для device_name существует - загружает.
        Если нет - строит из pdf_path.
        """
        await self.load_model()

        index_dir = os.path.join(self.index_root, device_name)
        index_file = os.path.join(index_dir, "index.faiss")
        store_file = os.path.join(index_dir, "store.json")

        # Структуры данных для текущего индекса
        index = None
        doc_store = {}

        # 1. Попытка загрузить готовый индекс с диска
        if os.path.exists(index_file) and os.path.exists(store_file):
            print(f"Loading cached index for {device_name}...")
            index = await asyncio.to_thread(faiss.read_index, index_file)
            with open(store_file, "r", encoding="utf-8") as f:
                raw_store = json.load(f)
                doc_store = {int(k): v for k, v in raw_store.items()}
        else:
            # 2. Если индекса нет, строим из PDF
            if not pdf_path or not os.path.exists(pdf_path):
                return []

            print(f"Building new index for {device_name} from PDF...")
            index, doc_store = await self._build_index_from_pdf(pdf_path, index_dir)

        if index is None or index.ntotal == 0:
            return []

        # 3. Поиск (Embedding Query + Search)
        # E5 требует префикс "query: " для поиска
        query_emb = await asyncio.to_thread(
            self.model.encode, [f"query: {query}"], normalize_embeddings=True
        )

        distances, indices = await asyncio.to_thread(
            index.search, np.array(query_emb), top_k
        )

        results = []
        for idx in indices[0]:
            if idx != -1 and idx in doc_store:
                results.append(doc_store[idx])

        return results

    async def _build_index_from_pdf(self, pdf_path: str, save_dir: str):
        """Парсит PDF, создает индекс и сохраняет на диск."""

        # Парсинг PDF (синхронная операция)
        def parse_and_chunk():
            reader = PdfReader(pdf_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"

            # Простой чанкер по символам/переносам строк (можно улучшить через LangChain)
            # Бьем по параграфам
            chunks = [p.strip() for p in text.split("\n") if len(p.strip()) > 50]
            return chunks

        chunks = await asyncio.to_thread(parse_and_chunk)
        if not chunks:
            return None, {}

        # Эмбеддинг (тяжелая операция)
        # E5 требует префикс "passage: " для документов
        passages = [f"passage: {c}" for c in chunks]
        embeddings = await asyncio.to_thread(
            self.model.encode, passages, normalize_embeddings=True
        )

        # Создание индекса FAISS
        d = embeddings.shape[1]  # Размерность вектора
        index = faiss.IndexFlatIP(
            d
        )  # Inner Product (косинусная близость для нормализованных)
        await asyncio.to_thread(index.add, np.array(embeddings))

        # Сохранение
        os.makedirs(save_dir, exist_ok=True)
        faiss.write_index(index, os.path.join(save_dir, "index.faiss"))

        doc_store = {i: chunks[i] for i in range(len(chunks))}
        with open(os.path.join(save_dir, "store.json"), "w", encoding="utf-8") as f:
            json.dump(doc_store, f, ensure_ascii=False, indent=2)

        return index, doc_store


# Синглтон
rag_engine = RAGEngine()
