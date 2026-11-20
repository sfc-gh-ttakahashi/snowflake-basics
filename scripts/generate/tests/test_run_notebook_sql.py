"""run_notebook_sql の、Snowflake に接続しない部分のテスト。"""

import pytest

from scripts.run_notebook_sql import select_cells, to_dev_sql


def test_本番用の名前を開発用に置き換える():
    sql = "USE DATABASE AI_HANDSON_DB; USE WAREHOUSE AI_HANDSON_WH;"
    assert to_dev_sql(sql, "COMPUTE_WH") == "USE DATABASE HANDSON_DEV_DB; USE WAREHOUSE COMPUTE_WH;"


def test_SQLセルがなければ失敗する():
    with pytest.raises(SystemExit, match="SQL セルがありません"):
        select_cells("# 見出しだけ\n", None)


def test_指定したセルから実行する():
    src = "```sql 1-1\nSELECT 1;\n```\n\n```sql 1-2\nSELECT 2;\n```\n"
    assert [c["name"] for c in select_cells(src, "SQL 1-2")] == ["SQL 1-2"]
