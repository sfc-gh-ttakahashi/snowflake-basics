"""B2C 通販の CRM 合成データ（構造化部分）を生成する。

問い合わせ・レビューの本文はここでは作らない。本文の生成に使う属性
（topic・tone など）だけを持たせ、generate_text.py が AI_COMPLETE で本文を付ける。

使い方:
    uv run python -m scripts.generate.generate_structured
"""

from __future__ import annotations

import csv
import random
from datetime import date, datetime, timedelta
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parents[2] / "data" / "csv"

PERIOD_START = date(2025, 12, 1)
PERIOD_END = date(2026, 11, 30)
RECENT_START = date(2026, 9, 1)

COUNTS = {
    "customers": 500,
    "customers_import": 80,
    "products": 30,
    "orders": 3000,
    "inquiries": 300,
    "reviews": 300,
}

# 配送遅延の問い合わせと低評価のレビューが集まる商品
DELAY_PRODUCT_ID = "P012"

PRODUCTS = [
    # (商品名, カテゴリ, 価格)
    ("北欧デザイン 電気ケトル 1.0L", "キッチン家電", 6980),
    ("ステンレス ハンドブレンダー", "キッチン家電", 8980),
    ("全自動コーヒーメーカー", "キッチン家電", 19800),
    ("ノンフライヤー 4.2L", "キッチン家電", 14800),
    ("電気圧力鍋 3L", "キッチン家電", 16500),
    ("今治タオル バスタオル 2枚組", "生活雑貨", 4400),
    ("珪藻土バスマット", "生活雑貨", 3300),
    ("竹製 まな板セット", "生活雑貨", 2980),
    ("アロマディフューザー", "生活雑貨", 5480),
    ("折りたたみ 収納ボックス 3個組", "生活雑貨", 3980),
    ("羽毛布団 シングル", "寝具", 29800),
    ("低反発マットレス シングル", "寝具", 39800),
    ("ガーゼケット シングル", "寝具", 6980),
    ("そば殻まくら", "寝具", 4980),
    ("ワイヤレスイヤホン", "デジタル", 12800),
    ("モバイルバッテリー 10000mAh", "デジタル", 3980),
    ("スマートウォッチ", "デジタル", 24800),
    ("USB-C 急速充電器 65W", "デジタル", 4480),
    ("有機栽培 ドリップコーヒー 30袋", "食品", 3240),
    ("国産はちみつ 500g", "食品", 2980),
    ("北海道産 ミックスナッツ 1kg", "食品", 3680),
    ("無添加 だしパック 50袋", "食品", 2480),
    ("オーガニック 緑茶ティーバッグ", "食品", 1980),
    ("ヨガマット 6mm", "スポーツ", 3980),
    ("可変式ダンベル 2個組", "スポーツ", 15800),
    ("ランニングシューズ", "スポーツ", 9800),
    ("プロテイン ココア味 1kg", "スポーツ", 4980),
    ("キャンプ用 折りたたみチェア", "アウトドア", 5980),
    ("LED ランタン", "アウトドア", 3480),
    ("保冷バッグ 25L", "アウトドア", 3980),
]

LAST_NAMES = [
    ("佐藤", "サトウ", "sato"), ("鈴木", "スズキ", "suzuki"), ("高橋", "タカハシ", "takahashi"),
    ("田中", "タナカ", "tanaka"), ("伊藤", "イトウ", "ito"), ("渡辺", "ワタナベ", "watanabe"),
    ("山本", "ヤマモト", "yamamoto"), ("中村", "ナカムラ", "nakamura"), ("小林", "コバヤシ", "kobayashi"),
    ("加藤", "カトウ", "kato"), ("吉田", "ヨシダ", "yoshida"), ("山田", "ヤマダ", "yamada"),
    ("佐々木", "ササキ", "sasaki"), ("山口", "ヤマグチ", "yamaguchi"), ("松本", "マツモト", "matsumoto"),
    ("井上", "イノウエ", "inoue"), ("木村", "キムラ", "kimura"), ("林", "ハヤシ", "hayashi"),
    ("斎藤", "サイトウ", "saito"), ("清水", "シミズ", "shimizu"),
]
FIRST_NAMES = [
    ("翔太", "ショウタ", "shota"), ("美咲", "ミサキ", "misaki"), ("大輔", "ダイスケ", "daisuke"),
    ("陽菜", "ヒナ", "hina"), ("健太", "ケンタ", "kenta"), ("さくら", "サクラ", "sakura"),
    ("拓也", "タクヤ", "takuya"), ("結衣", "ユイ", "yui"), ("直樹", "ナオキ", "naoki"),
    ("愛", "アイ", "ai"), ("亮", "リョウ", "ryo"), ("真由美", "マユミ", "mayumi"),
    ("誠", "マコト", "makoto"), ("恵", "メグミ", "megumi"), ("隆", "タカシ", "takashi"),
    ("彩", "アヤ", "aya"), ("浩二", "コウジ", "koji"), ("千尋", "チヒロ", "chihiro"),
    ("悠斗", "ユウト", "yuto"), ("七海", "ナナミ", "nanami"),
]
# 結婚などで変わった姓の候補（外部リストの表記揺れ用）
MAIDEN_NAMES = [("森", "モリ"), ("石川", "イシカワ"), ("前田", "マエダ"), ("岡田", "オカダ")]

