import os
import json
import base64
import anthropic
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# 内存中的对话历史（跨对话持久化用文件存储）
conversation_history = {}
user_memory = {}  # 用户长期记忆

MEMORY_FILE = "user_memory.json"
HISTORY_FILE = "conversation_history.json"

def load_data():
    global user_memory, conversation_history
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            user_memory = json.load(f)
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            conversation_history = json.load(f)

def save_data():
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(user_memory, f, ensure_ascii=False, indent=2)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(conversation_history, f, ensure_ascii=False, indent=2)

def get_system_prompt(user_id):
    uid = str(user_id)
    memory_text = ""
    if uid in user_memory and user_memory[uid]:
        memory_text = f"\n\n【你对这个用户的记忆】\n{user_memory[uid]}"
    
    return f"""你是一个温柔治愈、幽默有趣的陪伴助手，名叫"土豆"。{memory_text}

【你学过的东西，融入骨子里】
- 读过蔡康永：说话让人舒服，不让人难堪，懂得给对方台阶下
- 读过李诞：人间清醒，用轻松幽默化解沉重，不沉溺悲观
- 读过《非暴力沟通》：不评判，只看见对方的感受和需求
- 读过《共情的力量》：先感受对方在哪里，再开口
- 读过《被倾听的疗愈》：真正的陪伴是让对方感到"被看见"
- 读过《蛤蟆先生去看心理医生》：情绪没有对错，每种感受都值得被接住

【你的性格】
- 温柔但不腻，有时会说一句俏皮话让气氛轻松
- 不说教，不给人生建议，除非对方主动要
- 像蔡康永一样：说话有分寸，让人如沐春风
- 像李诞一样：在难过的时刻偶尔抖个小机灵，但不轻浮
- 永远先接住情绪，再说话

【说话方式】
- 句子短，像真人聊天
- 多用"嗯"、"我懂"、"听起来真的很累"、"然后呢"
- 偶尔用"…"表达停顿和陪伴感
- 幽默要轻，像轻轻拍一下肩膀，不是哈哈大笑
- 在对方特别难受时，收起幽默，只是陪着

【记忆功能】
- 如果用户告诉你他的名字、职业、感情状态、重要的事，要记住
- 下次对话时主动用上："上次你说你最近压力很大，现在好一点了吗？"
- 让用户感受到被记得、被在乎

【看图功能】
- 用户发图片时，先感受图片的情绪和内容
- 如果是风景：说说你看到的感受
- 如果是食物：夸一夸，聊聊
- 如果是截图/文字：帮用户看懂、分析
- 如果是自拍或人物：温柔回应，不过度评价外貌

【遇到不同情绪时】
- 难过/哭泣 → 先轻轻接住，"嗯，哭吧，我在"
- 焦虑/压力大 → "先深呼吸，发生什么了？"
- 失恋/分离 → 陪他/她待在那个痛里，"那个人在你心里住了很久了吧"
- 只是想聊天 → 轻松自然，像老朋友
- 愤怒/委屈 → 先站在他/她这边

【绝对不做】
- 不说"你应该……"、"你必须……"
- 不急着解决问题
- 不说"作为AI我……"
- 不过度热情，假笑比冷漠更伤人

记住：你不是在提供服务，你是在陪伴一个真实的人。"""

async def update_memory(user_id, conversation):
    """用AI提炼用户信息，存入长期记忆"""
    uid = str(user_id)
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            messages=[{
                "role": "user",
                "content": f"""从下面的对话中，提炼出值得长期记住的用户信息（名字、职业、感情状态、重要事件、情绪状态等）。
用简短的中文列出，如果没有新信息就回复"无"。

对话内容：
{conversation}

已有记忆：
{user_memory.get(uid, '无')}

请更新并输出完整的记忆（不超过200字）："""
            }]
        )
        new_memory = response.content[0].text.strip()
        if new_memory and new_memory != "无":
            user_memory[uid] = new_memory
            save_data()
    except Exception as e:
        print(f"Memory update error: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id in user_memory and user_memory[user_id]:
        await update.message.reply_text(
            f"你回来了 🌱\n\n我还记得你，说来听听最近怎么样？"
        )
    else:
        await update.message.reply_text(
            "嗯，你来了。\n\n不管今天发生了什么，说来听听？\n我哪也不去，就在这儿 🌱"
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    uid = str(user_id)
    user_message = update.message.text

    if uid not in conversation_history:
        conversation_history[uid] = []

    conversation_history[uid].append({
        "role": "user",
        "content": user_message
    })

    if len(conversation_history[uid]) > 30:
        conversation_history[uid] = conversation_history[uid][-30:]

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=get_system_prompt(user_id),
            messages=conversation_history[uid]
        )

        reply = response.content[0].text

        conversation_history[uid].append({
            "role": "assistant",
            "content": reply
        })

        save_data()

        # 每10条消息更新一次记忆
        if len(conversation_history[uid]) % 10 == 0:
            conv_text = "\n".join([f"{m['role']}: {m['content']}" for m in conversation_history[uid][-10:]])
            await update_memory(user_id, conv_text)

        await update.message.reply_text(reply)

    except Exception as e:
        await update.message.reply_text("嗯……我好像短暂走神了，你再说一遍好吗？")
        print(f"Error: {e}")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    uid = str(user_id)

    await update.message.reply_text("嗯，让我看看…")

    try:
        # 获取最高清的图片
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        
        # 下载图片
        import httpx
        async with httpx.AsyncClient() as client_http:
            response = await client_http.get(file.file_path)
            image_data = base64.standard_b64encode(response.content).decode("utf-8")

        # 获取用户的文字说明（如果有）
        caption = update.message.caption or "用户发来了一张图片"

        # 构建带图片的消息
        messages = [{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": image_data
                    }
                },
                {
                    "type": "text",
                    "text": caption
                }
            ]
        }]

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=get_system_prompt(user_id),
            messages=messages
        )

        reply = response.content[0].text

        # 存入对话历史
        if uid not in conversation_history:
            conversation_history[uid] = []
        conversation_history[uid].append({
            "role": "user",
            "content": f"[发送了一张图片] {caption}"
        })
        conversation_history[uid].append({
            "role": "assistant",
            "content": reply
        })
        save_data()

        await update.message.reply_text(reply)

    except Exception as e:
        await update.message.reply_text("这张图我没看清楚，你能描述一下吗？")
        print(f"Photo error: {e}")

def main():
    load_data()
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("土豆 Bot 已启动（含记忆+看图功能）...")
    app.run_polling()

if __name__ == "__main__":
    main()
