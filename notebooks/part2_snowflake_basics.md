# Part 2 : Snowflake 基礎

Part2 では、**Snowflake の基本機能**を一通り体験します。
題材は、通販会社「くらしモール」の会員データ（`customers`）と注文データ（`orders`）です。

| # | 機能 | ポイント |
|---|---|---|
| 1 | アダプティブウェアハウス | サイズ指定なしでワークロードに応じて自動スケール |
| 2 | ゼロコピークローン | ストレージを消費せずに瞬時にテーブルを複製 |
| 3 | データ修正と SWAP | 開発用コピーで修正し、本番とアトミックに入れ替え |
| 4 | UNDROP と Time Travel | 誤って削除したテーブルを瞬時に復旧し、過去のデータも参照する |
| 5 | 動的テーブル | SELECT 文を書くだけで自動更新されるパイプライン |

```sql 0-1
-- コンテキスト設定
USE ROLE ACCOUNTADMIN;
USE WAREHOUSE AI_HANDSON_WH;
USE DATABASE AI_HANDSON_DB;
USE SCHEMA CRM;
```

---
## 1. アダプティブウェアハウス

この後のハンズオンで利用するウェアハウスとして、アダプティブウェアハウスを作成します。
SQL で作成する手順になっていますが、GUI でも作成できます。

> **GUI での作成方法**
>
> Snowsight 左メニュー **コンピュート → ウェアハウス → + ウェアハウス** で、タイプに **適応型** を選択します。
> ※ ACCOUNTADMIN など、ウェアハウスの作成権限があるロールを選択してください。

```sql 1-1
-- アダプティブウェアハウスを作成
CREATE OR REPLACE ADAPTIVE WAREHOUSE AI_HANDSON_ADAPTIVE_WH
    MAX_QUERY_PERFORMANCE_LEVEL = MEDIUM
    QUERY_THROUGHPUT_MULTIPLIER = 2
    COMMENT = 'Part 2 アダプティブウェアハウス ハンズオン用';
```

```sql 1-2
-- 作成結果を確認
-- 確認ポイント:
--   1. "type" = ADAPTIVE → 従来の STANDARD ではなく、アダプティブウェアハウスとして作成されている
--   2. "size" = NULL → アダプティブ WH にはサイズ（XS/S/M/...）の概念がなく、ワークロードに応じて自動でスケールする
--   3. "state" = ENABLED → アダプティブ WH は SUSPEND/RESUME ではなく ENABLE/DISABLE で制御する
--   4. "max_query_performance_level" = MEDIUM → 1 クエリあたりに使えるコンピュートの上限
--   5. "query_throughput_multiplier" = 2 → 同時実行性能の倍率（大きいほど並列処理に強い。0 は無制限）
SHOW WAREHOUSES LIKE 'AI_HANDSON_ADAPTIVE_WH';
```

```sql 1-3
-- アダプティブウェアハウスでクエリを実行してみる
USE WAREHOUSE AI_HANDSON_ADAPTIVE_WH;

-- 会員ランク別の会員数・注文数・売上
SELECT
    c.member_rank,
    COUNT(DISTINCT c.customer_id) AS customers,
    COUNT(o.order_id)             AS orders,
    SUM(o.total_amount)           AS sales_amount
FROM customers c
LEFT JOIN orders o ON o.customer_id = c.customer_id
GROUP BY c.member_rank
ORDER BY sales_amount DESC;
```

```sql 1-4
-- 以降はハンズオン用のウェアハウスに戻す
USE WAREHOUSE AI_HANDSON_WH;
```

---
## 2. ゼロコピークローン

くらしモールでは、会員ランクの名称を **「ブロンズ」から「レギュラー」に変える**ことになりました。
本番テーブルを直接変更するのはリスクがあるため、まずは**開発用のコピー**を作成し、そちらで作業します。

Snowflake の `CLONE` は**ゼロコピークローン**と呼ばれ、データを物理的にコピーしません。
メタデータだけを複製するので、テーブルのサイズに関係なく**一瞬で完了し、追加のストレージも消費しません**。
クローン後に変更した部分だけが、新たにストレージとして記録されます。

