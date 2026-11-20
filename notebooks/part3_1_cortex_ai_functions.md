# Part 3-1 : Cortex AI 関数

Part3-1 では、**SQL から直接呼び出せる Cortex AI 関数**を使って、問い合わせ・レビュー・PDF から情報を取り出します。
どの関数も、まず **少ない行数** で入力と出力を確かめます。ここで試した SQL は、Part3-2 で Pipeline Builder のパイプラインにまとめます。

| # | 関数 | できること | 題材 |
|---|---|---|---|
| 1 | **AI_CLASSIFY** | テキストを、指定した分類に振り分ける | 問い合わせの種別 |
| 2 | **AI_SENTIMENT** | テキストの感情（肯定・否定など）を判定する | 商品レビュー |
| 3 | **AI_EXTRACT** | テキストや PDF から、指定した項目を取り出す | 返品申請書 PDF |
| 4 | **AI_AGG** | 複数の行のテキストをまとめて要約する | 商品ごとのレビュー |
| 5 | **AI_COMPLETE** | 自由なプロンプトで文章を生成する | 問い合わせへの返信案 |
| 6 | **AI_SIMILARITY** | 2 つのテキストの意味の近さ（0〜1）を返す | 外部リストと会員の名寄せ |

> **料金について:** AI 関数は、処理したトークン数に応じてクレジットを消費します。
> このハンズオンのセルは、処理する行数を絞ってあります。`LIMIT` を外して全件に実行しないでください。

```sql 0-1
-- コンテキスト設定
USE ROLE ACCOUNTADMIN;
USE WAREHOUSE AI_HANDSON_WH;
USE DATABASE AI_HANDSON_DB;
USE SCHEMA CRM;
```

---
## 1. AI_CLASSIFY — 問い合わせを種別に振り分ける

![AI_CLASSIFY関数](data/slides/part3/AI_CLASSIFY.png)

カスタマーサポートには、毎日いろいろな問い合わせが届きます。
問い合わせ（`inquiries` テーブル）の本文を、`AI_CLASSIFY` で 6 つの種別に振り分けます。

まずは、日本語の分類名をそのまま渡してみます。

```sql 1-1
-- 日本語の分類名で 10 件（Q0008〜Q0017）を分類する
SELECT
    inquiry_id,
    LEFT(body, 50) AS body_head,
    AI_CLASSIFY(body, ['配送', '返品・交換', '支払い', '商品仕様', '会員・ポイント', 'その他']) AS result
FROM inquiries
WHERE inquiry_id BETWEEN 'Q0008' AND 'Q0017'
ORDER BY inquiry_id;
```

> **観察ポイント:** `result` が `{"labels": []}`（空）になる行があります。どんな問い合わせか、本文を見てみましょう。
> `AI_CLASSIFY` のドキュメントには「入力と分類名には英語の平文を使う」とあります。日本語の分類名では、分類を返さないことがあります。

分類名を **英語** にし、それぞれに **説明（description）** を付けます。
`task_description` で、何を分類するのかも伝えます。

```sql 1-2
-- 英語の分類名 + 説明で、同じ 10 件を分類し、日本語に戻す
SELECT
    inquiry_id,
    LEFT(body, 50) AS body_head,
    AI_CLASSIFY(
        body,
        [
            {'label': 'shipping',     'description': 'late delivery, tracking not updated, package not arrived'},
            {'label': 'return',       'description': 'return, exchange, refund because of wrong size, defect, or not as expected'},
            {'label': 'payment',      'description': 'double charge, credit card error, invoice not received'},
            {'label': 'product_spec', 'description': 'questions about size, material, usage, or compatibility'},
            {'label': 'membership',   'description': 'points not granted, member rank, login problems'},
            {'label': 'other',        'description': 'gift wrapping, receipt, change of delivery address'}
        ],
        {'task_description': 'Classify a Japanese customer support inquiry for an online shop by its main topic.'}
    ):labels[0]::VARCHAR AS topic_en,
    DECODE(topic_en, 'shipping', '配送', 'return', '返品・交換', 'payment', '支払い',
                     'product_spec', '商品仕様', 'membership', '会員・ポイント', 'other', 'その他') AS topic
FROM inquiries
WHERE inquiry_id BETWEEN 'Q0008' AND 'Q0017'
ORDER BY inquiry_id;
```

### 答え合わせ

