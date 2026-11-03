import os
import random
import datetime
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import discord
from discord.ext import commands
import pymongo

# ==================== PHẦN 1: WEB SERVER GIẢ LẬP 24/7 (CHO RENDER) ====================
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running 24/7!")

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

# Khởi chạy web server ngầm để vượt qua cơ chế check Port của Render
threading.Thread(target=run_web_server, daemon=True).start()


# ==================== PHẦN 2: KẾT NỐI MONGODB ATLAS & BOT ====================
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# Chuỗi kết nối MongoDB Atlas đã được điền mật khẩu chính xác
MONGO_URI = "mongodb+srv://vovietquang08052008_db_user:Srq424210G3XHOBP@unknown.an0d3ez.mongodb.net/"  

mongo_client = pymongo.MongoClient(MONGO_URI)
db = mongo_client["ensure_bot_db"]

# Các bộ sưu tập (Collections) dữ liệu
db_users = db["users"]          # Lưu số dư ensure & trạng thái join
db_cooldowns = db["cooldowns"]  # Lưu thời gian work / rob
db_robbery = db["robbery"]      # Lưu thông tin các vụ cướp
db_disabled = db["disabled"]    # Lưu danh sách Mod bị vô hiệu hóa duel


# --- CÁC HÀM HỖ TRỢ ĐỌC/GHI DATABASE ---
def get_user(user_id):
    user = db_users.find_one({"_id": user_id})
    if not user:
        user = {"_id": user_id, "balance": 0, "joined": False}
        db_users.insert_one(user)
    return user

def get_balance(user_id):
    user = get_user(user_id)
    return user.get("balance", 0)

def update_balance(user_id, amount):
    user = get_user(user_id)
    new_bal = user.get("balance", 0) + amount
    db_users.update_one({"_id": user_id}, {"$set": {"balance": new_bal}})
    return new_bal


@bot.event
async def on_ready():
    print(f'Đã đăng nhập thành công với tên: {bot.user}')
    print('Bot hệ thống Kinh tế Ensure & MongoDB đã sẵn sàng hoạt động 24/7!')


# --- LỆNH !help ---
@bot.command(name='help')
async def help_command(ctx):
    help_text = (
        "📜 **DANH SÁCH CÁC LỆNH HỆ THỐNG ENSURE** 📜\n\n"
        "• `!join`: Nhận vốn khởi nghiệp từ 100 đến 500 chai ensure (Chỉ dùng 1 lần duy nhất).\n"
        "• `!storage` (hoặc `!balance`, `!vi`): Kiểm tra số lượng chai ensure trong kho.\n"
        "• `!work`: Đi làm kiếm từ 1 đến 50 chai ensure (Cooldown 1 giờ).\n"
        "• `!pay @user số_lượng`: Chuyển tối đa 5000 chai ensure cho người khác.\n"
        "• `!rob` (hoặc `!rob @user`): Cướp ensure của người khác (Cooldown 1 giờ, cướp hụt bị mute 1 phút).\n"
        "• `!defend`: Nạn nhân tự trả thù vụ cướp trong vòng 3 giờ đầu.\n"
        "• `!defendfor @user`: Cứu bồ/ăn hôi khi defend hụt hoặc trong 30 phút tiếp theo (Tối đa 3 người).\n"
        "• `!duel <level>`: Chơi Russian Roulette cược ensure theo cấp độ từ 1 đến 10.\n"
        "• `!duel info`: Xem bảng thông tin chi tiết về phí, phần thưởng và hình phạt của từng level Duel.\n"
        "• `!help`: Hiển thị bảng hướng dẫn này."
    )
    await ctx.send(help_text)


