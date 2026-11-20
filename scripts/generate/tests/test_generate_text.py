"""generate_text のうち、Snowflake に接続しない部分のテスト。"""

from scripts.generate.generate_text import (
    build_inquiry_prompt,
    build_review_prompt,
    connection_params,
    merge_texts,
    normalize_text,
)

PRODUCTS = {"P012": "低反発マットレス シングル"}


def test_問い合わせのプロンプトに属性が入る():
    row = {"inquiry_id": "Q0001", "order_id": "O00014", "product_id": "P012",
           "channel": "メール", "topic": "配送", "tone": "強い不満"}
    prompt = build_inquiry_prompt(row, PRODUCTS)
    for text in ["O00014", "低反発マットレス シングル", "配送", "強い不満", "メール"]:
        assert text in prompt


def test_注文のない問い合わせでは注文番号を書かせない():
    row = {"inquiry_id": "Q0002", "order_id": "", "product_id": "",
           "channel": "チャット", "topic": "会員・ポイント", "tone": "丁寧"}
    prompt = build_inquiry_prompt(row, PRODUCTS)
    assert "注文番号は書かない" in prompt


def test_電話の問い合わせは受付メモの形にする():
    row = {"inquiry_id": "Q0003", "order_id": "O00001", "product_id": "P012",
           "channel": "電話", "topic": "支払い", "tone": "急ぎ"}
    assert "受付メモ" in build_inquiry_prompt(row, PRODUCTS)


def test_レビューのプロンプトに評価と商品名が入る():
    row = {"review_id": "R0001", "product_id": "P012", "rating": "1"}
    prompt = build_review_prompt(row, PRODUCTS, delay_product_id="P012")
    assert "低反発マットレス シングル" in prompt
    assert "星 1" in prompt
    assert "届くまで" in prompt  # 配送遅延の商品には配送への不満を書かせる


def test_JSON文字列で返った本文を元の文字列に戻す():
    assert normalize_text('"件名\\n\\n本文"') == "件名\n\n本文"
    assert normalize_text(" そのままの本文\n") == "そのままの本文"


def test_レビューで商品を言い換えないよう指示する():
    row = {"review_id": "R0001", "product_id": "P012", "rating": "1"}
    assert "別の商品" in build_review_prompt(row, PRODUCTS, delay_product_id="P012")


def test_本文を指定した列に書き戻す():
    rows = [{"inquiry_id": "Q0001"}, {"inquiry_id": "Q0002"}]
    merged = merge_texts(rows, "inquiry_id", "body", {"Q0001": " 本文1\n", "Q0002": "本文2"})
    assert merged == [{"inquiry_id": "Q0001", "body": "本文1"},
                      {"inquiry_id": "Q0002", "body": "本文2"}]


def test_snowCLIの鍵パスをコネクタのキー名に読み替える(tmp_path):
    toml = tmp_path / "connections.toml"
    toml.write_text('[a]\naccount = "x"\nprivate_key_path = "/k.p8"\n[b]\naccount = "y"\n', encoding="utf-8")
    assert connection_params("a", toml) == {"account": "x", "private_key_file": "/k.p8"}
    assert connection_params("b", toml) == {"account": "y"}


def test_本文がない行があれば失敗する():
    rows = [{"inquiry_id": "Q0001"}, {"inquiry_id": "Q0002"}]
    try:
        merge_texts(rows, "inquiry_id", "body", {"Q0001": "本文1"})
    except KeyError as e:
        assert "Q0002" in str(e)
    else:
        raise AssertionError("KeyError が出なかった")
