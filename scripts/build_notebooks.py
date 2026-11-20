"""notebooks/*.md を Snowflake ノートブック（.ipynb）に変換する。

Markdown の書き方:
- ```sql 2-1 のコードブロックが、名前 "SQL 2-1" の SQL セルになる
- ```sql 4-2 error は、エラーになるのが正しいセル（run_notebook_sql.py が失敗と扱わない）
- コードブロックの間の文章が、Markdown セルになる

使い方:
    uv run python -m scripts.build_notebooks
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "notebooks"
FENCE = re.compile(r"^```sql (\S+)( error)?\n(.*?)^```\n?", re.MULTILINE | re.DOTALL)


def parse_cells(text: str) -> list[dict]:
    cells, pos, names = [], 0, set()
    for m in FENCE.finditer(text):
        md = text[pos:m.start()].strip()
        if md:
            cells.append({"type": "markdown", "source": md})
        name = f"SQL {m.group(1)}"
        if name in names:
            raise ValueError(f"SQL セルの名前が重複しています: {name}")
        names.add(name)
        cells.append({"type": "sql", "name": name, "source": m.group(3).strip(),
                      "expect_error": bool(m.group(2))})
        pos = m.end()
    tail = text[pos:].strip()
    if tail:
        cells.append({"type": "markdown", "source": tail})
    return cells


def _cell_id(index: int, source: str) -> str:
    return hashlib.sha1(f"{index}:{source}".encode()).hexdigest()[:12]


def to_notebook(cells: list[dict]) -> dict:
    out = []
    for i, c in enumerate(cells):
        if c["type"] == "markdown":
            out.append({"cell_type": "markdown", "id": _cell_id(i, c["source"]),
                        "metadata": {"codeCollapsed": True, "collapsed": False}, "source": c["source"]})
        else:
            out.append({
                "cell_type": "code", "id": _cell_id(i, c["source"]), "execution_count": None, "outputs": [],
                "metadata": {"language": "sql", "name": c["name"], "title": c["name"],
                             "resultVariableName": c["name"].replace(" ", "_").replace("-", "_")},
                "source": c["source"],
            })
    return {"cells": out,
            "metadata": {"kernelspec": {"display_name": "Jupyter Notebook", "name": "jupyter"},
                         "language_info": {"name": "python"}},
            "nbformat": 4, "nbformat_minor": 5}


def main() -> None:
    for src in sorted(SRC_DIR.glob("part*.md")):
        nb = to_notebook(parse_cells(src.read_text(encoding="utf-8")))
        dest = ROOT / f"{src.stem}.ipynb"
        dest.write_text(json.dumps(nb, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{src.relative_to(ROOT)} -> {dest.name}（{len(nb['cells'])} セル）")


if __name__ == "__main__":
    main()
