import os
import sqlite3
import time
from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton
)

# **********************************************
# --- মডিউল ইম্পোর্ট (ধরে নেওয়া হলো সব ফাইল তৈরি আছে) ---
# **********************************************
# USER_STATE এখানে ডিফাইন করা আছে, কিন্তু এটি withdraw মডিউলে গ্লোবালি হ্যান্ডেল হচ্ছে
from withdraw import setup_withdraw_handlers, USER_STATE
from admin import setup_admin_handlers, is_user_blocked

# Task মডিউলগুলো
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
OWNER_ID = 7702378694  # আপনার অ্যাডমিন আইডি
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

# মূল মেনুর বাটন (Reply Keyboard) - WITHDRAW ফিক্সড
main_menu_keyboard = ReplyKeyboardMarkup(
    [
        [KeyboardButton("💰 Daily Bonus"), KeyboardButton("🔗 Refer & Earn")],
        # ফিক্সড: ইমোজি ছাড়া শুধু 'Withdraw' ব্যবহার করা হয়েছে
        [KeyboardButton("WITHDRAW_NOW"), KeyboardButton("👤 My Account")],        [KeyboardButton("🧾 History"), KeyboardButton("👑 Status (Admin)")]
    ],
    resize_keyboard=True
)

# টাস্ক মেনুর বাটন (Inline Keyboard)
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
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO users (user_id, referred_by) VALUES (?, ?)", (user_id, referred_by))
        conn.commit()
        if referred_by:
            cursor.execute("UPDATE users SET referral_balance = referral_balance + ?, referral_count = referral_count + 1 WHERE user_id = ?", (REFER_BONUS, referred_by))
            conn.commit()
            return True
    return False


# --- হ্যান্ডলার: /start কমান্ড ---
@app.on_message(filters.command("start"))
async def start_command(client, message):
    user_id = message.from_user.id

    # ... [আপনার আগের /start লজিক] ...
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
                add_user(user_id, referred_by)
                await client.send_message(
                    referred_by,
                    f"🎉 অভিনন্দন! একজন নতুন ইউজার ({message.from_user.first_name}) আপনার রেফারেল লিংকে জয়েন করেছে। আপনি {REFER_BONUS:.2f} টাকা বোনাস পেয়েছেন!"
                )
        except ValueError:
            referred_by = None
            
    if add_user(user_id, referred_by):
        text = "👋 স্বাগতম! আপনি আপনার পছন্দের টাস্কগুলো করে আয় করা শুরু করতে পারেন।"
    else:
        text = "👋 আবার স্বাগতম! নিচে মূল মেনু দেওয়া হলো।"

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
        reply_markup=task_menu_keyboard
    )


# --- হ্যান্ডলার: Refer & Earn ---
@app.on_message(filters.regex("🔗 Refer & Earn"))
async def refer_command(client, message):
    if is_user_blocked(message.from_user.id): return
    # ... [আপনার আগের Refer & Earn লজিক] ...
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
    # ... [আপনার আগের My Account লজিক] ...
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
    # ... [আপনার আগের History লজিক] ...
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
    # ... [আপনার আগের Status লজিক] ...
    contact_button = InlineKeyboardMarkup(
        [[InlineKeyboardButton("💬 CONTACT", url=f"https://t.me/{ADMIN_CONTACT_USERNAME}")]]
    )
    
    text = "✳️ জরুরী প্রয়োজনে এডমিনের সাথে যোগাযোগ করুন ✳️"
    await message.reply_text(text, reply_markup=contact_button)


# --- ক্যোয়ারি হ্যান্ডলার: টাস্ক বাটনগুলো ---
@app.on_callback_query(filters.regex("^task_"))
async def task_callback_handler(client, callback_query):
    # Task logic এখন task_X.py ফাইলগুলোতে থাকবে
    task_id = callback_query.data.split('_')[1] 
    
    # আপাতত খালি লজিক (আপনার task_X.py তৈরি না হওয়া পর্যন্ত)
    await callback_query.answer(f"Task {task_id} এর লজিক এখনও Task মডিউলে সেট করা হয়নি।") 
    

# --- ক্যোয়ারি হ্যান্ডলার: Main Menu বাটন ---
@app.on_callback_query(filters.regex("^main_menu"))
async def back_to_main_menu(client, callback_query):
    await callback_query.edit_message_text(
        "👋 আপনি মূল মেনুতে ফিরে এসেছেন। নিচে মূল মেনু দেওয়া হলো:",
        reply_markup=main_menu_keyboard
    )
    await callback_query.answer("মূল মেনুতে ফিরে গেছেন।")


# --- চূড়ান্ত ফিক্স: নন-কমান্ড মেসেজ হ্যান্ডলার (এডমিনের কাছে ট্রান্সফার/অন্যান্য) ---
@app.on_message(filters.private & filters.text) 
async def process_text_messages(client, message):
    
    # 1. উইথড্র প্রসেস চলছে কিনা, তা পরীক্ষা করুন (চললে, withdraw.py হ্যান্ডেল করবে)
    if USER_STATE.get(message.from_user.id):
        return
    
    # *** 💡 CRITICAL FIX: যদি টেক্সটটি 'Withdraw' হয়, তবে পুরো হ্যান্ডলারটি থেকে বের হয়ে যাও ***
    # কারণ আমরা এখন বাটন টেক্সট হিসেবে "Withdraw" ব্যবহার করছি।
    if message.text.strip() == "Withdraw":
        return
        
    # 2. মেনু বাটনগুলোর টেক্সট থাকলে এড়িয়ে যান (এগুলো অন্য হ্যান্ডলার ধরবে)
    # Withdraw বাটন টেক্সট এখান থেকে সরানো হয়েছে।
    main_menu_texts = ["💰 Daily Bonus", "🔗 Refer & Earn", "👤 My Account", "🧾 History", "👑 Status (Admin)", "BKASH", "NAGAD", "CANCEL"] 
    if message.text in main_menu_texts:
        return
        
    user_id = message.from_user.id
    
    if is_user_blocked(user_id): return
    
    # অ্যাডমিনের কাছে মেসেজ ফরওয়ার্ড করা (যদি উপরের কোনো শর্তে না পড়ে)
    await client.forward_messages(
        chat_id=OWNER_ID,
        from_chat_id=message.chat.id,
        message_ids=message.id
    )
    
    # ইউজারকে নিশ্চিতকরণ মেসেজ দেওয়া
    await message.reply_text(
        "✅ আপনার মেসেজটি এডমিনের কাছে পাঠানো হয়েছে। খুব শীঘ্রই আপনাকে রিপ্লাই দেওয়া হবে।"
    )
    

# **********************************************
# --- মডিউল হ্যান্ডলারগুলো চালু করা ও বট চালু করা ---
# **********************************************

# 1. হ্যান্ডলার মডিউলগুলো চালু করা
setup_withdraw_handlers(app, USER_STATE)
setup_admin_handlers(app)
setup_task_handlers(app) # Task হ্যান্ডলার কল

# --- বট চালানো ---
print("Telegram Earning Bot is starting...")
app.run()
