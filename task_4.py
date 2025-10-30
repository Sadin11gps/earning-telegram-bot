import sqlite3
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import datetime
import time

# --- Database & Task Status Table Setup ---
conn = sqlite3.connect('user_data.db', check_same_thread=False)
cursor = conn.cursor()

# task_status টেবিল তৈরি: এটি ট্র্যাক করবে কোন ইউজার কোন টাস্ক করেছে এবং কবে করেছে
cursor.execute("""
CREATE TABLE IF NOT EXISTS task_status (
    user_id INTEGER,
    task_name TEXT,
    completed_at TEXT,
    PRIMARY KEY (user_id, task_name, completed_at) 
)
""")
conn.commit()

# =========================================================
# 🔴 আপনার পরিবর্তন করার জায়গা: প্রতিটি ফাইলে শুধু এই ৩টি ভেরিয়েবল পরিবর্তন করুন
# =========================================================
# NOTE: এই TASK_NAME আপনার বাটনের টেক্সটের (যেমন: TASK-1_10 TK) প্রথম অংশের সাথে মিলতে হবে। 
# task_1.py তে TASK-1, task_2.py তে TASK-2, ইত্যাদি হবে।
TASK_NAME = "TASK-4"          
TASK_AMOUNT = 10.00           
VISIT_LINK = "https://example.com/taskX" 
VISIT_TIME_SECONDS = 45       
# =========================================================

# টাস্কের অস্থায়ী অবস্থা ট্র্যাকিং: {user_id: start_time}
TASK_STATE = {} 

# --- Core Logic Functions ---

async def check_task_completion(user_id: int, task_name: str) -> bool:
    """
    Checks if the user has completed this task TODAY (resets at 00:00).
    """
    today_date = datetime.datetime.now().strftime("%Y-%m-%d")
    
    cursor.execute("""
        SELECT * FROM task_status 
        WHERE user_id = ? AND task_name = ? AND completed_at LIKE ?
    """, (user_id, task_name, f"{today_date}%"))
    
    return cursor.fetchone() is not None

async def reward_user_for_task(user_id: int, task_name: str, amount: float):
    """Updates user balance and records completion."""
    
    # 1. users টেবিলে task_balance আপডেট করা
    cursor.execute("UPDATE users SET task_balance = task_balance + ? WHERE user_id = ?", (amount, user_id))
    
    # 2. task_status টেবিলে সম্পন্ন হিসেবে রেকর্ড করা
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO task_status (user_id, task_name, completed_at) VALUES (?, ?, ?)", 
                   (user_id, task_name, current_time))
    
    conn.commit()

# --- Handler Setup Function (CRITICAL FIX: Uses @app.on_callback_query) ---
def setup_task_handlers(app: Client):
    
    # Handler 1: START TIMER বাটন কলব্যাক
    # filters.regex: start_task_x
    @app.on_callback_query(filters.regex(f"^start_{TASK_NAME.lower().replace('-', '_')}$")) 
    async def start_task_timer(client: Client, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        
        if await check_task_completion(user_id, TASK_NAME):
            await callback_query.answer("আপনি ইতিমধ্যেই আজকের এই কাজটি সম্পন্ন করেছেন।", show_alert=True)
            return

        # টাইমার শুরু করা
        TASK_STATE[user_id] = time.time()
        
        await callback_query.answer(f"⏱ টাইমার শুরু হয়েছে! {VISIT_TIME_SECONDS} সেকেন্ড অপেক্ষা করুন।", show_alert=True)
        
    # Handler 2: 'I Have Visited (Check)' বাটন কলব্যাক
    # filters.regex: check_task_x
    @app.on_callback_query(filters.regex(f"^check_{TASK_NAME.lower().replace('-', '_')}$")) 
    async def check_task_completion_handler(client: Client, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        
        if await check_task_completion(user_id, TASK_NAME):
            await callback_query.answer("আপনি ইতিমধ্যেই আজকের এই কাজটি সম্পন্ন করেছেন।", show_alert=True)
            return
            
        start_time = TASK_STATE.get(user_id)
        current_time = time.time()
        
        if not start_time:
             await callback_query.answer("❌ অনুগ্রহ করে আগে 'START TIMER' বাটনে ক্লিক করে টাইমার শুরু করুন।", show_alert=True)
             return
             
        elapsed_time = current_time - start_time
        
        if elapsed_time < VISIT_TIME_SECONDS:
            remaining_time = int(VISIT_TIME_SECONDS - elapsed_time)
            await callback_query.answer(f"❌ আপনাকে আরও {remaining_time} সেকেন্ড অপেক্ষা করতে হবে।", show_alert=True)
            return
            
        # রিওয়ার্ড প্রদান
        await reward_user_for_task(user_id, TASK_NAME, TASK_AMOUNT)
        
        if user_id in TASK_STATE:
            del TASK_STATE[user_id]
        
        # সফলতার মেসেজ
        await client.send_message(
            chat_id=callback_query.message.chat.id,
            text=f"🎉 অভিনন্দন! আপনি **{TASK_NAME}** কাজটি সফলভাবে সম্পন্ন করেছেন এবং আপনার একাউন্টে **{TASK_AMOUNT:.2f} টাকা** যোগ করা হয়েছে।"
        )
        await callback_query.answer("রিওয়ার্ড সফলভাবে যুক্ত হয়েছে!", show_alert=False)

    # Handler 3: টাস্ক ইনলাইন বাটন দেখানোর লজিক
    # filters.regex: task_x_
    @app.on_callback_query(filters.regex(f"^{TASK_NAME.lower().replace('-', '_')}_"))
    async def show_task_inline_buttons(client: Client, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        
        if await check_task_completion(user_id, TASK_NAME):
            await callback_query.answer("আপনি আজকের কাজটি সম্পন্ন করেছেন।", show_alert=True)
            return
            
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📂 OPEN 📂", url=VISIT_LINK)],
            [InlineKeyboardButton("⏱ START TIMER", callback_data=f"start_{TASK_NAME.lower().replace('-', '_')}")],
            [InlineKeyboardButton("✅ I Have Visited (Check)", callback_data=f"check_{TASK_NAME.lower().replace('-', '_')}")] 
        ])

        await callback_query.edit_message_text(
            f"🏅 **{TASK_NAME} - ওয়েবসাইট ভিজিটিং জব** 🏅\n"
            f"💰 {TASK_AMOUNT:.2f} টাকা\n\n"
            f"**📜 নিয়ম:** লিঙ্কে প্রবেশ করুন, **'START TIMER'** ক্লিক করুন, **{VISIT_TIME_SECONDS} সেকেন্ড** অপেক্ষা করুন এবং **'Check'** টিপুন।",
            reply_markup=keyboard
        )
        await callback_query.answer("টাস্ক শুরু করুন।")
    
    print(f"✅ Handler for {TASK_NAME} loaded.")
