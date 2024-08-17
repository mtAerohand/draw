import re
import threading
import time
import os

import requests
import logging
from bs4 import BeautifulSoup
from tinydb import TinyDB, Query

from pushbullet import Pushbullet

# DBの読み込み
db = TinyDB("cards.json")
db_sub = TinyDB("cards_sub.json")
query = Query()

# ログ設定
logging.basicConfig(
    filename="draw.log",
    filemode="a",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ----- constants -----

# GETリクエストの間隔(s)
GET_INTERVAL_SECONDS = 600
# 1ページごとのカードの取得件数
GET_SIZE = 100
# 遊戯王データベースのベースURL
BASE_URL = "https://www.db.yugioh-card.com"

# Pushbullet通知のタイトル
TITLE = "【Draw!!】コミット確認"
# レコード数変動イベントの通知文テンプレート
TOTAL_CHANGED = """
カードの総数が変化しました。前：{size}　後：{size_sub}
確認してコミットしてください。
"""

# ----- functions -----


# 指定ページを取得・解析しカードデータ一覧を取得して、DBに保存する関数
# 戻り値は保存したレコード数
def get_cards(page):
    # 戻り値
    record_num = 0
    # get用URL
    url = (
        BASE_URL
        + f"/yugiohdb/card_search.action?ope=1&request_locale=ja&page={page}&rp={GET_SIZE}"
    )
    # getレスポンス
    response = None

    # 指定ページ、GET_SIZE件の条件で取得をかける
    print(f"Request send. Page : {page}")
    logger.info(f"Request send. Page : {page}")
    response = requests.get(url)

    if response is None:
        raise Exception("Response is None.")
    else:
        print("Start parsing...")
        # ページのHTMLをパースしそれぞれのカード情報を持つdivをリスト化
        soup = BeautifulSoup(response.text, "html.parser")
        card_list_divs = soup.find("div", id="card_list").find_all(
            "div", recursive=False
        )
        for card_div in card_list_divs:
            # 1レコードのカードデータ
            card = {"id": 0, "card_type": "", "link": ""}
            # モンスター・魔法・罠を同定
            card_type = (
                card_div.find("span", class_="box_card_attribute")
                .find("span")
                .get_text()
            )
            if card_type == "魔法":
                card["card_type"] = "spell"
            elif card_type == "罠":
                card["card_type"] = "trap"
            else:
                card["card_type"] = "monster"

            # リンクとカードIDを取得
            link = card_div.find("input", class_="link_value").get("value")
            card["link"] = BASE_URL + link + "&request_locale=ja"
            id = re.search(r"cid=(\d+)", link).group(1)
            # IDをキーとしてdbにレコードを保存
            card["id"] = id
            targets = db_sub.search(query.id == id)
            if len(targets) > 0:
                db_sub.update(card, query.id == id)
            else:
                db_sub.insert(card)
            saved_card = db_sub.search(query.id == id)
            logger.info(f"Saved Data : {saved_card}")

            record_num += 1

    return record_num


# カードデータ自動更新用スレッドを走らせる関数
def run():
    # 一定時間ごとにget_cards関数を実行し、カードデータを保存する関数
    def crawl():
        page = 1
        while True:
            record_num = 0
            try:
                record_num = get_cards(page)
            except requests.exceptions.RequestException:
                print(f"Request failed. Page : {page}")
                logger.ERROR(f"Request failed. Page : {page}")
            except Exception as e:
                print(e)
            # cardsのサイズがGET_SIZE未満の場合、pageを1にリセットする
            if record_num < GET_SIZE:
                commit_check()
                db_sub.truncate()
                page = 1
            else:
                page += 1
            # GET_INTERVAL_SECONDS(s)だけ待機する
            print(f"Start pending {GET_INTERVAL_SECONDS} seconds...")
            time.sleep(GET_INTERVAL_SECONDS)

    thread = threading.Thread(target=crawl)
    thread.daemon = True
    thread.start()


# ----- utils -----


# サブDBが自動コミット可能かチェックする関数
def commit_check():
    commit_enabled = True

    # コンソールで確認を出す関数
    def confirm(confirm_text):
        while True:
            input_text = input(confirm_text + "(yes/no): ").strip().lower()
            if input_text == "yes":
                break
            elif input_text == "no":
                nonlocal commit_enabled
                commit_enabled = False
                break

    # sizeの比較
    size = len(db.all())
    size_sub = len(db_sub.all())
    if size_sub != 0 and size != size_sub:
        body = TOTAL_CHANGED.format(size=size, size_sub=size_sub)
        send_pushbullet_notification(TITLE, body)
        confirm(body)

    if commit_enabled:
        print("Committing...")
        commit()
    else:
        print("Commit canceled.")


# サブDBをメインDBにコミットする関数
def commit():
    db.truncate()
    db.insert_multiple(db_sub.all())


# Pushbulletに通知を送る関数
def send_pushbullet_notification(title, body):
    # Pushbullet APIトークン
    api_key = os.getenv("PUSHBULLET_KEY")

    # Pushbulletに接続
    pb = Pushbullet(api_key)

    # 通知を送信
    push = pb.push_note(title, body)

    if push:
        print("Notification sent.")
    else:
        print("Failed to sent notification.")
