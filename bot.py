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
# **** ক্লাউড হোস্টিং-এর জন্য এনভায়রনমেন্ট ভেরিয়েবল ****
# **********************************************
# এই Key গুলো Railway Variables থেকে স্বয়ংক্রিয়ভাবে আসবে
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# **** অ্যাডমিন আইডি (আপনার Telegram ID) ****
OWNER_ID = 7702378694  
ADMIN_CONTACT_USERNAME = "rdsratul81" # যোগাযোগের জন্য আপনার ইউজারনেম
# **********************************************

# **********************************************
# **** বটের ব্যবসায়িক লজিক ভেরিয়েবল (আপডেট করা হয়েছে) ****
# **********************************************
REFER_BONUS = 30.00          # প্রতি রেফারে 30 টাকা
MIN_WITHDRAW = 1500.00       # সর্বনিম্ন 1500 টাকা হলে উইথড্র করা যাবে
WITHDRAW_FEE_PERCENT = 10.0  # 10% উইথড্র ফি
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

# মূল মেনুর বাটন (Reply Keyboard) - "History" এবং "Stats" সহ
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

# --- ফাংশন: ইউজার ব্লক স্ট্যাটাস ---
def is_user_blocked(user_id):
    cursor.execute("SELECT is_blocked FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    if result:
        return result[0] == 1
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
            if referred_by == user_id or referred_by not in [row[0] for row in cursor.execute("SELECT user_id FROM users").fetchall()]:
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


# --- হ্যান্ডলার: 💰 Daily Bonus (এখন টাস্ক মেনু দেখাবে) ---
@app.on_message(filters.regex("💰 Daily Bonus"))
async def daily_bonus_handler(client, message):
    if is_user_blocked(message.from_user.id): return
    
    # ইউজারকে টাস্ক মেনু দেখান
    await message.reply_text(
        "✅ Task complete করতে নিচের বাটনগুলো ব্যবহার করুন.\n"
        "✅ নিয়ম মেনে কাজ করবেন ইনকাম নিশ্চিত🚀",
        reply_markup=task_menu_keyboard
    )


# --- হ্যান্ডলার: 🔗 Refer & Earn ---
@app.on_message(filters.regex("🔗 Refer & Earn"))
async def refer_command(client, message):
    if is_user_blocked(message.from_user.id): return

    user_id = message.from_user.id
    referral_link = f"https://t.me/{client.me.username}?start={user_id}"
    
    text = (
        "🎉 রেফার করে আয় করুন!\n"
        "-\n"
        f"আপনার বন্ধুকে রেফার করুন এবং প্রতি রেফারে একটি নিশ্চিত বোনাস পান।\n\n"
        f"💸 REFER BOUNS: **{REFER_BONUS:.2f} TK**\n"
        "-----------------------\n"
        "🌐 **REFER LINK** 🌐\n"
        f"🔗 `{referral_link}`\n\n"
        "🚀 উপরে ক্লিক করে লিংকটি কপি করে বন্ধুদের সাথে শেয়ার করুন।"
    )
    await message.reply_text(text)


# --- হ্যান্ডলার: 👤 My Account ---
@app.on_message(filters.regex("👤 My Account"))
async def account_command(client, message):
    if is_user_blocked(message.from_user.id): return

    user_id = message.from_user.id
    cursor.execute("SELECT task_balance, referral_balance, referral_count FROM users WHERE user_id = ?", (user_id,))
    data = cursor.fetchone()
    if data:
        task_balance, referral_balance, ref_count = data
    else:
        # যদি কোনোভাবে ইউজার না পাওয়া যায়
        task_balance, referral_balance, ref_count = 0.00, 0.00, 0
        
    total_balance = task_balance + referral_balance
    
    text = (
        "💼 **আপনার অ্যাকাউন্ট স্ট্যাটাস**\n"
        "-\n"
        f"🏅 Task ব্যালেন্স: **{task_balance:.2f} ৳**\n"
        f"💸 রেফার ব্যালেন্স: **{referral_balance:.2f} ৳**\n"
        f"💰 বর্তমান ব্যালেন্স: **{total_balance:.2f} ৳**\n"
        f"🔗 মোট রেফারেল: **{ref_count} জন**\n\n"
        "✅ কমিশন পেতে আরও বেশি রেফার করুন!\n"
        "✅ নিয়মিত সবগুলো টাস্ক কমপ্লিট করুন!"
    )
    await message.reply_text(text)


# --- হ্যান্ডলার: 💳 Withdraw ---
@app.on_message(filters.regex("💳 Withdraw"))
async def withdraw_command(client, message):
    if is_user_blocked(message.from_user.id): return
    
    # এখানে উইথড্র লজিক যোগ করতে হবে। বর্তমানে শুধু মেসেজ দেখাচ্ছে।
    await message.reply_text(
        f"❌ দুঃখিত! টাকা তোলার জন্য আপনার সর্বনিম্ন **{MIN_WITHDRAW:.2f} টাকা** প্রয়োজন।\n"
        f"উত্তোলন ফি: **{WITHDRAW_FEE_PERCENT:.0f}%**।"
    )


# --- হ্যান্ডলার: 🧾 History ---
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


# --- হ্যান্ডলার: 👑 Status (Admin) ---
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


# --- অ্যাডমিন কমান্ড হ্যান্ডলার: /stats ---
@app.on_message(filters.command("stats"))
async def stats_admin_command(client, message):
    if message.from_user.id != OWNER_ID: return
    
    cursor.execute("SELECT COUNT(user_id), SUM(task_balance + referral_balance) FROM users")
    total_users, total_balance = cursor.fetchone()
    
    text = (
        "👑 **অ্যাডমিন স্ট্যাটাস**\n"
        f"👥 মোট ইউজার: **{total_users} জন**\n"
        f"💰 মোট ব্যালেন্স (ইউজারদের): **{total_balance:.2f} টাকা**"
    )
    await message.reply_text(text)


# --- অ্যাডমিন কমান্ড: /send (নির্দিষ্ট ইউজারকে মেসেজ) ---
@app.on_message(filters.command("send"))
async def send_to_user(client, message):
    if message.from_user.id != OWNER_ID: return
    
    try:
        _, user_id_str, *msg_parts = message.text.split(maxsplit=2)
        user_id = int(user_id_str)
        msg = msg_parts[0]
        await client.send_message(user_id, f"✉️ অ্যাডমিনের মেসেজ:\n\n{msg}")
        await message.reply_text(f"✅ মেসেজটি ইউজার {user_id} কে পাঠানো হয়েছে।")
    except Exception as e:
        await message.reply_text(f"❌ কমান্ড ত্রুটি। ব্যবহার: `/send <user_id> <message>`")


# --- অ্যাডমিন কমান্ড: /broadcast (সবাইকে মেসেজ) ---
@app.on_message(filters.command("broadcast"))
async def broadcast_message(client, message):
    if message.from_user.id != OWNER_ID: return
    
    try:
        msg = message.text.split(maxsplit=1)[1]
        cursor.execute("SELECT user_id FROM users WHERE is_blocked = 0")
        users = cursor.fetchall()
        
        sent_count = 0
        for user in users:
            try:
                await client.send_message(user[0], f"📢 **অ্যাডমিন ব্রডকাস্ট**\n\n{msg}")
                sent_count += 1
            except Exception:
                pass
        
        await message.reply_text(f"✅ ব্রডকাস্ট সফল। মোট {sent_count} জন ইউজারকে পাঠানো হয়েছে।")
    except IndexError:
        await message.reply_text("❌ কমান্ড ত্রুটি। ব্যবহার: `/broadcast <message>`")


# --- অ্যাডমিন কমান্ড: /block ও /unblock ---
@app.on_message(filters.command(["block", "unblock"]))
async def block_unblock_user(client, message):
    if message.from_user.id != OWNER_ID: return
    
    try:
        _, user_id_str = message.text.split(maxsplit=1)
        user_id = int(user_id_str)
        
        status = 1 if message.command[0] == "block" else 0
        status_text = "🚫 ব্লক" if status == 1 else "✅ আনব্লক"
        
        cursor.execute("UPDATE users SET is_blocked = ? WHERE user_id = ?", (status, user_id))
        conn.commit()
        
        await message.reply_text(f"✅ ইউজার {user_id} সফলভাবে {status_text} করা হয়েছে।")
    except Exception:
        await message.reply_text(f"❌ কমান্ড ত্রুটি। ব্যবহার: `/{message.command[0]} <user_id>`")


# --- অ্যাডমিন কমান্ড: /user_list ---
@app.on_message(filters.command("user_list"))
async def user_list_command(client, message):
    if message.from_user.id != OWNER_ID: return
    
    cursor.execute("SELECT user_id, task_balance, referral_balance, referral_count, is_blocked FROM users ORDER BY user_id ASC")
    users = cursor.fetchall()
    
    if not users:
        await message.reply_text("❌ কোনো ইউজার পাওয়া যায়নি।")
        return

    list_text = "👥 **ইউজার তালিকা**\n\n"
    
    for i, user in enumerate(users):
        user_id, task_bal, ref_bal, ref_count, is_blocked = user
        total_balance = task_bal + ref_bal
        status_emoji = "🚫" if is_blocked == 1 else "✅"
        
        try:
            user_info = await client.get_users(user_id)
            user_name = user_info.first_name or "N/A"
        except Exception:
            user_name = "Deleted Account"
            
        new_entry = (
            f"{i+1}. 👤 User name: {user_name}\n"
            f" 🆔 User ID: `{user_id}`\n"
            f" 💰 Balance: {total_balance:.2f} ৳\n"
            f" 🎉 Refer: {ref_count} জন\n"
            f" 🎨 Status: {status_emoji}\n"
            "------------------------\n"
        )
        
        if len(list_text) + len(new_entry) > 3800: # মেসেজের সীমা
            await message.reply_text(list_text)
            list_text = "👥 **ইউজার তালিকা (চলমান)**\n\n"
            
        list_text += new_entry
            
    await message.reply_text(list_text)


# --- অ্যাডমিন কমান্ড: /withdraws (উইথড্র রিকোয়েস্ট দেখানো) ---
@app.on_message(filters.command("withdraws"))
async def admin_withdraw_list(client, message):
    if message.from_user.id != OWNER_ID: return
    
    cursor.execute(
        "SELECT id, user_id, amount, method, account_number, timestamp FROM withdraw_history WHERE status = 'Pending' ORDER BY timestamp ASC"
    )
    requests = cursor.fetchall()
    
    if not requests:
        await message.reply_text("✅ বর্তমানে কোনো Pending উইথড্র রিকোয়েস্ট নেই।")
        return
    
    for req in requests:
        req_id, user_id, amount, method, number, timestamp = req
        
        try:
            user_info = await client.get_users(user_id)
            user_name = user_info.first_name or "N/A"
        except Exception:
            user_name = "Deleted Account"

        text = (
            f"**💰 নতুন উইথড্র রিকোয়েস্ট (ID: {req_id})**\n\n"
            f"📅 {timestamp[:10]} - {timestamp[11:16]}\n"
            f"👤 User name: {user_name}\n"
            f"🆔 User ID: `{user_id}`\n"
            f"💰 Amount: **{amount:.2f} ৳**\n"
            f"🏦 Method: {method}\n"
            f"🔢 Number: {number}\n"
        )
        
        buttons = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("✅ Approve", callback_data=f"w_approve_{req_id}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"w_reject_{req_id}")
                ]
            ]
        )
        await message.reply_text(text, reply_markup=buttons)