このハンズオンの問い合わせは合成データなので、正解の種別を `inquiry_labels` テーブルに用意してあります。
50 件で、AI の分類と正解がどれだけ一致するかを確かめます。

```sql 1-3
-- 50 件で、AI の分類と正解の一致率を出す
WITH classified AS (
    SELECT
        i.inquiry_id,
        l.topic AS answer,
        DECODE(
            AI_CLASSIFY(
                i.body,
                [
                    {'label': 'shipping',     'description': 'late delivery, tracking not updated, package not arrived'},
                    {'label': 'return',       'description': 'return, exchange, refund because of wrong size, defect, or not as expected'},
                    {'label': 'payment',      'description': 'double charge, credit card error, invoice not received'},
                    {'label': 'product_spec', 'description': 'questions about size, material, usage, or compatibility'},
                    {'label': 'membership',   'description': 'points not granted, member rank, login problems'},
                    {'label': 'other',        'description': 'gift wrapping, receipt, change of delivery address'}
                ],
                {'task_description': 'Classify a Japanese customer support inquiry for an online shop by its main topic.'}
            ):labels[0]::VARCHAR,
            'shipping', '配送', 'return', '返品・交換', 'payment', '支払い',
            'product_spec', '商品仕様', 'membership', '会員・ポイント', 'other', 'その他'
        ) AS predicted
    FROM inquiries i
    JOIN inquiry_labels l USING (inquiry_id)
    ORDER BY i.inquiry_id
    LIMIT 50
)
SELECT
    COUNT(*)                                  AS total,
    COUNT_IF(answer = predicted)              AS matched,
    ROUND(matched / total * 100, 1)           AS match_pct,
    ARRAY_AGG(CASE WHEN answer <> predicted
                   THEN inquiry_id || ': 正解=' || answer || ' / AI=' || predicted END) AS mismatches
FROM classified;
```

> **観察ポイント:** 一致しなかった問い合わせの本文を読んでみましょう。
> 例えば「配送先を変えたい」という問い合わせは、「配送」とも「その他」とも読めます。AI の誤りか、分類の決め方の問題かは、人が判断します。

---
## 2. AI_SENTIMENT — レビューの感情を判定する

商品レビュー（`reviews` テーブル）の本文から、感情（positive / negative / neutral / mixed）を判定します。
レビューには星の数（`rating`）もあるので、AI の判定と比べてみます。

```sql 2-1
-- 2 つの商品のレビューで、星の数と AI の判定を比べる
WITH judged AS (
    SELECT
        r.product_id,
        p.product_name,
        r.rating,
        AI_SENTIMENT(r.body):categories[0]:sentiment::VARCHAR AS sentiment
    FROM reviews r
    JOIN products p USING (product_id)
    WHERE r.product_id IN ('P001', 'P012')
)
SELECT product_name, rating, sentiment, COUNT(*) AS reviews
FROM judged
GROUP BY ALL
ORDER BY product_name, rating, sentiment;
```

> **観察ポイント:**
> - 星 1 は negative、星 5 は positive になっているか
> - 「低反発マットレス シングル」には、星 2〜3 で mixed（肯定と否定が混ざる）のレビューが多い。どんなことが書かれているかは、4 章で確かめます

---
## 3. AI_EXTRACT — 返品申請書 PDF から項目を取り出す

![AI_EXTRACT関数](data/slides/part3/AI_EXTRACT.png)

返品・交換の申請は、PDF の申請書で届きます（ステージ `@DATA_STAGE/data/pdf/` の `return_*.pdf`）。
`AI_EXTRACT` で、申請書から注文番号・氏名・商品・希望を取り出します。

> サンプルの PDF は、GitHub のリポジトリの `data/pdf/` で中身を確かめられます。

```sql 3-1
-- ステージにある返品申請書の一覧
SELECT relative_path, size
FROM DIRECTORY(@DATA_STAGE)
WHERE relative_path LIKE 'data/pdf/return_%'
ORDER BY relative_path;
```

```sql 3-2
-- 返品申請書 3 件から項目を取り出す
SELECT
    relative_path,
    AI_EXTRACT(
        file => TO_FILE('@DATA_STAGE', relative_path),
        responseFormat => {
            'order_id':       '注文番号は？',
            'customer_name':  'お名前は？',
            'product_name':   '商品名は？',
            'request':        'ご希望は返金と交換のどちら？',
            'reason_summary': '返品・交換の理由を20文字以内で要約すると？'
        }
    ):response AS extracted
FROM DIRECTORY(@DATA_STAGE)
WHERE relative_path LIKE 'data/pdf/return_%'
ORDER BY relative_path
LIMIT 3;
```

