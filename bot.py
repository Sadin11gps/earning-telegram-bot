import os
import sqlite3
import time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# **********************************************
# **** আপনার গোপনীয় কী গুলো (আপনার দেওয়া তথ্য) ****
# **********************************************
API_ID = 28298245
API_HASH = "e4df3b85b3cc1c178120f2076d1685a2"
BOT_TOKEN = "8408784365:AAGdHhfFimVY30QMB1SGqFOzkyf9gbxcd-8"
OWNER_ID = 7702378694 # আপনার নিজের Telegram ID (সংখ্যা) এখানে বসান
# **********************************************

# ডেটাবেস কনফিগারেশন
DB_NAME = 'user_data.db'

# Pyrogram ক্লায়েন্ট ইনিশিয়ালাইজেশন
app = Client(
    "earning_bot_session",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    # Termux-এ নেটওয়ার্ক ফিক্সের জন্য in_memory ব্যবহার করা হলো
    in_memory=True 
)

# --- ১. ডেটাবেস ফাংশন ---
def initialize_db():
    """ডেটাবেস টেবিল তৈরি করে এবং সংযোগ স্থাপন করে"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 0.0,
            total_earned REAL DEFAULT 0.0,
            join_date TEXT,
            last_bonus_time INTEGER DEFAULT 0,
            referred_by INTEGER DEFAULT 0,
            total_referrals INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def add_new_user(user_id):
    """নতুন ইউজারকে ডেটাবেসে যুক্ত করে"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    join_date = time.strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT OR IGNORE INTO users (user_id, join_date) VALUES (?, ?)", (user_id, join_date))
    conn.commit()
    conn.close()

def get_user_data(user_id):
    """ইউজারের সব ডেটা ফেচ করে"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    data = cursor.fetchone()
    conn.close()
    return data # (user_id, balance, total_earned, join_date, last_bonus_time, referred_by, total_referrals)

# --- ২. কীবোর্ড ও UI ফাংশন ---
def get_main_keyboard():
    """প্রিমিয়াম লুকের জন্য মূল ইনলাইন কীবোর্ড"""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Daily Bonus", callback_data="daily_bonus")],
        [InlineKeyboardButton("🔗 Refer & Earn", callback_data="refer_earn"),
         InlineKeyboardButton("💼 My Account", callback_data="my_account")],
        [InlineKeyboardButton("💸 Withdraw", callback_data="withdraw"),
         InlineKeyboardButton("📈 Stats (Admin)", callback_data="admin_stats")]
    ])
    return keyboard

# --- ৩. বটের কমান্ড হ্যান্ডলার ---
@app.on_message(filters.command("start"))
def start_command(client, message):
    user_id = message.from_user.id
    
    # ডেটাবেসে ইউজারকে যুক্ত করা
    add_new_user(user_id)
    
    # ইউজারকে স্বাগতম বার্তা পাঠানো
    message.reply_text(
        f"👋 হ্যালো {message.from_user.first_name}!\n\n"
        f"আমাদের VIP আর্নিং বটে আপনাকে স্বাগতম। নিচে আপনার জন্য প্রিমিয়াম অপশন দেওয়া হলো:",
        reply_markup=get_main_keyboard()
    )

# --- ৪. কুইরি হ্যান্ডলার (বাটনে ক্লিক করলে) ---
@app.on_callback_query()
def handle_callbacks(client, callback_query):
    data = callback_query.data
    user_id = callback_query.from_user.id
    
    # কুইরি আইডি পেলে, সে অনুযায়ী উত্তর দেবে
    if data == "my_account":
        user_data = get_user_data(user_id)
        if user_data:
            balance = user_data[1] # ব্যালেন্স
            total_ref = user_data[6] # রেফারেল সংখ্যা
            
            # একটি সুন্দর অ্যাকাউন্ট স্টেটাস মেসেজ
            message_text = (
                "💼 **আপনার অ্যাকাউন্ট স্ট্যাটাস**\n"
                "---------------------------------------\n"
                f"💰 বর্তমান ব্যালেন্স: **{balance:.2f} ৳**\n"
                f"🔗 মোট রেফারেল: **{total_ref} জন**\n"
                "\n"
                "কমিশন পেতে আরও বেশি রেফার করুন!"
            )
            callback_query.message.edit_text(message_text, reply_markup=get_main_keyboard())
        else:
            callback_query.answer("আপনার ডেটা খুঁজে পাওয়া যায়নি। /start লিখে আবার শুরু করুন।")

    elif data == "refer_earn":
        # রেফারের লিংক তৈরি
        ref_link = f"https://t.me/{client.me.username}?start={user_id}"
        
        message_text = (
            "🔗 **রেফার করে আয় করুন!**\n"
            "---------------------------------\n"
            "আপনার বন্ধুকে রেফার করুন এবং প্রতি রেফারে একটি নিশ্চিত বোনাস পান।\n\n"
            "➡️ **আপনার রেফারেল লিংক:**\n"
            f"`{ref_link}`\n\n"
            "উপরে ক্লিক করে লিংকটি কপি করে বন্ধুদের সাথে শেয়ার করুন।"
        )
        callback_query.message.edit_text(message_text, reply_markup=get_main_keyboard())
        
    elif data == "daily_bonus":
        # এটি কেবল একটি প্লেসহোল্ডার, আপনি এখানে বোনাস লজিক লিখবেন
        callback_query.answer("Daily Bonus: এই ফিচারটি শীঘ্রই চালু করা হবে!")
        
    elif data == "withdraw":
        # এটি কেবল একটি প্লেসহোল্ডার
        callback_query.answer("Withdraw: আপনার ব্যালেন্স পর্যাপ্ত নয়।")
        
    elif data == "admin_stats":
        if user_id == OWNER_ID:
            callback_query.answer("Admin Stats: এই ফিচারটি ডেভেলপমেন্ট চলছে।")
        else:
            callback_query.answer("আপনি অ্যাডমিন নন।", show_alert=True)
            
    else:
        callback_query.answer("অজানা অপশন।")


# --- ৫. বট শুরু করার ফাংশন ---
if __name__ == "__main__":
    try:
        # বট চলার আগে ডেটাবেস তৈরি করে নেওয়া
        initialize_db() 
        print("ডেটাবেস ইনিশিয়ালাইজেশন সম্পন্ন।")
        print("বট চলছে... Termux অ্যাপটি বন্ধ করবেন না!")
        app.run() # বট শুরু করা
    except Exception as e:
        print(f"\n❌ বট শুরু করার সময় ত্রুটি: {e}")
        print("অনুগ্রহ করে আপনার API Key এবং BOT TOKEN সঠিক আছে কিনা পরীক্ষা করুন।")
