import sqlite3
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import datetime
import time

# --- Database & Task Status Table Setup ---
# এখানে user_data.db ফাইলটি ব্যবহার করা হয়েছে
conn = sqlite3.connect('user_data.db', check_same_thread=False)
cursor = conn.cursor()

# task_status টেবিল তৈরি: এটি ট্র্যাক করবে কোন ইউজার কোন টাস্ক করেছে এবং কবে করেছে
cursor.execute("""
CREATE TABLE IF NOT EXISTS task_status (
    user_id INTEGER,
    task_name TEXT,
    completed_at TEXT,
    PRIMARY KEY (user_id, task_name)
)
""")
conn.commit()

# --- Task Specific Variables ---
TASK_NAME = "TASK-1"          # মূল টাস্কের নাম
TASK_AMOUNT = 10.00           # এই টাস্কের জন্য ১০ টাকা পুরস্কার
VISIT_LINK = "https://otieu.com/4/10007498" # ইউজারকে ভিজিট করতে হবে
VISIT_TIME_SECONDS = 45       # 45 সেকেন্ড অপেক্ষা

# টাস্কের অস্থায়ী অবস্থা ট্র্যাকিং: {user_id: start_time}
TASK_STATE = {} 

# --- Core Logic Functions ---

async def check_task_completion(user_id: int, task_name: str) -> bool:
    """
    Checks if the user has completed this task TODAY. 
    Resets at 00:00 (midnight) based on the server's local time.
    """
    # বর্তমান তারিখ YYYY-MM-DD ফরম্যাটে নেওয়া
    today_date = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # ডাটাবেসে চেক করা: user_id, task_name এবং completed_at যদি আজকের তারিখ দিয়ে শুরু হয়।
    cursor.execute("""
        SELECT * FROM task_status 
        WHERE user_id = ? AND task_name = ? AND completed_at LIKE ?
    """, (user_id, task_name, f"{today_date}%"))
    
    return cursor.fetchone() is not None

async def reward_user_for_task(user_id: int, task_name: str, amount: float):
    """ইউজারের ব্যালেন্স আপডেট করে এবং টাস্কটিকে সম্পন্ন হিসেবে চিহ্নিত করে।"""
    
    # 1. users টেবিলে ব্যালেন্স আপডেট করা (ধরে নেওয়া হচ্ছে users টেবিল bot.py এ আছে)
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    
    # 2. task_status টেবিলে সম্পন্ন হিসেবে রেকর্ড করা
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO task_status (user_id, task_name, completed_at) VALUES (?, ?, ?)", 
                   (user_id, task_name, current_time))
    
    conn.commit()