| SQL | やること |
|---|---|
| 2-1 | 本番テーブル `customers` の会員ランク別の件数を確認 |
| 2-2 | `customers` をクローンして、開発用テーブル `customers_dev` を作成 |
| 2-3 | `customers_dev` に本番と同じデータが入っていることを確認 |

![IMAGE](./data/slides/part2/zerocopy.png)

```sql 2-1
-- 本番テーブルの会員ランク別の件数
SELECT member_rank, COUNT(*) AS customers
FROM customers
GROUP BY member_rank
ORDER BY customers DESC;
```

```sql 2-2
-- 開発用のクローンを作成
CREATE OR REPLACE TABLE customers_dev CLONE customers;
```

```sql 2-3
-- クローンの中身を確認（SQL 2-1 と同じ結果になる）
SELECT member_rank, COUNT(*) AS customers
FROM customers_dev
GROUP BY member_rank
ORDER BY customers DESC;
```

---
## 3. データ修正と SWAP

開発用のクローンで会員ランクの名称を変え、問題なければ本番テーブルと入れ替えます。

```sql 3-1
-- 開発用テーブルで「ブロンズ」を「レギュラー」に変更
UPDATE customers_dev
SET member_rank = 'レギュラー'
WHERE member_rank = 'ブロンズ';
```

```sql 3-2
-- 修正結果を確認（本番はまだ「ブロンズ」のまま）
SELECT 'dev' AS env, member_rank, COUNT(*) AS customers FROM customers_dev GROUP BY member_rank
UNION ALL
SELECT 'prod', member_rank, COUNT(*) FROM customers GROUP BY member_rank
ORDER BY env, customers DESC;
```

修正に問題がなさそうなので、本番テーブルと入れ替えます。

`SWAP WITH` は、2 つのテーブルの**メタデータとデータを交換**します。
アプリケーションから見ると、`customers` が一瞬で修正後のデータに切り替わります。

- **1 文で安全に入れ替えられる**: 一時テーブルを用意したり、名前の変更を何度も組み合わせたりする必要がありません。
- **ゼロコピークローンと組み合わせられる**: 「クローンで修正 → SWAP で本番に反映」という流れを、追加のストレージをほとんど使わずに実現できます。

```sql 3-3
-- 本番と開発を入れ替える
ALTER TABLE customers SWAP WITH customers_dev;
```

```sql 3-4
-- 本番が修正後のデータになっていることを確認
SELECT member_rank, COUNT(*) AS customers
FROM customers
GROUP BY member_rank
ORDER BY customers DESC;
```

---
## 4. UNDROP と Time Travel

後片付けで開発用テーブルを消すつもりが……**本番テーブルを誤って削除**してしまいました。

Snowflake には **Time Travel** という仕組みがあり、削除したテーブルも保持期間内（既定は 1 日）であれば `UNDROP` で復旧できます。
バックアップからのリストアは不要です。

![IMAGE](./data/slides/part2/timetravel.png)

```sql 4-1
-- 誤って本番テーブルを削除
DROP TABLE customers;
```

```sql 4-2 error
-- テーブルが存在しないためエラーになる
SELECT COUNT(*) FROM customers;
```

```sql 4-3
-- テーブルを復旧
UNDROP TABLE customers;
```

```sql 4-4
-- 修正後のデータのまま戻っていることを確認
SELECT member_rank, COUNT(*) AS customers
FROM customers
GROUP BY member_rank
ORDER BY customers DESC;
```

Time Travel では、**過去の時点のデータ**も参照できます。
3 章の UPDATE を実行する前の会員ランクを見てみます。

