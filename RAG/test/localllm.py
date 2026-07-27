from openai import OpenAI


MODEL_NAME = "Qwen/Qwen3-8B"

client = OpenAI(
    base_url="http://127.0.0.1:8000/v1",
    api_key="dummy",
)

response = client.chat.completions.create(
    model=MODEL_NAME,
    messages=[
        {
            "role": "user",
            "content": "日本の首都を一単語で答えてください。",
        }
    ],
    max_tokens=100,
)

answer = response.choices[0].message.content
print(answer)