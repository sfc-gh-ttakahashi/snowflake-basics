# Part 1 : Cortex Code (CoCo) 活用例

> **CoCo の開き方:** Snowsight の右下の **CoCo アイコン（吹き出し）** をクリックすると、チャットパネルが開きます。

Part1 では、通販会社「くらしモール」の CRM データを題材に、CoCo の基本的な使い方を試します。

| # | やること | CoCo に任せること |
|---|---|---|
| 1 | コードの説明 | 他の人が書いた SQL の意味を読み解く |
| 2 | 自然言語で SQL 生成 | テーブルを探して SQL を組み立てる |
| 3 | エラー修正 | 間違いを見つけて直す |
| 4 | テストデータ生成 | まだないデータを、既存のテーブルと結合できる形で作る |
| 5 | ドキュメント生成 | テーブル定義書を作る |

```sql 0-1
-- コンテキスト設定
USE ROLE ACCOUNTADMIN;
USE WAREHOUSE AI_HANDSON_WH;
USE DATABASE AI_HANDSON_DB;
USE SCHEMA CRM;
```

---
## 1. コードの説明

CoCo に既存のコードを読み解いてもらいます。
他の人が書いた SQL を引き継いだときなど、複雑なクエリの意味を知りたいときに便利です。

1. 下の SQL セルを **クリックして選択** する（または、セル右上の星マークをクリックする）
2. CoCo チャットで、次のように聞いてみましょう

```
この SQL を説明して
```

> **ポイント:** CoCo は選択したセルのコードを読み取り、処理の流れ・各 CTE の役割・最終的な出力を日本語で説明します。
> 説明を読んだら、セルを実行して結果を確かめてみましょう。

```sql 1-1
-- この SQL が何をしているか、CoCo に聞いてみましょう
WITH order_summary AS (
    SELECT
        customer_id,
        COUNT(*)            AS order_count,
        SUM(total_amount)   AS total_amount,
        MAX(ordered_at)     AS last_ordered_at
    FROM orders
    GROUP BY customer_id
),
touchpoint_trend AS (
    SELECT
        customer_id,
        COUNT_IF(occurred_at <  '2026-09-01') / 9 AS monthly_before,
        COUNT_IF(occurred_at >= '2026-09-01') / 3 AS monthly_recent
    FROM touchpoints
    GROUP BY customer_id
)
SELECT
    c.customer_id,
    c.name,
    c.member_rank,
    o.order_count,
    o.total_amount,
    o.last_ordered_at,
    ROUND(t.monthly_before, 1) AS monthly_touchpoints_before,
    ROUND(t.monthly_recent, 1) AS monthly_touchpoints_recent,
    CASE
        WHEN t.monthly_recent < t.monthly_before * 0.5
         AND o.last_ordered_at < '2026-09-01' THEN '離反の兆候あり'
        WHEN t.monthly_recent < t.monthly_before * 0.5 THEN '要注意'
        ELSE '安定'
    END AS status
FROM customers c
JOIN order_summary    o ON o.customer_id = c.customer_id
JOIN touchpoint_trend t ON t.customer_id = c.customer_id
WHERE c.member_rank IN ('ゴールド', 'プラチナ')
QUALIFY ROW_NUMBER() OVER (PARTITION BY status ORDER BY o.total_amount DESC) <= 3
ORDER BY status, o.total_amount DESC;
```

---
## 2. 自然言語で SQL 生成

CoCo にやりたいことを日本語で伝えるだけで、**テーブルの構造を自分で調べて SQL を生成**します。
テーブル名や列名を覚えていなくても大丈夫です。

### やってみよう

次の空のセルを選択し、CoCo チャットで次のように聞いてみましょう。

```
AI_HANDSON_DB.CRM にあるテーブルを使って、
会員ランク別・月別の平均注文金額とリピート率（2 回以上注文した会員の割合）を集計する SQL を書いて
```

> **観察ポイント:**
> - CoCo がまず `SHOW TABLES` や `DESCRIBE TABLE` でテーブルの構造を調べる
> - 列名・型を確かめてから SQL を組み立てる
> - 生成された SQL を、そのままセルに入れて実行できる

### もう 1 つ試してみよう

```
問い合わせをした会員としていない会員で、その後 3 か月の注文金額を比べる SQL を書いて
```

> **ポイント:** テーブル名を指定しなくても、CoCo は `inquiries` と `orders` を見つけ、日付の範囲で結合します。

```sql 2-1
-- ここに CoCo が生成した SQL を入れて実行する
SELECT 'CoCo が生成した SQL をここに入れてください' AS message;
```

---
## 3. エラー修正

次の SQL は「商品カテゴリ × 注文チャネル別に、注文数と売上を集計する」ものですが、**3 か所の誤りがあります**。
まず実行してエラーを確かめ、CoCo に直してもらいましょう。

