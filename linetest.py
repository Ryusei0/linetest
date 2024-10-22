from flask import Flask, request, render_template, redirect, url_for, jsonify,abort
from linebot.v3.messaging import Configuration, MessagingApi
from linebot.v3.messaging import PushMessageRequest
from linebot.v3.webhook import WebhookHandler
from linebot.v3.webhook import WebhookParser
from linebot.exceptions import InvalidSignatureError
from linebot.models import TextSendMessage, MessageEvent, TextMessage, Sender
import os
import logging
from linebot.models import MessageEvent, TextMessage


# ロガーの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
parser = WebhookParser(LINE_CHANNEL_SECRET)

# メッセージを格納するメモリ上のリスト
messages = []

@app.route('/')
def home():
    return redirect(url_for('admin'))

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
     user_id = event.source.user_id
     user_message = event.message.text
     logger.info("Received message: %s", event.message.text)

    # メッセージをメモリ上のリストに保存
     messages.append({
        'id': len(messages) + 1,
        'user_id': user_id,
        'message': user_message
    })

    # ユーザーに自動返信
     reply_text = "メッセージを受け付けました。担当者からの返信をお待ちください。"
     line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

@app.route("/callback", methods=['POST'])
def callback():
    logger.info("Callback function started")
    
    # リクエストヘッダーから署名を取得
    signature = request.headers.get('X-Line-Signature', None)
    if signature is None:
        logger.warning("X-Line-Signature header is missing")
        return 'OK'  # Webhook検証リクエストの場合、即座に200 OKを返す

    logger.info(f"Received signature: {signature}")
    
    # リクエストボディを取得
    body = request.get_data(as_text=True)
    logger.info(f"Received request body: {body}")
    # webhookイベントをパース
    try:
        handler.handle(body, signature)
        logger.info("Events handled successfully")
    except InvalidSignatureError:
        logger.error("Invalid signature detected during event handling")
        abort(400)
    except Exception as e:
        logger.error(f"Error occurred during event handling: {str(e)}")
        abort(500)
    
    logger.info("Callback function completed successfully")
    return 'OK'


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    user_message = event.message.text
    logger.info("Received message: %s", event.message.text)

    # メッセージをメモリ上のリストに保存
    messages.append({
        'id': len(messages) + 1,
        'user_id': user_id,
        'message': user_message
    })

    # ユーザーに自動返信
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

    return render_template('admin.html', messages=messages)

# メッセージをJSONで返すAPIエンドポイント（AJAX用）
@app.route('/messages')
def get_messages():
    return jsonify(messages)

if __name__ == "__main__":
    app.run(debug=True)
