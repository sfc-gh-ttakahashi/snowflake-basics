"""generate_structured の出力が仕様どおりかを確かめるテスト。"""

import re
from collections import Counter

import pytest

from scripts.generate.generate_structured import (
    COUNTS,
    DELAY_PRODUCT_ID,
    generate_all,
)


@pytest.fixture(scope="module")
def data():
    return generate_all(seed=42)


def test_件数が仕様どおり(data):
    for table, expected in COUNTS.items():
        assert len(data[table]) == expected, table


def test_同じシードなら同じデータになる():
    assert generate_all(seed=42) == generate_all(seed=42)


def test_主キーが一意(data):
    keys = {
        "customers": "customer_id",
        "products": "product_id",
        "orders": "order_id",
        "inquiries": "inquiry_id",
        "reviews": "review_id",
        "customers_import": "import_id",
    }
    for table, key in keys.items():
        values = [row[key] for row in data[table]]
        assert len(values) == len(set(values)), table


def test_外部キーが親テーブルに存在する(data):
    customer_ids = {r["customer_id"] for r in data["customers"]}
    product_ids = {r["product_id"] for r in data["products"]}
    order_ids = {r["order_id"] for r in data["orders"]}

    assert all(r["customer_id"] in customer_ids for r in data["orders"])
    assert all(r["order_id"] in order_ids for r in data["order_items"])
    assert all(r["product_id"] in product_ids for r in data["order_items"])
    assert all(r["customer_id"] in customer_ids for r in data["inquiries"])
    assert all(
        r["order_id"] is None or r["order_id"] in order_ids for r in data["inquiries"]
    )
    assert all(r["customer_id"] in customer_ids for r in data["reviews"])
    assert all(r["product_id"] in product_ids for r in data["reviews"])
    assert all(r["customer_id"] in customer_ids for r in data["touchpoints"])
    assert all(
        r["true_customer_id"] in customer_ids for r in data["customers_import"]
    )


def test_注文金額が明細の合計と一致する(data):
    prices = {r["product_id"]: r["price"] for r in data["products"]}
    totals = Counter()
    for item in data["order_items"]:
        totals[item["order_id"]] += prices[item["product_id"]] * item["quantity"]
    for order in data["orders"]:
        assert order["total_amount"] == totals[order["order_id"]]


def test_配送遅延の問い合わせが特定商品に偏っている(data):
    delay = [r for r in data["inquiries"] if r["topic"] == "配送"]
    share = sum(1 for r in delay if r["product_id"] == DELAY_PRODUCT_ID) / len(delay)
    assert share >= 0.3


def test_配送遅延の商品はレビュー評価が低い(data):
    target = [r["rating"] for r in data["reviews"] if r["product_id"] == DELAY_PRODUCT_ID]
    others = [r["rating"] for r in data["reviews"] if r["product_id"] != DELAY_PRODUCT_ID]
    assert sum(target) / len(target) < sum(others) / len(others) - 1.0


def test_離反の兆候がある上位会員は直近の接点が減っている(data):
    churn_ids = {r["customer_id"] for r in data["customers"] if r["churn_risk"]}
    assert churn_ids
    recent = [
        t for t in data["touchpoints"]
        if t["customer_id"] in churn_ids and t["occurred_at"] >= "2026-09-01"
    ]
    earlier = [
        t for t in data["touchpoints"]
        if t["customer_id"] in churn_ids and t["occurred_at"] < "2026-09-01"
    ]
    # 期間は直近 3 か月と、それより前の 9 か月。月あたりで比べる
    assert len(recent) / 3 < (len(earlier) / 9) * 0.5


def test_注文番号は数字の0と紛れない形式(data):
    # 英字 O で始めると、PDF や OCR で数字の 0 と読み違えるため ORD- を付ける
    assert all(re.fullmatch(r"ORD-\d{5}", r["order_id"]) for r in data["orders"])


def test_IDの順番が日時の順番と一致する(data):
    for table, key, ts in [
        ("orders", "order_id", "ordered_at"),
        ("inquiries", "inquiry_id", "received_at"),
        ("reviews", "review_id", "posted_at"),
        ("touchpoints", "touchpoint_id", "occurred_at"),
    ]:
        by_id = [r[ts] for r in sorted(data[table], key=lambda r: r[key])]
        assert by_id == sorted(by_id), table


def test_外部リストの全行に表記揺れがある(data):
    # 氏名・メール・住所のどれかが会員マスタと異なれば、揺れありとみなす
    exact = {(r["name"], r["email"], r["address"]) for r in data["customers"]}
    rows = data["customers_import"]
    unchanged = sum(1 for r in rows if (r["name"], r["email"], r["address"]) in exact)
    assert unchanged == 0
