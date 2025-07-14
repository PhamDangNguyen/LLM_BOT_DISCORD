import discord
from discord.ext import commands
from discord import app_commands, File
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import re
import os
from dotenv import load_dotenv
from collections import defaultdict, deque
from google import generativeai as genai

# ==== Load .env ====
load_dotenv()
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if not DISCORD_BOT_TOKEN:
    raise ValueError("❌ Thiếu DISCORD_BOT_TOKEN trong .env")

# ==== Kết nối Google Sheet ====
scope = [
    "https://spreadsheets.google.com/feeds",
    'https://www.googleapis.com/auth/spreadsheets',
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]
credentials = ServiceAccountCredentials.from_json_keyfile_name(
    "keen-truth-457904-j8-94e7a30ce2f7.json", scope)
client = gspread.authorize(credentials)
sheet = client.open("Tiền cơm").sheet1

# ==== Cấu hình Gemini ====
genai.configure(api_key="AIzaSyDXtr3yOe0uX-Qpz5fj8CS_NC3M670kLNc")

model = genai.GenerativeModel(
    "gemini-2.0-flash", 
    system_instruction=(
        "Bạn là một trợ lý AI cục cằn mà láo lếu dùng để tính tiền cơm hàng ngày, luôn trả lời bằng tiếng Việt một cách tự nhiên nhất. "
    )
)

model_owner = genai.GenerativeModel(
    "gemini-2.0-flash", 
    system_instruction=(
        "Bạn là một trợ lý AI cục súc mà hài hước dùng để tính tiền cơm, luôn trả lời bằng tiếng Việt một cách tự nhiên nhất. "
        "luôn lịch sự tận tình trả lời mọi câu hỏi"
    )
)

history = deque(maxlen=100)

OWNER_ID = 1251355260640038953

# ==== Intents & Khởi tạo Bot (CHỈ 1 LẦN) ====
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ==== Giao tiếp bằng mention bot để dùng Gemini ====
MAX_MSG_LENGTH = 2000

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if bot.user in message.mentions:
        user_input = message.content.replace(f"<@{bot.user.id}>", "").strip()
        if not user_input:
            await message.channel.send("🗣️ Có gì muốn nói không?")
            return

        try:
            history.append({"role": "user", "parts": [user_input]})

            if message.author.id == OWNER_ID:
                response = model_owner.generate_content(contents=list(history))
            else:
                response = model.generate_content(contents=list(history))

            history.append({"role": "model", "parts": [response.text]})

            # Gửi từng phần nhỏ nếu response dài quá
            for chunk in [response.text[i:i + MAX_MSG_LENGTH] for i in range(0, len(response.text), MAX_MSG_LENGTH)]:
                await message.channel.send(chunk)

        except Exception as e:
            print("Lỗi Gemini:", e)
            await message.channel.send("❌ Lỗi mịa rồi")

    await bot.process_commands(message)

# ==== Tiền cơm Slash Commands ====
def parse_money(money_str):
    money_str = money_str.lower().replace(',', '').strip()
    if 'k' in money_str:
        num = re.findall(r'\d+', money_str)
        return int(num[0]) * 1000 if num else 0
    try:
        return int(money_str)
    except:
        return 0