# --- ক্যোয়ারি হ্যান্ডলার: উইথড্র Approve/Reject ---
@app.on_callback_query(filters.regex("^w_(approve|reject)_"))
async def withdraw_action_handler(client, callback_query):
    if callback_query.from_user.id != OWNER_ID:
        await callback_query.answer("❌ আপনার এই অ্যাকশন নেওয়ার অনুমতি নেই।")
        return

    action, req_id_str = callback_query.data.split('_', 1)
    req_id = int(req_id_str)
    
    cursor.execute("SELECT status, user_id, amount FROM withdraw_history WHERE id = ?", (req_id,))
    req_data = cursor.fetchone()
    
    if not req_data:
        await callback_query.edit_message_text(f"❌ উইথড্র রিকোয়েস্ট (ID: {req_id}) খুঁজে পাওয়া যায়নি।")
        await callback_query.answer("ত্রুটি: রিকোয়েস্ট নেই।")
        return
        
    current_status, user_id, amount = req_data
    
    if current_status != 'Pending':
        await callback_query.edit_message_text(callback_query.message.text + f"\n\n**⚠️ ইতিমধ্যেই {current_status} করা হয়েছে।**")
        await callback_query.answer("এই রিকোয়েস্টটি ইতিমধ্যেই প্রক্রিয়াজাত করা হয়েছে।")
        return
        
    new_status = "Approved" if action == "approve" else "Rejected"
    
    # 1. Database আপডেট
    cursor.execute("UPDATE withdraw_history SET status = ? WHERE id = ?", (new_status, req_id))
    
    # 2. Reject হলে ব্যালেন্স ফিরিয়ে দেওয়া
    if new_status == "Rejected":
        # Note: এখানে ফি এর কোনো হিসাব নেই কারণ টাকাটি ডেটাবেসে ছিল, শুধু স্ট্যাটাস আপডেট হচ্ছে।
        # যখন উইথড্র রিকোয়েস্ট তৈরি হবে, তখন ফি-এর হিসাব যোগ করা হবে।
        # আপাতত পুরো টাকাটাই ফিরিয়ে দেওয়া হলো।
        cursor.execute("UPDATE users SET task_balance = task_balance + ? WHERE user_id = ?", (amount, user_id)) 
        await client.send_message(user_id, f"❌ দুঃখিত! আপনার **{amount:.2f} টাকা** উত্তোলনের অনুরোধটি বাতিল করা হয়েছে। টাকা আপনার অ্যাকাউন্টে ফেরত দেওয়া হয়েছে।")
    else:
        # Approve হলে টাকা তোলাই ছিল, শুধু স্ট্যাটাস আপডেট হবে।
        await client.send_message(user_id, f"✅ অভিনন্দন! আপনার **{amount:.2f} টাকা** উত্তোলনের অনুরোধটি সফলভাবে অনুমোদিত হয়েছে। আপনি শীঘ্রই আপনার পেমেন্ট পেয়ে যাবেন।")

    conn.commit()

    # 3. মেসেজ আপডেট
    await callback_query.edit_message_text(callback_query.message.text + f"\n\n**✅ স্ট্যাটাস: {new_status} (অ্যাডমিন দ্বারা)**")
    await callback_query.answer(f"রিকোয়েস্ট সফলভাবে {new_status} করা হয়েছে।")


# --- নন-কমান্ড মেসেজ হ্যান্ডলার (এডমিনের কাছে ট্রান্সফার) ---
@app.on_message(filters.text & ~filters.command)
async def forward_to_admin(client, message):
    
    # এটি নিশ্চিত করে যে এটি কোনো মেনু বাটন ক্লিক নয়
    main_menu_texts = ["💰 Daily Bonus", "🔗 Refer & Earn", "💳 Withdraw", "👤 My Account", "🧾 History", "👑 Status (Admin)"]
    if message.text in main_menu_texts:
        # যদি এটি মেনুর মেসেজ হয়, তবে এটি উপেক্ষা করবে, অন্য কোনো হ্যান্ডলার এটি গ্রহণ করবে
        return
        
    user_id = message.from_user.id
    
    # ইউজার ব্লক করা থাকলে কিছু করবে না
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

# --- বট চালানো ---
print("Telegram Earning Bot is starting...")
app.run()