```sql 4-5
-- Time Travel で修正前（3 章の UPDATE を実行する前）のデータを確認
SET update_qid = (
    SELECT query_id
    FROM TABLE(AI_HANDSON_DB.INFORMATION_SCHEMA.QUERY_HISTORY())
    WHERE query_type = 'UPDATE'
      AND query_text ILIKE '%customers_dev%'
      AND execution_status = 'SUCCESS'
    ORDER BY start_time DESC
    LIMIT 1
);

SELECT member_rank, COUNT(*) AS customers
FROM customers BEFORE (STATEMENT => $update_qid)
GROUP BY member_rank
ORDER BY customers DESC;
```

```sql 4-6
-- 今度こそ開発用テーブルを削除
DROP TABLE customers_dev;
```

---
## 5. 動的テーブルによるパイプライン

**動的テーブル（Dynamic Table）** は、「欲しい結果」を SELECT 文で定義するだけで、
元テーブルの変更を検知して**自動で更新**するテーブルです。

- `TARGET_LAG`: 元データからどのくらいの遅れまで許容するか（最小 1 分）
- `WAREHOUSE`: 更新処理に使うウェアハウス
- `REFRESH_MODE = INCREMENTAL`: 変わった行だけを計算し直す（指定しないと、クエリによっては毎回全件を計算し直す FULL が自動で選ばれる）

### このセクションでやること

注文データから、**「どのカテゴリが、どの月に、どれだけ売れているか」**を見る集計表を作ります。
新しい注文が入っても、集計表が**自動で最新の状態に保たれる**ことを確認します。

```
orders + order_items + products ──▶ DT_ORDER_LINES ──▶ DT_MONTHLY_CATEGORY_SALES
          (元データ)                 (注文明細に商品情報を付ける)   (月 × カテゴリで集計)
```

| Step | やること |
|---|---|
| 1 | 注文明細に、注文日と商品のカテゴリ・金額を付ける |
| 2 | 月 × カテゴリごとに注文数・売上を集計する |
| 3 | 元データに注文を追加し、2 段とも自動で更新されることを確認する |

![IMAGE](./data/slides/part2/dynamictable01.png)
![IMAGE](./data/slides/part2/dynamictable02.png)

### Step 1 : 注文明細に商品情報を付ける

```sql 5-1
-- 1 段目: 注文明細に注文日と商品の情報を付ける動的テーブル
CREATE OR REPLACE DYNAMIC TABLE DT_ORDER_LINES
    TARGET_LAG   = '1 minute'
    WAREHOUSE    = AI_HANDSON_WH
    REFRESH_MODE = INCREMENTAL
    COMMENT      = '注文明細に注文日と商品情報を付けたもの（Part2 の動的テーブル 1 段目）'
AS
SELECT
    o.order_id,
    o.ordered_at,
    o.channel,
    p.product_id,
    p.category,
    i.quantity,
    p.price * i.quantity AS line_amount
FROM orders o
JOIN order_items i ON i.order_id = o.order_id
JOIN products p    ON p.product_id = i.product_id;
```

```sql 5-2
SELECT * FROM DT_ORDER_LINES ORDER BY ordered_at DESC LIMIT 10;
```

### Step 2 : 月 × カテゴリで集計する

1 段目の動的テーブルを元に、さらに動的テーブルを作ります。
このように**動的テーブル同士をつなげてパイプラインを組める**のが特徴です。

```sql 5-3
-- 2 段目: 月 × カテゴリで集計する動的テーブル
CREATE OR REPLACE DYNAMIC TABLE DT_MONTHLY_CATEGORY_SALES
    TARGET_LAG   = '1 minute'
    WAREHOUSE    = AI_HANDSON_WH
    REFRESH_MODE = INCREMENTAL
    COMMENT      = '月 × カテゴリの売上集計（Part2 の動的テーブル 2 段目）'
AS
SELECT
    DATE_TRUNC('month', ordered_at) AS sales_month,
    category,
    COUNT(DISTINCT order_id)        AS orders,
    SUM(line_amount)                AS sales_amount
FROM DT_ORDER_LINES
GROUP BY ALL;
```

```sql 5-4
SELECT * FROM DT_MONTHLY_CATEGORY_SALES
ORDER BY sales_month DESC, sales_amount DESC
LIMIT 12;
```

