-- =============================================================
-- setup.sql - ハンズオン共通の事前セットアップ
-- 参照リポジトリ: https://github.com/sfc-gh-ttakahashi/snowflake-basics
--
-- 先に load.sql を実行して、Git リポジトリを作っておいてください。
-- 題材: 架空の通販会社「くらしモール」の CRM データ（すべて合成データ）
-- =============================================================

-- -----------------------------------------------
-- Step 1. ロール・クロスリージョン推論・ウェアハウス
-- -----------------------------------------------
USE ROLE ACCOUNTADMIN;

-- 東京リージョンにないモデルを AI 関数から使えるようにする
ALTER ACCOUNT SET CORTEX_ENABLED_CROSS_REGION = 'ANY_REGION';

CREATE WAREHOUSE IF NOT EXISTS AI_HANDSON_WH
    WAREHOUSE_SIZE      = 'xsmall'
    WAREHOUSE_TYPE      = 'standard'
    AUTO_SUSPEND        = 60
    AUTO_RESUME         = TRUE
    INITIALLY_SUSPENDED = TRUE
    COMMENT             = 'ハンズオン用ウェアハウス';

USE WAREHOUSE AI_HANDSON_WH;

-- -----------------------------------------------
-- Step 2. データベース・スキーマ・ステージ
-- -----------------------------------------------
CREATE OR REPLACE DATABASE AI_HANDSON_DB
    COMMENT = 'ハンズオン用データベース';
CREATE OR REPLACE SCHEMA AI_HANDSON_DB.CRM
    COMMENT = '通販会社くらしモールの CRM データ（合成データ）';
USE SCHEMA AI_HANDSON_DB.CRM;

CREATE OR REPLACE STAGE DATA_STAGE
    ENCRYPTION = (TYPE = 'SNOWFLAKE_SSE')
    DIRECTORY  = (ENABLE = TRUE)
    COMMENT    = 'CSV・PDF 用ステージ';

-- -----------------------------------------------
-- Step 3. Git リポジトリからステージへファイルをコピー
-- -----------------------------------------------
-- CSV（8 ファイル）
COPY FILES INTO @DATA_STAGE
FROM @AI_HANDSON_GIT_DB.GIT.ai_handson_git_repo/branches/main/
PATTERN = 'data/csv/.*[.]csv';

-- PDF（返品申請書 10 件、商品仕様書 6 件）
COPY FILES INTO @DATA_STAGE
FROM @AI_HANDSON_GIT_DB.GIT.ai_handson_git_repo/branches/main/
PATTERN = 'data/pdf/.*[.]pdf';

ALTER STAGE DATA_STAGE REFRESH;

-- -----------------------------------------------
-- Step 4. ファイルフォーマット
--   問い合わせ本文は改行を含むため、ダブルクォートで囲まれた値の中の改行を許可する
-- -----------------------------------------------
CREATE OR REPLACE FILE FORMAT csv_format
    TYPE                         = 'CSV'
    SKIP_HEADER                  = 1
    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
    EMPTY_FIELD_AS_NULL          = TRUE
    COMMENT                      = 'ハンズオン資材の CSV 用';

-- -----------------------------------------------
-- Step 5. テーブル作成
--
-- ER 関係:
--   customers (1) --- (N) orders (1) --- (N) order_items (N) --- (1) products
--   customers (1) --- (N) inquiries / reviews / touchpoints
--   customers_import は外部リスト（customers と同じ人物が表記を変えて載っている）
-- -----------------------------------------------
CREATE OR REPLACE TABLE customers (
    customer_id   VARCHAR(10) PRIMARY KEY COMMENT '会員ID',
    name          VARCHAR(50)             COMMENT '氏名',
    name_kana     VARCHAR(50)             COMMENT '氏名（カナ）',
    email         VARCHAR(100)            COMMENT 'メールアドレス',
    prefecture    VARCHAR(10)             COMMENT '都道府県',
    address       VARCHAR(200)            COMMENT '住所',
    member_rank   VARCHAR(10)             COMMENT '会員ランク（ブロンズ/シルバー/ゴールド/プラチナ）',
    registered_on DATE                    COMMENT '会員登録日'
)
COMMENT = '会員マスタ';

