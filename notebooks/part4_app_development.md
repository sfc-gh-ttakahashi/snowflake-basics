# Part 4 : 開発体験 — AI 処理の結果を使う

Part3-2 のパイプラインが作った `AI_PRODUCT_INSIGHTS` などのテーブルを、3 つの方法で使います。
どれも **CoCo に作らせる** のが基本です。うまくいかないときのために、各章に見本を用意しています。

| # | 作るもの | 見る人 | データの更新 |
|---|---|---|---|
| 4-1 | **Dashboards**（ダッシュボード） | 担当者が毎日見る | 開くたびに、見る人の権限で SQL を実行する |
| 4-2 | **HTML レポート** | 経営層に一度だけ報告する | 作った時点のデータを埋め込む（自動では更新されない） |
| 4-3 | **Streamlit アプリ** | 問い合わせ対応の担当者が操作する | 操作のたびに SQL と AI 関数を実行する |

```sql 0-1
-- コンテキスト設定と、Part3-2 の結果があるかの確認
USE ROLE ACCOUNTADMIN;
USE WAREHOUSE AI_HANDSON_WH;
USE DATABASE AI_HANDSON_DB;
USE SCHEMA CRM;

SELECT COUNT(*) AS products FROM AI_PRODUCT_INSIGHTS;  -- 30 なら準備ができています
```

> 0 行やエラーになる場合は、Part3-2 のパイプラインがまだ実行されていません。Part3-2 の「Pipeline Builder が使えないときの手順」で、`pipeline/` の SQL を順に実行してください。

---
## 4-1. Dashboards — 担当者が毎日見る画面を作る

### やってみよう

1. 左のファイル一覧で、ワークスペースのいちばん上（ルート）の **+** を選び、**Dashboard** を選択する（CoCo のチャットパネルが開く）
2. CoCo チャットで、次のように依頼する

```
AI_HANDSON_DB.CRM の AI_INQUIRY_TOPICS、INQUIRIES、AI_PRODUCT_INSIGHTS を使って、
カスタマーサポートの担当者が毎日見るダッシュボードを作って。タイルは次の 3 つ:

1. 問い合わせの種別ごとの件数（横棒グラフ）
2. 月別の問い合わせ件数を、種別ごとに積み上げたグラフ
3. 配送の問い合わせが多い商品の上位 10 件の表（配送の問い合わせ件数、レビューの平均評価、否定的なレビューの件数）
```

3. CoCo が `.dash` ファイルを作って開く。タイルの SQL とグラフを確かめる
4. 気になるところがあれば、続けて頼む（例: 「2 つ目のグラフを折れ線にして」「種別で絞り込めるフィルタを付けて」）

> **観察ポイント:**
> - 配送の問い合わせが多い月はいつか
> - 上位 10 件の表で、「低反発マットレス シングル」が飛び抜けていることが分かるか

### 見本: タイルの SQL

CoCo がうまくタイルを作れないときは、手動でタイルを追加し、次の SQL を使ってください。

```sql 1-1
-- タイル 1: 問い合わせの種別ごとの件数（横棒グラフ）
SELECT topic, COUNT(*) AS inquiries
FROM AI_INQUIRY_TOPICS
GROUP BY topic
ORDER BY inquiries DESC;
```

```sql 1-2
-- タイル 2: 月別・種別の問い合わせ件数（積み上げ棒グラフ。X 軸 = received_month、色 = topic）
SELECT DATE_TRUNC('month', i.received_at) AS received_month, t.topic, COUNT(*) AS inquiries
FROM inquiries i
JOIN AI_INQUIRY_TOPICS t USING (inquiry_id)
GROUP BY ALL
ORDER BY received_month, topic;
```

```sql 1-3
-- タイル 3: 配送の問い合わせが多い商品の上位 10 件（表）
SELECT product_name, shipping_inquiries, avg_rating, negative_reviews
FROM AI_PRODUCT_INSIGHTS
WHERE reviews > 0
ORDER BY shipping_inquiries DESC, avg_rating
LIMIT 10;
```

### 共有する（任意）

ダッシュボードを開いたまま **Publish artifact** を選ぶと、**ダッシュボードのアーティファクト**として、ほかのロールやユーザーに共有できます。
共有されたダッシュボードは、開く人の権限で SQL を実行します。テーブルを見る権限のない人には、データが表示されません。

---
## 4-2. HTML レポート — 経営層への報告書を作る

### やってみよう

1. 左のファイル一覧で、ワークスペースのいちばん上（ルート）の **+** を選び、**Report** を選択する（CoCo のチャットパネルが開く）
2. CoCo チャットで、次のように依頼する

```
AI_HANDSON_DB.CRM の AI_PRODUCT_INSIGHTS と AI_INQUIRY_TOPICS を使って、
経営層向けの「カスタマーサポート月次報告」を HTML レポートで作って。次の構成にして:

1. 要点（3 行）: 最も大きな問題と、その原因、打つべき対策
2. 問い合わせの種別ごとの件数のグラフ
3. 配送の問い合わせが多い商品の表と、その商品のレビューの不満点（AI_PRODUCT_INSIGHTS の review_complaints）
4. 対策の提案

対策を考えるときは、低反発マットレス シングルの商品仕様書に「受注生産のため、出荷まで 10〜14 営業日」とあることを踏まえて。
```

