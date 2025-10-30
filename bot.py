import sqlite3
import os
from pyrogram import Client, filters
from pyrogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

# --- টাস্ক এবং উইথড্র হ্যান্ডলার ইমপোর্ট ---
# এই ফাইলগুলোতে আপনার মূল লজিক আছে
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
import withdraw_handlers 

# --- API কনফিগারেশন ---
# API ID, API HASH এবং BOT_TOKEN এনভায়রনমেন্ট ভেরিয়েবল (.env ফাইল থেকে) থেকে নেওয়া হবে
API_ID = int(os.environ.get("API_ID", 12345))
API_HASH = os.environ.get("API_HASH", "your_api_hash")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "your_bot_token")

# --- Database সেটআপ ---
DB_NAME = 'user_data.db'
# একটি সংযোগ স্থাপন করা
conn = sqlite3.connect(DB_NAME, check_same_thread=False)
cursor = conn.cursor()

# ইউজার টেবিল তৈরি (যদি না থাকে)
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    balance REAL DEFAULT 0.00,
    referrer_id INTEGER
)
""")
conn.commit()

# --- গ্লোবাল স্টেট ---
# এটি উইথড্র ফ্লো এবং অন্যান্য টেম্পোরারি স্টেট ট্র্যাক করতে ব্যবহৃত হয়
USER_STATE = {}

# --- কীবোর্ড ডেফিনিশন ---
# বট মেনুর প্রধান কীবোর্ড
main_menu_keyboard = ReplyKeyboardMarkup(
    [
        [KeyboardButton("💰 Daily Bonus"), KeyboardButton("🔗 Refer & Earn")],
        [KeyboardButton("TASK-1"), KeyboardButton("TASK-2"), KeyboardButton("TASK-3")],
        [KeyboardButton("TASK-4"), KeyboardButton("TASK-5"), KeyboardButton("TASK-6")],
        [KeyboardButton("TASK-7"), KeyboardButton("TASK-8"), KeyboardButton("TASK-9")],
        [KeyboardButton("TASK-10")],
        [KeyboardButton("WITHDRAW_NOW"), KeyboardButton("My Account")],
        [KeyboardButton("🧾 History"), KeyboardButton("Status (Admin)")]
    ],
    resize_keyboard=True
)

# --- কোর ফাংশনালিটি ---
def create_user_if_not_exists(user_id, username, referrer_id=None):
    """যদি ইউজার ডাটাবেসে না থাকে, তবে একটি নতুন রেকর্ড তৈরি করে।"""
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO users (user_id, username, balance, referrer_id) VALUES (?, ?, ?, ?)",
                       (user_id, username, 0.00, referrer_id))
        conn.commit()

# --- হ্যান্ডলার: /start কমান্ড ---
@Client.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    user_id = message.from_user.id
    username = message.from_user.username
    
    # রেফারেল লজিক প্রক্রিয়া করা
    referrer_id = None
    if len(message.command) > 1 and message.command[1].isdigit():
        referrer_id = int(message.command[1])
    
    create_user_if_not_exists(user_id, username, referrer_id)
    
    await message.reply_text(
        f"স্বাগতম {message.from_user.first_name}!\nআপনি এখন মেনু থেকে কাজ শুরু করতে পারেন।",
        reply_markup=main_menu_keyboard
    )

# --- হ্যান্ডলার: My Account ---
@Client.on_message(filters.regex("My Account") & filters.private)
async def my_account_handler(client: Client, message: Message):
    """ইউজারের বর্তমান ব্যালেন্স দেখায়।"""
    user_id = message.from_user.id
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    balance = result[0] if result else 0.00
    
    await message.reply_text(f"আপনার বর্তমান ব্যালেন্স: **{balance:.2f} টাকা**")

# --- হ্যান্ডলার: সমস্ত Text মেসেজ ক্যাচ করা (ডিফল্ট ফলব্যাক) ---
@Client.on_message(filters.text & filters.private, group=99)
async def process_text_messages(client: Client, message: Message):
    """যদি কোনো নির্দিষ্ট হ্যান্ডলার মেসেজটি ব্যবহার না করে, তবে এটি ফলব্যাক হিসেবে কাজ করে।"""
    user_id = message.from_user.id
    
    # উইথড্র ফ্লোতে থাকলে, এই হ্যান্ডলারটি নিষ্ক্রিয় থাকবে
    if USER_STATE.get(user_id):
        return
        
    text = message.text.strip().lower()
    
    # পরিচিত বাটন বা টাস্ক মেসেজ না হলে ডিফল্ট রিপ্লাই
    if text not in ["/start", "withdraw_now", "my account", "history", "status (admin)", "daily bonus", "refer & earn"] and not text.startswith("task-"):
        await message.reply_text("দুঃখিত, আমি এই কমান্ডটি বুঝতে পারিনি। মেনু থেকে একটি বিকল্প নির্বাচন করুন।", reply_markup=main_menu_keyboard)


# --- অ্যাপ ইনিশিয়ালাইজেশন ---
app = Client(
    "earning_bot_session",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)


# --- হ্যান্ডলার সেটআপ এবং বট চালু করা ---
if __name__ == "__main__":
    
    # উইথড্র হ্যান্ডলার সেটআপ (গুরুত্বপূর্ণ: group=-1 প্রায়োরিটি)
    # এটি নিশ্চিত করে যে উইথড্র হ্যান্ডলার সবার আগে চালু হয়
    withdraw_handlers.setup_withdraw_handlers(app, USER_STATE, group=-1) 
    
    # ✅ সবকটি টাস্ক হ্যান্ডলার সেটআপ করা
    # এটি আপনার 10টি টাস্ককে কার্যকর করে তোলে
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
    
    # বট চালু করা
    app.run()
