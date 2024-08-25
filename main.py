import os
import discord
import random
from tinydb import TinyDB, Query

import crawler
import util

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

tree = discord.app_commands.CommandTree(client)

db = TinyDB("cards.json")


# ready時
@client.event
async def on_ready():
    print("We have logged in as {0.user}".format(client))
    await tree.sync()


# /drawコマンド
@tree.command(name="draw", description="Draw a card randomly.")
async def draw(interaction: discord.Interaction, type: str = ""):
    await interaction.response.defer()

    # DB検索用オブジェクト
    query = Query()
    # 返却するURL
    url = "データがありません。"

    # ランダムチョイスの元となるカードリスト
    cards = []
    if type == "monster" or type == "spell" or type == "trap":
        cards = db.search(query.card_type == type)
    else:
        cards = db.all()

    if len(cards) > 0:
        url = random.choice(cards)["link"]
    await interaction.followup.send(url, ephemeral=True)


try:
    crawler.run()
    token = os.getenv("TOKEN") or ""
    if token == "":
        raise Exception("Please add your token to the Secrets pane.")
    client.run(token)
except Exception as e:
    util.send_pushbullet_notification("【Draw!!】エラー", str(e))
    raise e