PREFECTURES = [
    ("東京都", 20), ("神奈川県", 10), ("大阪府", 9), ("愛知県", 7), ("埼玉県", 7),
    ("千葉県", 6), ("兵庫県", 5), ("北海道", 5), ("福岡県", 5), ("静岡県", 3),
    ("宮城県", 3), ("京都府", 3), ("広島県", 3), ("茨城県", 2), ("新潟県", 2),
    ("長野県", 2), ("岡山県", 2), ("熊本県", 2), ("沖縄県", 2), ("石川県", 2),
]
CITY = {
    "東京都": "世田谷区", "神奈川県": "横浜市港北区", "大阪府": "大阪市北区", "愛知県": "名古屋市中区",
    "埼玉県": "さいたま市浦和区", "千葉県": "船橋市", "兵庫県": "神戸市中央区", "北海道": "札幌市中央区",
    "福岡県": "福岡市博多区", "静岡県": "浜松市中央区", "宮城県": "仙台市青葉区", "京都府": "京都市左京区",
    "広島県": "広島市南区", "茨城県": "つくば市", "新潟県": "新潟市中央区", "長野県": "松本市",
    "岡山県": "岡山市北区", "熊本県": "熊本市中央区", "沖縄県": "那覇市", "石川県": "金沢市",
}
RANKS = [("ブロンズ", 50), ("シルバー", 30), ("ゴールド", 15), ("プラチナ", 5)]
CHANNELS = [("Web", 55), ("アプリ", 35), ("電話", 10)]

INQUIRY_TOPICS = [("配送", 30), ("返品・交換", 20), ("支払い", 12), ("商品仕様", 20), ("会員・ポイント", 10), ("その他", 8)]
INQUIRY_CHANNELS = [("メール", 50), ("チャット", 30), ("電話", 20)]
INQUIRY_TONES = [("丁寧", 45), ("困惑", 30), ("強い不満", 15), ("急ぎ", 10)]

TOUCHPOINT_TYPES = [("メール開封", 35), ("サイト訪問", 30), ("アプリ起動", 20), ("クーポン利用", 10), ("電話", 5)]


def _weighted(rng: random.Random, pairs):
    values, weights = zip(*pairs)
    return rng.choices(values, weights=weights, k=1)[0]


def _random_dt(rng: random.Random, start: date, end: date) -> datetime:
    days = (end - start).days
    d = start + timedelta(days=rng.randrange(days + 1))
    return datetime(d.year, d.month, d.day, rng.randrange(7, 24), rng.randrange(60), rng.randrange(60))


def _fmt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _renumber(rows: list[dict], key: str, ts: str, prefix: str, width: int) -> dict[str, str]:
    """rows を ts 列の順に並べ替え、key 列に連番を振り直す。旧 ID → 新 ID の対応を返す。"""
    rows.sort(key=lambda r: (r[ts], r[key]))
    mapping = {}
    for i, r in enumerate(rows, start=1):
        new_id = f"{prefix}{i:0{width}d}"
        mapping[r[key]] = new_id
        r[key] = new_id
    return mapping


def _to_fullwidth(text: str) -> str:
    """英数字と記号を全角にする（外部リストの表記揺れ用）。"""
    out = []
    for ch in text:
        code = ord(ch)
        if 0x21 <= code <= 0x7E:
            out.append(chr(code + 0xFEE0))
        else:
            out.append(ch)
    return "".join(out)


def gen_products() -> list[dict]:
    return [
        {"product_id": f"P{i:03d}", "product_name": name, "category": cat, "price": price}
        for i, (name, cat, price) in enumerate(PRODUCTS, start=1)
    ]


