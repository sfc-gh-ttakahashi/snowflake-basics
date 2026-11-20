# Snowflake 基礎ハンズオン

架空の通販会社「くらしモール」の CRM データ（すべて合成データ）を使って、Snowflake の基本機能・Cortex AI 関数・Cortex Code（CoCo）を一通り体験するハンズオンの資材です。

## 流れ

| Part | ファイル | 内容 |
|---|---|---|
| 準備 | `load.sql`、`setup.sql` | Git 連携、ウェアハウス・データベース・テーブルの作成、データのロード |
| 1 | `part1_cortex_code.ipynb` | CoCo で SQL を説明させる・生成させる・直させる、テストデータと定義書を作らせる |
| 2 | `part2_snowflake_basics.ipynb` | アダプティブウェアハウス、ゼロコピークローン、SWAP、UNDROP と Time Travel、動的テーブル |
| 3-1 | `part3_1_cortex_ai_functions.ipynb` | AI_CLASSIFY・AI_SENTIMENT・AI_EXTRACT・AI_AGG・AI_COMPLETE・AI_SIMILARITY |
| 3-2 | `part3_2_pipeline_builder.ipynb`、`pipeline/*.sql` | Pipeline Builder で AI 処理をパイプラインにする |
| 4 | `part4_app_development.ipynb`、`streamlit/inquiry_app.py` | Dashboards、HTML レポート、Streamlit アプリ |
| 後片付け | `cleanup.sql` | ハンズオンで作ったオブジェクトの削除 |

## 前提

- Snowflake のアカウント（AWS / Asia Pacific (Tokyo) / Enterprise を想定）
- `ACCOUNTADMIN` ロールが使えること
- Cortex AI 関数と Cortex Code in Snowsight が使えること

## 準備

### 1. Git 連携を作る

Snowsight でワークシート（または SQL ファイル）を開き、[`load.sql`](load.sql) の内容を貼り付けて、すべて実行します。
次のオブジェクトが作られます。

- API 統合 `ai_handson_git_integration`（このリポジトリへの接続を許可する）
- Git リポジトリ `AI_HANDSON_GIT_DB.GIT.ai_handson_git_repo`

### 2. Git 連携ワークスペースを作る

1. Snowsight の左メニュー **Projects → Workspaces** を開く
2. ワークスペースのメニューで **From Git repository** を選ぶ
3. 次のとおり入力して **Create** を選ぶ
   - Repository URL: `https://github.com/sfc-gh-ttakahashi/snowflake-basics`
   - API Integration: `AI_HANDSON_GIT_INTEGRATION`
   - 認証方法: **Public repository**

ワークスペースに、このリポジトリのファイルが表示されます。

### 3. セットアップを実行する

ワークスペースで [`setup.sql`](setup.sql) を開き、すべて実行します。
最後のクエリの結果で、`result` と `expected` がすべて一致すれば準備は完了です。

## データ

| テーブル | 件数 | 内容 |
|---|---|---|
| `customers` | 500 | 会員 |
| `products` | 30 | 商品 |
| `orders` / `order_items` | 3,000 / 4,935 | 注文と注文明細 |
| `inquiries` | 300 | カスタマーサポートへの問い合わせ（本文は AI 関数の入力） |
| `inquiry_labels` | 300 | 問い合わせの種別の正解（AI_CLASSIFY の答え合わせ用） |
| `reviews` | 300 | 商品レビュー |
| `touchpoints` | 4,034 | 会員との接点の履歴 |
| `customers_import` | 80 | 名寄せ用の外部リスト（表記揺れあり） |

ステージ `@AI_HANDSON_DB.CRM.DATA_STAGE` には、返品申請書 10 件と商品仕様書 6 件の PDF（`data/pdf/`）があります。

データはすべて合成データです。実在の人物・企業とは関係ありません。

## 料金について

AI 関数は、処理したトークン数に応じてクレジットを消費します。ノートブックのセルは、処理する行数を絞ってあります。
`LIMIT` を外して全件に実行しないでください。Part3-2 のパイプラインは、まだ処理していない行だけに AI 関数を呼ぶので、何度実行しても AI の料金は増えません。

## 後片付け

[`cleanup.sql`](cleanup.sql) を実行します。ワークスペースのファイル（ダッシュボード・HTML レポート・Pipeline Builder のフォルダ）と、公開したアーティファクトは手動で削除してください。

---

## 資材の作成者向け

### データを作り直す

```bash
uv run python -m scripts.generate.generate_structured                       # 構造化データ（シード固定）
uv run python -m scripts.generate.generate_text --connection <接続名>       # 問い合わせ・レビューの本文（AI_COMPLETE）
uv run python -m scripts.generate.generate_pdf                              # 返品申請書・商品仕様書の PDF
```

- 本文の生成結果は `scripts/generate/.cache/` に保存されます。2 回目以降は、未生成の行だけを生成します
- `generate_structured` を実行し直すと、`inquiries.csv` と `reviews.csv` の本文の列が消えます。続けて `generate_text` を実行してください
- PDF の日本語フォントは、環境変数 `HANDSON_PDF_FONT` で TrueType フォント（`.ttf`）を指定できます

### ノートブックを編集する

ノートブックの本文は `notebooks/*.md` に Markdown で書き、`.ipynb` に変換します。`.ipynb` を直接編集しないでください。

- ```` ```sql 2-1 ```` のコードブロックが、名前「SQL 2-1」の SQL セルになります
- ```` ```sql 4-2 error ```` は、エラーになるのが正しいセルです

```bash
uv run python -m scripts.build_notebooks
```

### 開発用データベースで確かめる

GitHub に push する前に、ローカルのファイルで手順を確かめられます。
開発用データベース `HANDSON_DEV_DB` を作り、`setup.sql` の Git からのコピーをローカルファイルの PUT に置き換えて実行します。

```bash
uv run python -m scripts.dev_setup --connection <接続名>                         # setup.sql を開発用 DB で実行
uv run python -m scripts.run_notebook_sql --connection <接続名> part2_snowflake_basics   # ノートブックの SQL セルを順に実行
uv run python -m scripts.run_pipeline_sql --connection <接続名>                  # pipeline/*.sql を順に実行
```

- Part2 は `customers` を変更・削除します。Part2 の後に別の Part を確かめるときは、先に `dev_setup` で作り直してください
- `run_pipeline_sql` を 2 回続けて実行すると、2 回目は AI 関数を呼ばないことを確かめられます

### テスト

```bash
uv run --group dev pytest -q
```

生成データの性質、`setup.sql` の件数の期待値と CSV の一致、`cleanup.sql` の削除漏れなどを確かめます。
