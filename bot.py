import os
# <<<<<<< CRITICAL FIX: PostgreSQL সংযোগের জন্য psycopg2 ব্যবহার করা হলো >>>>>>>
import psycopg2 
import time
from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton
)

# **********************************************
# --- মডিউল ইম্পোর্ট ---
# **********************************************
from withdraw import setup_withdraw_handlers, USER_STATE
from admin import setup_admin_handlers, is_user_blocked

# Task মডিউলগুলো (আপনার নিশ্চিতকরণ অনুযায়ী ইমপোর্ট সচল রাখা হলো)
from task_1 import setup_task_1_handler
from task_2 import setup_task_2_handler
from task_3 import setup_task_3_handler
from task_4 import setup_task_4_handler
from task_5 import setup_task_5_handler
from task_6 import setup_task_6_handler
from task_7 import setup_task_7_handler
from task_8 import setup_task_8_handler
from task_9 import setup_task_9_handler
from task_10 import setup_task_10_handler

# --- টাস্ক হ্যান্ডলার সেটআপ ফাংশন ---
def setup_task_handlers(app: Client):
    # প্রতিটি Task মডিউলের সেটআপ ফাংশন এখানে কল করা হবে
    setup_task_1_handler(app)
    setup_task_2_handler(app)
    setup_task_3_handler(app)
    setup_task_4_handler(app)
    setup_task_5_handler(app)
    setup_task_6_handler(app)
    setup_task_7_handler(app)
    setup_task_8_handler(app)
    setup_task_9_handler(app)
    setup_task_10_handler(app)


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
# **** বটের ব্যবসায়িক লজিক ভেরিয়েবল ****
# **********************************************
REFER_BONUS = 30.00          
MIN_WITHDRAW = 1500.00       
WITHDRAW_FEE_PERCENT = 10.0  
REQUIRED_REFERRALS = 20      
# **********************************************


# --- Database সেটআপ (PostgreSQL) ---
# <<<<<<< CRITICAL FIX: PostgreSQL সংযোগ লজিক যোগ করা হলো >>>>>>>
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    if not DATABASE_URL:
        print("Error: DATABASE_URL not set.")
        return None 
    
    try:
        # ক্লাউড হোস্টিং (Railway/Render) এর জন্য sslmode='require' আবশ্যক
        conn = psycopg2.connect(DATABASE_URL, sslmode='require') 
        return conn
    except Exception as e:
        print(f"Database connection failed: {e}")
        return None

# ডেটাবেস সংযোগ ইনিশিয়ালাইজ করুন
conn = get_db_connection()
cursor = conn.cursor() if conn else None


