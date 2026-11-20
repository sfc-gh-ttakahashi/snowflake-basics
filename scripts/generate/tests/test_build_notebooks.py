"""build_notebooks（Markdown → .ipynb 変換）のテスト。"""

from scripts.build_notebooks import parse_cells, to_notebook

SRC = """# Part 2 : 基礎

説明の文章。

```sql 0-1
USE ROLE ACCOUNTADMIN;
```

---
## 1. 見出し

```sql 1-1
SELECT 1;
```

```sql 1-2 error
SELECT * FROM no_such_table;
```
"""


def test_文章とSQLをセルに分ける():
    cells = parse_cells(SRC)
    assert [(c["type"], c.get("name")) for c in cells] == [
        ("markdown", None), ("sql", "SQL 0-1"), ("markdown", None), ("sql", "SQL 1-1"), ("sql", "SQL 1-2"),
    ]
    assert cells[0]["source"] == "# Part 2 : 基礎\n\n説明の文章。"
    assert cells[2]["source"] == "---\n## 1. 見出し"
    assert cells[3]["source"] == "SELECT 1;"


def test_エラーになるのが正しいセルに印を付ける():
    cells = parse_cells(SRC)
    assert cells[4]["expect_error"] is True
    assert cells[3]["expect_error"] is False


def test_Snowflakeノートブックの形式で出力する():
    nb = to_notebook(parse_cells(SRC))
    assert nb["nbformat"] == 4
    sql = nb["cells"][1]
    assert sql["cell_type"] == "code"
    assert sql["metadata"] == {"language": "sql", "name": "SQL 0-1", "title": "SQL 0-1",
                               "resultVariableName": "SQL_0_1"}
    assert sql["source"] == "USE ROLE ACCOUNTADMIN;"
    assert nb["cells"][0]["cell_type"] == "markdown"
    # セル ID は内容から決め、変換し直しても差分が出ないようにする
    assert to_notebook(parse_cells(SRC)) == nb


def test_SQLセルの名前が重複したら失敗する():
    try:
        parse_cells("```sql 1-1\nSELECT 1;\n```\n\n```sql 1-1\nSELECT 2;\n```\n")
    except ValueError as e:
        assert "SQL 1-1" in str(e)
    else:
        raise AssertionError("ValueError が出なかった")
