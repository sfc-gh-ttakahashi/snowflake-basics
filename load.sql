-- =============================================================
-- load.sql - GitHub のハンズオン資材を Snowflake から参照できるようにする
-- 参照リポジトリ: https://github.com/sfc-gh-ttakahashi/snowflake-basics
--
-- ここで作る Git リポジトリは、ワークスペースの Git 連携と setup.sql の
-- COPY FILES の両方で使います。
-- =============================================================
USE ROLE ACCOUNTADMIN;

CREATE DATABASE IF NOT EXISTS AI_HANDSON_GIT_DB
    COMMENT = 'ハンズオン資材の Git リポジトリを置くデータベース';
CREATE SCHEMA IF NOT EXISTS AI_HANDSON_GIT_DB.GIT
    COMMENT = 'ハンズオン資材の Git リポジトリを置くスキーマ';
USE SCHEMA AI_HANDSON_GIT_DB.GIT;

CREATE OR REPLACE API INTEGRATION ai_handson_git_integration
    API_PROVIDER         = git_https_api
    API_ALLOWED_PREFIXES = ('https://github.com/sfc-gh-ttakahashi/')
    ENABLED              = TRUE
    COMMENT              = 'ハンズオン資材の GitHub リポジトリ（公開・認証なし）への接続';

CREATE OR REPLACE GIT REPOSITORY ai_handson_git_repo
    API_INTEGRATION = ai_handson_git_integration
    ORIGIN          = 'https://github.com/sfc-gh-ttakahashi/snowflake-basics.git'
    COMMENT         = 'ハンズオン資材（SQL・ノートブック・データ）';

ALTER GIT REPOSITORY ai_handson_git_repo FETCH;
