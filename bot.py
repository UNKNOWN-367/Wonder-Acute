import os
import random
import datetime
import json
import threading
from flask import Flask
import discord
from discord import app_commands
from discord.ext import commands

# ==================== PHẦN 1: FLASK WEB SERVER (GIỮ BOT SỐNG 24/7) ====================
app = Flask(__name__)

@app.route('/')
def home():
    return "Ensure Economy Bot (Full Slash Commands) is running 24/7!"

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, use_reloader=False)

# Chạy web server bằng luồng ngầm
threading.Thread(target=run_web_server, daemon=True).start()


# ==================== PHẦN 2: QUẢN LÝ DỮ LIỆU BẰNG FILE JSON ====================
DATA_FILE = "ensure_data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        default_data = {"users": {}, "cooldowns": {}, "robbery": {}, "disabled": {}}
        save_data(default_data)
        return default_data
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "users" not in data: data["users"] = {}
            if "cooldowns" not in data: data["cooldowns"] = {}
            if "robbery" not in data: data["robbery"] = {}
            if "disabled" not in data: data["disabled"] = {}
            return data
    except Exception:
        return {"users": {}, "cooldowns": {}, "robbery": {}, "disabled": {}}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_user(data, user_id):
    str_id = str(user_id)
    if str_id not in data["users"]:
        data["users"][str_id] = {"balance": 0, "joined": False}
        save_data(data)
    return data["users"][str_id]

def get_balance(data, user_id):
    user = get_user(data, user_id)
    return user.get("balance", 0)

def update_balance(data, user_id, amount):
    str_id = str(user_id)
    user = get_user(data, user_id)
    user["balance"] = user.get("balance", 0) + amount
    save_data(data)
    return user["balance"]


# ==================== PHẦN 3: KHỞI TẠO BOT & SLASH COMMANDS ====================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # Bật intent quản lý thành viên để lấy tên hiển thị chuẩn xác

class EnsureBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("Đã đồng bộ thành công các lệnh Slash Commands (/) với Discord!")

bot = EnsureBot()

@bot.event
async def on_ready():
    print(f'Đã đăng nhập thành công với tên: {bot.user}')
    print('Hệ thống kinh tế Ensure đầy đủ tính năng đã sẵn sàng!')


# ==================== CÁC LỆNH SLASH COMMANDS (/) ====================

# 1. Lệnh /help
@bot.tree.command(name="help", description="Xem danh sách toàn bộ các lệnh hệ thống Ensure")
async def slash_help(interaction: discord.Interaction):
    help_text = (
        "📜 **DANH SÁCH CÁC LỆNH HỆ THỐNG ENSURE** 📜\n\n"
        "• `/join`: Nhận vốn khởi nghiệp từ 100 đến 500 chai ensure.\n"
        "• `/storage`: Kiểm tra số lượng chai ensure trong kho.\n"
        "• `/work`: Đi làm kiếm từ 1 đến 50 chai ensure (Cooldown 1 giờ).\n"
        "• `/pay`: Chuyển tối đa 5000 chai ensure cho người khác (Hỗ trợ tag tên hoặc nhập ID).\n"
        "• `/rob`: Cướp ensure của người khác (Hỗ trợ tag tên hoặc nhập ID).\n"
        "• `/defend`: Nạn nhân tự trả thù vụ cướp trong vòng 3 giờ đầu.\n"
        "• `/defendfor`: Cứu bồ khi defend hụt hoặc trong 30 phút tiếp theo.\n"
        "• `/duel`: Chơi Russian Roulette cược ensure theo cấp độ từ 1 đến 10.\n"
        "• `/duel_info`: Xem bảng thông tin chi tiết các cấp độ Duel.\n"
        "• `/leaderboard`: Xem bảng xếp hạng top những người giàu nhất (Hiện tên, không ping).\n"
        "• `/give`: Phát ensure cho thành viên (Hỗ trợ tag tên hoặc nhập ID - Chỉ Server Owner).\n"
        "• `/forgive`: Gỡ lệnh cấm chơi `/duel` cho thành viên (Chỉ Admin)."
    )
    await interaction.response.send_message(help_text)


