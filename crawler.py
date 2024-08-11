import re
import threading
import time

import requests
from bs4 import BeautifulSoup
from tinydb import TinyDB, Query

# DBの読み込み
db = TinyDB("cards.json")
query = Query()

# ----- constants -----

# GETリクエストの間隔(s)
GET_INTERVAL_SECONDS = 1
# GET_INTERVAL_SECONDS = 600
# 1ページごとのカードの取得件数
GET_SIZE = 100
#遊戯王データベースのベースURL
BASE_URL = "https://www.db.yugioh-card.com"

# ----- functions -----

# 指定ページを取得・解析しカードデータ一覧を取得して、DBに保存する関数
# 戻り値は保存したレコード数
def get_cards(page):
  # 戻り値
  record_num = 0
  # get用URL
  url = BASE_URL + f"/yugiohdb/card_search.action?ope=1&request_locale=ja&page={page}&rp={GET_SIZE}"
  # getレスポンス
  response = None

  # 指定ページ、GET_SIZE件の条件で取得をかける
  print(f"Request send. Page : {page}")
  response = requests.get(url)

  if response is None:
    raise Exception("Response is None.")
  else:
    print("Start parsing...")
    # ページのHTMLをパースしそれぞれのカード情報を持つdivをリスト化
    soup = BeautifulSoup(response.text, "html.parser")
    card_list_divs = soup.find("div", id="card_list").find_all("div",
                                                               recursive=False)
    for card_div in card_list_divs:
      # 1レコードのカードデータ
      card = {"id": 0, "card_type": "", "link": ""}
      # モンスター・魔法・罠を同定
      card_type = card_div.find(
          "span", class_="box_card_attribute").find("span").get_text()
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
      db.insert(card)
      saved_card = db.search(query.id == id)
      print(f"Saved Data : {saved_card}")

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
      except Exception as e:
        print(e)
      # cardsのサイズがGET_SIZE未満の場合、pageを0にリセットする
      if (record_num < GET_SIZE):
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

