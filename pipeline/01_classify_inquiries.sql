-- =============================================================
-- 01_classify_inquiries.sql
-- 問い合わせを種別に振り分け、AI_INQUIRY_TOPICS に入れる（Part3-2 のタスク 1）
--
-- まだ分類していない問い合わせだけに AI_CLASSIFY を呼ぶ。
-- タスクグラフを何度実行しても、同じ問い合わせに AI を呼び直さない。
-- =============================================================
CREATE TABLE IF NOT EXISTS AI_HANDSON_DB.CRM.AI_INQUIRY_TOPICS (
    inquiry_id    VARCHAR(10) PRIMARY KEY COMMENT '問い合わせID',
    topic         VARCHAR(20)             COMMENT 'AI が判定した種別',
    classified_at TIMESTAMP_LTZ           COMMENT '分類した日時'
)
COMMENT = 'AI_CLASSIFY で判定した問い合わせの種別（Part3-2 のパイプラインで作成）';

INSERT INTO AI_HANDSON_DB.CRM.AI_INQUIRY_TOPICS (inquiry_id, topic, classified_at)
SELECT
    i.inquiry_id,
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
    ),
    CURRENT_TIMESTAMP()
FROM AI_HANDSON_DB.CRM.inquiries i
WHERE NOT EXISTS (
    SELECT 1 FROM AI_HANDSON_DB.CRM.AI_INQUIRY_TOPICS t WHERE t.inquiry_id = i.inquiry_id
);