# 2. Lệnh /join (Khởi nghiệp)
@bot.tree.command(name="join", description="Nhận vốn khởi nghiệp chai ensure (Chỉ 1 lần duy nhất)")
async def slash_join(interaction: discord.Interaction):
    data = load_data()
    user_id = interaction.user.id
    user = get_user(data, user_id)

    if user.get("joined", False):
        await interaction.response.send_message(f"⚠️ {interaction.user.mention}, bạn đã nhận vốn khởi nghiệp từ trước rồi!", ephemeral=True)
        return

    starting_money = random.randint(100, 500)
    update_balance(data, user_id, starting_money)
    data["users"][str(user_id)]["joined"] = True
    save_data(data)

    await interaction.response.send_message(f"🎁 Chúc mừng {interaction.user.mention} đã khởi nghiệp thành công và nhận được **{starting_money} chai ensure**!")


# 3. Lệnh /storage (Kiểm tra kho)
@bot.tree.command(name="storage", description="Kiểm tra số lượng chai ensure trong kho của bạn")
async def slash_storage(interaction: discord.Interaction):
    data = load_data()
    bal = get_balance(data, interaction.user.id)
    await interaction.response.send_message(f"📦 {interaction.user.mention}, kho của bạn hiện có: **{bal} chai ensure**.")


# 4. Lệnh /work (Cày cuốc)
@bot.tree.command(name="work", description="Đi làm chăm chỉ để kiếm thêm chai ensure (Cooldown 1 giờ)")
async def slash_work(interaction: discord.Interaction):
    data = load_data()
    user_id = str(interaction.user.id)
    now = datetime.datetime.now()

    if "cooldowns" not in data:
        data["cooldowns"] = {}

    cd_doc = data["cooldowns"].get(user_id, {})
    if "last_work" in cd_doc:
        last_time = datetime.datetime.fromisoformat(cd_doc["last_work"])
        elapsed = (now - last_time).total_seconds()
        if elapsed < 3600:
            remaining = int(3600 - elapsed)
            mins = remaining // 60
            secs = remaining % 60
            await interaction.response.send_message(f"⏳ {interaction.user.mention}, bạn đang mệt! Hãy nghỉ ngơi thêm **{mins} phút {secs} giây** nữa mới được `/work` tiếp.", ephemeral=True)
            return

    earned = random.randint(1, 50)
    new_bal = update_balance(data, interaction.user.id, earned)
    
    data["cooldowns"][user_id] = data["cooldowns"].get(user_id, {})
    data["cooldowns"][user_id]["last_work"] = now.isoformat()
    save_data(data)

    await interaction.response.send_message(f"💼 {interaction.user.mention} đã chăm chỉ làm việc và kiếm được **{earned} chai ensure**! *(Tổng kho: {new_bal} chai)*")


