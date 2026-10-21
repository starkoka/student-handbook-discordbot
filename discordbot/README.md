# Discord Bot

Discord Botは`RAG/GenResponce.py`の`gen_response()`を直接呼び出します。
セットアップ、Discordへの追加方法、統合起動については
[プロジェクトのREADME](../README.md)を参照してください。

`/handbook question:卒業の条件を教えて hyde_sample:3` のように、
質問ごとにHyDEで生成する仮想文書の数を指定できます。
`hyde_sample` は省略時に `1`、指定できる範囲は `0〜10` です。
`0` はHyDEを使わず、元の質問の埋め込みで検索します。
指定値はその質問にのみ適用されます。
生成数を増やすとLLMの呼び出し回数が増え、120秒の回答待ち時間を超える場合があります。

`python run.py` での統合起動では、GPU利用率を起動時の空き容量から自動計算します。
vLLMはGPUを使用し、Discord Botの埋め込みモデルはCPUで実行します。
Bot子プロセスにのみ `CUDA_VISIBLE_DEVICES=-1` を設定して、GPUメモリの競合を防ぎます。
Botを単体起動する場合も同じ動作にするには、
`CUDA_VISIBLE_DEVICES=-1 python discordbot/bot.py` を使用してください。
`(空き容量 − 2 GiB) / GPU全体容量` を小数点以下3桁で切り捨て、上限を `0.90` とします。
`CUDA_VISIBLE_DEVICES` を反映した `cuda:0` を別プロセスのPyTorchで調べます。
取得に失敗した場合は理由を表示して終了します。
設定はシェルの環境変数で指定してください（`discordbot/.env` はランチャーでは読み込みません）。

```bash
# 自動計算（既定）
python run.py
# 他の処理用に4 GiBを残して自動計算
VLLM_GPU_MEMORY_RESERVE_GIB=4 python run.py
# 利用率を手動指定（自動計算をスキップ）
VLLM_GPU_MEMORY_UTILIZATION=0.70 python run.py
```

`VLLM_GPU_MEMORY_UTILIZATION` は `auto` または `0 < 値 <= 1`、
`VLLM_GPU_MEMORY_RESERVE_GIB` は0以上の有限の数値を指定できます。
この計算は起動時点の空き容量に基づきます。モデルやKVキャッシュが収まる保証はなく、
計測後に他のプロセスがメモリを使った場合にも起動が失敗することがあります。

現時点の `RAG/GenResponce.py` には、`gen_response()` が `search()` の
第4引数（`top_k`）に `model` を渡している問題があります。
この状態ではHyDEの有効・無効にかかわらず検索でエラーになります。
RAG側では、第4引数を省略するか `top_k=5` などの整数にする修正が必要です。