CREATE OR REPLACE TABLE products (
    product_id   VARCHAR(10) PRIMARY KEY COMMENT '商品ID',
    product_name VARCHAR(100)            COMMENT '商品名',
    category     VARCHAR(20)             COMMENT '商品カテゴリ',
    price        NUMBER(10,0)            COMMENT '販売価格（円・税込）'
)
COMMENT = '商品マスタ';

CREATE OR REPLACE TABLE orders (
    order_id     VARCHAR(10) PRIMARY KEY COMMENT '注文番号',
    customer_id  VARCHAR(10)             COMMENT '会員ID',
    ordered_at   TIMESTAMP_NTZ           COMMENT '注文日時',
    channel      VARCHAR(10)             COMMENT '注文チャネル（Web/アプリ/電話）',
    total_amount NUMBER(12,0)            COMMENT '注文金額（円・税込）'
)
COMMENT = '注文';

CREATE OR REPLACE TABLE order_items (
    order_id   VARCHAR(10) COMMENT '注文番号',
    product_id VARCHAR(10) COMMENT '商品ID',
    quantity   NUMBER      COMMENT '数量'
)
COMMENT = '注文明細';

CREATE OR REPLACE TABLE inquiries (
    inquiry_id  VARCHAR(10) PRIMARY KEY COMMENT '問い合わせID',
    customer_id VARCHAR(10)             COMMENT '会員ID',
    order_id    VARCHAR(10)             COMMENT '注文番号（注文に関係しない問い合わせは NULL）',
    product_id  VARCHAR(10)             COMMENT '対象の商品ID（注文に関係しない問い合わせは NULL）',
    received_at TIMESTAMP_NTZ           COMMENT '受付日時',
    channel     VARCHAR(10)             COMMENT '受付チャネル（メール/チャット/電話）',
    body        VARCHAR                 COMMENT '問い合わせ本文（電話は受付メモ）。AI 関数の入力'
)
COMMENT = 'カスタマーサポートへの問い合わせ';

CREATE OR REPLACE TABLE inquiry_labels (
    inquiry_id VARCHAR(10) PRIMARY KEY COMMENT '問い合わせID',
    topic      VARCHAR(20)             COMMENT '問い合わせの種別（正解）',
    tone       VARCHAR(10)             COMMENT '本文の口調（正解）'
)
COMMENT = '問い合わせの種別と口調の正解。AI_CLASSIFY の答え合わせにだけ使う';

CREATE OR REPLACE TABLE reviews (
    review_id   VARCHAR(10) PRIMARY KEY COMMENT 'レビューID',
    customer_id VARCHAR(10)             COMMENT '会員ID',
    product_id  VARCHAR(10)             COMMENT '商品ID',
    rating      NUMBER(1,0)             COMMENT '評価（1〜5）',
    posted_at   TIMESTAMP_NTZ           COMMENT '投稿日時',
    body        VARCHAR                 COMMENT 'レビュー本文。AI 関数の入力'
)
COMMENT = '商品レビュー';

CREATE OR REPLACE TABLE touchpoints (
    touchpoint_id   VARCHAR(10) PRIMARY KEY COMMENT '接点ID',
    customer_id     VARCHAR(10)             COMMENT '会員ID',
    occurred_at     TIMESTAMP_NTZ           COMMENT '発生日時',
    touchpoint_type VARCHAR(20)             COMMENT '接点の種類（メール開封/サイト訪問/アプリ起動/クーポン利用/電話）'
)
COMMENT = '会員との接点履歴';

CREATE OR REPLACE TABLE customers_import (
    import_id        VARCHAR(10) PRIMARY KEY COMMENT '外部リストの行ID',
    name             VARCHAR(50)             COMMENT '氏名（表記揺れあり）',
    email            VARCHAR(100)            COMMENT 'メールアドレス（表記揺れあり）',
    address          VARCHAR(200)            COMMENT '住所（表記揺れあり）',
    source           VARCHAR(50)             COMMENT '入手元',
    true_customer_id VARCHAR(10)             COMMENT '正解の会員ID（結果の検証用。名寄せには使わない）'
)
COMMENT = 'AI_SIMILARITY（名寄せ）用の外部リスト。展示会の来場者リストを想定';

