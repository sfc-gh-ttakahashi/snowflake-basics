-- =============================================================
-- cleanup.sql - ハンズオン環境のクリーンアップ
--
-- Part 1〜4 で作成したオブジェクトをまとめて削除します。
-- ハンズオンの終了後に実行してください。
-- 最後に AI_HANDSON_DB をデータベースごと削除するため、Part ごとの DROP を
-- 実行しなくても、データベースの中のオブジェクトはすべて消えます。
-- =============================================================
USE ROLE ACCOUNTADMIN;

-- -----------------------------------------------
-- Part 1 で作成したオブジェクト
--   CoCo の「テストデータ生成」で作ったテーブルは、名前が人によって異なります。
--   create_campaign_data.sql の末尾の DROP TABLE を実行するか、
--   作成したテーブル名に合わせて、下のコメントを外して実行してください。
-- -----------------------------------------------
-- DROP TABLE IF EXISTS AI_HANDSON_DB.CRM.campaigns;
-- DROP TABLE IF EXISTS AI_HANDSON_DB.CRM.campaign_deliveries;

-- -----------------------------------------------
-- Part 2 で作成したオブジェクト
-- -----------------------------------------------
DROP DYNAMIC TABLE IF EXISTS AI_HANDSON_DB.CRM.DT_MONTHLY_CATEGORY_SALES;
DROP DYNAMIC TABLE IF EXISTS AI_HANDSON_DB.CRM.DT_ORDER_LINES;
DROP TABLE IF EXISTS AI_HANDSON_DB.CRM.customers_dev;
DROP WAREHOUSE IF EXISTS AI_HANDSON_ADAPTIVE_WH;

-- -----------------------------------------------
-- Part 3-2 で作成したオブジェクト
--   Pipeline Builder のタスク・タスクグラフ・DCM プロジェクトは、AI_HANDSON_DB.CRM に作られます。
--   名前は画面で決めるため、ここでは個別に削除せず、下の DROP DATABASE でまとめて削除します。
--   ワークスペースの crm_ai_pipeline フォルダは、ワークスペースから手動で削除してください。
-- -----------------------------------------------
DROP TABLE IF EXISTS AI_HANDSON_DB.CRM.AI_PRODUCT_INSIGHTS;
DROP TABLE IF EXISTS AI_HANDSON_DB.CRM.AI_PRODUCT_REVIEW_SUMMARY;
DROP TABLE IF EXISTS AI_HANDSON_DB.CRM.AI_RETURN_FORMS;
DROP TABLE IF EXISTS AI_HANDSON_DB.CRM.AI_REVIEW_SENTIMENT;
DROP TABLE IF EXISTS AI_HANDSON_DB.CRM.AI_INQUIRY_TOPICS;

-- -----------------------------------------------
-- Part 4 で作成したオブジェクト
--   Streamlit アプリ（inquiry_app）は、下の DROP DATABASE で削除されます。
--   ダッシュボード（.dash）と HTML レポート（.html）のファイルは、ワークスペースから手動で削除してください。
--   公開したアーティファクトは、Snowsight 左メニュー Projects → Artifacts から削除してください。
-- -----------------------------------------------
DROP STREAMLIT IF EXISTS AI_HANDSON_DB.CRM.INQUIRY_APP;

-- -----------------------------------------------
-- setup.sql で作成した共通オブジェクト
-- -----------------------------------------------
DROP DATABASE IF EXISTS AI_HANDSON_DB;
DROP WAREHOUSE IF EXISTS AI_HANDSON_WH;

-- -----------------------------------------------
-- Git 連携のオブジェクト（load.sql で作成）
--   ワークスペースの Git 連携に使っているため、ここでは削除しません。
--   削除するときは、先にワークスペースを削除してから、下のコメントを外して実行してください。
-- -----------------------------------------------
-- DROP DATABASE IF EXISTS AI_HANDSON_GIT_DB;
-- DROP API INTEGRATION IF EXISTS ai_handson_git_integration;
