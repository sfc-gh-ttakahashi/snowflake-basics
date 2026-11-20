-- =============================================================
-- 04_product_insights.sql
-- 1〜3 の結果を商品ごとに集計し、AI_AGG でレビューを要約する（Part3-2 のタスク 4）
--
-- 要約（AI_AGG）は AI_PRODUCT_REVIEW_SUMMARY に分けて保存し、
-- まだ要約していない商品と、要約した後にレビューが増えた商品だけを要約し直す。
-- 集計（AI_PRODUCT_INSIGHTS）は AI を使わないので、毎回作り直す。
-- Part4 の Dashboards・HTML レポート・SiS は、AI_PRODUCT_INSIGHTS を使う。
-- =============================================================
CREATE TABLE IF NOT EXISTS AI_HANDSON_DB.CRM.AI_PRODUCT_REVIEW_SUMMARY (
    product_id        VARCHAR(10) PRIMARY KEY COMMENT '商品ID',
    reviews           NUMBER                  COMMENT '要約したときのレビュー件数',
    review_complaints VARCHAR                 COMMENT 'AI_AGG で取り出したレビューの不満点',
    summarized_at     TIMESTAMP_LTZ           COMMENT '要約した日時'
)
COMMENT = 'AI_AGG で要約した商品ごとのレビューの不満点（Part3-2 のパイプラインで作成）';

MERGE INTO AI_HANDSON_DB.CRM.AI_PRODUCT_REVIEW_SUMMARY s
USING (
    SELECT
        r.product_id,
        COUNT(*) AS reviews,
        AI_AGG(
            r.body,
            '通販サイトの商品レビューから、購入者の不満点を最大3つ挙げてください。'
            || '出力は「・」で始まる箇条書きだけにし、前置き・見出し・説明は書かないでください。'
            || '同じ内容の不満は1つにまとめてください。不満がなければ「・特になし」とだけ書いてください。'
        ) AS review_complaints
    FROM AI_HANDSON_DB.CRM.reviews r
    WHERE r.product_id IN (
        -- まだ要約していない商品と、要約した後にレビューが増えた商品だけを対象にする
        SELECT v.product_id
        FROM AI_HANDSON_DB.CRM.reviews v
        LEFT JOIN AI_HANDSON_DB.CRM.AI_PRODUCT_REVIEW_SUMMARY x USING (product_id)
        GROUP BY v.product_id, x.reviews
        HAVING x.reviews IS NULL OR COUNT(*) <> x.reviews
    )
    GROUP BY r.product_id
) n
ON s.product_id = n.product_id
WHEN MATCHED THEN UPDATE SET
    reviews = n.reviews, review_complaints = n.review_complaints, summarized_at = CURRENT_TIMESTAMP()
WHEN NOT MATCHED THEN INSERT (product_id, reviews, review_complaints, summarized_at)
    VALUES (n.product_id, n.reviews, n.review_complaints, CURRENT_TIMESTAMP());

CREATE OR REPLACE TABLE AI_HANDSON_DB.CRM.AI_PRODUCT_INSIGHTS
COMMENT = '商品ごとの問い合わせ・レビュー・返品の集計と、レビューの要約（Part3-2 のパイプラインで作成）'
AS
WITH inquiry_stats AS (
    SELECT
        i.product_id,
        COUNT(*)                                AS inquiries,
        COUNT_IF(t.topic = '配送')              AS shipping_inquiries,
        COUNT_IF(t.topic = '返品・交換')        AS return_inquiries
    FROM AI_HANDSON_DB.CRM.inquiries i
    JOIN AI_HANDSON_DB.CRM.AI_INQUIRY_TOPICS t USING (inquiry_id)
    WHERE i.product_id IS NOT NULL
    GROUP BY i.product_id
),
review_stats AS (
    SELECT
        r.product_id,
        COUNT(*)                                AS reviews,
        ROUND(AVG(r.rating), 2)                 AS avg_rating,
        COUNT_IF(s.sentiment = 'negative')      AS negative_reviews
    FROM AI_HANDSON_DB.CRM.reviews r
    JOIN AI_HANDSON_DB.CRM.AI_REVIEW_SENTIMENT s USING (review_id)
    GROUP BY r.product_id
),
return_stats AS (
    -- 申請書の商品名で、注文の中のどの商品の返品かを特定する
    SELECT
        i.product_id,
        COUNT(*) AS return_forms
    FROM AI_HANDSON_DB.CRM.AI_RETURN_FORMS f
    JOIN AI_HANDSON_DB.CRM.order_items i
      ON i.order_id = f.order_id
    JOIN AI_HANDSON_DB.CRM.products p
      ON p.product_id = i.product_id AND p.product_name = f.product_name
    GROUP BY i.product_id
)
SELECT
    p.product_id,
    p.product_name,
    p.category,
    COALESCE(q.inquiries, 0)          AS inquiries,
    COALESCE(q.shipping_inquiries, 0) AS shipping_inquiries,
    COALESCE(q.return_inquiries, 0)   AS return_inquiries,
    COALESCE(v.reviews, 0)            AS reviews,
    v.avg_rating,
    COALESCE(v.negative_reviews, 0)   AS negative_reviews,
    COALESCE(f.return_forms, 0)       AS return_forms,
    m.review_complaints,
    CURRENT_TIMESTAMP()               AS updated_at
FROM AI_HANDSON_DB.CRM.products p
LEFT JOIN inquiry_stats q USING (product_id)
LEFT JOIN review_stats  v USING (product_id)
LEFT JOIN return_stats  f USING (product_id)
LEFT JOIN AI_HANDSON_DB.CRM.AI_PRODUCT_REVIEW_SUMMARY m USING (product_id);