# 5. Lệnh /pay (Chuyển tiền - Hỗ trợ cả tag tên lẫn nhập ID)
@bot.tree.command(name="pay", description="Chuyển chai ensure cho thành viên khác (Tối đa 5000)")
@app_commands.describe(target="Tag tên hoặc nhập ID Discord người nhận", amount="Số lượng chai ensure cần chuyển")
async def slash_pay(interaction: discord.Interaction, target: str, amount: int):
    data = load_data()
    sender_id = interaction.user.id

    # Xử lý chuỗi target để hỗ trợ cả dạng tag (<@ID> hoặc <@!ID>) lẫn dạng nhập ID thuần túy
    clean_id_str = target.replace("<@", "").replace(">", "").replace("!", "")
    if not clean_id_str.isdigit():
        await interaction.response.send_message("⚠️ Thành viên không hợp lệ! Vui lòng tag đúng người hoặc nhập đúng ID Discord.", ephemeral=True)
        return
    
    receiver_id = int(clean_id_str)

    if sender_id == receiver_id:
        await interaction.response.send_message("⚠️ Bạn không thể tự chuyển cho chính mình được!", ephemeral=True)
        return

    if amount <= 0 or amount > 5000:
        await interaction.response.send_message("⚠️ Số lượng chuyển phải lớn hơn 0 và tối đa là **5000 chai ensure**!", ephemeral=True)
        return

    sender_bal = get_balance(data, sender_id)
    if sender_bal < amount:
        await interaction.response.send_message("⚠️ Kho của bạn không đủ ensure để thực hiện giao dịch này!", ephemeral=True)
        return

    # Lấy tên hiển thị của người nhận nếu có trong server
    receiver_member = interaction.guild.get_member(receiver_id)
    receiver_name = receiver_member.display_name if receiver_member else f"User {receiver_id}"

    update_balance(data, sender_id, -amount)
    update_balance(data, receiver_id, amount)

    await interaction.response.send_message(f"💸 {interaction.user.mention} đã chuyển thành công **{amount} chai ensure** cho **{receiver_name}**!")


# 6. Lệnh /rob (Cướp bóc - Hỗ trợ tag tên hoặc nhập ID)
@bot.tree.command(name="rob", description="Cướp ensure của người khác")
@app_commands.describe(target="Tag tên hoặc nhập ID mục tiêu (để trống để cướp ngẫu nhiên)")
async def slash_rob(interaction: discord.Interaction, target: str = None):
    data = load_data()
    robber_id = str(interaction.user.id)
    now = datetime.datetime.now()

    robber_user = get_user(data, interaction.user.id)
    if not robber_user.get("joined", False):
        await interaction.response.send_message("⚠️ Bạn phải `/join` nhận vốn khởi nghiệp trước thì mới được đi cướp bóc!", ephemeral=True)
        return

    if "cooldowns" not in data:
        data["cooldowns"] = {}

    cd_doc = data["cooldowns"].get(robber_id, {})
    if "last_rob" in cd_doc:
        last_rob_time = datetime.datetime.fromisoformat(cd_doc["last_rob"])
        elapsed_rob = (now - last_rob_time).total_seconds()
        if elapsed_rob < 3600:
            remaining_rob = int(3600 - elapsed_rob)
            mins_r = remaining_rob // 60
            secs_r = remaining_rob % 60
            await interaction.response.send_message(f"⏳ Bạn vừa mới đi cướp về! Hãy đợi thêm **{mins_r} phút {secs_r} giây** nữa.", ephemeral=True)
            return

    if target is not None:
        clean_id_str = target.replace("<@", "").replace(">", "").replace("!", "")
        if not clean_id_str.isdigit():
            await interaction.response.send_message("⚠️ Mục tiêu không hợp lệ! Vui lòng tag đúng người hoặc nhập đúng ID Discord.", ephemeral=True)
            return
        victim_id = int(clean_id_str)

        if victim_id == interaction.user.id:
            await interaction.response.send_message("⚠️ Bạn không thể tự cướp kho của chính mình!", ephemeral=True)
            return
        vic_doc = get_user(data, victim_id)
        if not vic_doc.get("joined", False):
            await interaction.response.send_message("⚠️ Mục tiêu bạn muốn cướp chưa từng `/join` khởi nghiệp nên không có gì để cướp!", ephemeral=True)
            return
        
        victim_member = interaction.guild.get_member(victim_id)
        victim_name = f"**{victim_member.display_name}**" if victim_member else f"User {victim_id}"
    else:
        all_joined = [uid for uid, info in data["users"].items() if info.get("joined") and uid != robber_id]
        if not all_joined:
            await interaction.response.send_message("⚠️ Hiện tại không có mục tiêu nào khả dĩ để cướp cả!", ephemeral=True)
            return
        victim_id = int(random.choice(all_joined))
        victim_member = interaction.guild.get_member(victim_id)
        victim_name = f"**{victim_member.display_name}**" if victim_member else f"User {victim_id}"

    is_failed = random.random() < 0.40
    data["cooldowns"][robber_id] = data["cooldowns"].get(robber_id, {})
    data["cooldowns"][robber_id]["last_rob"] = now.isoformat()
    save_data(data)

    if is_failed:
        try:
            duration = datetime.timedelta(seconds=60)
            await interaction.user.timeout(duration, reason="Cướp bóc thất bại!")
            await interaction.response.send_message(f"🚨 **BẮT QUẢ TANG!** {interaction.user.mention} đi cướp ensure nhưng bị tóm gọn, ăn ngay quả timeout **1 phút**! 🚓")
        except Exception:
            await interaction.response.send_message(f"🚨 {interaction.user.mention} cướp hụt nhưng may thoát cảnh sát vì bot thiếu quyền Timeout!")
    else:
        stolen_amount = random.randint(1, 100)
        victim_bal = get_balance(data, victim_id)
        
        actual_stolen = min(stolen_amount, victim_bal)
        if actual_stolen <= 0:
            await interaction.response.send_message(f"🥷 {interaction.user.mention} đã đột nhập vào kho của {victim_name} nhưng phát hiện trống rỗng không có chai ensure nào!")
            return

        update_balance(data, victim_id, -actual_stolen)
        update_balance(data, interaction.user.id, actual_stolen)

        if "robbery" not in data:
            data["robbery"] = {}

        data["robbery"][str(victim_id)] = {
            "robber_id": interaction.user.id,
            "amount": actual_stolen,
            "time": now.isoformat(),
            "defended": False,
            "defend_failed": False,
            "helpers": []
        }
        save_data(data)

        await interaction.response.send_message(
            f"🥷 **CƯỚP THÀNH CÔNG!** {interaction.user.mention} đã cướp được **{actual_stolen} chai ensure** từ {victim_name}!\n"
            f"⏳ *Nạn nhân có **3 giờ** để dùng lệnh `/defend` trả thù đòi lại.*"
        )


