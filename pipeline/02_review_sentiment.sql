-- =============================================================
-- 02_review_sentiment.sql
-- レビューの感情を判定し、AI_REVIEW_SENTIMENT に入れる（Part3-2 のタスク 2）
--
-- まだ判定していないレビューだけに AI_SENTIMENT を呼ぶ。
-- =============================================================
CREATE TABLE IF NOT EXISTS AI_HANDSON_DB.CRM.AI_REVIEW_SENTIMENT (
    review_id   VARCHAR(10) PRIMARY KEY COMMENT 'レビューID',
    sentiment   VARCHAR(10)             COMMENT 'AI が判定した感情（positive/negative/neutral/mixed）',
    judged_at   TIMESTAMP_LTZ           COMMENT '判定した日時'
)
COMMENT = 'AI_SENTIMENT で判定したレビューの感情（Part3-2 のパイプラインで作成）';

INSERT INTO AI_HANDSON_DB.CRM.AI_REVIEW_SENTIMENT (review_id, sentiment, judged_at)
SELECT
    r.review_id,
    AI_SENTIMENT(r.body):categories[0]:sentiment::VARCHAR,
    CURRENT_TIMESTAMP()
FROM AI_HANDSON_DB.CRM.reviews r
WHERE NOT EXISTS (
    SELECT 1 FROM AI_HANDSON_DB.CRM.AI_REVIEW_SENTIMENT s WHERE s.review_id = r.review_id
);
