import os
import psycopg2 
from urllib.parse import urlparse
import time
from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton
    # ✅ FIX: Message, CallbackQuery কে আলাদাভাবে ইমপোর্ট করা হলো exec() এর জন্য
)
from pyrogram.types import Message, CallbackQuery 


# **********************************************
# --- ✅ ফিক্সড মডিউল ইম্পোর্ট ---
# **********************************************
import withdraw_handlers as withdraw_mod 
import task_1 
import task_2 
import task_3 
import task_4 
import task_5 
import task_6 
import task_7 
import task_8 
import task_9 
import task_10 


# --- টাস্ক হ্যান্ডলার সেটআপ ফাংশন ---
def setup_task_handlers(app: Client):
    task_1.setup_task_handlers(app)
    task_2.setup_task_handlers(app)
    task_3.setup_task_handlers(app)
    task_4.setup_task_handlers(app)
    task_5.setup_task_handlers(app)
    task_6.setup_task_handlers(app)
    task_7.setup_task_handlers(app)
    task_8.setup_task_handlers(app)
    task_9.setup_task_handlers(app)
    task_10.setup_task_handlers(app)


# **********************************************
# **** ক্লাউড হোস্টিং-এর জন্য এনভায়রনমেন্ট ভেরিয়েবল ****
# **********************************************
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# **** অ্যাডমিন আইডি (আপনার Telegram ID) ****
OWNER_ID = 7702378694  
ADMIN_CONTACT_USERNAME = "rdsratul81" 
# **********************************************

# **********************************************
# **** গ্লোবাল স্টেট এবং ব্যবসায়িক লজিক ভেরিয়েবল ****
# **********************************************
USER_STATE = {} 
REFER_BONUS = 30.00          
MIN_WITHDRAW = 1500.00       
WITHDRAW_FEE_PERCENT = 10.0  
REQUIRED_REFERRALS = 20      
# **********************************************


# --- Database সেটআপ ---
conn = sqlite3.connect('user_data.db', check_same_thread=False)
cursor = conn.cursor()

# ইউজার টেবিল তৈরি/আপডেট
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        task_balance REAL DEFAULT 0.00,
        referral_balance REAL DEFAULT 0.00,
        referral_count INTEGER DEFAULT 0,
        referred_by INTEGER,
        is_blocked INTEGER DEFAULT 0,
        last_bonus_time INTEGER DEFAULT 0
    )