-- -----------------------------------------------
-- Step 6. データロード
-- -----------------------------------------------
COPY INTO customers        FROM @DATA_STAGE/data/csv/customers.csv        FILE_FORMAT = (FORMAT_NAME = csv_format);
COPY INTO products         FROM @DATA_STAGE/data/csv/products.csv         FILE_FORMAT = (FORMAT_NAME = csv_format);
COPY INTO orders           FROM @DATA_STAGE/data/csv/orders.csv           FILE_FORMAT = (FORMAT_NAME = csv_format);
COPY INTO order_items      FROM @DATA_STAGE/data/csv/order_items.csv      FILE_FORMAT = (FORMAT_NAME = csv_format);
COPY INTO reviews          FROM @DATA_STAGE/data/csv/reviews.csv          FILE_FORMAT = (FORMAT_NAME = csv_format);
COPY INTO touchpoints      FROM @DATA_STAGE/data/csv/touchpoints.csv      FILE_FORMAT = (FORMAT_NAME = csv_format);
COPY INTO customers_import FROM @DATA_STAGE/data/csv/customers_import.csv FILE_FORMAT = (FORMAT_NAME = csv_format);

-- inquiries.csv の列: inquiry_id, customer_id, order_id, product_id, received_at, channel, topic, tone, body
-- 正解の列（topic, tone）は inquiry_labels に分けて入れる
COPY INTO inquiries
FROM (SELECT $1, $2, $3, $4, $5, $6, $9 FROM @DATA_STAGE/data/csv/inquiries.csv)
FILE_FORMAT = (FORMAT_NAME = csv_format);

COPY INTO inquiry_labels
FROM (SELECT $1, $7, $8 FROM @DATA_STAGE/data/csv/inquiries.csv)
FILE_FORMAT = (FORMAT_NAME = csv_format);

-- -----------------------------------------------
-- Step 7. セットアップ確認（result と expected がすべて一致すれば完了）
-- -----------------------------------------------
SELECT 'customers'        AS check_item, COUNT(*)::VARCHAR AS result, '500'  AS expected FROM customers        UNION ALL
SELECT 'products',                       COUNT(*)::VARCHAR,           '30'               FROM products         UNION ALL
SELECT 'orders',                         COUNT(*)::VARCHAR,           '3000'             FROM orders           UNION ALL
SELECT 'order_items',                    COUNT(*)::VARCHAR,           '4935'             FROM order_items      UNION ALL
SELECT 'inquiries',                      COUNT(*)::VARCHAR,           '300'              FROM inquiries        UNION ALL
SELECT 'inquiry_labels',                 COUNT(*)::VARCHAR,           '300'              FROM inquiry_labels   UNION ALL
SELECT 'reviews',                        COUNT(*)::VARCHAR,           '300'              FROM reviews          UNION ALL
SELECT 'touchpoints',                    COUNT(*)::VARCHAR,           '4034'             FROM touchpoints      UNION ALL
SELECT 'customers_import',               COUNT(*)::VARCHAR,           '80'               FROM customers_import UNION ALL
SELECT 'inquiries.body_is_null',         COUNT_IF(body IS NULL)::VARCHAR, '0'            FROM inquiries        UNION ALL
SELECT 'stage:csv',                      COUNT_IF(relative_path LIKE '%.csv')::VARCHAR, '8'  FROM DIRECTORY(@DATA_STAGE) UNION ALL
SELECT 'stage:pdf',                      COUNT_IF(relative_path LIKE '%.pdf')::VARCHAR, '16' FROM DIRECTORY(@DATA_STAGE)
ORDER BY check_item;

-- =============================================================
-- クリーンアップはハンズオン終了後に cleanup.sql を実行してください
-- =============================================================
