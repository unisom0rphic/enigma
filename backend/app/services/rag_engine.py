import json
import os
from typing import List

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


class RAGEngine:
    def __init__(
        self,
        index_path: str = "data/faiss_index",
        model_name: str = "intfloat/multilingual-e5-base",
    ):
        self.model = None
        self.index = None
        self.doc_store = {}
        self.index_path = index_path
        self.model_name = model_name

    def load(self):
        print(f"Loading embedding model {self.model_name}...")
        self.model = SentenceTransformer(self.model_name)

        index_file = os.path.join(self.index_path, "index.faiss")
        store_file = os.path.join(self.index_path, "store.json")

        if os.path.exists(index_file) and os.path.exists(store_file):
            print("Loading FAISS index...")
            self.index = faiss.read_index(index_file)
            with open(store_file, "r", encoding="utf-8") as f:
                raw_store = json.load(f)
                self.doc_store = {int(k): v for k, v in raw_store.items()}
        else:
            # В реальном проекте здесь должен быть вызов скрипта индексации
            print("Warning: Index not found. RAG will return empty context.")
            self.index = None

    def get_context(self, query: str, top_k: int = 3) -> List[str]:
        if not self.model or not self.index:
            return []

        # E5 требует префикс "query: " для поиска
        query_emb = self.model.encode([f"query: {query}"], normalize_embeddings=True)

        distances, indices = self.index.search(np.array(query_emb), top_k)

        results = []
        for idx in indices[0]:
            if (
                idx != -1 and idx in self.doc_store
            ):  # FAISS может вернуть -1 если мало данных
                results.append(self.doc_store[idx])

        return results


# Синглтон для использования в приложении
rag_engine = RAGEngine()