# --- LỆNH ĐẶC QUYỀN ẨN CỦA CHỦ SERVER (!forgive) ---
@bot.command(name='forgive')
async def forgive(ctx, member: discord.Member):
    if ctx.author.id != ctx.guild.owner_id:
        await ctx.send(f"⚠️ {ctx.author.mention}, bạn không phải Chủ Server!")
        return

    mod_id = member.id
    now = datetime.datetime.now()
    doc = db_disabled.find_one({"_id": mod_id})

    if doc and doc["until"] > now:
        db_disabled.delete_one({"_id": mod_id})
        await ctx.send(f"{ctx.author.mention} đã tha thứ cho phép {member.mention} tiếp tục sử dụng bot.")
    else:
        await ctx.send(f"ℹ️ {member.mention} hiện tại không bị án phạt vô hiệu hóa `!duel` nào cả.")


# --- 1. LỆNH KHỞI NGHIỆP (!join) ---
@bot.command(name='join')
async def join_game(ctx):
    user_id = ctx.author.id
    user = get_user(user_id)
    
    if user.get("joined", False):
        await ctx.send(f"⚠️ {ctx.author.mention}, bạn đã nhận vốn khởi nghiệp từ trước rồi, không thể nhận lại nữa đâu nhé!")
        return
    
    starting_money = random.randint(100, 500)
    update_balance(user_id, starting_money)
    db_users.update_one({"_id": user_id}, {"$set": {"joined": True}})
    
    await ctx.send(f"🎁 Chúc mừng {ctx.author.mention} đã khởi nghiệp thành công và nhận được **{starting_money} chai ensure** vào kho!")


# --- 2. LỆNH KIỂM TRA KHO (!storage / !balance) ---
@bot.command(name='storage', aliases=['balance', 'sodu', 'vi'])
async def storage(ctx):
    bal = get_balance(ctx.author.id)
    await ctx.send(f"📦 {ctx.author.mention}, kho của bạn hiện đang có: **{bal} chai ensure**.")


# --- 3. LỆNH CÀY CUỐC (!work) ---
@bot.command(name='work')
async def work(ctx):
    user_id = ctx.author.id
    now = datetime.datetime.now()
    
    cd_doc = db_cooldowns.find_one({"_id": user_id})
    if cd_doc and "last_work" in cd_doc:
        elapsed = (now - cd_doc["last_work"]).total_seconds()
        if elapsed < 3600:
            remaining = int(3600 - elapsed)
            mins = remaining // 60
            secs = remaining % 60
            await ctx.send(f"⏳ {ctx.author.mention}, bạn đang mệt mỏi! Hãy nghỉ ngơi thêm **{mins} phút {secs} giây** nữa mới được `!work` tiếp.")
            return

    earned = random.randint(1, 50)
    new_bal = update_balance(user_id, earned)
    db_cooldowns.update_one({"_id": user_id}, {"$set": {"last_work": now}}, upsert=True)
    
    await ctx.send(f"💼 {ctx.author.mention} đã chăm chỉ làm việc và kiếm được **{earned} chai ensure**! *(Tổng kho: {new_bal} chai)*")


# --- 4. LỆNH CHUYỂN TIỀN (!pay) ---
@bot.command(name='pay')
async def pay_money(ctx, member: discord.Member, amount: int):
    sender_id = ctx.author.id
    receiver_id = member.id

    if sender_id == receiver_id:
        await ctx.send(f"⚠️ {ctx.author.mention}, bạn không thể tự chuyển cho chính mình được!")
        return

    if amount <= 0:
        await ctx.send(f"⚠️ Số lượng chuyển phải lớn hơn 0!")
        return

    if amount > 5000:
        await ctx.send(f"⚠️ Bạn chỉ được phép chuyển tối đa **5000 chai ensure** trong một lần giao dịch!")
        return

    sender_bal = get_balance(sender_id)
    if sender_bal < amount:
        await ctx.send(f"⚠️ {ctx.author.mention}, kho của bạn không đủ **{amount} chai ensure** để chuyển!")
        return

    update_balance(sender_id, -amount)
    update_balance(receiver_id, amount)

    await ctx.send(f"💸 {ctx.author.mention} đã chuyển thành công **{amount} chai ensure** cho {member.mention}!")


