import os
from pushbullet import Pushbullet


# Pushbulletで通知を送る関数
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
