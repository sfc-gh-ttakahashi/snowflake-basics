"""pipeline/*.sql を、開発用データベースでファイル名の順に実行する（資材作成者向け）。

Pipeline Builder のタスクグラフと同じ順番で実行し、結果のテーブルの件数を表示する。
2 回続けて実行すると、未処理の行だけに AI 関数を呼ぶ作りになっているか（件数が増えないか）を確かめられる。

使い方:
    uv run python -m scripts.run_pipeline_sql --connection SFSEAPAC-TTAKAHASHI_AWS1
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from scripts.dev_setup import DEV_DB
from scripts.run_notebook_sql import to_dev_sql

ROOT = Path(__file__).resolve().parents[1]
PIPELINE_DIR = ROOT / "pipeline"
RESULT_TABLES = ["AI_INQUIRY_TOPICS", "AI_REVIEW_SENTIMENT", "AI_RETURN_FORMS",
                 "AI_PRODUCT_REVIEW_SUMMARY", "AI_PRODUCT_INSIGHTS"]


def main() -> None:
    import snowflake.connector

    from scripts.generate.generate_text import connection_params

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--connection", required=True)
    parser.add_argument("--warehouse", default="COMPUTE_WH")
    args = parser.parse_args()

    files = sorted(PIPELINE_DIR.glob("*.sql"))
    if not files:
        raise SystemExit("pipeline/ に SQL ファイルがありません")
    with snowflake.connector.connect(**{**connection_params(args.connection), "warehouse": args.warehouse}) as conn:
        for path in files:
            start = time.monotonic()
            conn.execute_string(to_dev_sql(path.read_text(encoding="utf-8"), args.warehouse), remove_comments=True)
            print(f"{path.name}: {time.monotonic() - start:.1f} 秒")
        cur = conn.cursor()
        for table in RESULT_TABLES:
            cur.execute(f"SELECT COUNT(*) FROM {DEV_DB}.CRM.{table}")
            print(f"  {table}: {cur.fetchone()[0]} 行")


if __name__ == "__main__":
    main()