# 7. Lệnh /defend (Trả thù)
@bot.tree.command(name="defend", description="Nạn nhân tự trả thù vụ cướp trong vòng 3 giờ đầu")
async def slash_defend(interaction: discord.Interaction):
    data = load_data()
    victim_id = str(interaction.user.id)
    now = datetime.datetime.now()

    robbery_records = data.get("robbery", {})
    if victim_id not in robbery_records:
        await interaction.response.send_message("⚠️ Bạn không có vụ cướp nào cần trả thù cả!", ephemeral=True)
        return

    record = robbery_records[victim_id]
    if record["defended"]:
        await interaction.response.send_message("⚠️ Vụ cướp này đã được xử lý xong xuôi rồi!", ephemeral=True)
        return

    record_time = datetime.datetime.fromisoformat(record["time"])
    elapsed_hours = (now - record_time).total_seconds() / 3600
    if elapsed_hours > 3:
        await interaction.response.send_message("⏰ Đã quá thời hạn 3 giờ để `/defend` trả thù! Người khác có thể dùng `/defendfor` để cứu bồ.", ephemeral=True)
        return

    robber_id = record["robber_id"]
    amount = record["amount"]
    is_success = random.random() < 0.50

    robber_member = interaction.guild.get_member(int(robber_id))
    robber_name = f"**{robber_member.display_name}**" if robber_member else f"User {robber_id}"

    if is_success:
        record["defended"] = True
        save_data(data)

        robber_bal = get_balance(data, robber_id)
        refund_amount = min(amount, robber_bal)
        
        update_balance(data, robber_id, -refund_amount)
        update_balance(data, interaction.user.id, refund_amount)

        await interaction.response.send_message(f"⚔️ **PHỤC THÙ THÀNH CÔNG!** {interaction.user.mention} đã đánh bại tên cướp {robber_name} và đòi lại **{refund_amount} chai ensure**!")
    else:
        record["defend_failed"] = True
        save_data(data)
        await interaction.response.send_message(f"❌ {interaction.user.mention} phản công thất bại! **Cơ hội cứu bồ (`/defendfor`) đã được kích hoạt ngay lập tức**!")


