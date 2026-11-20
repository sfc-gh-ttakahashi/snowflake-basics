"""ノートブックが参照する画像が、リポジトリにあることのテスト。"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
IMAGE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)\)")
NOTEBOOKS = sorted((ROOT / "notebooks").glob("*.md"))


@pytest.mark.parametrize("md", NOTEBOOKS, ids=lambda p: p.name)
def test_referenced_images_exist(md: Path):
    # ノートブックはリポジトリの直下に置くため、画像のパスはリポジトリの直下から数える
    paths = [p for p in IMAGE.findall(md.read_text(encoding="utf-8")) if not p.startswith(("http://", "https://"))]
    missing = [p for p in paths if not (ROOT / p).is_file()]
    assert missing == []


def test_images_live_under_data_slides():
    paths = [p for md in NOTEBOOKS for p in IMAGE.findall(md.read_text(encoding="utf-8"))]
    assert paths, "画像を参照するノートブックがない"
    assert all(p.startswith("data/slides/") for p in paths)