### Step 3 : 元データを追加して自動更新を確認する

**元テーブル `orders` と `order_items`** に、新しい注文を 1 件追加します。

> ポイント: 追加するのは元テーブルだけです。Step 1・2 で作った動的テーブルには、**INSERT も UPDATE も一切していません**。

それでも `TARGET_LAG`（1 分）以内に、元テーブルの変更が 2 段の動的テーブルへ自動で反映されます。
追加する注文は、まだデータのない **2026 年 12 月**の注文です。

```sql 5-5
-- 2026 年 12 月の注文を 1 件追加（羽毛布団 シングル × 2）
INSERT INTO orders (order_id, customer_id, ordered_at, channel, total_amount)
VALUES ('ORD-99999', 'C0001', '2026-12-08 14:00:00', 'Web', 59600);

INSERT INTO order_items (order_id, product_id, quantity)
VALUES ('ORD-99999', 'P011', 2);
```

1 分ほど待ってから次のセルを実行してください。
待っている間に、下の **DAG（依存関係グラフ）** を確認してみましょう。

> 結果が 0 件の場合は、まだ動的テーブルが更新されていません。少し待って再実行してください。

```sql 5-6
-- 2026 年 12 月の行が集計に増えていることを確認
SELECT *
FROM DT_MONTHLY_CATEGORY_SALES
WHERE sales_month = '2026-12-01';
```

```sql 5-7
-- 更新履歴を確認する
-- 確認ポイント:
--   refresh_action = INCREMENTAL → 追加した行だけを計算し直した
--   refresh_action = NO_DATA     → 元データに変更がなかったので、計算していない
SELECT name, refresh_action, state, data_timestamp
FROM TABLE(AI_HANDSON_DB.INFORMATION_SCHEMA.DYNAMIC_TABLE_REFRESH_HISTORY())
WHERE name IN ('DT_ORDER_LINES', 'DT_MONTHLY_CATEGORY_SALES')
ORDER BY data_timestamp DESC
LIMIT 6;
```

### DAG（有向非循環グラフ）でパイプラインを確認する

動的テーブル同士の依存関係は、Snowsight 上でグラフとして確認できます。

1. Snowsight 左メニュー **カタログ → データベースエクスプローラー** を開く
2. **AI_HANDSON_DB → CRM → 動的テーブル → DT_MONTHLY_CATEGORY_SALES** を選択
3. **グラフ** タブを開く

`ORDERS / ORDER_ITEMS / PRODUCTS → DT_ORDER_LINES → DT_MONTHLY_CATEGORY_SALES` の流れと、各テーブルの更新状況（最終更新時刻、ラグ）を確認できます。
**更新履歴** タブでは、各リフレッシュが増分（INCREMENTAL）で実行されたかも確認できます。

```sql 5-8
-- SQL で更新状況を確認することもできる
SHOW DYNAMIC TABLES IN SCHEMA AI_HANDSON_DB.CRM;
```

---
## まとめ

- **アダプティブウェアハウス**: サイズを意識せずに使える
- **ゼロコピークローン + SWAP**: 本番を止めずに、安全に修正して切り替えられる
- **UNDROP と Time Travel**: 誤削除をすぐに戻せ、過去のデータも参照できる
- **動的テーブル**: SELECT を書くだけで、自動更新されるパイプラインを作れる

Part3 の後半では、**Pipeline Builder** でもパイプラインを作ります。2 つの違いは次のとおりです。

| | 動的テーブル（Part2） | Pipeline Builder（Part3） |
|---|---|---|
| 書くもの | 「欲しい結果」の SELECT 文 | 実行する処理（SQL）と、その順番 |
| 更新のタイミング | 元データの変更を検知して自動で更新 | スケジュール、または手動で実行 |
| 向いている処理 | 集計・結合など、結果を常に最新に保ちたいもの | AI 関数の呼び出しなど、実行の回数と順番を管理したいもの |
