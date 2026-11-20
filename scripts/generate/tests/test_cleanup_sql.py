"""cleanup.sql が、ノートブックとパイプラインで作るオブジェクトをすべて削除するかを確かめるテスト。

DROP ... IF EXISTS は名前を打ち間違えてもエラーにならないため、作る側の名前と照合する。
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CLEANUP = (ROOT / "cleanup.sql").read_text(encoding="utf-8")
CREATE = re.compile(
    r"CREATE (?:OR REPLACE )?(?:ADAPTIVE )?(DYNAMIC TABLE|TABLE|WAREHOUSE)(?: IF NOT EXISTS)?\s+([\w.]+)",
    re.IGNORECASE,
)


def _active_lines(sql: str) -> str:
    return "\n".join(line for line in sql.splitlines() if not line.lstrip().startswith("--"))


def _dropped() -> set[str]:
    names = re.findall(r"DROP [A-Z ]+? IF EXISTS\s+([\w.]+)", _active_lines(CLEANUP), re.IGNORECASE)
    return {n.split(".")[-1].upper() for n in names}


def _created(paths) -> set[str]:
    found = set()
    for path in paths:
        for _, name in CREATE.findall(_active_lines(path.read_text(encoding="utf-8"))):
            found.add(name.split(".")[-1].upper())
    return found


def test_ノートブックとパイプラインで作るオブジェクトをすべて削除する():
    sources = [*sorted((ROOT / "notebooks").glob("part*.md")), *sorted((ROOT / "pipeline").glob("*.sql"))]
    created = _created(sources)
    assert created, "作成するオブジェクトが見つからない"
    missing = created - _dropped()
    assert not missing, f"cleanup.sql で削除していない: {sorted(missing)}"


def test_共通のデータベースとウェアハウスを削除する():
    dropped = _dropped()
    assert {"AI_HANDSON_DB", "AI_HANDSON_WH"} <= dropped


def test_Git連携のオブジェクトは削除しない():
    # ワークスペースの Git 連携に使うため、コメントアウトのまま残す
    assert "AI_HANDSON_GIT_DB" not in _dropped()
