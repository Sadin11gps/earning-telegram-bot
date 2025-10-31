import os
import time
import asyncio
import psycopg2 
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    Message, CallbackQuery
)
from dotenv import load_dotenv

# dotenv লোড করা (যদি .env ফাইল থাকে)
load_dotenv() 

# **********************************************
# --- ✅ ফিক্সড মডিউল ইম্পোর্ট ---
# **********************************************
# NOTE: আপনার এই মডিউল ফাইলগুলোতেও PostgreSQL সিনট্যাক্স (%s) ফিক্স করতে হবে।
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
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# ✅ চূড়ান্ত ফিক্স: DATABASE_URL নিশ্চিত করা
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL and os.getenv("PGHOST"):
    # Railway-এর স্বতন্ত্র ভেরিয়েবলগুলো ব্যবহার করে URL তৈরি করা
    PGHOST = os.getenv("PGHOST")
    PGUSER = os.getenv("PGUSER")
    PGPASSWORD = os.getenv("PGPASSWORD")
    PGDATABASE = os.getenv("PGDATABASE")
    PGPORT = os.getenv("PGPORT")
    DATABASE_URL = f"postgres://{PGUSER}:{PGPASSWORD}@{PGHOST}:{PGPORT}/{PGDATABASE}"

# **********************************************

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


# --- ✅ ডেটাবেস সংযোগ ও ইনিশিয়ালাইজেশন (PostgreSQL) ---
conn = None
cursor = None

