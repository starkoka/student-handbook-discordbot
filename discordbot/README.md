# 学生便覧 RAG Discord Bot

学生便覧についての質問を `/handbook` コマンドで受け付け、外部のRAG
APIへ問い合わせる薄いDiscord Botです。LLM推論、文書検索、PDF処理などの
RAG機能はこのBotには含まれず、別サービスとして起動しておく必要があります。

## 必要環境

- Python 3.12
- Discord Botトークン
- 起動済みのRAG API（`POST /query`）

## セットアップ

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

`.env`を開き、次の値を設定します。

```dotenv
DISCORD_BOT_TOKEN=取得したBotトークン
RAG_API_URL=http://127.0.0.1:8000/query
DISCORD_GUILD_ID=開発用サーバーのID
```

`DISCORD_GUILD_ID`を指定すると、そのサーバーだけへコマンドを同期するため、
開発中の反映が速くなります。空にするとグローバルコマンドとして同期します。

## Discord Developer Portal側の設定

1. [Discord Developer Portal](https://discord.com/developers/applications)で
   Applicationを作成します。
2. `Bot`画面でBotを作成し、トークンを取得して`.env`へ設定します。
3. OAuth2 URL Generatorで`bot`と`applications.commands`を選択し、
   Botを利用するサーバーへ追加します。
4. このBotはスラッシュコマンドだけを使うため、特権Intentは不要です。

## 起動

RAG APIを先に起動し、仮想環境内で実行します。

```bash
python bot.py
```

Discordで次のように実行します。

```text
/handbook question:卒業に必要な単位数は？
```

## モックRAG APIでの動作確認

RAGサービスがまだない場合は、別の作業ディレクトリでFastAPIとUvicornを
インストールします（Bot本体の依存関係ではありません）。

```bash
python3 -m venv .mock-venv
source .mock-venv/bin/activate
pip install fastapi uvicorn
```

次の内容を`mock_api.py`として保存します。

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class Query(BaseModel):
    question: str


@app.post("/query")
async def query(_: Query) -> dict[str, object]:
    return {
        "answer": "これはRAG APIのモック回答です。",
        "sources": [
            {
                "document": "テスト用学生便覧",
                "page": 1,
            }
        ],
    }
```

モックを起動します。

```bash
uvicorn mock_api:app --host 127.0.0.1 --port 8000
```

Bot側の`.env`で
`RAG_API_URL=http://127.0.0.1:8000/query`を指定してBotを起動し、
`/handbook`を実行してください。

## テスト

実際のDiscordやRAGサーバーへの接続は行わず、HTTP通信には
`httpx.MockTransport`を使用します。

```bash
pytest
```

## API契約

Botは設定されたURLへ質問だけを送信します。

```json
{"question": "卒業に必要な単位数は？"}
```

RAG APIはHTTP 200で次の形式を返す必要があります。

```json
{
  "answer": "卒業には167単位以上の修得が必要です。",
  "sources": [
    {
      "document": "2026年度学生便覧",
      "page": 42
    }
  ]
}
```

回答は1メッセージ1900文字以内に分割され、RAG APIから返されたメンションは
無効化して送信されます。
