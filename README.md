# 学生便覧 RAG Discord Bot

ローカルのvLLMと既存の`RAG/GenResponce.py`を使い、Discordの
`/handbook`コマンドから学生便覧を検索するBotです。

Discord Botは`gen_response()`を直接呼び出します。`run.py`を使うと、
vLLM（既定: `127.0.0.1:8000`）の準備完了後にDiscord Botを起動し、
両方をまとめて停止できます。

## セットアップ

Python 3.12、vLLMが利用できるGPU環境、およびDiscord Botトークンが必要です。

```bash
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt
cp discordbot/.env.example discordbot/.env
```

`discordbot/.env`を編集します。

```dotenv
DISCORD_BOT_TOKEN=取得したBotトークン
DISCORD_GUILD_ID=開発用DiscordサーバーのID
```

`DISCORD_GUILD_ID`は任意です。指定すると、そのサーバーだけにスラッシュ
コマンドを同期するため開発中の反映が速くなります。未指定時はグローバル同期です。

Discord Developer PortalのOAuth2 URL Generatorでは`bot`と
`applications.commands`を選択してBotをサーバーへ追加してください。
特権Intentは不要です。

## 統合起動

リポジトリのルートで実行します。

```bash
source env/bin/activate
python run.py
```

vLLMの`GET /v1/models`が応答可能になるまで待ってからBotが起動します。
停止は`Ctrl+C`です。どちらかが異常終了した場合も、残ったプロセスを終了します。

Discordでは次のように質問できます。

```text
/handbook question:卒業に必要な単位数は？
```

## 起動設定

| 変数 | 既定値 | 用途 |
|---|---|---|
| `VLLM_MODEL` | `Qwen/Qwen3-8B` | vLLMが読み込むモデルのパスまたはID |
| `VLLM_STARTUP_TIMEOUT` | `600` | vLLM起動待ち秒数 |

`GenResponce.py`の既存設定に合わせ、vLLMは`127.0.0.1:8000`で起動します。
`VLLM_MODEL`をローカルパスへ変更しても、vLLMには既存コードが要求する
`Qwen/Qwen3-8B`名で公開されます。

## 個別起動

デバッグ時は別々にも起動できます。

```bash
vllm serve Qwen/Qwen3-8B --host 127.0.0.1 --port 8000
python discordbot/bot.py
```

## テスト

```bash
pytest
```
