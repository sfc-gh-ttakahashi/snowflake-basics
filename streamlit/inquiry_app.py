"""問い合わせ対応アプリ（Part4-3 の見本）。

CoCo に作らせたアプリがうまく動かないときに、この見本をそのまま使えます。
- 種別と商品で問い合わせを絞り込み、一覧を表示する
- 選んだ問い合わせに、AI_COMPLETE で返信案を作る（商品仕様書がある商品は、仕様書を根拠にする）

Part3-2 のパイプラインが作った AI_INQUIRY_TOPICS と AI_PRODUCT_INSIGHTS を使います。
"""

import streamlit as st
from snowflake.snowpark.context import get_active_session

DB = "AI_HANDSON_DB.CRM"
MODEL = "claude-sonnet-4-5"

session = get_active_session()
st.set_page_config(page_title="問い合わせ対応アプリ", layout="wide")
st.title("問い合わせ対応アプリ")
st.caption("くらしモール カスタマーサポート（ハンズオン用の合成データ）")


@st.cache_data(ttl=300)
def load_products() -> list:
    rows = session.sql(f"SELECT product_name FROM {DB}.AI_PRODUCT_INSIGHTS ORDER BY product_name").collect()
    return [r["PRODUCT_NAME"] for r in rows]


@st.cache_data(ttl=300)
def load_topics() -> list:
    rows = session.sql(f"SELECT DISTINCT topic FROM {DB}.AI_INQUIRY_TOPICS ORDER BY topic").collect()
    return [r["TOPIC"] for r in rows]


@st.cache_data(ttl=300)
def load_insight(product_name: str):
    rows = session.sql(
        f"SELECT inquiries, shipping_inquiries, avg_rating, review_complaints "
        f"FROM {DB}.AI_PRODUCT_INSIGHTS WHERE product_name = ?",
        params=[product_name],
    ).collect()
    return rows[0] if rows else None


@st.cache_data(ttl=300)
def load_inquiries(topic: str, product_name: str):
    return session.sql(
        f"""
        SELECT i.inquiry_id, i.received_at, i.channel, t.topic, p.product_name, i.body
        FROM {DB}.inquiries i
        JOIN {DB}.AI_INQUIRY_TOPICS t USING (inquiry_id)
        LEFT JOIN {DB}.products p USING (product_id)
        WHERE t.topic = ? AND p.product_name = ?
        ORDER BY i.received_at DESC
        """,
        params=[topic, product_name],
    ).to_pandas()


def generate_reply(inquiry_id: str) -> str:
    # 商品仕様書がある商品は仕様書を根拠にし、ない商品は問い合わせの本文だけで返信案を作る
    sql = f"""
        WITH target AS (
            SELECT i.body, d.relative_path AS spec_path
            FROM {DB}.inquiries i
            LEFT JOIN DIRECTORY(@{DB}.DATA_STAGE) d
              ON d.relative_path = 'data/pdf/spec_' || i.product_id || '.pdf'
            WHERE i.inquiry_id = ?
        )
        SELECT CASE
            WHEN spec_path IS NOT NULL THEN AI_COMPLETE(
                '{MODEL}',
                PROMPT(
                    'あなたは通販サイトのカスタマーサポート担当です。添付の商品仕様書を根拠に、次の問い合わせへの返信案を 200 文字以内で書いてください。仕様書にないことは書かないでください。\\n\\n問い合わせ: {{0}}\\n\\n商品仕様書: {{1}}',
                    body,
                    TO_FILE('@{DB}.DATA_STAGE', spec_path)
                )
            )::VARCHAR
            ELSE AI_COMPLETE(
                '{MODEL}',
                'あなたは通販サイトのカスタマーサポート担当です。次の問い合わせへの返信案を 200 文字以内で書いてください。確認が必要なことは、担当者が確認すると書いてください。\\n\\n問い合わせ: ' || body
            )::VARCHAR
        END AS reply_draft
        FROM target
    """
    return session.sql(sql, params=[inquiry_id]).collect()[0]["REPLY_DRAFT"]


with st.sidebar:
    st.header("絞り込み")
    topic = st.selectbox("問い合わせの種別", load_topics(), index=None, placeholder="種別を選ぶ")
    product_name = st.selectbox("商品", load_products(), index=None, placeholder="商品を選ぶ")

if not topic or not product_name:
    st.info("左のサイドバーで、問い合わせの種別と商品を選んでください。")
    st.stop()

insight = load_insight(product_name)
if insight is not None:
    col1, col2, col3 = st.columns(3)
    col1.metric("問い合わせ件数", insight["INQUIRIES"])
    col2.metric("うち配送", insight["SHIPPING_INQUIRIES"])
    col3.metric("レビューの平均評価", insight["AVG_RATING"] if insight["AVG_RATING"] is not None else "-")
    with st.expander("レビューの不満点（AI_AGG の要約）"):
        st.write(insight["REVIEW_COMPLAINTS"] or "レビューがありません")

df = load_inquiries(topic, product_name)
st.subheader(f"問い合わせ一覧（{len(df)} 件）")
if df.empty:
    st.write("該当する問い合わせはありません。")
    st.stop()

st.dataframe(df[["INQUIRY_ID", "RECEIVED_AT", "CHANNEL", "BODY"]], hide_index=True, use_container_width=True)

inquiry_id = st.selectbox("返信案を作る問い合わせ", df["INQUIRY_ID"].tolist())
st.text_area("問い合わせの本文", df.loc[df["INQUIRY_ID"] == inquiry_id, "BODY"].iloc[0], height=150, disabled=True)

if st.button("返信案を作る", type="primary"):
    with st.spinner("AI_COMPLETE で返信案を作っています..."):
        st.text_area("返信案（送る前に必ず内容を確かめてください）", generate_reply(inquiry_id), height=200)
