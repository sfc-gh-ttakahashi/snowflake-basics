"""notebooks/<part>.md の SQL セルを、開発用データベースで上から順に実行する（資材作成者向け）。

置き換える名前:
- AI_HANDSON_DB → HANDSON_DEV_DB（dev_setup.py で作ったもの）
- AI_HANDSON_WH → --warehouse で指定したウェアハウス

```sql N-M error のセルは、エラーになることを確かめる（成功したら失敗として報告する）。

使い方:
    uv run python -m scripts.run_notebook_sql --connection SFSEAPAC-TTAKAHASHI_AWS1 part2_snowflake_basics
    uv run python -m scripts.run_notebook_sql --connection ... part3_cortex_ai_functions --from "SQL 3-1"
"""

from __future__ import annotations

import argparse
import sys

from scripts.build_notebooks import SRC_DIR, parse_cells
from scripts.dev_setup import DEV_DB


def to_dev_sql(sql: str, warehouse: str) -> str:
    return sql.replace("AI_HANDSON_DB", DEV_DB).replace("AI_HANDSON_WH", warehouse)


def select_cells(markdown: str, start: str | None) -> list[dict]:
    """Markdown から SQL セルを取り出す。SQL セルが 1 つもなければ終了する（空のファイルを成功と誤報しないため）。"""
    cells = [c for c in parse_cells(markdown) if c["type"] == "sql"]
    if not cells:
        raise SystemExit("SQL セルがありません。Markdown の中身を確かめてください")
    if start:
        names = [c["name"] for c in cells]
        cells = cells[names.index(start):]
    return cells


def main() -> None:
    import snowflake.connector

    from scripts.generate.generate_text import connection_params

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--connection", required=True)
    parser.add_argument("--warehouse", default="COMPUTE_WH")
    parser.add_argument("--from", dest="start", help="このセルから実行する（例: 'SQL 3-1'）")
    parser.add_argument("notebook", help="notebooks/ の中のファイル名（拡張子なし）")
    args = parser.parse_args()

    cells = select_cells((SRC_DIR / f"{args.notebook}.md").read_text(encoding="utf-8"), args.start)

    failures = []
    with snowflake.connector.connect(**{**connection_params(args.connection), "warehouse": args.warehouse}) as conn:
        conn.cursor().execute(f"USE SCHEMA {DEV_DB}.CRM")
        for c in cells:
            try:
                cursors = conn.execute_string(to_dev_sql(c["source"], args.warehouse), remove_comments=True)
                rows = cursors[-1].fetchall() if cursors and cursors[-1].description else []
                status = "NG（エラーになるはず）" if c["expect_error"] else "OK"
                if c["expect_error"]:
                    failures.append(c["name"])
                print(f"[{status}] {c['name']}: {len(rows)} 行")
                for row in rows[:3]:
                    print("    ", str(row)[:200])
            except snowflake.connector.errors.ProgrammingError as e:
                if c["expect_error"]:
                    print(f"[OK（想定どおりのエラー）] {c['name']}: {str(e.msg)[:120]}")
                else:
                    print(f"[NG] {c['name']}: {str(e.msg)[:300]}")
                    failures.append(c["name"])
    if failures:
        print(f"\n失敗したセル: {', '.join(failures)}")
        sys.exit(1)
    print(f"\n{len(cells)} セルすべてが想定どおりに動きました")


if __name__ == "__main__":
    main()