def gen_customers(rng: random.Random) -> list[dict]:
    rows = []
    used_emails = set()
    for i in range(1, COUNTS["customers"] + 1):
        ln, ln_kana, ln_roma = rng.choice(LAST_NAMES)
        fn, fn_kana, fn_roma = rng.choice(FIRST_NAMES)
        email = f"{fn_roma}.{ln_roma}{rng.randrange(10, 99)}@example.com"
        while email in used_emails:
            email = f"{fn_roma}.{ln_roma}{rng.randrange(100, 999)}@example.com"
        used_emails.add(email)
        pref = _weighted(rng, PREFECTURES)
        rank = _weighted(rng, RANKS)
        registered = PERIOD_START - timedelta(days=rng.randrange(30, 1500))
        rows.append({
            "customer_id": f"C{i:04d}",
            "name": f"{ln} {fn}",
            "name_kana": f"{ln_kana} {fn_kana}",
            "email": email,
            "prefecture": pref,
            "address": f"{pref}{CITY[pref]}{rng.randrange(1, 9)}-{rng.randrange(1, 30)}-{rng.randrange(1, 20)}",
            "member_rank": rank,
            "registered_on": registered.isoformat(),
            # 上位ランクの一部に、直近 3 か月で接点が減る傾向を持たせる
            "churn_risk": rank in ("ゴールド", "プラチナ") and rng.random() < 0.3,
        })
    return rows


def gen_orders(rng: random.Random, customers: list[dict], products: list[dict]):
    weight_by_rank = {"ブロンズ": 1, "シルバー": 2, "ゴールド": 4, "プラチナ": 7}
    weights = [weight_by_rank[c["member_rank"]] for c in customers]
    prices = {p["product_id"]: p["price"] for p in products}
    orders, items = [], []
    for i in range(1, COUNTS["orders"] + 1):
        customer = rng.choices(customers, weights=weights, k=1)[0]
        if customer["churn_risk"] and rng.random() < 0.8:
            ordered_at = _random_dt(rng, PERIOD_START, RECENT_START - timedelta(days=1))
        else:
            ordered_at = _random_dt(rng, PERIOD_START, PERIOD_END)
        order_id = f"O{i:05d}"
        chosen = rng.sample(products, k=rng.choices([1, 2, 3], weights=[50, 35, 15])[0])
        total = 0
        for p in chosen:
            qty = rng.choices([1, 2, 3], weights=[80, 15, 5])[0]
            items.append({"order_id": order_id, "product_id": p["product_id"], "quantity": qty})
            total += prices[p["product_id"]] * qty
        orders.append({
            "order_id": order_id,
            "customer_id": customer["customer_id"],
            "ordered_at": _fmt(ordered_at),
            "channel": _weighted(rng, CHANNELS),
            "total_amount": total,
        })
    mapping = _renumber(orders, "order_id", "ordered_at", "ORD-", 5)
    for it in items:
        it["order_id"] = mapping[it["order_id"]]
    items.sort(key=lambda r: (r["order_id"], r["product_id"]))
    return orders, items


def gen_inquiries(rng: random.Random, orders: list[dict], items: list[dict]) -> list[dict]:
    items_by_order: dict[str, list[str]] = {}
    for it in items:
        items_by_order.setdefault(it["order_id"], []).append(it["product_id"])
    delay_orders = [o for o in orders if DELAY_PRODUCT_ID in items_by_order[o["order_id"]]]
    rows = []
    for i in range(1, COUNTS["inquiries"] + 1):
        topic = _weighted(rng, INQUIRY_TOPICS)
        if topic == "配送" and rng.random() < 0.5:
            order = rng.choice(delay_orders)
            product_id = DELAY_PRODUCT_ID
        else:
            order = rng.choice(orders)
            product_id = rng.choice(items_by_order[order["order_id"]])
        ordered_at = datetime.strptime(order["ordered_at"], "%Y-%m-%d %H:%M:%S")
        received = min(ordered_at + timedelta(days=rng.randrange(1, 15), hours=rng.randrange(24)),
                       datetime(2026, 11, 30, 23, 0, 0))
        has_order = topic not in ("会員・ポイント",) and rng.random() < 0.85
        rows.append({
            "inquiry_id": f"Q{i:04d}",
            "customer_id": order["customer_id"],
            "order_id": order["order_id"] if has_order else None,
            "product_id": product_id if has_order else None,
            "received_at": _fmt(received),
            "channel": _weighted(rng, INQUIRY_CHANNELS),
            # 以下は本文生成用の属性。ハンズオンで AI に当てさせる正解でもある
            "topic": topic,
            "tone": _weighted(rng, INQUIRY_TONES),
        })
    _renumber(rows, "inquiry_id", "received_at", "Q", 4)
    return rows


