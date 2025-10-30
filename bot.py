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

# --- মডিউল ইমপোর্ট করা ---
from withdraw import setup_withdraw_handlers, USER_STATE
from admin import setup_admin_handlers, is_user_blocked


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
REFER_BONUS = 30.00          # প্রতি রেফারে 30 টাকা
MIN_WITHDRAW = 1500.00       # সর্বনিম্ন 1500 টাকা হলে উইথড্র করা যাবে
WITHDRAW_FEE_PERCENT = 10.0  # 10% উইথড্র ফি
REQUIRED_REFERRALS = 20      # উইথড্র করার জন্য ২০ টি রেফার
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

# মূল মেনুর বাটন (Reply Keyboard) - **বাটন ও হ্যান্ডলারের সাথে ইমোজি ম্যাচ করবে**
main_menu_keyboard = ReplyKeyboardMarkup(
    [
        [KeyboardButton("💰 Daily Bonus"), KeyboardButton("🔗 Refer & Earn")],
        [KeyboardButton("💳 Withdraw"), KeyboardButton("👤 My Account")],
        [KeyboardButton("🧾 History"), KeyboardButton("👑 Status (Admin)")]
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
            # রেফারেল বোনাস যোগ করা
            cursor.execute("UPDATE users SET referral_balance = referral_balance + ?, referral_count = referral_count + 1 WHERE user_id = ?", (REFER_BONUS, referred_by))
            conn.commit()
            return True
    return False


# --- হ্যান্ডলার: /start কমান্ড ---
@app.on_message(filters.command("start"))
async def start_command(client, message):
    user_id = message.from_user.id

    if is_user_blocked(user_id):
        await message.reply_text("❌ দুঃখিত! আপনাকে বটটি ব্যবহার থেকে ব্লক করা হয়েছে।")
        return

    referred_by = None
    
    # রেফারেল লিংক থেকে আসা ইউজার শনাক্ত করা
    if len(message.command) > 1:
        try:
            referred_by = int(message.command[1])
            # নিশ্চিত করুন রেফারেল আইডিটি নিজের না এবং ডাটাবেসে আছে
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
            
    # ইউজারকে Database এ যোগ করা
    if add_user(user_id, referred_by):
        text = "👋 স্বাগতম! আপনি আপনার পছন্দের টাস্কগুলো করে আয় করা শুরু করতে পারেন।"
    else:
        text = "👋 আবার স্বাগতম! নিচে মূল মেনু দেওয়া হলো।"

    await message.reply_text(
        text,
        reply_markup=main_menu_keyboard
    )


# --- হ্যান্ডলার: Daily Bonus (ইমোজি সহ) ---
@app.on_message(filters.regex("💰 Daily Bonus"))
async def daily_bonus_handler(client, message):
    if is_user_blocked(message.from_user.id): return
    
    # ইউজারকে টাস্ক মেনু দেখান
    await message.reply_text(
        "✅ Task complete করতে নিচের বাটনগুলো ব্যবহার করুন.\n"
        "✅ নিয়ম মেনে কাজ করবেন ইনকাম নিশ্চিত🚀",
        reply_markup=task_menu_keyboard
    )


# --- হ্যান্ডলার: Refer & Earn (ইমোজি সহ) ---
@app.on_message(filters.regex("🔗 Refer & Earn"))
async def refer_command(client, message):
    if is_user_blocked(message.from_user.id): return

    user_id = message.from_user.id
    referral_link = f"https://t.me/{client.me.username}?start={user_id}"
    
    cursor.execute("SELECT referral_count FROM users WHERE user_id = ?", (user_id,))
    ref_count = cursor.fetchone()[0]
    
    text = (
        "🎉 **রেফার করে আয় করুন!**\n"
        "-\n"
        f"আপনার বন্ধুকে রেফার করুন এবং প্রতি রেফারে একটি নিশ্চিত বোনাস পান।\n\n"
        f"💸 REFER BOUNS: **{REFER_BONUS:.2f} TK**\n"
        f"🔗 মোট রেফারেল: **{ref_count} জন**\n"
        "-----------------------\n"
        "🌐 **REFER LINK** 🌐\n"
        f"🔗 `{referral_link}`\n\n"
        "🚀 উপরে ক্লিক করে লিংকটি কপি করে বন্ধুদের সাথে শেয়ার করুন।"
    )
    await message.reply_text(text)


# --- হ্যান্ডলার: My Account (ইমোজি সহ) ---
@app.on_message(filters.regex("👤 My Account"))
async def account_command(client, message):
    if is_user_blocked(message.from_user.id): return

    user_id = message.from_user.id
    cursor.execute("SELECT task_balance, referral_balance, referral_count FROM users WHERE user_id = ?", (user_id,))
    data = cursor.fetchone()
    if data:
        task_balance, referral_balance, ref_count = data
    else:
        task_balance, referral_balance, ref_count = 0.00, 0.00, 0
        
    total_balance = task_balance + referral_balance
    
    text = (
        "💼 **আপনার অ্যাকাউন্ট স্ট্যাটাস**\n"
        "-\n"
        f"🏅 Task ব্যালেন্স: **{task_balance:.2f} ৳**\n"
        f"💸 রেফার ব্যালেন্স: **{referral_balance:.2f} ৳**\n"
        f"💰 বর্তমান ব্যালেন্স: **{total_balance:.2f} ৳**\n"
        f"🔗 মোট রেফারেল: **{ref_count} জন**\n\n"
        f"⚠️ **উইথড্র শর্ত**: **{MIN_WITHDRAW:.2f} ৳** এবং **{REQUIRED_REFERRALS} জন রেফার**।\n\n"
        "✅ কমিশন পেতে আরও বেশি রেফার করুন!\n"
        "✅ নিয়মিত সবগুলো টাস্ক কমপ্লিট করুন!"
    )
    await message.reply_text(text)


# --- হ্যান্ডলার: History (ইমোজি সহ) ---
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


# --- হ্যান্ডলার: Status (Admin) (ইমোজি সহ) ---
@app.on_message(filters.regex("👑 Status \\(Admin\\)"))
async def admin_status_command(client, message):
    if is_user_blocked(message.from_user.id): return

    contact_button = InlineKeyboardMarkup(
        [[InlineKeyboardButton("💬 CONTACT", url=f"https://t.me/{ADMIN_CONTACT_USERNAME}")]]
    )
    
    text = "✳️ জরুরী প্রয়োজনে এডমিনের সাথে যোগাযোগ করুন ✳️"
    await message.reply_text(text, reply_markup=contact_button)


# --- ক্যোয়ারি হ্যান্ডলার: টাস্ক বাটনগুলো ---
@app.on_callback_query(filters.regex("^task_"))
async def task_callback_handler(client, callback_query):
    # টাস্ক লজিক এখানে যুক্ত করা হবে
    await callback_query.answer("আপাতত এই টাস্কের কোড সেটআপ করা হয়নি।")

# --- ক্যোয়ারি হ্যান্ডলার: Main Menu বাটন ---
@app.on_callback_query(filters.regex("^main_menu"))
async def back_to_main_menu(client, callback_query):
    # যখন ইউজার Inline বাটন ব্যবহার করে Main Menu-তে ফিরতে চায়
    await callback_query.edit_message_text(
        "👋 আপনি মূল মেনুতে ফিরে এসেছেন। নিচে মূল মেনু দেওয়া হলো:",
        reply_markup=main_menu_keyboard
    )
    await callback_query.answer("মূল মেনুতে ফিরে গেছেন।")


# --- নন-কমান্ড মেসেজ হ্যান্ডলার (এডমিনের কাছে ট্রান্সফার) ---
@app.on_message(filters.private & filters.text) 
async def forward_to_admin(client, message):
    
    # 1. চেক করে যদি উইথড্র প্রসেস চলে, তবে এখানেই থেমে যাবে (withdraw.py হ্যান্ডেল করবে)
    if USER_STATE.get(message.from_user.id):
        return

    # 2. এটি নিশ্চিত করে যে এটি কোনো মেনু বাটন ক্লিক নয় (ইমোজি সহ চেক করা হচ্ছে)
    main_menu_texts = ["💰 Daily Bonus", "🔗 Refer & Earn", "💳 Withdraw", "👤 My Account", "🧾 History", "👑 Status (Admin)"]
    if message.text in main_menu_texts:
        return
        
    user_id = message.from_user.id
    
    if is_user_blocked(user_id): return
    
    # অ্যাডমিনের কাছে মেসেজ ফরওয়ার্ড করা
    await client.forward_messages(
        chat_id=OWNER_ID,
        from_chat_id=message.chat.id,
        message_ids=message.id
    )
    
    # ইউজারকে নিশ্চিতকরণ মেসেজ দেওয়া
    await message.reply_text(
        "✅ আপনার মেসেজটি এডমিনের কাছে পাঠানো হয়েছে। খুব শীঘ্রই আপনাকে রিপ্লাই দেওয়া হবে।"
    )
    

# --- মডিউল যুক্ত করা ---
setup_withdraw_handlers(app, USER_STATE)
setup_admin_handlers(app)


# --- বট চালানো ---
print("Telegram Earning Bot is starting...")
app.run()
