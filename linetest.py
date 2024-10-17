from flask import Flask, request, render_template, redirect, url_for
from linebot.v3.messaging import Configuration, MessagingApi
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

# ルートパスへのハンドラーを追加
@app.route('/')
def home():
    return 'Hello, this is the LINE Bot server!'

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

# 担当者用のメッセージ閲覧・返信ページ
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        user_id = request.form['user_id']
        reply_message = request.form['reply_message']
        staff_name = request.form['staff_name']
        staff_icon_url = request.form['staff_icon_url']  # 新たにアイコンURLを取得

        # Senderオブジェクトを作成
        sender = Sender(
            name=staff_name,
            icon_url=staff_icon_url
        )

        # ユーザーに返信メッセージを送信
        line_bot_api.push_message(
            user_id,
            TextSendMessage(
                text=reply_message,
                sender=sender
            )
        )
        return redirect(url_for('admin'))

    # データベースからメッセージを取得
    with sqlite3.connect('messages.db') as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM messages")
        messages = c.fetchall()
    return render_template('admin.html', messages=messages)

# テンプレートの設定（admin.html）
# 以下はtemplates/admin.htmlの内容です。
"""
<!DOCTYPE html>
<html>
<head>
    <title>管理者ページ</title>
</head>
<body>
    <h1>受信メッセージ一覧</h1>
    <table border="1">
        <tr>
            <th>ID</th>
            <th>ユーザーID</th>
            <th>メッセージ</th>
            <th>返信</th>
        </tr>
        {% for message in messages %}
        <tr>
            <td>{{ message[0] }}</td>
            <td>{{ message[1] }}</td>
            <td>{{ message[2] }}</td>
            <td>
                <form method="post">
                    <input type="hidden" name="user_id" value="{{ message[1] }}">
                    <input type="text" name="reply_message" placeholder="返信内容" required><br>
                    <input type="text" name="staff_name" placeholder="担当者名（必須）" required><br>
                    <input type="text" name="staff_icon_url" placeholder="アイコンURL（任意）"><br>
                    <button type="submit">返信</button>
                </form>
            </td>
        </tr>
        {% endfor %}
    </table>
</body>
</html>
"""

if __name__ == "__main__":
    app.run(debug=True)