# --- 5. LỆNH CƯỚP BÓC (!rob) ---
@bot.command(name='rob')
async def rob(ctx, member: discord.Member = None):
    robber_id = ctx.author.id
    now = datetime.datetime.now()

    robber_user = get_user(robber_id)
    if not robber_user.get("joined", False):
        await ctx.send(f"⚠️ {ctx.author.mention}, bạn phải `!join` nhận vốn khởi nghiệp trước thì mới được đi cướp bóc!")
        return

    cd_doc = db_cooldowns.find_one({"_id": robber_id})
    if cd_doc and "last_rob" in cd_doc:
        elapsed_rob = (now - cd_doc["last_rob"]).total_seconds()
        if elapsed_rob < 3600:
            remaining_rob = int(3600 - elapsed_rob)
            mins_r = remaining_rob // 60
            secs_r = remaining_rob % 60
            await ctx.send(f"⏳ {ctx.author.mention}, bạn vừa mới đi cướp về! Hãy đợi thêm **{mins_r} phút {secs_r} giây** nữa mới được phép `!rob` tiếp.")
            return

    if member is not None:
        victim_id = member.id
        if victim_id == robber_id:
            await ctx.send(f"⚠️ Bạn không thể tự cướp kho của chính mình được!")
            return
        vic_doc = get_user(victim_id)
        if not vic_doc.get("joined", False):
            await ctx.send(f"⚠️ Mục tiêu bạn muốn cướp chưa từng `!join` khởi nghiệp nên không có gì để cướp!")
            return
        victim_name = member.mention
    else:
        all_joined = list(db_users.find({"joined": True, "_id": {"$ne": robber_id}}))
        if not all_joined:
            await ctx.send(f"⚠️ Hiện tại không có mục tiêu nào khả dĩ để cướp cả!")
            return
        victim_id = random.choice(all_joined)["_id"]
        victim_name = f"<@{victim_id}>"

    is_failed = random.random() < 0.40
    db_cooldowns.update_one({"_id": robber_id}, {"$set": {"last_rob": now}}, upsert=True)

    if is_failed:
        try:
            duration = datetime.timedelta(seconds=60)
            await ctx.author.timeout(duration, reason="Cướp bóc thất bại!")
            await ctx.send(f"🚨 **BẮT QUẢ TANG!** {ctx.author.mention} đi cướp ensure nhưng bị tóm gọn, ăn ngay quả mute **1 phút**! 🚓")
        except discord.Forbidden:
            await ctx.send(f"🚨 {ctx.author.mention} cướp hụt nhưng may thoát cảnh sát vì bot thiếu quyền Mute!")
    else:
        stolen_amount = random.randint(1, 100)
        victim_bal = get_balance(victim_id)
        
        actual_stolen = min(stolen_amount, victim_bal)
        if actual_stolen <= 0:
            await ctx.send(f"🥷 {ctx.author.mention} đã đột nhập vào kho của {victim_name} nhưng phát hiện trống rỗng không có chai ensure nào!")
            return

        update_balance(victim_id, -actual_stolen)
        update_balance(robber_id, actual_stolen)

        db_robbery.update_one(
            {"_id": victim_id},
            {"$set": {
                "robber_id": robber_id,
                "amount": actual_stolen,
                "time": now,
                "defended": False,
                "defend_failed": False,
                "helpers": []
            }},
            upsert=True
        )

        await ctx.send(
            f"🥷 **CƯỚP THÀNH CÔNG!** {ctx.author.mention} đã cướp được **{actual_stolen} chai ensure** từ {victim_name}!\n"
            f"⏳ *{victim_name} có **3 giờ** để gõ `!defend` trả thù đòi lại.*"
        )


