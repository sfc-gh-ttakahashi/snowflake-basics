-- =============================================================
-- 03_extract_return_forms.sql
-- 返品申請書 PDF から項目を取り出し、AI_RETURN_FORMS に入れる（Part3-2 のタスク 3）
--
-- まだ取り出していない PDF だけに AI_EXTRACT を呼ぶ。
-- ステージに PDF を追加してタスクグラフを実行すると、追加した PDF だけが処理される。
-- =============================================================
CREATE TABLE IF NOT EXISTS AI_HANDSON_DB.CRM.AI_RETURN_FORMS (
    file_path      VARCHAR(200) PRIMARY KEY COMMENT 'ステージ上の PDF のパス',
    order_id       VARCHAR(10)              COMMENT '申請書の注文番号',
    customer_name  VARCHAR(50)              COMMENT '申請書の氏名',
    product_name   VARCHAR(100)             COMMENT '申請書の商品名',
    request        VARCHAR(10)              COMMENT '希望（返金/交換）',
    reason_summary VARCHAR(200)             COMMENT '返品・交換の理由の要約',
    extracted_at   TIMESTAMP_LTZ            COMMENT '取り出した日時'
)
COMMENT = 'AI_EXTRACT で返品申請書 PDF から取り出した項目（Part3-2 のパイプラインで作成）';

-- ステージの一覧を最新にする（新しく置いた PDF を DIRECTORY に反映する）
ALTER STAGE AI_HANDSON_DB.CRM.DATA_STAGE REFRESH;

INSERT INTO AI_HANDSON_DB.CRM.AI_RETURN_FORMS
    (file_path, order_id, customer_name, product_name, request, reason_summary, extracted_at)
WITH extracted AS (
    SELECT
        d.relative_path,
        AI_EXTRACT(
            file => TO_FILE('@AI_HANDSON_DB.CRM.DATA_STAGE', d.relative_path),
            responseFormat => {
                'order_id':       '注文番号は？',
                'customer_name':  'お名前は？',
                'product_name':   '商品名は？',
                'request':        'ご希望は返金と交換のどちら？',
                'reason_summary': '返品・交換の理由を20文字以内で要約すると？'
            }
        ):response AS r
    FROM DIRECTORY(@AI_HANDSON_DB.CRM.DATA_STAGE) d
    WHERE d.relative_path LIKE 'data/pdf/return_%'
      AND NOT EXISTS (
          SELECT 1 FROM AI_HANDSON_DB.CRM.AI_RETURN_FORMS f WHERE f.file_path = d.relative_path
      )
)
SELECT
    relative_path,
    r:order_id::VARCHAR,
    r:customer_name::VARCHAR,
    r:product_name::VARCHAR,
    r:request::VARCHAR,
    r:reason_summary::VARCHAR,
    CURRENT_TIMESTAMP()
FROM extracted;
