"""dev_setup の setup.sql 書き換えのテスト。

書き換えが漏れると、デモアカウントの既存オブジェクトを上書きするおそれがあるため、
本番用の名前と危険な文が残らないことを確かめる。
"""

from pathlib import Path

from scripts.dev_setup import DEV_DB, to_dev_statements

SETUP_SQL = (Path(__file__).resolve().parents[3] / "setup.sql").read_text(encoding="utf-8")


def test_本番用のデータベース名が残らない():
    joined = "\n".join(to_dev_statements(SETUP_SQL, Path("/repo")))
    assert "AI_HANDSON_DB" not in joined
    assert DEV_DB in joined


def test_アカウント設定とウェアハウス作成とGit参照を外す():
    for stmt in to_dev_statements(SETUP_SQL, Path("/repo")):
        upper = stmt.upper()
        assert not upper.startswith("ALTER ACCOUNT")
        assert "CREATE WAREHOUSE" not in upper
        assert "AI_HANDSON_GIT_DB" not in upper
        assert "AI_HANDSON_WH" not in upper


def test_COPY_FILESをローカルファイルのPUTに置き換える():
    stmts = to_dev_statements(SETUP_SQL, Path("/repo"))
    puts = [s for s in stmts if s.startswith("PUT ")]
    assert puts == [
        "PUT 'file:///repo/data/csv/*.csv' @DATA_STAGE/data/csv/ AUTO_COMPRESS = FALSE OVERWRITE = TRUE",
        "PUT 'file:///repo/data/pdf/*.pdf' @DATA_STAGE/data/pdf/ AUTO_COMPRESS = FALSE OVERWRITE = TRUE",
    ]


def test_確認クエリが最後の文として残る():
    last = to_dev_statements(SETUP_SQL, Path("/repo"))[-1]
    assert last.startswith("SELECT 'customers'")
