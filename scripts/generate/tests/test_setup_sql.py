"""setup.sql の件数確認の期待値が、data/ の実ファイルと一致するかを確かめるテスト。"""

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SETUP_SQL = (ROOT / "setup.sql").read_text(encoding="utf-8")
# 例: SELECT 'orders', COUNT(*)::VARCHAR, '3000' FROM orders
COUNT_CHECK = re.compile(r"SELECT '(\w+)'\s*(?:AS check_item)?,\s*COUNT\(\*\)::VARCHAR\s*(?:AS result)?,\s*'(\d+)'")


def _csv_rows(name: str) -> int:
    with (ROOT / "data" / "csv" / f"{name}.csv").open(encoding="utf-8", newline="") as f:
        return sum(1 for _ in csv.DictReader(f))


def test_テーブル件数の期待値がCSVの行数と一致する():
    checks = dict(COUNT_CHECK.findall(SETUP_SQL))
    assert len(checks) == 9, checks
    for table, expected in checks.items():
        source = "inquiries" if table == "inquiry_labels" else table
        assert int(expected) == _csv_rows(source), table


def test_ステージのファイル数の期待値が実ファイル数と一致する():
    expected = dict(re.findall(r"SELECT 'stage:(\w+)'.*?'(\d+)'\s+FROM DIRECTORY", SETUP_SQL))
    assert int(expected["csv"]) == len(list((ROOT / "data" / "csv").glob("*.csv")))
    assert int(expected["pdf"]) == len(list((ROOT / "data" / "pdf").glob("*.pdf")))
