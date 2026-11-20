"""返品申請書と商品仕様書の PDF を生成する（AI_EXTRACT の題材）。

返品申請書は inquiries.csv の「返品・交換」の問い合わせから作るため、
PDF の中身（注文番号・氏名・商品）が CSV のデータと一致する。

使い方:
    uv run python -m scripts.generate.generate_pdf
"""

from __future__ import annotations

import csv
import hashlib
import os
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[2]
CSV_DIR = ROOT / "data" / "csv"
PDF_DIR = ROOT / "data" / "pdf"
COMPANY = "くらしモール株式会社"  # 架空の通販会社

# 日本語の TrueType フォントを PDF に埋め込む。CID フォントは埋め込まれず、表示する側に
# フォントがないと文字が消えるため使わない。既定は UDEV Gothic（SIL Open Font License）
FONT_PATH = Path(os.environ.get(
    "HANDSON_PDF_FONT",
    Path.home() / ".nix-profile/share/fonts/truetype/UDEVGothicNF-Regular.ttf",
))
if not FONT_PATH.exists():
    raise SystemExit(f"日本語フォントがありません: {FONT_PATH}（環境変数 HANDSON_PDF_FONT で .ttf を指定してください）")
FONT = "HandsonJP"
pdfmetrics.registerFont(TTFont(FONT, str(FONT_PATH)))
TITLE = ParagraphStyle("title", fontName=FONT, fontSize=16, leading=22, spaceAfter=6)
BODY = ParagraphStyle("body", fontName=FONT, fontSize=10, leading=15)
SMALL = ParagraphStyle("small", fontName=FONT, fontSize=8, leading=12, textColor=colors.grey)

# 商品仕様書を作る商品と、その仕様。P012 は受注生産で出荷が遅いことを仕様書に書いておく
SPECS = {
    "P012": {
        "サイズ": "幅 97cm × 長さ 195cm × 厚さ 8cm",
        "素材": "ウレタンフォーム（低反発）、カバー: ポリエステル 100%",
        "重量": "約 6.5kg",
        "生産": "国内工場での受注生産",
        "出荷の目安": "ご注文から 10〜14 営業日（受注生産のため）",
        "保証": "購入日から 1 年間（へたりが 2cm を超えた場合）",
        "お手入れ": "カバーは洗濯機で洗えます。本体は陰干ししてください",
    },
    "P001": {
        "容量": "1.0L",
        "消費電力": "1200W",
        "サイズ": "幅 22cm × 奥行 15cm × 高さ 21cm",
        "重量": "約 1.1kg",
        "出荷の目安": "ご注文から 1〜2 営業日",
        "保証": "購入日から 1 年間",
        "安全機能": "空だき防止、自動電源オフ",
    },
    "P003": {
        "抽出方式": "ミル付き全自動（豆・粉の両対応）",
        "容量": "最大 5 杯（0.75L）",
        "消費電力": "650W",
        "重量": "約 3.2kg",
        "出荷の目安": "ご注文から 1〜2 営業日",
        "保証": "購入日から 1 年間",
    },
    "P011": {
        "サイズ": "150cm × 210cm",
        "中わた": "ホワイトダックダウン 85%、フェザー 15%（1.2kg）",
        "側生地": "綿 100%",
        "出荷の目安": "ご注文から 2〜3 営業日",
        "保証": "購入日から 1 年間",
        "お手入れ": "家庭での洗濯はできません。専門のクリーニングに出してください",
    },
    "P015": {
        "連続再生時間": "最大 8 時間（ケース併用で 32 時間）",
        "接続": "Bluetooth 5.3",
        "防水": "IPX4",
        "対応機種": "iOS 15 以降、Android 10 以降",
        "出荷の目安": "ご注文から 1〜2 営業日",
        "保証": "購入日から 1 年間",
    },
    "P017": {
        "画面": "1.4 インチ AMOLED",
        "電池の持ち": "通常使用で最大 10 日",
        "防水": "5ATM",
        "対応機種": "iOS 15 以降、Android 10 以降",
        "出荷の目安": "ご注文から 1〜2 営業日",
        "保証": "購入日から 1 年間",
    },
}
SPEC_PRODUCT_IDS = list(SPECS)


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def build_return_forms(inquiries, orders, items, customers, products, limit: int = 10) -> list[dict]:
    """「返品・交換」の問い合わせのうち、注文のあるものから返品申請書の項目を作る。"""
    customer = {c["customer_id"]: c for c in customers}
    product = {p["product_id"]: p for p in products}
    qty = {(i["order_id"], i["product_id"]): i["quantity"] for i in items}
    forms = []
    for q in inquiries:
        if q["topic"] != "返品・交換" or not q["order_id"]:
            continue
        c = customer[q["customer_id"]]
        # 希望（返金・交換）は問い合わせ ID から決める。乱数を使わないので毎回同じになる
        digest = int(hashlib.sha256(q["inquiry_id"].encode()).hexdigest(), 16)
        forms.append({
            "inquiry_id": q["inquiry_id"],
            "form_no": f"RTN-{q['inquiry_id'][1:]}",
            "applied_on": q["received_at"][:10],
            "order_id": q["order_id"],
            "customer_name": c["name"],
            "address": c["address"],
            "product_name": product[q["product_id"]]["product_name"],
            "quantity": qty[(q["order_id"], q["product_id"])],
            "request": "交換" if digest % 3 == 0 else "返金",
            "reason": q["body"],
        })
        if len(forms) == limit:
            break
    return forms