def gen_reviews(rng: random.Random, orders: list[dict], items: list[dict]) -> list[dict]:
    order_by_id = {o["order_id"]: o for o in orders}
    delay_items = [it for it in items if it["product_id"] == DELAY_PRODUCT_ID]
    rows = []
    for i in range(1, COUNTS["reviews"] + 1):
        it = rng.choice(delay_items) if rng.random() < 0.12 else rng.choice(items)
        order = order_by_id[it["order_id"]]
        if it["product_id"] == DELAY_PRODUCT_ID:
            rating = rng.choices([1, 2, 3, 4, 5], weights=[35, 35, 20, 7, 3])[0]
        else:
            rating = rng.choices([1, 2, 3, 4, 5], weights=[4, 6, 15, 35, 40])[0]
        ordered_at = datetime.strptime(order["ordered_at"], "%Y-%m-%d %H:%M:%S")
        posted = min(ordered_at + timedelta(days=rng.randrange(3, 30)), datetime(2026, 11, 30, 22, 0, 0))
        rows.append({
            "review_id": f"R{i:04d}",
            "customer_id": order["customer_id"],
            "product_id": it["product_id"],
            "rating": rating,
            "posted_at": _fmt(posted),
        })
    _renumber(rows, "review_id", "posted_at", "R", 4)
    return rows


def gen_touchpoints(rng: random.Random, customers: list[dict]) -> list[dict]:
    rows = []
    for c in customers:
        base = {"ブロンズ": 6, "シルバー": 9, "ゴールド": 14, "プラチナ": 18}[c["member_rank"]]
        n = max(1, int(rng.gauss(base, 2)))
        for _ in range(n):
            if c["churn_risk"] and rng.random() < 0.9:
                dt = _random_dt(rng, PERIOD_START, RECENT_START - timedelta(days=1))
            else:
                dt = _random_dt(rng, PERIOD_START, PERIOD_END)
            rows.append({"customer_id": c["customer_id"], "occurred_at": _fmt(dt),
                         "touchpoint_type": _weighted(rng, TOUCHPOINT_TYPES)})
    rows.sort(key=lambda r: (r["occurred_at"], r["customer_id"]))
    for i, r in enumerate(rows, start=1):
        r["touchpoint_id"] = f"T{i:05d}"
    return [{"touchpoint_id": r["touchpoint_id"], **{k: v for k, v in r.items() if k != "touchpoint_id"}}
            for r in rows]


def gen_customers_import(rng: random.Random, customers: list[dict]) -> list[dict]:
    """展示会の来場者リストを想定した外部リスト。会員と同一人物を表記を変えて載せる。"""
    rows = []
    for i, c in enumerate(rng.sample(customers, COUNTS["customers_import"]), start=1):
        last, first = c["name"].split(" ")
        variant = i % 5
        name, email, address = c["name"], c["email"], c["address"]
        if variant == 0:  # 姓と名の間の空白なし、メールは大文字
            name, email = f"{last}{first}", email.upper()
        elif variant == 1:  # カタカナ表記、住所の番地を全角
            name = c["name_kana"]
            address = _to_fullwidth(address)
        elif variant == 2:  # 旧姓、住所は都道府県を省略
            maiden = rng.choice(MAIDEN_NAMES)[0]
            name = f"{maiden} {first}"
            address = address.replace(c["prefecture"], "", 1)
        elif variant == 3:  # 全角空白、メールのドメイン違い
            name = f"{last}　{first}"
            email = email.replace("@example.com", "@example.co.jp")
        else:  # 番地を「丁目・番・号」で書く（例: 世田谷区3-12-5 → 世田谷区3丁目12番5号）
            prefix, ban, go = address.rsplit("-", 2)
            address = f"{prefix}丁目{ban}番{go}号"
        rows.append({
            "import_id": f"X{i:03d}",
            "name": name,
            "email": email,
            "address": address,
            "source": "展示会来場者リスト",
            # 結果を確かめるための正解。ハンズオンでは突合に使わない
            "true_customer_id": c["customer_id"],
        })
    return rows


def generate_all(seed: int = 42) -> dict[str, list[dict]]:
    rng = random.Random(seed)
    products = gen_products()
    customers = gen_customers(rng)
    orders, items = gen_orders(rng, customers, products)
    return {
        "products": products,
        "customers": customers,
        "orders": orders,
        "order_items": items,
        "inquiries": gen_inquiries(rng, orders, items),
        "reviews": gen_reviews(rng, orders, items),
        "touchpoints": gen_touchpoints(rng, customers),
        "customers_import": gen_customers_import(rng, customers),
    }


# CSV に書き出さない列（傾向を仕込むための内部属性）
HIDDEN_COLUMNS = {"customers": {"churn_risk"}}


def write_csv(rows: list[dict], path: Path, hidden: set[str] = frozenset()) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [k for k in rows[0] if k not in hidden]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: ("" if row[k] is None else row[k]) for k in fields})


def main() -> None:
    data = generate_all()
    for table, rows in data.items():
        write_csv(rows, OUT_DIR / f"{table}.csv", HIDDEN_COLUMNS.get(table, set()))
        print(f"{table}: {len(rows)} 行")


if __name__ == "__main__":
    main()