def init_db():
    global conn, cursor
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # ইউজার টেবিল তৈরি (PostgreSQL Syntax)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                task_balance NUMERIC(10, 2) DEFAULT 0.00,
                referral_balance NUMERIC(10, 2) DEFAULT 0.00,
                referral_count INTEGER DEFAULT 0,
                referred_by BIGINT,
                is_blocked INTEGER DEFAULT 0,
                last_bonus_time BIGINT DEFAULT 0
            )
        """)

        # উইথড্র হিস্টরি টেবিল (PostgreSQL Syntax)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS withdraw_history (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                amount NUMERIC(10, 2),
                method TEXT,
                account_number TEXT,
                status TEXT DEFAULT 'Pending',
                timestamp TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        print("Database initialized successfully.")
        return conn, cursor
    except Exception as e:
        print(f"Database connection error: {e}")
        return None, None

# অ্যাপ্লিকেশন শুরু করার আগে ডেটাবেস সংযোগ করুন
conn, cursor = init_db()

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

# টাস্ক মেনুর বাটন (Reply Keyboard)
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

# --- ফিক্সড: ব্লকড ইউজার চেক ---
def is_user_blocked(user_id):
    global conn, cursor # ✅ গ্লোবাল ডিক্লারেশন
    
    # ✅ NoneType ফিক্স
    if cursor is None: return True
    
    # ✅ PostgreSQL (%s) ব্যবহার
    cursor.execute("SELECT is_blocked FROM users WHERE user_id = %s", (user_id,)) 
    result = cursor.fetchone()
    return result and result[0] == 1

# --- ফাংশন: ইউজার Database এ যোগ করা ---
def add_user(user_id, referred_by=None):
    global conn, cursor # ✅ গ্লোবাল ডিক্লারেশন
    
    # ✅ NoneType ফিক্স
    if cursor is None: return

    # ✅ PostgreSQL (%s) ব্যবহার
    cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,)) 
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO users (user_id, referred_by) VALUES (%s, %s)", (user_id, referred_by))
        conn.commit()
        if referred_by:
            # ✅ PostgreSQL (%s) ব্যবহার
            cursor.execute("UPDATE users SET referral_balance = referral_balance + %s, referral_count = referral_count + 1 WHERE user_id = %s", (REFER_BONUS, referred_by))
            conn.commit()
            return True
    return False


# --- হ্যান্ডলার: /start কমান্ড ---
@app.on_message(filters.command("start"))
async def start_command(client, message):
    global conn, cursor # ✅ গ্লোবাল ডিক্লারেশন
    
    # ✅ NoneType ফিক্স (হ্যান্ডলারের শুরুতে)
    if cursor is None:
        await message.reply_text("⛔️ দুঃখিত! সার্ভার সংযোগের সমস্যার কারণে বটটি বর্তমানে কাজ করছে না। কিছুক্ষণ পর আবার চেষ্টা করুন।")
        return
    
    user_id = message.from_user.id
    first_name = message.from_user.first_name # নাম পাওয়ার জন্য

    if is_user_blocked(user_id):
        await message.reply_text("❌ দুঃখিত! আপনাকে বটটি ব্যবহার থেকে ব্লক করা হয়েছে।")
        return

    referred_by = None
    
    if len(message.command) > 1:
        try:
            referred_by = int(message.command[1])
            # ✅ PostgreSQL (%s) ব্যবহার
            cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (referred_by,)) 
            if referred_by == user_id or cursor.fetchone() is None:
                 referred_by = None
            else:
                pass 
        except ValueError:
            referred_by = None
            
    # ✅ নতুন স্টার্ট মেসেজ
    if add_user(user_id, referred_by):
        text = f"👋 হ্যালো 🅳🅴🅰🆁 {first_name} ☀️\n\n෴❤️෴ 𝐖𝐞𝐥𝐜𝐨𝐦𝐞 ෴❤️෴\n\nনিচে মূল মেনু দেওয়া হলো।"
    else:
        text = f"👋 হ্যালো 🅳🅴🅰🆁 {first_name} ☀️\n\n෴❤️෴ 𝐖𝐞𝐥𝐜𝐨𝐦𝐞 ෴❤️෴\n\nনিচে মূল মেনু দেওয়া হলো।"


    await message.reply_text(
        text,
        reply_markup=main_menu_keyboard
    )


# --- হ্যান্ডলার: Daily Bonus (আপনার লজিক) ---
@app.on_message(filters.regex("💰 Daily Bonus"))
async def daily_bonus_handler(client, message):
    global conn, cursor # ✅ গ্লোবাল ডিক্লারেশন
    if is_user_blocked(message.from_user.id): return
    
    # ✅ NoneType ফিক্স
    if cursor is None:
        await message.reply_text("⛔️ ডেটাবেস সংযোগ নেই। কিছুক্ষণ পর আবার চেষ্টা করুন।")
        return
        
    await message.reply_text(
        "✅ Task complete করতে নিচের বাটনগুলো ব্যবহার করুন.\n"
        "✅ নিয়ম মেনে কাজ করবেন ইনকাম নিশ্চিত🚀",
        reply_markup=TASK_MENU_KEYBOARD_REPLY
    )

# --- হ্যান্ডলার: MAIN MENU বাটন ---
@app.on_message(filters.regex("🏠 MAIN MENU") & filters.private)
async def back_to_main_menu(client, message):
    await message.reply_text(
        "👋 আপনি মূল মেনুতে ফিরে এসেছেন।",
        reply_markup=main_menu_keyboard
    )


# --- হ্যান্ডলার: Refer & Earn (আপনার লজিক) ---
@app.on_message(filters.regex("🔗 Refer & Earn"))
async def refer_command(client, message):
    global conn, cursor # ✅ গ্লোবাল ডিক্লারেশন
    if is_user_blocked(message.from_user.id): return
    
    # ✅ NoneType ফিক্স
    if cursor is None:
        await message.reply_text("⛔️ ডেটাবেস সংযোগ নেই। কিছুক্ষণ পর আবার চেষ্টা করুন।")
        return
        
    user_id = message.from_user.id
    bot_username = client.me.username if client.me.username else "YourBotUsername"
    referral_link = f"https://t.me/{bot_username}?start={user_id}"
    
    # ✅ PostgreSQL (%s) ব্যবহার
    cursor.execute("SELECT referral_count FROM users WHERE user_id = %s", (user_id,)) 
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


# --- হ্যান্ডলার: My Account (আপনার লজিক) ---
@app.on_message(filters.regex("👤 My Account"))
async def account_command(client, message):
    global conn, cursor # ✅ গ্লোবাল ডিক্লারেশন
    if is_user_blocked(message.from_user.id): return
    
    # ✅ NoneType ফিক্স
    if cursor is None:
        await message.reply_text("⛔️ ডেটাবেস সংযোগ নেই। কিছুক্ষণ পর আবার চেষ্টা করুন।")
        return
        
    user_id = message.from_user.id
    # ✅ PostgreSQL (%s) ব্যবহার
    cursor.execute("SELECT task_balance, referral_balance, referral_count FROM users WHERE user_id = %s", (user_id,)) 
    data = cursor.fetchone()
    
    if data:
        # PostgreSQL NUMERIC 
        task_balance = float(data[0])
        referral_balance = float(data[1])
        ref_count = data[2]
        
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


# --- হ্যান্ডলার: History (আপনার লজিক) ---
@app.on_message(filters.regex("🧾 History"))
async def history_command(client, message):
    global conn, cursor # ✅ গ্লোবাল ডিক্লারেশন
    if is_user_blocked(message.from_user.id): return
    
    # ✅ NoneType ফিক্স
    if cursor is None:
        await message.reply_text("⛔️ ডেটাবেস সংযোগ নেই। কিছুক্ষণ পর আবার চেষ্টা করুন।")
        return
        
    user_id = message.from_user.id
    # ✅ PostgreSQL (%s) ব্যবহার
    cursor.execute(
        "SELECT timestamp, amount, method, account_number, status FROM withdraw_history WHERE user_id = %s ORDER BY timestamp DESC LIMIT 10", 
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
        
        # PostgreSQL timestamp ফর্মাট করা
        formatted_timestamp = timestamp.strftime("%Y-%m-%d %H:%M")
        
        history_text += (
            f"📅 {formatted_timestamp[:10]} - {formatted_timestamp[11:16]}\n"
            f"💰 {float(amount):.2f} ৳\n"
            f"🏦 {method}\n"
            f"🔢 {number}\n"
            f"🎨 {status_emoji}\n"
            "-----------------------\n"
        )
    
    await message.reply_text(history_text)


# --- হ্যান্ডলার: Status (Admin) (আপনার লজিক) ---
@app.on_message(filters.regex("👑 Status \\(Admin\\)"))
async def admin_status_command(client, message):
    global conn, cursor # ✅ গ্লোবাল ডিক্লারেশন
    if is_user_blocked(message.from_user.id): return
    
    # ✅ NoneType ফিক্স
    if cursor is None:
        await message.reply_text("⛔️ ডেটাবেস সংযোগ নেই। কিছুক্ষণ পর আবার চেষ্টা করুন।")
        return
        
    contact_button = InlineKeyboardMarkup(
        [[InlineKeyboardButton("💬 CONTACT", url=f"https://t.me/{ADMIN_CONTACT_USERNAME}")]]
    )
    
    text = "✳️ জরুরী প্রয়োজনে এডমিনের সাথে যোগাযোগ করুন ✳️"
    await message.reply_text(text, reply_markup=contact_button)


# 🟢 ✅ চূড়ান্ত ফিক্স: ডায়নামিক টাস্ক বাটন হ্যান্ডলারস
for i in range(1, 11):
    task_name = f"TASK-{i}"
    button_text = f"🏅 {task_name}_10 TK"
    callback_data = f"task_{i}_" 
    
    exec(f"""
@app.on_message(filters.regex("{button_text}") & filters.private)
async def show_task_{i}_details(client: Client, message: Message):
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
    global conn, cursor # ✅ গ্লোবাল ডিক্লারেশন
    
    # ✅ NoneType ফিক্স
    if cursor is None:
        await message.reply_text("⛔️ ডেটাবেস সংযোগ নেই। কিছুক্ষণ পর আবার চেষ্টা করুন।")
        return
        
    main_menu_texts = ["💰 Daily Bonus", "🔗 Refer & Earn", "👤 My Account", "🧾 History", "👑 Status (Admin)", "BKASH", "NAGAD", "CANCEL", "🏠 MAIN MENU"] 
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
