# Part 3-2 : Pipeline Builder で AI 処理をパイプラインにする

Part3-1 では、AI 関数を 1 つずつ試しました。
Part3-2 では、そのうち 4 つの処理を **Pipeline Builder** でつなぎ、**1 回の実行でまとめて動くパイプライン**にします。
このパイプラインが作るテーブルは、Part4 の Dashboards・HTML レポート・Streamlit アプリで使います。

```
01 問い合わせの分類   02 レビューの感情   03 返品申請書の抽出
  (AI_CLASSIFY)        (AI_SENTIMENT)      (AI_EXTRACT)
        │                    │                   │
        └────────────┬───────┴───────────────────┘
                     ▼
            04 商品ごとの集計と要約
                  (AI_AGG)
                     │
                     ▼
            AI_PRODUCT_INSIGHTS → Part4 で使う
```

| ファイル | 処理 | 作るテーブル |
|---|---|---|
| `pipeline/01_classify_inquiries.sql` | 問い合わせを種別に振り分ける | `AI_INQUIRY_TOPICS` |
| `pipeline/02_review_sentiment.sql` | レビューの感情を判定する | `AI_REVIEW_SENTIMENT` |
| `pipeline/03_extract_return_forms.sql` | 返品申請書 PDF から項目を取り出す | `AI_RETURN_FORMS` |
| `pipeline/04_product_insights.sql` | 1〜3 の結果を商品ごとに集計し、レビューを要約する | `AI_PRODUCT_REVIEW_SUMMARY`、`AI_PRODUCT_INSIGHTS` |

> **料金を抑える作り:** 01〜04 は、**まだ処理していない行だけ**に AI 関数を呼びます。
> パイプラインを何度実行しても、同じ問い合わせやレビューに AI を呼び直すことはありません。
> 処理の中身は、各ファイルを開いて確かめてみましょう。

---
## 1. パイプラインを作る

1. 左のファイル一覧で、ワークスペースのいちばん上（ルート）の **+** を選び、**Pipeline Builder** を選択する
2. **Create Pipeline Builder** の画面で、次のとおり入力して **Create** を選択する
   - Name: `crm_ai_pipeline`
   - Database: `AI_HANDSON_DB`
   - Schema: `CRM`
3. ワークスペースに `crm_ai_pipeline` フォルダができ、空のキャンバスが開く

> フォルダの中には `manifest.yml`、`pipeline.yml`（パイプラインの定義）、`sources/` フォルダができます。
> Pipeline Builder のパイプラインは、**DCM プロジェクト**として管理されます。

## 2. SQL ファイルをプロジェクトに入れる

リポジトリの `pipeline/` フォルダにある 4 つの SQL ファイルを、`crm_ai_pipeline` フォルダに移します。

1. 左のファイル一覧で、`pipeline` フォルダを開く
2. `01_classify_inquiries.sql` から `04_product_insights.sql` までの 4 つのファイルを、`crm_ai_pipeline` フォルダにドラッグする

> `crm_ai_pipeline` の中の `sources/` フォルダには入れないでください。`sources/` のファイルは、タスクにできません。

## 3. タスクを並べてつなぐ

1. `crm_ai_pipeline` の中の `01_classify_inquiries.sql` を、キャンバスにドラッグする
   - **SQL file** のタスクができ、右側に設定の画面が開く
   - **Name** が `AI_HANDSON_DB.CRM.<タスク名>` になっていることを確かめる
2. `02_review_sentiment.sql` を、1 で作ったカードの **右側** にドラッグし、**Run After** と表示されたら離す
3. `03_extract_return_forms.sql` を、2 で作ったカードの **右側** にドラッグし、同じように離す
4. `04_product_insights.sql` を、3 で作ったカードの **右側** にドラッグし、同じように離す

カードが 01 → 02 → 03 → 04 の順につながり、**タスクグラフ**ができます。最初のタスク（01）が、グラフの起点（ルート）になります。

> **補足:** 01〜03 は互いに関係がないので、本来は並列に実行できます。
> このハンズオンでは操作を分かりやすくするため、一列につなぎます。時間があれば、01 から 02・03 へ分岐させてみましょう。

## 4. 実行に使うウェアハウスを設定する

1. キャンバスの上の **Objects** を選び、**Task graphs** を選んで、作られたタスクグラフを開く
2. **Task defaults** の **Warehouse** に `AI_HANDSON_WH` を選ぶ
3. **Desired state** は **Suspended** のままにする（スケジュールでは動かさず、手動で実行する）

## 5. デプロイする

1. キャンバスの右上の **Deploy** を選択する（見えないときは、ワークスペースの下のパネルを閉じる）
2. DCM プロジェクトがまだないことを知らせる画面が出たら、作成を確定する
3. **Review planned changes** の画面に、作られるタスクとタスクグラフが表示される。内容を確かめて **Deploy** を選択する
4. デプロイが終わると、**Deploy** の横に **Deployed Project** が表示される

## 6. 実行する

画面から実行する場合:

1. **Deployed Project** を選び、**Objects** タブでタスクグラフを選ぶ
2. **Graph** タブを開き、**Run Task Graph** のアイコンを選択する
3. **Overview** タブで、実行の状況を確かめる（4 つのタスクが終わるまで 1〜2 分かかります）

SQL で実行・確認する場合は、次のセルを使います。

```sql 6-1
-- コンテキスト設定
USE ROLE ACCOUNTADMIN;
USE WAREHOUSE AI_HANDSON_WH;
USE DATABASE AI_HANDSON_DB;
USE SCHEMA CRM;

-- このスキーマにあるタスクグラフの名前を確かめる
SHOW TASK GRAPHS IN SCHEMA AI_HANDSON_DB.CRM;
```