''')

# উইথড্র হিস্টরি টেবিল 
cursor.execute('''
    CREATE TABLE IF NOT EXISTS withdraw_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount REAL,
        method TEXT,
        account_number TEXT,
        status TEXT DEFAULT 'Pending',
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
''')
conn.commit()

# --- কীবোর্ড সেটআপ ---

# মূল মেনুর বাটন (Reply Keyboard)
main_menu_keyboard = ReplyKeyboardMarkup(
    [
        [KeyboardButton("💰 Daily Bonus"), KeyboardButton("🔗 Refer & Earn")],
        [KeyboardButton("Withdraw"), KeyboardButton("👤 My Account")],
        [KeyboardButton("🧾 History"), KeyboardButton("👑 Status (Admin)")]
    ],
    resize_keyboard=True
)

# ✅ ফিক্সড: টাস্ক মেনুর বাটন (Reply Keyboard)
TASK_MENU_KEYBOARD_REPLY = ReplyKeyboardMarkup(
    [
        [KeyboardButton("🏅 TASK-1_10 TK"), KeyboardButton("🏅 TASK-2_10 TK")],
        [KeyboardButton("🏅 TASK-3_10 TK"), KeyboardButton("🏅 TASK-4_10 TK")],
        [KeyboardButton("🏅 TASK-5_10 TK"), KeyboardButton("🏅 TASK-6_10 TK")],
        [KeyboardButton("🏅 TASK-7_10 TK"), KeyboardButton("🏅 TASK-8_10 TK")],
        [KeyboardButton("🏅 TASK-9_10 TK"), KeyboardButton("🏅 TASK-10_10 TK")],
        [KeyboardButton("🏠 MAIN MENU")]
    ],
    resize_keyboard=True
)


# --- Pyrogram ক্লায়েন্ট সেটআপ ---
app = Client(
    "earning_bot",
    api_id=int(API_ID),
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# --- ফাংশন: ইউজার Database এ যোগ করা ---
def add_user(user_id, referred_by=None):
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO users (user_id, referred_by) VALUES (?, ?)", (user_id, referred_by))
        conn.commit()
        if referred_by:
            cursor.execute("UPDATE users SET referral_balance = referral_balance + ?, referral_count = referral_count + 1 WHERE user_id = ?", (REFER_BONUS, referred_by))
            conn.commit()
            return True
    return False

# --- ফিক্সড: ব্লকড ইউজার চেক ---
def is_user_blocked(user_id):
    cursor.execute("SELECT is_blocked FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    return result and result[0] == 1


# --- হ্যান্ডলার: /start কমান্ড ---
@app.on_message(filters.command("start"))
async def start_command(client, message):
    user_id = message.from_user.id

    if is_user_blocked(user_id):
        await message.reply_text("❌ দুঃখিত! আপনাকে বটটি ব্যবহার থেকে ব্লক করা হয়েছে।")
        return

    referred_by = None
    
    if len(message.command) > 1:
        try:
            referred_by = int(message.command[1])
            cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (referred_by,))
            if referred_by == user_id or cursor.fetchone() is None:
                 referred_by = None
            else:
                pass 
        except ValueError:
            referred_by = None
            
    if add_user(user_id, referred_by):
        text = "👋 স্বাগতম! আপনি আপনার পছন্দের টাস্কগুলো করে আয় করা শুরু করতে পারেন।"
    else:
        text = "👋 হ্যালো 🅳🅴🅰🆁 {first_name} ☀️\n\n෴❤️෴ 𝐖𝐞𝐥𝐜𝐨𝐦𝐞 ෴❤️෴\n\nনিচে মূল মেনু দেওয়া হলো।"

    await message.reply_text(
        text,
        reply_markup=main_menu_keyboard
    )


# --- হ্যান্ডলার: Daily Bonus ---
@app.on_message(filters.regex("💰 Daily Bonus"))
async def daily_bonus_handler(client, message):
    if is_user_blocked(message.from_user.id): return
    
    await message.reply_text(
        "✅ Task complete করতে নিচের বাটনগুলো ব্যবহার করুন.\n"
        "✅ নিয়ম মেনে কাজ করবেন ইনকাম নিশ্চিত🚀",
        reply_markup=TASK_MENU_KEYBOARD_REPLY # ✅ ফিক্সড: Reply Keyboard
    )

# --- হ্যান্ডলার: MAIN MENU বাটন ---
@app.on_message(filters.regex("🏠 MAIN MENU") & filters.private)
async def back_to_main_menu(client, message):
    await message.reply_text(
        "👋 আপনি মূল মেনুতে ফিরে এসেছেন।",
        reply_markup=main_menu_keyboard
    )


# --- হ্যান্ডলার: Refer & Earn ---
@app.on_message(filters.regex("🔗 Refer & Earn"))
async def refer_command(client, message):
    if is_user_blocked(message.from_user.id): return
    user_id = message.from_user.id
    bot_username = client.me.username if client.me.username else "YourBotUsername"
    referral_link = f"https://t.me/{bot_username}?start={user_id}"
    
    cursor.execute("SELECT referral_count FROM users WHERE user_id = ?", (user_id,))
    data = cursor.fetchone()
    ref_count = data[0] if data else 0
    
    text = (
        "🎉 **রেফার করে আয় করুন!**\n"
        "-\n"
        f"💸 REFER BOUNS: **{REFER_BONUS:.2f} TK**\n"
        f"🔗 মোট রেফারেল: **{ref_count} জন**\n"
        "-----------------------\n"
        "🌐 **REFER LINK** 🌐\n"
        f"🔗 `{referral_link}`\n\n"
        "🚀 উপরে ক্লিক করে লিংকটি কপি করে বন্ধুদের সাথে শেয়ার করুন।"
    )
    await message.reply_text(text)


# --- হ্যান্ডলার: My Account ---
@app.on_message(filters.regex("👤 My Account"))
async def account_command(client, message):
    if is_user_blocked(message.from_user.id): return
    user_id = message.from_user.id
    cursor.execute("SELECT task_balance, referral_balance, referral_count FROM users WHERE user_id = ?", (user_id,))
    data = cursor.fetchone()
    
    if data:
        task_balance, referral_balance, ref_count = data
        total_balance = task_balance + referral_balance
        
        text = (
            "💼 **আপনার অ্যাকাউন্ট স্ট্যাটাস**\n"
            "-\n"
            f"🏅 Task ব্যালেন্স: **{task_balance:.2f} ৳**\n"
            f"💸 রেফার ব্যালেন্স: **{referral_balance:.2f} ৳**\n"
            f"💰 বর্তমান ব্যালেন্স: **{total_balance:.2f} ৳**\n"
            f"🔗 মোট রেফারেল: **{ref_count} জন**\n\n"
            f"⚠️ **উইথড্র শর্ত**: **{MIN_WITHDRAW:.2f} ৳** এবং **{REQUIRED_REFERRALS} জন রেফার**।"
        )
    else:
        text = "❌ অ্যাকাউন্ট তথ্য পাওয়া যায়নি। /start কমান্ড দিন।"

    await message.reply_text(text)


# --- হ্যান্ডলার: History ---
@app.on_message(filters.regex("🧾 History"))
async def history_command(client, message):
    if is_user_blocked(message.from_user.id): return
    user_id = message.from_user.id
    cursor.execute(
        "SELECT timestamp, amount, method, account_number, status FROM withdraw_history WHERE user_id = ? ORDER BY timestamp DESC LIMIT 10", 
        (user_id,)
    )
    history = cursor.fetchall()
    
    if not history:
        await message.reply_text("❌ আপনার কোনো উইথড্র হিস্টরি পাওয়া যায়নি।")
        return

    history_text = "🧾 **আপনার উইথড্র হিস্টরি**\n\n"
    for item in history:
        timestamp, amount, method, number, status = item
        status_emoji = "✅ Approved" if status == "Approved" else ("❌ Rejected" if status == "Rejected" else "⏳ Pending")
        
        history_text += (
            f"📅 {timestamp[:10]} - {timestamp[11:16]}\n"
            f"💰 {amount:.2f} ৳\n"
            f"🏦 {method}\n"
            f"🔢 {number}\n"
            f"🎨 {status_emoji}\n"
            "-----------------------\n"
        )
    
    await message.reply_text(history_text)


# --- হ্যান্ডলার: Status (Admin) ---
@app.on_message(filters.regex("👑 Status \\(Admin\\)"))
async def admin_status_command(client, message):
    if is_user_blocked(message.from_user.id): return
    contact_button = InlineKeyboardMarkup(
        [[InlineKeyboardButton("💬 CONTACT", url=f"https://t.me/{ADMIN_CONTACT_USERNAME}")]]
    )
    
    text = "✳️ জরুরী প্রয়োজনে এডমিনের সাথে যোগাযোগ করুন ✳️"
    await message.reply_text(text, reply_markup=contact_button)


# 🟢 ✅ চূড়ান্ত ফিক্স: ডায়নামিক টাস্ক বাটন হ্যান্ডলারস
# (Reply Keyboard এর বাটনগুলোতে ক্লিক করলে Inline Keyboard দেখানোর লজিক)
for i in range(1, 11):
    task_name = f"TASK-{i}"
    button_text = f"🏅 {task_name}_10 TK"
    callback_data = f"task_{i}_" # এটি task_x.py এর Handler 4 কে ট্রিগার করবে
    
    # 💥 FIX: exec() ব্লকের ভেতরে Message এবং InlineKeyboardButton ইমপোর্ট করা হয়েছে
    exec(f"""
@app.on_message(filters.regex("{button_text}") & filters.private)
async def show_task_{i}_details(client: Client, message: Message):
    # ✅ FIX: NameError এড়াতে এখানে Pyrogram.types থেকে সরাসরি কল করা হয়েছে
    from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton 
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ কাজ শুরু করুন", callback_data="{callback_data}")]
    ])
    await message.reply_text(
        f"🏅 **{task_name}** শুরু করতে প্রস্তুত?\\n"
        "অনুগ্রহ করে **'কাজ শুরু করুন'** বাটনে ক্লিক করে টাস্ক শুরু করুন:",
        reply_markup=keyboard
    )
    """)
# =========================================================


# --- ক্যোয়ারি হ্যান্ডলার: Main Menu বাটন (Inline) ---
@app.on_callback_query(filters.regex("^main_menu"))
async def back_to_main_menu_callback(client, callback_query):
    await callback_query.edit_message_text(
        "👋 আপনি মূল মেনুতে ফিরে এসেছেন।",
        reply_markup=main_menu_keyboard
    )
    await callback_query.answer("মূল মেনুতে ফিরে গেছেন।")


# --- চূড়ান্ত ফিক্স: নন-কমান্ড মেসেজ হ্যান্ডলার ---
@app.on_message(filters.private & filters.text & ~filters.regex("^Withdraw$")) 
async def process_text_messages(client, message):
    
    main_menu_texts = ["💰 Daily Bonus", "🔗 Refer & Earn", "👤 My Account", "🧾 History", "👑 Status (Admin)", "BKASH", "NAGAD", "CANCEL"] 
    if message.text in main_menu_texts:
        return
        
    user_id = message.from_user.id
    
    if is_user_blocked(user_id): return
    
    await client.forward_messages(
        chat_id=OWNER_ID,
        from_chat_id=message.chat.id,
        message_ids=message.id
    )
    
    await message.reply_text(
        "✅ আপনার মেসেজটি এডমিনের কাছে পাঠানো হয়েছে। খুব শীঘ্রই আপনাকে রিপ্লাই দেওয়া হবে।"
    )
    

# **********************************************
# --- মডিউল হ্যান্ডলারগুলো চালু করা ও বট চালু করা ---
# **********************************************

# 1. হ্যান্ডলার মডিউলগুলো চালু করা
withdraw_mod.setup_withdraw_handlers(app, USER_STATE, group=-1) 
setup_task_handlers(app) 

# --- বট চালানো ---
print("Telegram Earning Bot is starting...")
if __name__ == "__main__":
    app.run()