3. CoCo が SQL を実行し、`.html` ファイルを作る。プレビューで内容を確かめる
4. 気になるところがあれば、続けて頼む（例: 「要点をもっと短く」「グラフの色を落ち着いた色に」）

> **観察ポイント:**
> - 要点に「受注生産で出荷に時間がかかることを、購入前に伝えていない」という原因が書かれているか
> - 数字が、4-1 のダッシュボードの数字と一致しているか

### 公開する

1. 作った `.html` ファイルを開いたまま、**Publish artifact** を選ぶ
2. **Who has access** で、見せたいロールやユーザーを追加する（初期状態では自分だけが見られる）
3. **Create** を選ぶと、レポートのリンクがクリップボードにコピーされる

> **ダッシュボードとの違い:** HTML レポートは、作った時点のデータを **埋め込みます**。開いた人の権限で SQL を実行し直すことはありません。
> テーブルを見る権限のない人でも、レポートに埋め込まれたデータは見えます。公開する前に、載せてよい内容か確かめてください。

---
## 4-3. Streamlit アプリ — 問い合わせ対応アプリを作る

問い合わせ対応の担当者が使うアプリを、CoCo に作らせます。
アプリの中で `AI_COMPLETE` を呼び、選んだ問い合わせへの返信案を作ります。

### やってみよう

1. Snowsight 左メニュー **Projects → Streamlit** を開き、**+ Streamlit App** を選ぶ
2. 次のとおり入力して **Create** を選ぶ
   - App title: `inquiry_app`
   - App location: `AI_HANDSON_DB`、`CRM`
   - Runtime: **Run on container**（コンテナランタイム）
   - Query warehouse: `AI_HANDSON_WH`
3. エディタが開いたら、CoCo チャットで次のように依頼する

```
AI_HANDSON_DB.CRM のテーブルを使って、カスタマーサポートの問い合わせ対応アプリを Streamlit で作って。

- サイドバーで、問い合わせの種別（AI_INQUIRY_TOPICS.topic）と商品（PRODUCTS.product_name）を選ぶ
- 選んだ商品の、問い合わせ件数・配送の問い合わせ件数・レビューの平均評価を AI_PRODUCT_INSIGHTS から表示する
- 条件に合う問い合わせ（INQUIRIES）の一覧を表示する
- 一覧から 1 件選んでボタンを押すと、AI_COMPLETE で返信案を作って表示する
  - 商品仕様書がある商品（ステージ @AI_HANDSON_DB.CRM.DATA_STAGE の data/pdf/spec_<商品ID>.pdf）は、仕様書を PROMPT と TO_FILE で渡し、仕様書を根拠に返信させる
  - 仕様書がない商品は、本文だけで返信案を作る
- SQL に値を渡すときは、文字列に埋め込まずにバインド変数を使う
```

4. CoCo がコードを書いたら、アプリを実行して動きを確かめる
5. 「種別 = 配送」「商品 = 低反発マットレス シングル」を選び、問い合わせを 1 件選んで返信案を作ってみる

> **観察ポイント:**
> - 返信案が、商品仕様書の「受注生産のため、出荷まで 10〜14 営業日」を根拠にしているか
> - 仕様書のない商品の問い合わせでも、エラーにならずに返信案が作られるか

### 見本: アプリのコード

CoCo がうまくアプリを作れないときは、リポジトリの `streamlit/inquiry_app.py` の中身を、エディタにそのまま貼り付けて実行してください。

> **後片付け:** コンテナランタイムのアプリは、開いている間コンピュートプールを使います。
> 確かめ終わったら、アプリの画面を閉じてください。アプリを使わない状態が続くと、コンピュートプールは自動で止まります。

---
## まとめ

| | Dashboards | HTML レポート | Streamlit アプリ |
|---|---|---|---|
| 向いている用途 | 毎日見る定型の画面 | 一度きりの報告・説明 | 操作に応じて処理する業務アプリ |
| データ | 開くたびに SQL を実行 | 作った時点のデータを埋め込む | 操作のたびに SQL・AI 関数を実行 |
| 共有 | ダッシュボードのアーティファクト | レポートのアーティファクト | Streamlit アプリの権限 |
| CoCo に任せたこと | タイルの SQL とグラフ | 構成・文章・グラフ | 画面とコード |

このハンズオンでは、次の流れを一通り体験しました。

1. **Part1**: CoCo で SQL を読み、書き、直す
2. **Part2**: Snowflake の基本機能（クローン、Time Travel、動的テーブル）
3. **Part3**: AI 関数で非構造化データ（問い合わせ・レビュー・PDF）を構造化し、Pipeline Builder でパイプラインにする
4. **Part4**: その結果を、ダッシュボード・レポート・アプリで使う

後片付けは、`cleanup.sql` を実行してください。