# --- Handler Setup Function ---
def setup_task_handlers(app: Client):
    
    # ----------------------------------------------------------------------
    # Handler 1: মূল TASK-1 বাটনে ক্লিক করলে
    # ----------------------------------------------------------------------
    @app.on_message(filters.regex(f"^{TASK_NAME}$", flags=filters.re.IGNORECASE) & filters.private)
    async def task_1_initial(client: Client, message: Message):
        user_id = message.from_user.id
        
        # ১. টাস্ক সম্পন্ন হয়েছে কিনা তা চেক করা (আজকের জন্য)
        if await check_task_completion(user_id, TASK_NAME):
            await message.reply_text(
                f"❌ দুঃখিত! আপনি আজকের **{TASK_NAME}** কাজটি সম্পন্ন করেছেন। আবার কাল ০০:০০ টায় চেষ্টা করুন।"
            )
            return

        # ২. টাস্কের বিবরণ এবং OPEN বাটন পাঠানো
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📂 OPEN 📂", url=VISIT_LINK)],
            [InlineKeyboardButton("✅ I Have Visited (Check)", callback_data="check_task_1")]
        ])
        
        await message.reply_text(
            f"🏅 ওয়েবসাইট ভিজিটিং জব 🏅\n"
            f"💰 {TASK_AMOUNT:.2f} টাকা\n\n"
            f"**📜 নিয়ম:** লিঙ্কে প্রবেশ করুন এবং **{VISIT_TIME_SECONDS} সেকেন্ড** অপেক্ষা করুন। অপেক্ষা শেষ হলে **'I Have Visited (Check)'** বাটনে ক্লিক করুন।\n\n"
            f"নিয়ম ভঙ্গ করলে আপনার উইথড্র রিজেক্ট করা হবে।",
            reply_markup=keyboard
        )

    # ----------------------------------------------------------------------
    # Handler 2: 'I Have Visited (Check)' বাটন কলব্যাক
    # ----------------------------------------------------------------------
    @app.on_callback_query(filters.regex("check_task_1"))
    async def check_task_1_completion(client: Client, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        
        # ১. যদি ইউজার আজ টাস্ক করে থাকে
        if await check_task_completion(user_id, TASK_NAME):
            await callback_query.answer("আপনি ইতিমধ্যেই আজকের এই কাজটি সম্পন্ন করেছেন।", show_alert=True)
            return
            
        # ২. সময় চেক করা (সার্ভার সাইড সিমুলেশন)
        start_time = TASK_STATE.get(user_id)
        current_time = time.time()
        
        # যদি ইউজার একবারও OPEN বাটন ক্লিক না করে
        if not start_time:
             await callback_query.answer("অনুগ্রহ করে আগে 'OPEN' বাটনে ক্লিক করে ওয়েবসাইট ভিজিট করুন।", show_alert=True)
             return
             
        elapsed_time = current_time - start_time
        
        # ৩. সময়কাল যাচাই
        if elapsed_time < VISIT_TIME_SECONDS:
            remaining_time = int(VISIT_TIME_SECONDS - elapsed_time)
            
            await callback_query.answer(
                f"❌ আপনাকে আরও {remaining_time} সেকেন্ড অপেক্ষা করতে হবে।",
                show_alert=True
            )
            return
            
        # ৪. রিওয়ার্ড দেওয়া (যদি সময় ঠিক থাকে)
        await reward_user_for_task(user_id, TASK_NAME, TASK_AMOUNT)
        
        # স্টেট থেকে ইউজারকে মুছে দেওয়া
        if user_id in TASK_STATE:
            del TASK_STATE[user_id]
        
        # সাফল্যের মেসেজ আপডেট করা
        await client.edit_message_text(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.id,
            text=f"🎉 অভিনন্দন! আপনি **{TASK_NAME}** কাজটি সফলভাবে সম্পন্ন করেছেন এবং আপনার একাউন্টে **{TASK_AMOUNT:.2f} টাকা** যোগ করা হয়েছে।\n\n"
                 f"রিওয়ার্ডটি এখন আপনার ব্যালেন্সে যুক্ত হয়েছে।",
            reply_markup=None # কীবোর্ড মুছে ফেলুন
        )

        await callback_query.answer("রিওয়ার্ড সফলভাবে যুক্ত হয়েছে!", show_alert=False)


    # ----------------------------------------------------------------------
    # Handler 3: Visit Link Tracking (OPEN বাটনে ক্লিক করলে)
    # ----------------------------------------------------------------------
    @app.on_inline_keyboard_button(filters.url(VISIT_LINK))
    async def task_1_start_timer(client: Client, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        
        if await check_task_completion(user_id, TASK_NAME):
            await callback_query.answer("আপনি ইতিমধ্যেই আজকের এই কাজটি সম্পন্ন করেছেন।", show_alert=True)
            return

        # ইউজার স্টেট ট্র্যাকিং শুরু
        TASK_STATE[user_id] = time.time()
        
        await callback_query.answer(f"এই লিংক ভিজিট করুন । {VISIT_TIME_SECONDS} সেকেন্ড অপেক্ষা করুন এবং তারপর চেক বাটন টিপুন।", show_alert=False)

    print(f"✅ Handler for {TASK_NAME} (Visit Logic) loaded.")
