from flask import Flask, request, render_template, redirect, url_for
from linebot.v3.messaging import Configuration, MessagingApi
from linebot.v3.messaging import PushMessageRequest
from linebot.v3.webhook import WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import TextSendMessage, MessageEvent, TextMessage, Sender
import sqlite3
import os
from flask import abort

app = Flask(__name__)

# 環境変数からLINEのチャンネルアクセストークンとシークレットを取得
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')

# 環境変数が設定されていない場合のエラーチェック
if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_CHANNEL_SECRET:
    raise ValueError("LINE_CHANNEL_ACCESS_TOKEN と LINE_CHANNEL_SECRET の環境変数を設定してください。")

configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
line_bot_api = MessagingApi(configuration)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# データベースの初期化
def init_db():
    with sqlite3.connect('messages.db') as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS messages
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id TEXT,
                      message TEXT)''')
        conn.commit()

init_db()

@app.route('/')
def home():
    # データベースからメッセージを取得
    with sqlite3.connect('messages.db') as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM messages ORDER BY id DESC")  # 最新のメッセージを先に表示
        messages = c.fetchall()
    return render_template('admin.html', messages=messages)


# ユーザーからのメッセージを受信するエンドポイント
@app.route("/callback", methods=['POST'])
def callback():
    # リクエストヘッダーから署名を取得
    signature = request.headers['X-Line-Signature']
    # リクエストボディを取得
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # 署名を検証してイベントを処理
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# メッセージイベントのハンドラー
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    user_message = event.message.text

    # メッセージをデータベースに保存
    with sqlite3.connect('messages.db') as conn:
        c = conn.cursor()
        c.execute("INSERT INTO messages (user_id, message) VALUES (?, ?)", (user_id, user_message))
        conn.commit()

    # ユーザーに自動返信（必要に応じて）
    reply_text = "メッセージを受け付けました。担当者からの返信をお待ちください。"
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        user_id = request.form['user_id']
        reply_message = request.form['reply_message']
        staff_name = request.form['staff_name']
        staff_icon_url = request.form['staff_icon_url']

        # ユーザーに返信メッセージを送信
        try:
            line_bot_api.push_message_with_http_info(
                PushMessageRequest(
                    to=user_id,
                    messages=[TextMessage(
                        text=reply_message,
                        sender={
                            "name": staff_name,
                            "iconUrl": staff_icon_url
                        }
                    )]
                )
            )
        except Exception as e:
            print(f"メッセージ送信エラー: {e}")
            # エラー処理を追加することができます

        return redirect(url_for('admin'))

    # データベースからメッセージを取得
    with sqlite3.connect('messages.db') as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM messages ORDER BY id DESC")  # 最新のメッセージを先に表示
        messages = c.fetchall()
    return render_template('admin.html', messages=messages)


if __name__ == "__main__":
    app.run(debug=True)