class MealCog(commands.Cog):
    def __init__(self, bot, sheet):
        self.bot = bot
        self.sheet = sheet

    @app_commands.command(name="add", description="Thêm tiền cơm vào Google Sheet")
    async def add(self, interaction: discord.Interaction, name: str, money: str, note: str = None):
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("❌ Bạn không có quyền dùng lệnh này.", ephemeral=True)
            return
        name = name.strip().lower().title()
        amount = parse_money(money)
        if amount == 0:
            await interaction.response.send_message("❌ Số tiền không hợp lệ.")
            return

        if not note:
            note = datetime.now().strftime('%d/%m')

        try:
            sheet.append_row([name, amount, note], value_input_option='USER_ENTERED')
            records = self.sheet.get_all_records()
            debt_details = defaultdict(list)

            for row in records:
                person = row['Tên'].strip().lower().title()
                money_val = int(row['Số tiền'])
                date_val = row['Ghi chú']
                debt_details[person].append((money_val, date_val))

            lines = []
            for person in sorted(debt_details):
                lines.append(f"**{person}:**")
                total = 0
                for money_val, date_val in debt_details[person]:
                    lines.append(f"  - {money_val:,}đ  {date_val}")
                    total += money_val
                lines.append(f"  Tổng nợ hiện tại: {total:,}đ\n")

            message = (
                f"✅ Đã thêm: `{name}` - `{amount}`đ - `{note}`\n\n"
                "📊 **Chi tiết nợ:**\n" + "\n".join(lines)
            )
            await interaction.response.send_message(message)

        except Exception as e:
            await interaction.response.send_message(f"❌ Lỗi ghi vào Google Sheet: {e}")

    @app_commands.command(name="list_all", description="Tổng hợp nợ từng người + log theo ngày + ảnh mã QR")
    async def list_all(self, interaction: discord.Interaction):
        try:
            records = self.sheet.get_all_records()
            if not records:
                await interaction.response.send_message("❌ Không có dữ liệu ghi nợ.")
                return

            debt_map = {}
            log_map = {}

            for row in records:
                name = row['Tên'].strip().lower().title()
                amount = int(row['Số tiền'])
                date = row.get('Ghi chú', '???')
                debt_map[name] = debt_map.get(name, 0) + amount
                if name not in log_map:
                    log_map[name] = {}
                log_map[name][date] = log_map[name].get(date, 0) + amount

            lines = ["📊 **Tổng nợ hiện tại:**"]
            for name in sorted(debt_map):
                lines.append(f"- {name}: {debt_map[name]:,}đ")

            lines.append("\n📅 **Chi tiết từng ngày:**\n")
            for name in sorted(log_map):
                lines.append(f"🔸 {name}:")
                for date, amt in sorted(log_map[name].items()):
                    lines.append(f"  • {date}: {amt:,}đ")
                lines.append("")

            message = "\n".join(lines)
            qr_path = "imgs/QR.jpg"
            if os.path.exists(qr_path):
                file = File(qr_path, filename="QR.jpg")
                await interaction.response.send_message(content=message, file=file)
            else:
                await interaction.response.send_message(f"{message}\n⚠️ Không tìm thấy ảnh QR tại `{qr_path}`.")

        except Exception as e:
            await interaction.response.send_message(f"❌ Lỗi khi xử lý: {e}")

    @app_commands.command(name="get_link", description="Lấy link Google Sheet theo dõi cơm")
    async def get_link(self, interaction: discord.Interaction):
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("❌ Bạn không có quyền dùng lệnh này.", ephemeral=True)
            return
        link = "https://docs.google.com/spreadsheets/d/1Z3DxoLJ3f-Ro_TCCAwGz0L97ESw5TMQph-tcKnVZmqQ/edit?gid=0#gid=0"
        await interaction.response.send_message(f"📄 Đây là link Google Sheet:\n{link}", ephemeral=True)

    @app_commands.command(name="reset", description="Xoá toàn bộ nợ của một người khỏi Google Sheet")
    async def reset(self, interaction: discord.Interaction, name: str):
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("❌ Bạn không có quyền dùng lệnh này.", ephemeral=True)
            return
        await interaction.response.defer()

        try:
            all_values = self.sheet.get_all_values()
            if len(all_values) < 2:
                await interaction.followup.send("❌ Sheet trống hoặc không có dữ liệu.")
                return

            headers = all_values[0]
            data_rows = all_values[1:]
            target_name = name.strip().lower().title()
            rows_to_keep = []
            deleted_count = 0

            for row in data_rows:
                if len(row) < 3:
                    continue
                row_name = row[0].strip().lower().title()
                if row_name != target_name:
                    rows_to_keep.append(row)
                else:
                    deleted_count += 1

            if deleted_count == 0:
                await interaction.followup.send(f"❌ Không tìm thấy dữ liệu nào của `{target_name}`.")
                return

            self.sheet.resize(rows=1)
            if rows_to_keep:
                self.sheet.append_rows(rows_to_keep)

            await interaction.followup.send(f"🗑️ Đã xoá {deleted_count} dòng dữ liệu của `{target_name}`.")
        except Exception as e:
            await interaction.followup.send(f"❌ Lỗi khi xoá dữ liệu: {e}")


# ==== Khi bot khởi động ====
@bot.event
async def on_ready():
    await bot.add_cog(MealCog(bot, sheet))
    try:
        synced = await bot.tree.sync()
        print(f"✅ Slash command đã sync ({len(synced)} lệnh)")
    except Exception as e:
        print(f"❌ Lỗi sync lệnh: {e}")
    print(f"🤖 Bot đang hoạt động: {bot.user}")


# ==== Chạy bot ====
if __name__ == "__main__":
    bot.run(DISCORD_BOT_TOKEN)
