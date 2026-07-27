import json
from sentence_transformers import SentenceTransformer
import numpy as np
from openai import OpenAI

model = SentenceTransformer("intfloat/multilingual-e5-small")
chunk_embeddings = np.load("RAG/data/student_handbook_embeddings.npy")
with open("RAG/data/student_handbook_chunks.json", mode="rt", encoding="utf-8") as f:
    student_handbook_chunks = json.load(f)

LLM_MODEL_NAME = "Qwen/Qwen3-8B"

llm_client = OpenAI(
    base_url="http://127.0.0.1:8000/v1",
    api_key="dummy",
)

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

def make_prompt(contexts: list, query: str):
    prompt = f"""あなたは学生便覧を案内するアシスタントです。
    以下の資料だけを根拠に質問へ回答してください。
    資料に答えがない場合は、「学生便覧の資料からは確認できません」と回答してください。
    回答には根拠となった学生便覧のページ番号を示してください。
    
    """

    for context in contexts:
        prompt += f"\n\n資料-----\n {context['text']}\n学生便覧ページ番号: {context['page_number']}\n"

    prompt += f"\n\n質問: {query}\n"
    
    return prompt

def call_llm(prompt: str) -> str:
    response = llm_client.chat.completions.create(
        model=LLM_MODEL_NAME,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        max_tokens=500,
        temperature=0.7,
        top_p=0.8,
        extra_body={
            "top_k": 20,
            "chat_template_kwargs": {
                "enable_thinking": False,
            },
        },
    )

    answer = response.choices[0].message.content

    if answer is None:
        raise RuntimeError("LLMから回答本文が返されませんでした")

    return answer.strip()

def gen_response(query: str):
    search_results = search(query, student_handbook_chunks, chunk_embeddings, model)
    prompt = make_prompt(search_results, query)
    return call_llm(prompt)


if __name__ == "__main__":
    print(gen_response("卒業の条件を教えて"))
