from sentence_transformers import SentenceTransformer

model = SentenceTransformer("intfloat/multilingual-e5-small")
documents = [
    "卒業するためには、所定の修業年限以上在籍し、必要な単位を修得しなければならない。",
    "自転車で通学する学生は、所定の手続きを行い、許可を受けなければならない。",
    "学生が病気などにより長期間修学できない場合は、休学を願い出ることができる。",
]
query = "学校に長い間通えなくなった場合どうすればいい？"

query_text = "query: " + query

document_texts = [
    "passage: " + document
    for document in documents
]

query_embedding = model.encode(
    query_text,
    normalize_embeddings=True,
)

document_embeddings = model.encode(
    document_texts,
    normalize_embeddings=True,
)

scores = document_embeddings @ query_embedding

for document, score in zip(documents, scores):
    print(f"Score: {score:.4f}, Document: {document}")