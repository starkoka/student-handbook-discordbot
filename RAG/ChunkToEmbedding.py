import json
from sentence_transformers import SentenceTransformer
import numpy as np

chunk_json_path = "RAG/data/student_handbook_chunks.json"
embedding_output_path = "RAG/data/student_handbook_embeddings.npy"
model = SentenceTransformer("intfloat/multilingual-e5-small")

with open(chunk_json_path, mode="rt", encoding="utf-8") as f:
    student_handbook_chunks = json.load(f)


passages = ["passage: " + chunk["text"] for chunk in student_handbook_chunks]
passage_embeddings = model.encode(
    passages,
    normalize_embeddings=True,
)

np.save(embedding_output_path, passage_embeddings)