# 8. Lệnh /defendfor (Cứu bồ)
@bot.tree.command(name="defendfor", description="Cứu bồ / ăn hôi khi defend hụt hoặc trong 30 phút tiếp theo")
@app_commands.describe(target="Tag tên hoặc nhập ID thành viên cần cứu giúp")
async def slash_defendfor(interaction: discord.Interaction, target: str):
    data = load_data()
    helper_id = interaction.user.id

    clean_id_str = target.replace("<@", "").replace(">", "").replace("!", "")
    if not clean_id_str.isdigit():
        await interaction.response.send_message("⚠️ Thành viên không hợp lệ! Vui lòng tag đúng người hoặc nhập đúng ID Discord.", ephemeral=True)
        return
    
    victim_id = clean_id_str
    now = datetime.datetime.now()

    robbery_records = data.get("robbery", {})
    if victim_id not in robbery_records:
        await interaction.response.send_message("⚠️ Người chơi này không có lịch sử bị cướp nào cần cứu viện!", ephemeral=True)
        return

    record = robbery_records[victim_id]
    if record["defended"]:
        await interaction.response.send_message("⚠️ Vụ cướp này đã được giải quyết xong xuôi rồi!", ephemeral=True)
        return

    helpers = record.get("helpers", [])
    if len(helpers) >= 3:
        await interaction.response.send_message("⚠️ Vụ cướp này đã đủ tối đa 3 người cứu giúp tham gia rồi!", ephemeral=True)
        return

    if helper_id == int(victim_id) or helper_id == int(record["robber_id"]):
        await interaction.response.send_message("⚠️ Bạn không thể tự cứu trong vụ việc của chính mình!", ephemeral=True)
        return

    record_time = datetime.datetime.fromisoformat(record["time"])
    elapsed_hours = (now - record_time).total_seconds() / 3600
    is_time_valid = record.get("defend_failed", False) or (3 <= elapsed_hours <= 3.5)

    if not is_time_valid:
        if elapsed_hours < 3:
            await interaction.response.send_message("⏳ Chưa đến lúc! Nạn nhân vẫn đang trong thời hạn tự `/defend` và chưa defend hụt.", ephemeral=True)
        else:
            await interaction.response.send_message("⏰ Đã quá thời hạn cứu giúp, vụ việc đã khép lại!", ephemeral=True)
        return

    is_success = random.random() < 0.60

    robber_id = record["robber_id"]
    robber_member = interaction.guild.get_member(int(robber_id))
    robber_name = f"**{robber_member.display_name}**" if robber_member else f"User {robber_id}"

    if is_success:
        helpers.append(helper_id)
        record["helpers"] = helpers
        amount = record["amount"]

        robber_bal = get_balance(data, robber_id)
        loot_amount = min(amount, robber_bal)

        update_balance(data, robber_id, -loot_amount)
        update_balance(data, helper_id, loot_amount)

        if len(helpers) >= 3:
            record["defended"] = True
        save_data(data)

        await interaction.response.send_message(f"🦸 **CỨU GIÚP THÀNH CÔNG!** {interaction.user.mention} đã trừng trị tên cướp {robber_name} và hốt trọn **{loot_amount} chai ensure**! *(Cứu giúp: {len(helpers)}/3)*")
    else:
        await interaction.response.send_message(f"💥 {interaction.user.mention} lao vào cứu giúp nhưng bị đánh văng ngược lại, cứu hụt hoàn toàn!")


