"""問い合わせ本文とレビュー本文を AI_COMPLETE で生成し、CSV に書き戻す。

generate_structured.py が作った inquiries.csv / reviews.csv の属性（topic・tone・rating）
を元にプロンプトを作り、Snowflake の AI_COMPLETE で本文を生成する。生成結果は
scripts/generate/.cache/ に保存し、2 回目以降は未生成の行だけを生成する。

使い方:
    uv run python -m scripts.generate.generate_text --connection SFSEAPAC-TTAKAHASHI_AWS1
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from scripts.generate.generate_structured import DELAY_PRODUCT_ID

ROOT = Path(__file__).resolve().parents[2]
CSV_DIR = ROOT / "data" / "csv"
CACHE_DIR = Path(__file__).resolve().parent / ".cache"
DEFAULT_MODEL = "claude-sonnet-4-5"

CHANNEL_STYLE = {
    "メール": "顧客がサポート窓口に送ったメールの本文。宛名と署名（顧客の名字のみ）を含める",
    "チャット": "顧客が Web サイトのチャットに書き込んだ文。1〜3 文で短く、くだけた書き方",
    "電話": "オペレーターが電話の内容を書いた受付メモ。「お客様より〜とのこと。」のように三人称で書く",
}
TONE_STYLE = {
    "丁寧": "落ち着いた丁寧な書き方",
    "困惑": "どうすればよいか分からず困っている書き方",
    "強い不満": "強い不満が伝わる書き方。ただし暴言は使わない",
    "急ぎ": "急いで対応してほしいことが伝わる書き方",
}
TOPIC_HINT = {
    "配送": "届く予定日を過ぎても届かない、配送状況が更新されない、など配送の問題",
    "返品・交換": "サイズ違い・初期不良・イメージ違いによる返品や交換の希望",
    "支払い": "二重請求、クレジットカードの決済エラー、後払いの請求書が届かない、など支払いの問題",
    "商品仕様": "サイズ・素材・使い方・対応機種など、商品の仕様についての質問",
    "会員・ポイント": "ポイントの付与漏れ、会員ランク、ログインできない、など会員サービスの問題",
    "その他": "ギフト包装、領収書の発行、配送先の変更など",
}


def build_inquiry_prompt(row: dict, products: dict[str, str]) -> str:
    """問い合わせ 1 件分の本文を生成させるプロンプトを作る。"""
    lines = [
        "あなたは日本の通販サイトの CRM 用サンプルデータを作っています。",
        "次の条件で、問い合わせの本文を 1 件だけ書いてください。",
        f"- 形式: {CHANNEL_STYLE[row['channel']]}",
        f"- 内容: {TOPIC_HINT[row['topic']]}",
        f"- 口調: {TONE_STYLE[row['tone']]}",
    ]
    if row["order_id"]:
        lines.append(f"- 対象の商品: {products[row['product_id']]}")
        lines.append(f"- 注文番号 {row['order_id']} を本文の中に自然に含める")
    else:
        lines.append("- 特定の注文についての問い合わせではないので、注文番号は書かない")
    lines += [
        "- 長さ: 60〜200 文字",
        "- 実在の企業名・人名・電話番号・メールアドレスは書かない",
        "- 本文だけを出力し、見出し・前置き・説明は書かない",
    ]
    return "\n".join(lines)


def build_review_prompt(row: dict, products: dict[str, str], delay_product_id: str = DELAY_PRODUCT_ID) -> str:
    """レビュー 1 件分の本文を生成させるプロンプトを作る。"""
    rating = int(row["rating"])
    lines = [
        "あなたは日本の通販サイトの CRM 用サンプルデータを作っています。",
        "次の条件で、購入者が書いた商品レビューを 1 件だけ書いてください。",
        f"- 商品: {products[row['product_id']]}",
        "- 本文で商品を別の商品名や別の種類の商品に言い換えない",
        f"- 評価: 5 段階で星 {rating}。本文の内容と評価を一致させる",
    ]
    if row["product_id"] == delay_product_id and rating <= 3:
        lines.append("- 商品そのものより、届くまでに時間がかかったことへの不満を中心に書く")
    lines += [
        "- 長さ: 40〜150 文字",
        "- 本文だけを出力し、見出し・星の数・前置きは書かない",
    ]
    return "\n".join(lines)


def normalize_text(text: str) -> str:
    """AI_COMPLETE の戻り値を本文の文字列にする。

    model_parameters を渡すと、戻り値が JSON の文字列リテラル（"..."）になるため、その場合は読み直す。
    """
    text = text.strip()
    if text.startswith('"') and text.endswith('"'):
        text = json.loads(text)
    return text.strip()


def merge_texts(rows: list[dict], key: str, column: str, texts: dict[str, str]) -> list[dict]:
    """texts（ID → 本文）を rows の column 列に入れる。本文がない行があれば KeyError。"""
    missing = [r[key] for r in rows if r[key] not in texts]
    if missing:
        raise KeyError(f"本文がない行: {', '.join(missing[:10])}")
    return [{**r, column: normalize_text(texts[r[key]])} for r in rows]


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(rows: list[dict], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def complete_all(conn, prompts: dict[str, str], model: str, batch_size: int = 50) -> dict[str, str]:
    """プロンプトを batch_size 件ずつ VALUES 句に入れ、AI_COMPLETE を 1 本の SELECT で呼ぶ。

    テーブルを作らないので、カレントデータベースのないセッションでも動く。
    """
    cur = conn.cursor()
    items = list(prompts.items())
    results: dict[str, str] = {}
    for start in range(0, len(items), batch_size):
        batch = items[start:start + batch_size]
        placeholders = ", ".join(["(%s, %s)"] * len(batch))
        params = [model] + [v for pair in batch for v in pair]
        cur.execute(
            "SELECT column1, AI_COMPLETE(%s, column2, {'temperature': 0.8}) "
            f"FROM VALUES {placeholders}",
            params,
        )
        results.update({row_id: text for row_id, text in cur.fetchall()})
        print(f"  {min(start + batch_size, len(items))} / {len(items)} 件")
    return results


def generate(conn, kind: str, rows: list[dict], key: str, build, model: str) -> dict[str, str]:
    cache_path = CACHE_DIR / f"{kind}.json"
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
    todo = {r[key]: build(r) for r in rows if r[key] not in cache}
    if todo:
        print(f"{kind}: {len(todo)} 件を生成します（モデル: {model}）")
        cache.update(complete_all(conn, todo, model))
        CACHE_DIR.mkdir(exist_ok=True)
        cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    else:
        print(f"{kind}: すべてキャッシュにあります")
    return cache


def connection_params(name: str, path: Path = Path.home() / ".snowflake" / "connections.toml") -> dict:
    """connections.toml の接続定義を読み、Python コネクタに渡せる形にする。

    snow CLI の書き方（private_key_path）を、コネクタのキー名（private_key_file）に読み替える。
    """
    import tomllib

    params = dict(tomllib.loads(path.read_text(encoding="utf-8"))[name])
    if "private_key_path" in params:
        params["private_key_file"] = params.pop("private_key_path")
    return params


def main() -> None:
    import snowflake.connector

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--connection", required=True, help="~/.snowflake/connections.toml の接続名")
    parser.add_argument("--warehouse", default="COMPUTE_WH")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--sample", type=int, default=0,
                        help="問い合わせとレビューをこの件数だけ生成して表示する。CSV とキャッシュは変えない")
    args = parser.parse_args()

    products = {r["product_id"]: r["product_name"] for r in read_csv(CSV_DIR / "products.csv")}
    inquiries = read_csv(CSV_DIR / "inquiries.csv")
    reviews = read_csv(CSV_DIR / "reviews.csv")

    with snowflake.connector.connect(**{**connection_params(args.connection), "warehouse": args.warehouse}) as conn:
        if args.sample:
            # チャネルと配送遅延の商品が偏らないように選ぶ
            picked_q = [next(r for r in inquiries if r["channel"] == ch) for ch in CHANNEL_STYLE][: args.sample]
            picked_r = sorted(reviews, key=lambda r: (r["product_id"] != DELAY_PRODUCT_ID, r["review_id"]))[: args.sample]
            prompts = {r["inquiry_id"]: build_inquiry_prompt(r, products) for r in picked_q}
            prompts |= {r["review_id"]: build_review_prompt(r, products) for r in picked_r}
            for row_id, text in sorted(complete_all(conn, prompts, args.model).items()):
                print(f"== {row_id}\n{normalize_text(text)}\n")
            return
        q_texts = generate(conn, "inquiries", inquiries, "inquiry_id",
                           lambda r: build_inquiry_prompt(r, products), args.model)
        r_texts = generate(conn, "reviews", reviews, "review_id",
                           lambda r: build_review_prompt(r, products), args.model)

    # 再実行しても列が重ならないよう、既存の本文列を外してから入れる
    inquiries = [{k: v for k, v in r.items() if k != "body"} for r in inquiries]
    reviews = [{k: v for k, v in r.items() if k != "body"} for r in reviews]
    write_csv(merge_texts(inquiries, "inquiry_id", "body", q_texts), CSV_DIR / "inquiries.csv")
    write_csv(merge_texts(reviews, "review_id", "body", r_texts), CSV_DIR / "reviews.csv")
    print("inquiries.csv と reviews.csv に本文を書き込みました")


if __name__ == "__main__":
    main()