# ইউজার টেবিল তৈরি/আপডেট (PostgreSQL সিনট্যাক্স)
if conn and cursor:
    try:
        # Task Status টেবিল (task_1.py-এর লজিক অনুযায়ী)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_status (
                user_id BIGINT,
                task_name TEXT,
                completed_at TEXT,
                PRIMARY KEY (user_id, task_name, completed_at)
            )
        ''')
        
        # ইউজার টেবিল 
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                task_balance REAL DEFAULT 0.00,
                referral_balance REAL DEFAULT 0.00,
                referral_count INTEGER DEFAULT 0,
                referred_by BIGINT,
                is_blocked INTEGER DEFAULT 0,
                last_bonus_time INTEGER DEFAULT 0
            )
        ''')

        # উইথড্র হিস্টরি টেবিল তৈরি 
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS withdraw_history (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                amount REAL,
                method TEXT,
                account_number TEXT,
                status TEXT DEFAULT 'Pending',
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
    except Exception as e:
        print(f"Database table creation failed: {e}")

# <<<<<<< CRITICAL FIX END >>>>>>>


# --- কীবোর্ড সেটআপ (অপরিবর্তিত) ---
main_menu_keyboard = ReplyKeyboardMarkup(
    [
        [KeyboardButton("💰 Daily Bonus"), KeyboardButton("🔗 Refer & Earn")],
        [KeyboardButton("Withdraw"), KeyboardButton("👤 My Account")],
        [KeyboardButton("🧾 History"), KeyboardButton("👑 Status (Admin)")]
    ],
    resize_keyboard=True
)

task_menu_keyboard = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton("🏅 TASK-1_10 TK", callback_data="task_1_10"),
            InlineKeyboardButton("🏅 TASK-2_10 TK", callback_data="task_2_10")
        ],
        [
            InlineKeyboardButton("🏅 TASK-3_10 TK", callback_data="task_3_10"),
            InlineKeyboardButton("🏅 TASK-4_10 TK", callback_data="task_4_10")
        ],
        [
            InlineKeyboardButton("🏅 TASK-5_10 TK", callback_data="task_5_10"),
            InlineKeyboardButton("🏅 TASK-6_10 TK", callback_data="task_6_10")
        ],
        [
            InlineKeyboardButton("🏅 TASK-7_10 TK", callback_data="task_7_10"),
            InlineKeyboardButton("🏅 TASK-8_10 TK", callback_data="task_8_10")
        ],
        [
            InlineKeyboardButton("🏅 TASK-9_10 TK", callback_data="task_9_10"),
            InlineKeyboardButton("🏅 TASK-10_10 TK", callback_data="task_10_10")
        ],
        [
            InlineKeyboardButton("🏠 MAIN MENU", callback_data="main_menu")
        ]
    ]
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
    if conn is None or cursor is None:
        return False
        
    cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO users (user_id, referred_by) VALUES (%s, %s)", (user_id, referred_by))
        conn.commit()
        if referred_by:
            cursor.execute("UPDATE users SET referral_balance = referral_balance + %s, referral_count = referral_count + 1 WHERE user_id = %s", (REFER_BONUS, referred_by))
            conn.commit()
            return True
    return False


# --- হ্যান্ডলার: /start কমান্ড ---
@app.on_message(filters.command("start"))
async def start_command(client, message):
    user_id = message.from_user.id
    
    if conn is None or cursor is None:
        await message.reply_text("❌ ডেটাবেস সংযোগ নেই। কিছুক্ষণ পর আবার চেষ্টা করুন।")
        return

    if is_user_blocked(user_id):
        await message.reply_text("❌ দুঃখিত! আপনাকে বটটি ব্যবহার থেকে ব্লক করা হয়েছে।")
        return

    referred_by = None
    
    if len(message.command) > 1:
        try:
            referred_by = int(message.command[1])
            cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (referred_by,))
            if referred_by == user_id or cursor.fetchone() is None:
                 referred_by = None
            else:
                add_user(user_id, referred_by)
                await client.send_message(
                    referred_by,
                    f"🎉 অভিনন্দন! একজন নতুন ইউজার ({message.from_user.first_name}) আপনার রেফারেল লিংকে জয়েন করেছে। আপনি {REFER_BONUS:.2f} টাকা বোনাস পেয়েছেন!"
                )
        except ValueError:
            referred_by = None
            
    if add_user(user_id, referred_by):
        first_name = message.from_user.first_name
        text = f"👋 হ্যালো 🅳🅴🅰🆁 {first_name} ☀️\n\n෴❤️෴ 𝐖𝐞𝐥𝐜𝐨𝐦𝐞 ෴❤️෴\n\n<নিচে মূল মেনু দেওয়া হলো।"
    else:
        text = "👋 আবার স্বাগতম! নিচে মূল মেনু দেওয়া হলো।"

    await message.reply_text(
        text,
        reply_markup=main_menu_keyboard
    )


# --- অন্যান্য হ্যান্ডলার... (অপরিবর্তিত) ---
@app.on_message(filters.regex("💰 Daily Bonus"))
async def daily_bonus_handler(client, message):
    if is_user_blocked(message.from_user.id): return
    await message.reply_text(
        "✅ Task complete করতে নিচের বাটনগুলো ব্যবহার করুন.\n"
        "✅ নিয়ম মেনে কাজ করবেন ইনকাম নিশ্চিত🚀", 
        reply_markup=task_menu_keyboard
    )

