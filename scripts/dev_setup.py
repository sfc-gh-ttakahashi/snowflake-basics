"""setup.sql を開発用のデータベースで動かす（資材作成者向け。参加者は使わない）。

setup.sql は GitHub のリポジトリからファイルをコピーするため、push 前には動かせない。
このスクリプトは setup.sql を読み、次の点だけを書き換えて実行する。

- データベース名 AI_HANDSON_DB → HANDSON_DEV_DB
- ALTER ACCOUNT・CREATE WAREHOUSE を外し、既存のウェアハウスを使う
- Git リポジトリからの COPY FILES を、ローカルファイルの PUT に置き換える

使い方:
    uv run python -m scripts.dev_setup --connection SFSEAPAC-TTAKAHASHI_AWS1
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEV_DB = "HANDSON_DEV_DB"


def split_statements(sql: str) -> list[str]:
    """コメント行を除き、セミコロンで文に分ける（setup.sql は文字列中にセミコロンを含まない）。"""
    body = "\n".join(line for line in sql.splitlines() if not line.lstrip().startswith("--"))
    return [s.strip() for s in body.split(";") if s.strip()]


def to_dev_statements(sql: str, root: Path) -> list[str]:
    out = []
    for stmt in split_statements(sql):
        upper = stmt.upper()
        if upper.startswith(("ALTER ACCOUNT", "CREATE WAREHOUSE", "USE WAREHOUSE")):
            continue
        if upper.startswith("COPY FILES"):
            m = re.search(r"PATTERN = '(data/\w+)/\.\*\[\.\](\w+)'", stmt)
            folder, ext = m.group(1), m.group(2)
            out.append(f"PUT 'file://{root}/{folder}/*.{ext}' @DATA_STAGE/{folder}/ "
                       "AUTO_COMPRESS = FALSE OVERWRITE = TRUE")
            continue
        out.append(stmt.replace("AI_HANDSON_DB", DEV_DB))
    return out


def main() -> None:
    import snowflake.connector

    from scripts.generate.generate_text import connection_params

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--connection", required=True)
    parser.add_argument("--warehouse", default="COMPUTE_WH")
    args = parser.parse_args()

    stmts = to_dev_statements((ROOT / "setup.sql").read_text(encoding="utf-8"), ROOT)
    with snowflake.connector.connect(**{**connection_params(args.connection), "warehouse": args.warehouse}) as conn:
        cur = conn.cursor()
        for stmt in stmts:
            print(f"-- {stmt.splitlines()[0][:80]}")
            cur.execute(stmt)
        print(f"\n{'check_item':<24}{'result':>8}{'expected':>10}")
        for item, result, expected in cur.fetchall():
            mark = "" if result == expected else "  <-- 不一致"
            print(f"{item:<24}{result:>8}{expected:>10}{mark}")


if __name__ == "__main__":
    main()
