
from qdrant_client import QdrantClient
import numpy as np
from gensim.models import FastText
from preprocess import preprocess_text
from rank_bm25 import BM25Okapi

client = QdrantClient(url='http://localhost:6333')
collection_name = "books"


model = FastText.load("FastText_model.model")

def vectorize_query(query: str, model) -> np.ndarray:
    # Разбиваем на токены (можно использовать свой токенизатор)
    tokens = preprocess_text(query)
    # FastText выдаст вектор даже для OOV-слов
    vectors = [model.wv[w] for w in tokens]
    return np.mean(vectors, axis=0) if vectors else np.zeros(model.vector_size)

query = "Разработка мобильных приложений для ios"
hits = client.search(
    collection_name=collection_name,
    query_vector=vectorize_query(query,model),
    limit=50
)



# 2. Собираем тексты для BM25 (например, из поля "name")
candidate_texts = [
    (hit.payload["name"] + " " + hit.payload.get("annotation", ""))
    for hit in hits
]
tokenized_texts = [preprocess_text(text) for text in candidate_texts]

# 3. Строим BM25 по этим кандидатам
bm25 = BM25Okapi(tokenized_texts)
tokenized_query = preprocess_text(query)
bm25_scores = bm25.get_scores(tokenized_query)

# 4. Комбинируем BM25-score и исходный score (можно по-разному: просто BM25, или сумма, или взвешенная сумма)
results = []
for hit, bm25_score in zip(hits, bm25_scores):
    # Пример: комбинируем исходный score и bm25_score (настройте веса под себя)
    combined_score = hit.score + bm25_score * 0.3
    results.append((hit, combined_score))

# 5. Сортируем по новому скору
results.sort(key=lambda x: x[1], reverse=True)

# 6. Выводим топ-5 по комбинированному скору
for hit, score in results[:10]:
    print(hit.payload["name"], score)