取り出した注文番号を使えば、PDF の申請書と注文データを結合できます。
申請書の氏名が、注文した会員の氏名と一致するかを確かめます。

```sql 3-3
-- 申請書から取り出した注文番号で注文データと結合し、氏名が一致するかを確かめる
WITH extracted AS (
    SELECT
        relative_path,
        AI_EXTRACT(
            file => TO_FILE('@DATA_STAGE', relative_path),
            responseFormat => {'order_id': '注文番号は？', 'customer_name': 'お名前は？'}
        ):response AS r
    FROM DIRECTORY(@DATA_STAGE)
    WHERE relative_path LIKE 'data/pdf/return_%'
    ORDER BY relative_path
    LIMIT 5
)
SELECT
    e.relative_path,
    e.r:order_id::VARCHAR      AS order_id,
    e.r:customer_name::VARCHAR AS name_on_form,
    c.name                     AS name_in_crm,
    name_on_form = name_in_crm AS name_matched,
    o.ordered_at,
    o.total_amount
FROM extracted e
JOIN orders o    ON o.order_id = e.r:order_id::VARCHAR
JOIN customers c ON c.customer_id = o.customer_id
ORDER BY e.relative_path;
```

---
## 4. AI_AGG — 商品ごとにレビューを要約する

`AI_AGG` は、`GROUP BY` でまとめた**複数の行のテキスト**を、1 つの指示で要約します。
2 章で mixed が多かった「低反発マットレス シングル」のレビューから、不満の中身を取り出します。

```sql 4-1
-- 2 つの商品について、レビューから不満の点を取り出す
SELECT
    p.product_name,
    COUNT(*)                AS reviews,
    ROUND(AVG(r.rating), 1) AS avg_rating,
    AI_AGG(r.body, 'これは通販サイトの商品レビューです。購入者の不満点を3つ、日本語の箇条書きで挙げてください。') AS complaints
FROM reviews r
JOIN products p USING (product_id)
WHERE r.product_id IN ('P001', 'P012')
GROUP BY p.product_name;
```

> **観察ポイント:** 「低反発マットレス シングル」の不満は、商品そのものより **配送の遅さ** に集まっています。
> 次の 5 章で、その理由を商品仕様書から確かめます。

---
## 5. AI_COMPLETE — 商品仕様書を根拠に返信案を作る

![AI_COMPLETE関数](data/slides/part3/AI_COMPLETE.png)

`AI_COMPLETE` は、自由なプロンプトで文章を生成します。テキストだけでなく、**PDF や画像も入力**にできます。
「低反発マットレス シングル」の商品仕様書（`data/pdf/spec_P012.pdf`）を渡し、配送の問い合わせへの返信案を作らせます。

```sql 5-1
-- 低反発マットレス シングルの配送の問い合わせ 3 件に、仕様書を根拠にした返信案を作る
WITH target AS (
    SELECT i.inquiry_id, i.body
    FROM inquiries i
    WHERE i.product_id = 'P012'
      AND AI_FILTER(PROMPT('この問い合わせは、商品が届かない・配送が遅いという内容ですか？: {0}', i.body))
    ORDER BY i.inquiry_id
    LIMIT 3
)
SELECT
    inquiry_id,
    body,
    AI_COMPLETE(
        'claude-sonnet-4-5',
        PROMPT(
            'あなたは通販サイトのカスタマーサポート担当です。添付の商品仕様書を根拠に、次の問い合わせへの返信案を 200 文字以内で書いてください。仕様書にないことは書かないでください。\n\n問い合わせ: {0}\n\n商品仕様書: {1}',
            body,
            TO_FILE('@DATA_STAGE', 'data/pdf/spec_P012.pdf')
        )
    )::VARCHAR AS reply_draft
FROM target;
```

> **観察ポイント:**
> - 仕様書の「受注生産のため、ご注文から 10〜14 営業日で出荷」を根拠に返信しているか
> - 仕様書にないこと（具体的な到着日など）を書いていないか
> - `AI_FILTER` は、条件に合う行だけを AI で選ぶ関数です。ここでは「配送が遅い」という内容の問い合わせだけを選んでいます
> - PDF を渡すと、`AI_COMPLETE` は VARIANT 型で結果を返します。`::VARCHAR` で文字列に変えています

