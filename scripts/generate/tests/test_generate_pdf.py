"""generate_pdf のテスト。"""

from scripts.generate.generate_pdf import (
    SPEC_PRODUCT_IDS,
    build_return_forms,
    write_all,
)

CUSTOMERS = [{"customer_id": "C0001", "name": "佐藤 美咲", "address": "東京都世田谷区1-2-3"}]
PRODUCTS = [{"product_id": "P012", "product_name": "低反発マットレス シングル", "price": "39800", "category": "寝具"}]
ORDERS = [{"order_id": "ORD-00001", "customer_id": "C0001", "ordered_at": "2026-01-05 10:00:00"}]
ITEMS = [{"order_id": "ORD-00001", "product_id": "P012", "quantity": "1"}]


def _inquiry(i, topic="返品・交換", order_id="ORD-00001"):
    return {"inquiry_id": f"Q{i:04d}", "customer_id": "C0001", "order_id": order_id,
            "product_id": "P012" if order_id else "", "received_at": f"2026-01-{10 + i:02d} 09:00:00",
            "topic": topic, "body": "サイズが合わないので返品したいです。"}


def test_返品申請書は返品交換の問い合わせから作る():
    inquiries = [_inquiry(1), _inquiry(2, topic="配送"), _inquiry(3, order_id="")]
    forms = build_return_forms(inquiries, ORDERS, ITEMS, CUSTOMERS, PRODUCTS, limit=10)
    assert [f["inquiry_id"] for f in forms] == ["Q0001"]


def test_返品申請書の項目が元データと一致する():
    form = build_return_forms([_inquiry(1)], ORDERS, ITEMS, CUSTOMERS, PRODUCTS, limit=10)[0]
    assert form["order_id"] == "ORD-00001"
    assert form["customer_name"] == "佐藤 美咲"
    assert form["product_name"] == "低反発マットレス シングル"
    assert form["quantity"] == "1"
    assert form["applied_on"] == "2026-01-11"
    assert form["request"] in ("返金", "交換")


def test_返品申請書は件数の上限を守る():
    inquiries = [_inquiry(i) for i in range(1, 15)]
    assert len(build_return_forms(inquiries, ORDERS, ITEMS, CUSTOMERS, PRODUCTS, limit=10)) == 10


def test_配送遅延の商品の仕様書を作る():
    assert "P012" in SPEC_PRODUCT_IDS


def test_PDFファイルを書き出す(tmp_path):
    forms = build_return_forms([_inquiry(1)], ORDERS, ITEMS, CUSTOMERS, PRODUCTS, limit=10)
    paths = write_all(tmp_path, forms, PRODUCTS, spec_ids=["P012"])
    names = sorted(p.name for p in paths)
    assert names == ["return_Q0001.pdf", "spec_P012.pdf"]
    for p in paths:
        assert p.read_bytes().startswith(b"%PDF")
