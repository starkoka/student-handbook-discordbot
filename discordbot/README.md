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

現時点の `RAG/GenResponce.py` には、`gen_response()` が `search()` の
第4引数（`top_k`）に `model` を渡している問題があります。
この状態ではHyDEの有効・無効にかかわらず検索でエラーになります。
RAG側では、第4引数を省略するか `top_k=5` などの整数にする修正が必要です。