# 9. Lệnh /duel_info (Xem bảng thông tin các cấp độ Duel)
@bot.tree.command(name="duel_info", description="Xem bảng thông tin chi tiết các cấp độ Duel Russian Roulette")
async def slash_duel_info(interaction: discord.Interaction):
    info_text = (
        "📊 **BẢNG THÔNG TIN CÁC CẤP ĐỘ DUEL** 📊\n\n"
        "• **Lv 1**: Phí: 0 | Thưởng: 5 | Tỉ lệ: 90-99% | Phạt: Mute 15 giây\n"
        "• **Lv 2**: Phí: 5 | Thưởng: 20 | Tỉ lệ: 80-90% | Phạt: Mute 30 giây\n"
        "• **Lv 3**: Phí: 10 | Thưởng: 50 | Tỉ lệ: 70-80% | Phạt: Mute 1 phút\n"
        "• **Lv 4**: Phí: 25 | Thưởng: 150 | Tỉ lệ: 60-70% | Phạt: Mute 2 phút\n"
        "• **Lv 5**: Phí: 50 | Thưởng: 300 | Tỉ lệ: 50-60% | Phạt: Mute 5 phút\n"
        "• **Lv 6**: Phí: 75 | Thưởng: 600 | Tỉ lệ: 40-50% | Phạt: Mute 10 phút\n"
        "• **Lv 7**: Phí: 100 | Thưởng: 1.200 | Tỉ lệ: 30-40% | Phạt: Mute 15 phút\n"
        "• **Lv 8**: Phí: 200 | Thưởng: 2.200 | Tỉ lệ: 20-30% | Phạt: Mute 20 phút\n"
        "• **Lv 9**: Phí: 500 | Thưởng: 3.500 | Tỉ lệ: 12-20% | Phạt: Mute 30 phút\n"
        "• **Lv 10**: Phí: 36 | Thưởng: 5.000 | Tỉ lệ: 5-10% | Phạt: Mute 1 giờ"
    )
    await interaction.response.send_message(info_text)