---
## 6. AI_SIMILARITY — 外部リストを会員と名寄せする

![AI_SIMILARITY関数](data/slides/part3/AI_SIMILARITY.png)

展示会の来場者リスト（`customers_import` テーブル、80 件）を、会員マスタ（`customers` テーブル、500 件）と突き合わせます。
同じ人物でも、氏名・メール・住所の書き方が違うため、完全一致の JOIN では見つかりません。

**表記揺れの例**

| 種類 | 来場者リスト | 会員マスタ |
|---|---|---|
| 空白の有無 | `佐藤美咲` | `佐藤 美咲` |
| カタカナ表記 | `サトウ ミサキ` | `佐藤 美咲` |
| 旧姓 | `森 美咲` | `佐藤 美咲` |
| 全角の番地 | `世田谷区３－１２－５` | `世田谷区3-12-5` |
| 丁目表記 | `世田谷区3丁目12番5号` | `世田谷区3-12-5` |

```sql 6-1
-- 来場者リストの中身を確認
SELECT import_id, name, email, address
FROM customers_import
ORDER BY import_id
LIMIT 10;
```

80 件 × 500 件の全組み合わせ（4 万組）を `AI_SIMILARITY` で比べると、呼び出し回数が多くなります。
そこで、**都道府県が一致する会員だけを候補**にしてから、類似度を計算します。

```sql 6-2
-- 都道府県が一致する会員だけを候補にして、最も似ている会員を選ぶ
-- true_customer_id は答え合わせ用の正解。突き合わせには使っていない
WITH candidates AS (
    SELECT
        x.import_id,
        x.name    AS import_name,
        x.true_customer_id,
        c.customer_id,
        c.name    AS customer_name,
        AI_SIMILARITY(x.name || ' ' || x.email || ' ' || x.address,
                      c.name || ' ' || c.email || ' ' || c.address) AS score
    FROM customers_import x
    JOIN customers c ON CONTAINS(x.address, c.prefecture)
)
SELECT *
FROM candidates
QUALIFY ROW_NUMBER() OVER (PARTITION BY import_id ORDER BY score DESC) = 1
ORDER BY import_id;
```

> **観察ポイント:**
> - `customer_id` と `true_customer_id`（正解）が一致しているか
> - 結果は何件か。80 件より少ないはずです

```sql 6-3
-- 候補に入らなかった来場者を確かめる
SELECT import_id, name, address
FROM customers_import x
WHERE NOT EXISTS (
    SELECT 1 FROM customers c WHERE CONTAINS(x.address, c.prefecture)
)
ORDER BY import_id;
```

### やってみよう: CoCo に名寄せの条件を改善させる

6-3 の来場者は、住所に都道府県が書かれていないため、候補に入りませんでした。
6-2 のセルを選択し、CoCo チャットで次のように頼んでみましょう。

```
このクエリでは、住所に都道府県が書かれていない来場者が候補に入らない。
AI_SIMILARITY を呼ぶ組み合わせを増やしすぎずに、候補に入るようにして
```

> **観察ポイント:** CoCo がどんな条件を考えるか（市区町村で絞る、メールアドレスで絞る、など）を見てみましょう。
> 候補を広げるほど `AI_SIMILARITY` の呼び出しが増えます。精度と料金のバランスを決めるのは人です。

---
## まとめ

| 関数 | 試したこと | Part3-2 のパイプラインに入れるか |
|---|---|---|
| AI_CLASSIFY | 問い合わせの種別。英語の分類名と説明で精度が上がる | 入れる |
| AI_SENTIMENT | レビューの感情 | 入れる |
| AI_EXTRACT | 返品申請書 PDF の項目 | 入れる |
| AI_AGG | 商品ごとのレビューの要約 | 入れる |
| AI_COMPLETE | 仕様書を根拠にした返信案 | 入れない（Part4 のアプリで、画面の操作に合わせて呼ぶ） |
| AI_SIMILARITY | 外部リストの名寄せ | 入れない（呼び出し回数が多く、条件を人が決める必要がある） |

次の Part3-2 では、ここで試した SQL を **Pipeline Builder** でパイプラインにまとめます。
