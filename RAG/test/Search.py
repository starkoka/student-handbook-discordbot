import json
from sentence_transformers import SentenceTransformer
import numpy as np

def search(query: str, chunks: list[dict], chunk_embeddings, model, top_k: int = 5):
    query_embedding = model.encode(
        "query: " + query,
        normalize_embeddings=True,
    )

    scores = chunk_embeddings @ query_embedding
    topk_idx = np.argsort(scores)[-top_k:][::-1]

    result = [chunks[i] for i in topk_idx]
    for i in range(top_k):
        result[i]["score"] = float(scores[topk_idx[i]])
    return result

#print("質問を入力")
#query = input()
model = SentenceTransformer("intfloat/multilingual-e5-small")
chunk_embeddings = np.load("RAG/data/student_handbook_embeddings.npy")
with open("RAG/data/student_handbook_chunks.json", mode="rt", encoding="utf-8") as f:
    student_handbook_chunks = json.load(f)

queries = [
    "卒業の条件を教えて",
    "卒業するには何が必要ですか",
    "卒業に必要な単位数はいくつですか",
    "何単位取れば卒業できますか",
    "卒業認定の基準を知りたい",
    "必修科目を全部取れば卒業できますか",
]

for query in queries:
    search_results = search(query, student_handbook_chunks, chunk_embeddings, model)
    print(f"Query: {query}")
    print(search_results)