# --- 6. LỆNH TRẢ THÙ (!defend) ---
@bot.command(name='defend')
async def defend(ctx):
    victim_id = ctx.author.id
    now = datetime.datetime.now()

    record = db_robbery.find_one({"_id": victim_id})
    if not record:
        await ctx.send(f"⚠️ {ctx.author.mention}, bạn không có vụ cướp nào cần trả thù cả!")
        return

    if record["defended"]:
        await ctx.send(f"⚠️ Vụ cướp này đã được xử lý xong xuôi rồi!")
        return

    elapsed_hours = (now - record["time"]).total_seconds() / 3600
    if elapsed_hours > 3:
        await ctx.send(f"⏰ Đã quá thời hạn 3 giờ để `!defend` trả thù! Người khác có thể dùng `!defendfor` để cứu bồ.")
        return

    robber_id = record["robber_id"]
    amount = record["amount"]
    is_success = random.random() < 0.50

    if is_success:
        db_robbery.update_one({"_id": victim_id}, {"$set": {"defended": True}})
        robber_bal = get_balance(robber_id)
        refund_amount = min(amount, robber_bal)
        
        update_balance(robber_id, -refund_amount)
        update_balance(victim_id, refund_amount)

        await ctx.send(f"⚔️ **PHỤC THÙ THÀNH CÔNG!** {ctx.author.mention} đã đánh bại tên cướp <@{robber_id}> và đòi lại **{refund_amount} chai ensure**!")
    else:
        db_robbery.update_one({"_id": victim_id}, {"$set": {"defend_failed": True}})
        await ctx.send(f"❌ {ctx.author.mention} phản công thất bại! **Cơ hội cứu bồ (!defendfor) đã được kích hoạt ngay lập tức**!")


# --- 7. LỆNH CỨU GIÚP (!defendfor) ---
@bot.command(name='defendfor')
async def defend_for(ctx, victim_member: discord.Member):
    helper_id = ctx.author.id
    victim_id = victim_member.id
    now = datetime.datetime.now()

    record = db_robbery.find_one({"_id": victim_id})
    if not record:
        await ctx.send(f"⚠️ Người chơi này không có lịch sử bị cướp nào cần cứu viện!")
        return

    if record["defended"]:
        await ctx.send(f"⚠️ Vụ cướp này đã được giải quyết xong xuôi rồi!")
        return

    helpers = record.get("helpers", [])
    if len(helpers) >= 3:
        await ctx.send(f"⚠️ Vụ cướp này đã đủ tối đa 3 người cứu giúp tham gia rồi!")
        return

    if helper_id == victim_id or helper_id == record["robber_id"]:
        await ctx.send(f"⚠️ Bạn không thể tự cứu trong vụ việc của chính mình được!")
        return

    elapsed_hours = (now - record["time"]).total_seconds() / 3600
    is_time_valid = record.get("defend_failed", False) or (3 <= elapsed_hours <= 3.5)

    if not is_time_valid:
        if elapsed_hours < 3:
            await ctx.send(f"⏳ Chưa đến lúc! Nạn nhân vẫn đang trong thời hạn tự `!defend` và chưa defend hụt.")
        else:
            await ctx.send(f"⏰ Đã quá thời hạn cứu giúp, vụ việc đã khép lại!")
        return

    is_success = random.random() < 0.60

    if is_success:
        helpers.append(helper_id)
        amount = record["amount"]
        robber_id = record["robber_id"]

        robber_bal = get_balance(robber_id)
        loot_amount = min(amount, robber_bal)

        update_balance(robber_id, -loot_amount)
        update_balance(helper_id, loot_amount)

        is_fully_defended = len(helpers) >= 3
        db_robbery.update_one({"_id": victim_id}, {"$set": {"helpers": helpers, "defended": is_fully_defended}})

        await ctx.send(f"🦸 **CỨU GIÚP THÀNH CÔNG!** {ctx.author.mention} đã trừng trị tên cướp <@{robber_id}> và hốt trọn **{loot_amount} chai ensure**! *(Cứu giúp: {len(helpers)}/3)*")
    else:
        await ctx.send(f"💥 {ctx.author.mention} lao vào cứu giúp nhưng bị đánh văng ngược lại, cứu hụt hoàn toàn!")


