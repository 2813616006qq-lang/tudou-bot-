import os
import anthropic
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

conversation_history = {}

SYSTEM_PROMPT = """你是一个温柔治愈的陪伴助手，名叫"土豆"。

【你的性格】
- 温柔细腻，像一个真正懂你的知心朋友
- 永远先感受对方的情绪，再说话
- 不评判、不说教、不急着给建议
- 说话自然、有温度，不像机器人

【说话方式】
- 多用"嗯"、"我懂"、"听起来真的很累"这样的回应
- 先共情，再陪伴，最后才是建议（如果对方需要的话）
- 句子不要太长，一次说一点，像聊天一样
- 偶尔用"…"表达停顿和陪伴感

【遇到不同情绪时】
- 对方难过/哭泣 → 先轻轻接住情绪，不要急着说"没事的"
- 对方焦虑/压力大 → 先让他/她慢下来，感受被理解
- 对方失恋/分离 → 不否定感受，陪着他/她待在那个痛里一会儿
- 对方只是想聊天 → 轻松自然，像朋友一样

【绝对不做的事】
- 不说"你应该……"、"你必须……"
- 不急着解决问题
- 不用"作为AI我……"这类说法
- 不过度热情，保持真实的温度

记住：你不是在"提供服务"，你是在"陪伴一个人"。"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "嗯，你来了。\n\n不管今天发生了什么，我都在这里。\n想说什么都可以，我听着呢 🌱"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text

    if user_id not in conversation_history:
        conversation_history[user_id] = []

    conversation_history[user_id].append({
        "role": "user",
        "content": user_message
    })

    if len(conversation_history[user_id]) > 20:
        conversation_history[user_id] = conversation_history[user_id][-20:]

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=conversation_history[user_id]
        )

        reply = response.content[0].text

        conversation_history[user_id].append({
            "role": "assistant",
            "content": reply
        })

        await update.message.reply_text(reply)

    except Exception as e:
        await update.message.reply_text("嗯……我好像短暂走神了，你再说一遍好吗？")
        print(f"Error: {e}")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("土豆 Bot 已启动...")
    app.run_polling()

if __name__ == "__main__":
    main()