> 6-1 の結果の `name` 列に表示された名前を、次のセルの `<タスクグラフ名>` に入れて実行します。

```text
-- タスクグラフを実行する（<タスクグラフ名> を書き換えてから実行）
EXECUTE TASK GRAPH AI_HANDSON_DB.CRM.<タスクグラフ名>;
```

```sql 6-2
-- 実行の結果を確かめる（直近 1 時間に AI_HANDSON_DB.CRM で実行したタスク）
SELECT name, state, scheduled_time, completed_time, error_message
FROM TABLE(AI_HANDSON_DB.INFORMATION_SCHEMA.TASK_HISTORY(
    SCHEDULED_TIME_RANGE_START => DATEADD('hour', -1, CURRENT_TIMESTAMP())))
WHERE database_name = 'AI_HANDSON_DB'
  AND schema_name   = 'CRM'
ORDER BY scheduled_time DESC
LIMIT 10;
```

---
## 7. 結果を確かめる

パイプラインが作ったテーブルの件数を確かめます。

```sql 7-1
SELECT 'AI_INQUIRY_TOPICS'         AS table_name, COUNT(*) AS row_count FROM AI_INQUIRY_TOPICS         UNION ALL
SELECT 'AI_REVIEW_SENTIMENT',                     COUNT(*)              FROM AI_REVIEW_SENTIMENT       UNION ALL
SELECT 'AI_RETURN_FORMS',                         COUNT(*)              FROM AI_RETURN_FORMS           UNION ALL
SELECT 'AI_PRODUCT_REVIEW_SUMMARY',               COUNT(*)              FROM AI_PRODUCT_REVIEW_SUMMARY UNION ALL
SELECT 'AI_PRODUCT_INSIGHTS',                     COUNT(*)              FROM AI_PRODUCT_INSIGHTS;
```

> 期待する件数: `AI_INQUIRY_TOPICS` 300、`AI_REVIEW_SENTIMENT` 300、`AI_RETURN_FORMS` 10、`AI_PRODUCT_REVIEW_SUMMARY` 30、`AI_PRODUCT_INSIGHTS` 30

最終結果の `AI_PRODUCT_INSIGHTS` を、配送の問い合わせが多い順に見てみます。

```sql 7-2
SELECT
    product_name,
    inquiries,
    shipping_inquiries,
    reviews,
    avg_rating,
    negative_reviews,
    return_forms,
    review_complaints
FROM AI_PRODUCT_INSIGHTS
ORDER BY shipping_inquiries DESC, avg_rating
LIMIT 10;
```

> **観察ポイント:** 「低反発マットレス シングル」は、配送の問い合わせが飛び抜けて多く、レビューの評価も低くなっています。
> Part3-1 の 5 章で見た商品仕様書には「受注生産のため、出荷まで 10〜14 営業日」とありました。
> 商品の品質ではなく、**出荷までの日数を購入前に伝えていない**ことが、問い合わせと低評価の原因と考えられます。

### もう一度実行してみる

6 の手順で、タスクグラフをもう一度実行してください。
1 回目より速く終わります。01〜04 が、まだ処理していない行だけに AI 関数を呼ぶためです（今回は対象の行がありません）。

```sql 7-3
-- 2 回目の実行のあとも、件数は変わらない
SELECT 'AI_INQUIRY_TOPICS' AS table_name, COUNT(*) AS row_count, MAX(classified_at) AS last_processed FROM AI_INQUIRY_TOPICS UNION ALL
SELECT 'AI_REVIEW_SENTIMENT',             COUNT(*),              MAX(judged_at)                        FROM AI_REVIEW_SENTIMENT UNION ALL
SELECT 'AI_PRODUCT_REVIEW_SUMMARY',       COUNT(*),              MAX(summarized_at)                    FROM AI_PRODUCT_REVIEW_SUMMARY;
```

> `last_processed` の日時が 1 回目の実行のときのままなら、2 回目は AI 関数を呼んでいません。

---
## Pipeline Builder が使えないときの手順

Pipeline Builder は **Public Preview** の機能です。画面の操作でつまずいたときは、次の手順で同じテーブルを作れます。

1. 左のファイル一覧で `pipeline` フォルダを開く
2. `01_classify_inquiries.sql` を開き、右上の **実行（▶）** の横の **∨** から **すべて実行** を選ぶ
3. 同じように、`02` → `03` → `04` の順に実行する
4. 7 章のセルで結果を確かめる

---
## まとめ

- Part3-1 で 1 つずつ試した AI 関数の SQL を、Pipeline Builder で **順番に実行するパイプライン**にした
- **まだ処理していない行だけ**に AI 関数を呼ぶ作りにすると、何度実行しても料金が増えない
- パイプラインは **DCM プロジェクト**として管理され、デプロイの前に変更の内容を確かめられる

| | 動的テーブル（Part2） | Pipeline Builder（Part3-2） |
|---|---|---|
| 書くもの | 「欲しい結果」の SELECT 文 | 実行する処理（SQL）と、その順番 |
| 更新のタイミング | 元データの変更を検知して自動で更新 | スケジュール、または手動で実行 |
| 向いている処理 | 集計・結合など、結果を常に最新に保ちたいもの | AI 関数の呼び出しなど、実行の回数と順番を管理したいもの |

次の Part4 では、このパイプラインが作った `AI_PRODUCT_INSIGHTS` を、Dashboards・HTML レポート・Streamlit アプリで使います。