```sql 3-1 error
-- 商品カテゴリ × 注文チャネル別の注文数と売上
-- channel: 注文チャネル（Web / アプリ / 電話）
-- sales_amount: 単価 × 数量 の合計
SELECT
    p.category,
    p.product_name,
    o.channel,
    COUNT(DISTINCT o.order_id)          AS orders,
    SUM(i.quantity)                     AS units,
    SUM(i.price * i.quantity)           AS sales_amount
FROM orders o
JOIN order_items i ON i.order_id = o.order_id
JOIN products p    ON p.product_id = o.product_id
GROUP BY p.category, o.channel
ORDER BY sales_amount DESC;
```

エラーが出たら、結果の欄に表示される **エラーを修正** をクリックしてください。

> **観察ポイント:** Snowflake は、1 回の実行で誤りを 1 か所しか報告しません。
> CoCo は報告された 1 か所だけでなく、SQL 全体を読んで残りの誤りもまとめて直すかを見てみましょう。

> **解答: 仕込んだ誤り 3 か所**（エラーが報告される順）
>
> | # | 誤りの箇所 | 原因 | 直し方 |
> |---|---|---|---|
> | 1 | `i.price` | `order_items` に `price` 列はない。`products` の列 | `p.price * i.quantity` にする |
> | 2 | `p.product_name` | SELECT にあるのに `GROUP BY` にない | `GROUP BY` に `p.product_name` を加えるか、SELECT から外す |
> | 3 | `o.product_id` | `orders` に `product_id` 列はない。注文と商品は `order_items` でつながる | `p.product_id = i.product_id` にする |

---
## 4. テストデータ生成

CoCo は、テーブル定義と既存データの文脈を読み取り、**既存のデータと整合するサンプルデータ**を作れます。
ここでは CoCo に `.sql` ファイルを作らせ、メールキャンペーンのデータを用意して、会員データと結合して分析します。

### シナリオ

くらしモールでは、会員にメールキャンペーンを送っていますが、**どのキャンペーンを誰に送り、誰が反応したか**のデータがまだありません。
キャンペーンのマスタと配信結果のテーブルを作り、「会員ランクによって反応率が違うか」を分析しましょう。

### やってみよう

CoCo チャットで、次のように依頼してみましょう。

```
メールキャンペーンの効果を分析したいが、まだデータがないのでサンプルデータから作りたい。
AI_HANDSON_DB.CRM の CUSTOMERS テーブルと JOIN できる形で、以下を含む SQL ファイル「create_campaign_data.sql」を作成して。

- キャンペーンのマスタテーブル（5 件程度）の作成とサンプルデータの投入
- 会員ごとの配信結果テーブル（配信日時、開封、クリック、購入の有無）の作成とサンプルデータの投入
- 作成したデータと会員データを JOIN して、会員ランク別の開封率・購入率を出す確認用のクエリ
- 末尾にクリーンアップ用の DROP TABLE（コメントアウト）
```

> **観察ポイント:**
> - 列の定義を指定しなくても、CoCo が既存のテーブルの構造を読み取って、列を設計する
> - 左のファイル一覧に `create_campaign_data.sql` が表示される
> - ファイルを開いて、CoCo がどんな列やデータを設計したかを確かめてみましょう
> - 末尾にコメントアウトされた DROP TABLE 文があるので、ハンズオン後の後片付けにも使える

ファイルができたら、左のサイドバーから **`create_campaign_data.sql` を開いて実行（▶）** してください。

**補足**
- 生成される SQL は人によって変わります。内容を確かめながら実行してください。
- 長いコードは、1 回でうまく動かないこともあります。その場合は、CoCo にエラーの修正を頼みながら進めてください。

---
## 5. ドキュメント生成

CoCo にスキーマのメタデータを読ませて、**テーブル定義書**を作らせます。
テーブルが増えるたびに、手作業でドキュメントを更新する手間がなくなります。

### やってみよう

CoCo チャットで、次のように依頼してみましょう。

```
AI_HANDSON_DB.CRM スキーマの全テーブルについて、テーブル定義書を Markdown ファイルで新規作成して。
各テーブルごとに以下を含めて:
- テーブルの説明
- 列の一覧（列名、型、説明）
- 他のテーブルとの関係
```

> **観察ポイント:** `setup.sql` で各テーブル・列に付けた `COMMENT` を、CoCo が定義書の説明に使います。
> テーブルにコメントを付けておくと、CoCo の生成するドキュメントや SQL の質が上がります。

---
## まとめ

- **コードの説明**: 引き継いだ SQL の意味をすぐに把握できる
- **自然言語で SQL 生成**: テーブル名を覚えていなくても、CoCo が構造を調べて SQL を書く
- **エラー修正**: 報告されたエラーだけでなく、SQL 全体の誤りを直せる
- **テストデータ生成・ドキュメント生成**: 既存のテーブルの構造に合わせて、データやドキュメントを作れる

次の Part2 では、同じ CRM データを使って Snowflake の基本機能を試します。