# 10. Lệnh /duel (Chơi minigame Russian Roulette)
@bot.tree.command(name="duel", description="Chơi Russian Roulette cược ensure theo cấp độ từ 1 đến 10")
@app_commands.describe(level="Cấp độ duel từ 1 đến 10")
async def slash_duel(interaction: discord.Interaction, level: int):
    data = load_data()
    user_id = str(interaction.user.id)
    now = datetime.datetime.now()

    disabled_records = data.get("disabled", {})
    if user_id in disabled_records:
        until_time = datetime.datetime.fromisoformat(disabled_records[user_id]["until"])
        if now < until_time:
            remaining = int((until_time - now).total_seconds())
            time_str = f"{remaining // 3600} giờ" if remaining >= 3600 else (f"{remaining // 60} phút" if remaining >= 60 else f"{remaining} giây")
            await interaction.response.send_message(f"🚫 {interaction.user.mention}, bạn đang bị vô hiệu hóa tính năng `/duel` trong **{time_str}** nữa!", ephemeral=True)
            return
        else:
            del data["disabled"][user_id]
            save_data(data)

    if level < 1 or level > 10:
        await interaction.response.send_message("⚠️ Cấp độ Duel phải từ **1** đến **10**! Dùng `/duel_info` để xem chi tiết.", ephemeral=True)
        return

    game_config = {
        1:  {"cost": 0,    "min_win": 0.90, "max_win": 0.99, "reward": 5,     "mute_sec": 15},
        2:  {"cost": 5,    "min_win": 0.80, "max_win": 0.90, "reward": 20,    "mute_sec": 30},
        3:  {"cost": 10,   "min_win": 0.70, "max_win": 0.80, "reward": 50,    "mute_sec": 60},
        4:  {"cost": 25,   "min_win": 0.60, "max_win": 0.70, "reward": 150,   "mute_sec": 120},
        5:  {"cost": 50,   "min_win": 0.50, "max_win": 0.60, "reward": 300,   "mute_sec": 300},
        6:  {"cost": 75,   "min_win": 0.40, "max_win": 0.50, "reward": 600,   "mute_sec": 600},
        7:  {"cost": 100,  "min_win": 0.30, "max_win": 0.40, "reward": 1200,  "mute_sec": 900},
        8:  {"cost": 200,  "min_win": 0.20, "max_win": 0.30, "reward": 2200,  "mute_sec": 1200},
        9:  {"cost": 500,  "min_win": 0.12, "max_win": 0.20, "reward": 3500,  "mute_sec": 1800},
        10: {"cost": 36,   "min_win": 0.05, "max_win": 0.10, "reward": 5000,  "mute_sec": 3600},
    }

    cfg = game_config[level]
    cost = cfg["cost"]

    current_bal = get_balance(data, interaction.user.id)
    if current_bal < cost:
        await interaction.response.send_message(f"⚠️ {interaction.user.mention}, kho của bạn không đủ {cost} chai ensure để tham gia level này!", ephemeral=True)
        return

    if cost > 0:
        update_balance(data, interaction.user.id, -cost)

    current_win_rate = random.uniform(cfg["min_win"], cfg["max_win"])
    is_win = random.random() <= current_win_rate
    hien_thi_ti_le = round(current_win_rate * 100, 1)

    if is_win:
        reward = cfg["reward"]
        new_balance = update_balance(data, interaction.user.id, cost + reward)
        await interaction.response.send_message(f"✨ **[LEVEL {level}] (Tỉ lệ: {hien_thi_ti_le}%)**\nSúng không nổ! {interaction.user.mention} thắng **{reward} chai ensure**! 🎉 *(Kho: {new_balance} chai)*")
    else:
        mute_sec = cfg["mute_sec"]
        hien_thi_tg = "1 giờ" if mute_sec >= 3600 else (f"{mute_sec // 60} phút" if mute_sec >= 60 else f"{mute_sec} giây")

        try:
            duration = datetime.timedelta(seconds=mute_sec)
            await interaction.user.timeout(duration, reason=f"Thua Duel Level {level}")
            lost_bal = get_balance(data, interaction.user.id)
            await interaction.response.send_message(f"💥 **[LEVEL {level}] (Tỉ lệ: {hien_thi_ti_le}%)**\nĐOÀNG! {interaction.user.mention} bị timeout **{hien_thi_tg}**. 💀 *(Kho: {lost_bal} chai)*")
        except Exception:
            disabled_until = now + datetime.timedelta(seconds=mute_sec)
            if "disabled" not in data:
                data["disabled"] = {}
            data["disabled"][user_id] = {"until": disabled_until.isoformat()}
            save_data(data)
            lost_bal = get_balance(data, interaction.user.id)
            await interaction.response.send_message(f"💥 **[LEVEL {level}] (Tỉ lệ: {hien_thi_ti_le}%)**\nĐOÀNG! {interaction.user.mention} bị **khóa `/duel` trong {hien_thi_tg}**! 💀 *(Kho: {lost_bal} chai)*")


# 11. Lệnh /leaderboard (Bảng xếp hạng top giàu nhất - Hiện tên, không ping)
@bot.tree.command(name="leaderboard", description="Xem bảng xếp hạng top những người có nhiều chai ensure nhất")
async def slash_leaderboard(interaction: discord.Interaction):
    data = load_data()
    users_data = data.get("users", {})

    if not users_data:
        await interaction.response.send_message("📊 Bảng xếp hạng hiện tại đang trống!", ephemeral=True)
        return

    sorted_users = sorted(users_data.items(), key=lambda x: x[1].get("balance", 0), reverse=True)
    top_users = sorted_users[:10]

    lb_text = "🏆 **BẢNG XẾP HẠNG ENSURE TOP GIÀU NHẤT** 🏆\n\n"
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

    for index, (uid, info) in enumerate(top_users):
        medal = medals[index] if index < len(medals) else f"**{index + 1}.**"
        bal = info.get("balance", 0)
        
        member = interaction.guild.get_member(int(uid))
        if member:
            name = member.display_name
        else:
            name = f"User {uid}"

        lb_text += f"{medal} **{name}** — **{bal:,}** chai ensure\n"

    await interaction.response.send_message(lb_text)