def _table(rows: list[tuple[str, str]], first_col: float = 40 * mm) -> Table:
    data = [[Paragraph(escape(k), BODY), Paragraph(escape(str(v)).replace("\n", "<br/>"), BODY)] for k, v in rows]
    t = Table(data, colWidths=[first_col, 170 * mm - first_col])
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return t


def write_return_form(form: dict, path: Path) -> None:
    doc = SimpleDocTemplate(str(path), pagesize=A4, title=f"返品・交換申請書 {form['form_no']}")
    story = [
        Paragraph("返品・交換申請書", TITLE),
        Paragraph(f"{COMPANY} カスタマーサポート 御中", BODY),
        Spacer(1, 6 * mm),
        _table([
            ("申請番号", form["form_no"]),
            ("申請日", form["applied_on"]),
            ("注文番号", form["order_id"]),
            ("お名前", form["customer_name"]),
            ("ご住所", form["address"]),
            ("商品名", form["product_name"]),
            ("数量", form["quantity"]),
            ("ご希望", form["request"]),
            ("返品・交換の理由", form["reason"]),
        ]),
        Spacer(1, 6 * mm),
        Paragraph("※ 商品到着から 30 日以内にお送りください。返送料は初期不良の場合のみ当社が負担します。", SMALL),
        Paragraph("※ この申請書はハンズオン用の架空のデータです。", SMALL),
    ]
    doc.build(story)


def write_spec(product: dict, spec: dict, path: Path) -> None:
    doc = SimpleDocTemplate(str(path), pagesize=A4, title=f"商品仕様書 {product['product_id']}")
    story = [
        Paragraph("商品仕様書", TITLE),
        Paragraph(f"{COMPANY}", BODY),
        Spacer(1, 6 * mm),
        _table([
            ("商品 ID", product["product_id"]),
            ("商品名", product["product_name"]),
            ("カテゴリ", product["category"]),
            ("販売価格", f"{int(product['price']):,} 円（税込）"),
            *spec.items(),
        ]),
        Spacer(1, 6 * mm),
        Paragraph("※ この仕様書はハンズオン用の架空のデータです。", SMALL),
    ]
    doc.build(story)


def write_all(out_dir: Path, forms: list[dict], products: list[dict], spec_ids=SPEC_PRODUCT_IDS) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    product = {p["product_id"]: p for p in products}
    paths = []
    for form in forms:
        path = out_dir / f"return_{form['inquiry_id']}.pdf"
        write_return_form(form, path)
        paths.append(path)
    for pid in spec_ids:
        path = out_dir / f"spec_{pid}.pdf"
        write_spec(product[pid], SPECS[pid], path)
        paths.append(path)
    return paths


def main() -> None:
    forms = build_return_forms(
        read_csv(CSV_DIR / "inquiries.csv"), read_csv(CSV_DIR / "orders.csv"),
        read_csv(CSV_DIR / "order_items.csv"), read_csv(CSV_DIR / "customers.csv"),
        read_csv(CSV_DIR / "products.csv"),
    )
    for p in write_all(PDF_DIR, forms, read_csv(CSV_DIR / "products.csv")):
        print(p.relative_to(ROOT))


if __name__ == "__main__":
    main()