@app.on_message(filters.regex("🔗 Refer & Earn"))
async def refer_command(client, message):
    if is_user_blocked(message.from_user.id): return
    user_id = message.from_user.id
    cursor.execute("SELECT referral_count FROM users WHERE user_id = %s", (user_id,))
    data = cursor.fetchone()
    bot_username = client.me.username if client.me.username else "YourBotUsername"
    referral_link = f"https://t.me/{bot_username}?start={user_id}"
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

@app.on_message(filters.regex("👤 My Account"))
async def account_command(client, message):
    if is_user_blocked(message.from_user.id): return
    user_id = message.from_user.id
    cursor.execute("SELECT task_balance, referral_balance, referral_count FROM users WHERE user_id = %s", (user_id,))
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

@app.on_message(filters.regex("🧾 History"))
async def history_command(client, message):
    if is_user_blocked(message.from_user.id): return
    user_id = message.from_user.id
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
        timestamp_str = str(timestamp)
        status_emoji = "✅ Approved" if status == "Approved" else ("❌ Rejected" if status == "Rejected" else "⏳ Pending")
        history_text += (
            f"📅 {timestamp_str[:10]} - {timestamp_str[11:16]}\n"
            f"💰 {amount:.2f} ৳\n"
            f"🏦 {method}\n"
            f"🔢 {number}\n"
            f"🎨 {status_emoji}\n"
            "-----------------------\n"
        )
    await message.reply_text(history_text)

@app.on_message(filters.regex("👑 Status \\(Admin\\)"))
async def admin_status_command(client, message):
    if is_user_blocked(message.from_user.id): return
    contact_button = InlineKeyboardMarkup(
        [[InlineKeyboardButton("💬 CONTACT", url=f"https://t.me/{ADMIN_CONTACT_USERNAME}")]]
    )
    text = "✳️ জরুরী প্রয়োজনে এডমিনের সাথে যোগাযোগ করুন ✳️" 
    await message.reply_text(text, reply_markup=contact_button)

@app.on_callback_query(filters.regex("^task_"))
async def task_callback_handler(client, callback_query):
    # এই হ্যান্ডলারটি এখন task_X.py ফাইলগুলোর ভেতরে সংজ্ঞায়িত হবে
    task_id = callback_query.data.split('_')[1] 
    await callback_query.answer(f"Task {task_id} এর লজিক সেটআপ করা হয়েছে।") 
    
@app.on_callback_query(filters.regex("^main_menu"))
async def back_to_main_menu(client, callback_query):
    await callback_query.edit_message_text(
        "👋 আপনি মূল মেনুতে ফিরে এসেছেন। নিচে মূল মেনু দেওয়া হলো:",
        reply_markup=main_menu_keyboard
    )
    await callback_query.answer("মূল মেনুতে ফিরে গেছেন।")

@app.on_message(filters.private & filters.text) 
async def process_text_messages(client, message):
    if USER_STATE.get(message.from_user.id): return
    if message.text.strip() == "Withdraw": return
        
    main_menu_texts = ["💰 Daily Bonus", "🔗 Refer & Earn", "👤 My Account", "🧾 History", "👑 Status (Admin)", "BKASH", "NAGAD", "CANCEL"] 
    if message.text in main_menu_texts: return
        
    user_id = message.from_user.id
    if is_user_blocked(user_id): return
    
    await client.forward_messages(
        chat_id=OWNER_ID, from_chat_id=message.chat.id, message_ids=message.id
    )
    await message.reply_text(
        "✅ আপনার মেসেজটি এডমিনের কাছে পাঠানো হয়েছে। খুব শীঘ্রই আপনাকে রিপ্লাই দেওয়া হবে।"
    )
    

# **********************************************
# --- মডিউল হ্যান্ডলারগুলো চালু করা ও বট চালু করা ---
# **********************************************
setup_withdraw_handlers(app, USER_STATE)
setup_admin_handlers(app)
setup_task_handlers(app) 

# --- বট চালানো ---
print("Telegram Earning Bot is starting...")

# <<<<<<< CRITICAL FIX: ডেটাবেস সংযোগ না হলে বট বন্ধ হয়ে যাবে >>>>>>>
if conn is None:
    print("FATAL ERROR: Bot is shutting down due to database connection failure.")
else:
    app.run()
# <<<<<<< CRITICAL FIX END >>>>>>>