# 12. Lệnh /give (Phát ensure - Hỗ trợ tag tên hoặc nhập ID - Chỉ Server Owner)
@bot.tree.command(name="give", description="Phát ensure cho thành viên (Chỉ Server Owner)")
@app_commands.describe(target="Tag tên hoặc nhập ID thành viên nhận", amount="Số lượng chai ensure cần phát")
async def slash_give(interaction: discord.Interaction, target: str, amount: int):
    is_server_owner = interaction.guild and interaction.guild.owner_id == interaction.user.id

    if not is_server_owner:
        await interaction.response.send_message("❌ Bạn không có quyền sử dụng lệnh này! Chỉ **Chủ Server** mới có thể phát ensure.", ephemeral=True)
        return

    clean_id_str = target.replace("<@", "").replace(">", "").replace("!", "")
    if not clean_id_str.isdigit():
        await interaction.response.send_message("⚠️ Thành viên không hợp lệ! Vui lòng tag đúng người hoặc nhập đúng ID Discord.", ephemeral=True)
        return
    
    receiver_id = int(clean_id_str)

    if amount <= 0:
        await interaction.response.send_message("⚠️ Số lượng ensure cần phát phải lớn hơn 0!", ephemeral=True)
        return

    receiver_member = interaction.guild.get_member(receiver_id)
    receiver_name = receiver_member.display_name if receiver_member else f"User {receiver_id}"

    data = load_data()
    new_bal = update_balance(data, receiver_id, amount)

    await interaction.response.send_message(f"🎁 **PHÁT THƯỞNG!** {interaction.user.mention} đã cấp thêm **{amount:,} chai ensure** cho **{receiver_name}**! *(Kho hiện có: {new_bal:,} chai)*")


# 13. Lệnh /forgive (Gỡ lệnh cấm /duel cho thành viên - Chỉ Admin)
@bot.tree.command(name="forgive", description="Tha lỗi, gỡ lệnh cấm chơi /duel cho thành viên (Chỉ Admin)")
@app_commands.describe(target="Tag tên hoặc nhập ID thành viên cần gỡ cấm")
async def slash_forgive(interaction: discord.Interaction, target: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Bạn không có quyền sử dụng lệnh này! Chỉ Quản trị viên mới có thể tha lỗi.", ephemeral=True)
        return

    clean_id_str = target.replace("<@", "").replace(">", "").replace("!", "")
    if not clean_id_str.isdigit():
        await interaction.response.send_message("⚠️ Thành viên không hợp lệ! Vui lòng tag đúng người hoặc nhập đúng ID Discord.", ephemeral=True)
        return

    target_id = clean_id_str
    data = load_data()

    target_member = interaction.guild.get_member(int(target_id))
    target_name = target_member.display_name if target_member else f"User {target_id}"

    if "disabled" in data and target_id in data["disabled"]:
        del data["disabled"][target_id]
        save_data(data)
        await interaction.response.send_message(f"🕊️ **ĐÃ THA LỖI!** {interaction.user.mention} đã gỡ lệnh cấm chơi `/duel` cho **{target_name}** thành công!")
    else:
        await interaction.response.send_message(f"⚠️ **{target_name}** hiện tại không bị cấm chơi `/duel` nào cả!", ephemeral=True)


# ==================== CHẠY BOT ====================
if __name__ == "__main__":
    BOT_TOKEN = os.getenv("DISCORD_TOKEN")
    if not BOT_TOKEN:
        raise ValueError("Chưa thiết lập biến môi trường DISCORD_TOKEN!")
    bot.run(BOT_TOKEN)
