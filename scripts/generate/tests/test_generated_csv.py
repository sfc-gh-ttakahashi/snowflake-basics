"""data/csv/ に置いた生成済み CSV の品質を確かめるテスト。

本文を AI_COMPLETE で作り直したときに、空の本文・前置き・注文番号の欠落が
紛れ込んでいないかを検出する。
"""

import csv
import re
from pathlib import Path

import pytest

CSV_DIR = Path(__file__).resolve().parents[3] / "data" / "csv"
# メールの「件名:」の行は実際のメールにもあるので、前置きとは扱わない
PREFACE = re.compile(r"^(以下|こちら|承知|はい[、。])")


def _read(name: str) -> list[dict]:
    with (CSV_DIR / name).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope="module")
def inquiries():
    return _read("inquiries.csv")


@pytest.fixture(scope="module")
def reviews():
    return _read("reviews.csv")


@pytest.mark.parametrize("name", ["inquiries.csv", "reviews.csv"])
def test_本文が空でなく長さが範囲内(name):
    for r in _read(name):
        assert 20 <= len(r["body"]) <= 400, (r, len(r["body"]))


@pytest.mark.parametrize("name", ["inquiries.csv", "reviews.csv"])
def test_本文に前置きや見出しがない(name):
    bad = [r[next(iter(r))] for r in _read(name) if PREFACE.match(r["body"])]
    assert not bad, bad[:10]


def test_注文のある問い合わせは本文に注文番号を含む(inquiries):
    missing = [r["inquiry_id"] for r in inquiries if r["order_id"] and r["order_id"] not in r["body"]]
    assert len(missing) <= len(inquiries) * 0.05, missing[:10]


def test_注文のない問い合わせは本文に注文番号を含まない(inquiries):
    stray = [r["inquiry_id"] for r in inquiries if not r["order_id"] and re.search(r"O\d{5}", r["body"])]
    assert not stray, stray


def test_レビュー本文に星の記号がない(reviews):
    assert not [r["review_id"] for r in reviews if "★" in r["body"] or "☆" in r["body"]]
