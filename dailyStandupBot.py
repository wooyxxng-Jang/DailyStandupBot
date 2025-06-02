import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import datetime
import json
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")


CHANNEL_ID = 1378788697104977920
USER_ID = 820655822954692639  # 우영이 ID

DATA_FILE = "daily_data.json"

intents = discord.Intents.default()
intents.message_content = True
intents.dm_messages = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
scheduler = AsyncIOScheduler()

# ✅ 데이터 저장/불러오기
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)
        
def format_todolist(text):
    # 줄바꿈 기준으로 split 후, 각 줄 앞에 - 붙여서 다시 join
    lines = text.strip().split("\n")
    return "\n".join([f"- {line.strip()}" for line in lines if line.strip()])

# ✅ 질문 상태 추적용 메모리
user_states = {}

# ✅ 1. 오전 10시에 자동 DM 보내기
async def send_daily_checkin():
    user = await bot.fetch_user(USER_ID)
    if not user:
        return

    data = load_data()
    today = str(datetime.date.today())
    yesterday = str(datetime.date.today() - datetime.timedelta(days=1))

    yesterday_plan = data.get(str(USER_ID), {}).get(yesterday, {}).get("today_plan", "없음")

    msg = f"🌞 데일리 스탠드업 시간입니다~!\n어제 계획은 `{yesterday_plan}` 였어요.\n어제를 회고해보세요!"
    await user.send(msg)

    # 상태 저장
    user_states[USER_ID] = {
        "step": "yesterday_result",
        "date": today,
        "yesterday_plan": yesterday_plan,
        "partial": {}
    }

# ✅ 2. DM 응답 처리
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if isinstance(message.channel, discord.DMChannel) and message.author.id == USER_ID:
        state = user_states.get(USER_ID)

        if not state:
            return

        data = load_data()
        today = state["date"]

        if message.content.lower() == "취소":
            await message.channel.send("❌ 스탠드업 취소")
            user_states.pop(USER_ID, None)
            return

        # 1단계: 어제 한 일
        if state["step"] == "yesterday_result":
            state["partial"]["yesterday_result"] = message.content
            state["step"] = "today_plan"
            await message.channel.send("👍 오늘 할 일은 무엇인가요?")
            return
        # 2단계: 오늘 계획
        if state["step"] == "today_plan":
            state["partial"]["today_plan"] = message.content

            # 저장
            if str(USER_ID) not in data:
                data[str(USER_ID)] = {}
            data[str(USER_ID)][today] = state["partial"]
            save_data(data)

            # ✅ 요약 메시지 만들기 (함수 안으로 옮김!)
            user_name = message.author.display_name
            today_str = datetime.date.today().strftime("%m/%d")

            summary = f"""📣 [{user_name}의 {today_str} 데일리 스탠드업]

📌 어제 계획
{format_todolist(state['yesterday_plan'])}

✅ 어제 결과
{format_todolist(state['partial']['yesterday_result'])}

🗓 오늘 할 일
{format_todolist(state['partial']['today_plan'])}

🔥 파이팅입니다! 오늘도 좋은 하루 되세요!
"""

            # 응원 메시지 보내고
            await message.channel.send("파이팅~~ 오늘도 좋은 하루 되세용😄🎶")

            # 채널에 전송
            channel = bot.get_channel(CHANNEL_ID)
            if channel:
                await channel.send(summary)

            # 상태 초기화
            user_states.pop(USER_ID, None)
            return

    await bot.process_commands(message)

# ✅ 봇 실행 준비
@bot.event
async def on_ready():
    print(f"✅ {bot.user} 봇이 온라인입니다!")
    scheduler.add_job(send_daily_checkin, 'cron', hour=10, minute=00)
    scheduler.start()

bot.run(TOKEN)