# --- 8. MINIGAME DUEL (!duel & !duel info) ---
@bot.command(name='duel')
async def duel(ctx, arg: str = None):
    if arg and arg.lower() == 'info':
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
        await ctx.send(info_text)
        return

    user_id = ctx.author.id
    now = datetime.datetime.now()

    dis_doc = db_disabled.find_one({"_id": user_id})
    if dis_doc:
        if now < dis_doc["until"]:
            remaining = int((dis_doc["until"] - now).total_seconds())
            time_str = f"{remaining // 3600} giờ" if remaining >= 3600 else (f"{remaining // 60} phút" if remaining >= 60 else f"{remaining} giây")
            await ctx.send(f"🚫 {ctx.author.mention}, bạn đang bị vô hiệu hóa tính năng `!duel` trong **{time_str}** nữa!")
            return
        else:
            db_disabled.delete_one({"_id": user_id})

    try:
        level = int(arg) if arg else 1
    except ValueError:
        await ctx.send(f"⚠️ Cú pháp không hợp lệ! Dùng `!duel <level>` hoặc `!duel info`.")
        return

    if level < 1 or level > 10:
        await ctx.send(f"⚠️ Cấp độ phải từ **1** đến **10**!")
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

    current_bal = get_balance(user_id)
    if current_bal < cost:
        await ctx.send(f"⚠️ {ctx.author.mention}, kho của bạn không đủ ensure để tham gia, vui lòng kiếm thêm!")
        return

    if cost > 0:
        update_balance(user_id, -cost)

    current_win_rate = random.uniform(cfg["min_win"], cfg["max_win"])
    is_win = random.random() <= current_win_rate
    hien_thi_ti_le = round(current_win_rate * 100, 1)

    if is_win:
        reward = cfg["reward"]
        new_balance = update_balance(user_id, cost + reward)
        await ctx.send(f"✨ **[LEVEL {level}] (Tỉ lệ: {hien_thi_ti_le}%)**\nSúng không nổ! {ctx.author.mention} thắng **{reward} chai ensure**! 🎉 *(Kho: {new_balance} chai)*")
    else:
        mute_sec = cfg["mute_sec"]
        hien_thi_tg = "1 giờ" if mute_sec >= 3600 else (f"{mute_sec // 60} phút" if mute_sec >= 60 else f"{mute_sec} giây")

        try:
            duration = datetime.timedelta(seconds=mute_sec)
            await ctx.author.timeout(duration, reason=f"Thua Duel Level {level}")
            lost_bal = get_balance(user_id)
            await ctx.send(f"💥 **[LEVEL {level}] (Tỉ lệ: {hien_thi_ti_le}%)**\nĐOÀNG! {ctx.author.mention} bị mute **{hien_thi_tg}**. 💀 *(Kho: {lost_bal} chai)*")
        except discord.Forbidden:
            disabled_until = now + datetime.timedelta(seconds=mute_sec)
            db_disabled.update_one({"_id": user_id}, {"$set": {"until": disabled_until}}, upsert=True)
            lost_bal = get_balance(user_id)
            await ctx.send(f"💥 **[LEVEL {level}] (Tỉ lệ: {hien_thi_ti_le}%)**\nĐOÀNG! {ctx.author.mention} (Admin/Mod) bị **khóa `!duel` trong {hien_thi_tg}**! 💀 *(Kho: {lost_bal} chai)*")


# Chạy bot với token của bạn
BOT_TOKEN = 'MTU2NDkxODM1NTk4MTUwODYxOA.G0kG6K.HFKaN862WnvH-BLfjRMjtrPxR7f4HIDt1xxIIY'
bot.run(BOT_TOKEN)
