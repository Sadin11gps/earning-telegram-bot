import time
import datetime
# <<<<<<< CRITICAL FIX: bot.py থেকে গ্লোবাল সংযোগ ইমপোর্ট করা হলো >>>>>>>
# এই conn এবং cursor অবজেক্টগুলো bot.py-এ PostgreSQL দ্বারা ইনিশিয়ালাইজ করা হয়েছে
# CRITICAL FIX: সার্কুলার ইমপোর্ট এড়ানোর জন্য
from db_utils import conn, cursor
from bot import is_user_blocked 
from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

# **********************************************
# --- টাস্ক কনফিগারেশন ---
# **********************************************
TASK_NAME = "TASK-1" 
TASK_AMOUNT = 10.00          # মেনু অনুযায়ী 10 টাকা
VISIT_LINK = "https://otieu.com/4/100074" # আপনার দেওয়া ডেমো লিংক ব্যবহার করা হলো
VISIT_TIME_SECONDS = 59      # 59 সেকেন্ড অপেক্ষা
TASK_STATE = {}              # টাস্কের অস্থায়ী অবস্থা ট্র্যাকিং

# **********************************************
# --- Core Logic Functions (PostgreSQL Syntax) ---
# **********************************************

# 1. টাস্ক কমপ্লিট হয়েছে কিনা, তা চেক করা
async def check_task_completion(user_id):
    # আজকের তারিখের স্ট্রিং: "YYYY-MM-DD"
    today_date = datetime.datetime.now().strftime("%Y-%m-%d") 
    
    # Task Status টেবিল চেক (PostgreSQL এর জন্য LIKE '%')
    cursor.execute("""
        SELECT * FROM task_status 
        WHERE user_id = %s 
        AND task_name = %s 
        AND completed_at LIKE %s
    """, (user_id, TASK_NAME, f"{today_date}%")) 
    
    return cursor.fetchone() is not None

# 2. ইউজারকে রিওয়ার্ড দেওয়া এবং রেকর্ড করা
async def reward_user_for_task(user_id):
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. users টেবিলে task_balance আপডেট
    cursor.execute("""
        UPDATE users SET task_balance = task_balance + %s 
        WHERE user_id = %s
    """, (TASK_AMOUNT, user_id)) 
    
    # 2. task_status টেবিলে রেকর্ড করা
    cursor.execute("""
        INSERT INTO task_status (user_id, task_name, completed_at) 
        VALUES (%s, %s, %s)
    """, (user_id, TASK_NAME, current_time)) 
    
    conn.commit()


# **********************************************
# --- Handler Setup Function (CRITICAL NAME FIX) ---
# **********************************************
# <<<<<<< CRITICAL FIX: ফাংশনের নাম setup_task_1_handler করা হলো >>>>>>>
def setup_task_1_handler(app: Client): 

    # Handler 4: টাস্ক ইনলাইন বাটন দেখানো (callback: task_1_10)
    @app.on_callback_query(filters.regex(f"task_{TASK_NAME.split('-')[1].lower()}"))
    async def show_task_inline_buttons(client, callback_query):
        user_id = callback_query.from_user.id
        
        if is_user_blocked(user_id): return
        
        if await check_task_completion(user_id):
            await callback_query.answer("⚠️ আপনি আজকের জন্য এই টাস্কটি ইতিমধ্যেই সম্পন্ন করেছেন।", show_alert=True)
            return

        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("🔗 Open Link", url=VISIT_LINK)],
                [InlineKeyboardButton("✅ START TIMER", callback_data=f"start_task_{TASK_NAME.split('-')[1].lower()}")],
            ]
        )
        
        # মেসেজ এডিট করা
        await callback_query.edit_message_text(
            f"🏅 **{TASK_NAME}**\n"
            f"💰 {TASK_AMOUNT:.2f} টাকা\n"
            f"⏱️ {VISIT_TIME_SECONDS} সেকেন্ড লিংক ভিজিট করে অপেক্ষা করুন, তারপর 'Check' বাটনে ক্লিক করুন।\n"
            "----------------------------\n"
            "🌐 লিংক ভিজিট করে প্রবেশ করুন:",
            reply_markup=keyboard
        )
        await callback_query.answer(f"টাস্ক: {TASK_NAME}")

    # Handler 2: START TIMER বাটন কলব্যাক
    @app.on_callback_query(filters.regex(f"start_task_{TASK_NAME.split('-')[1].lower()}"))
    async def start_task_timer(client, callback_query):
        user_id = callback_query.from_user.id
        
        if await check_task_completion(user_id):
            await callback_query.answer("⚠️ আপনি ইতিমধ্যেই এই টাস্কটি সম্পন্ন করেছেন।", show_alert=True)
            return

        # টাইমার শুরু করা
        TASK_STATE[user_id] = time.time()
        
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("🔗 Open Link", url=VISIT_LINK)],
                [InlineKeyboardButton("✅ I Have Visited (Check)", callback_data=f"check_task_{TASK_NAME.split('-')[1].lower()}")],
            ]
        )
        
        # মেসেজ এডিট করা
        await callback_query.edit_message_text(
            f"🏅 **{TASK_NAME}**\n"
            f"💰 {TASK_AMOUNT:.2f} টাকা\n"
            f"✅ **টাইমার শুরু হয়েছে!** অনুগ্রহ করে লিংকে প্রবেশ করে **{VISIT_TIME_SECONDS} সেকেন্ড** অপেক্ষা করুন।\n"
            "----------------------------\n"
            "🌐 লিংক ভিজিট করে প্রবেশ করুন:",
            reply_markup=keyboard
        )
        await callback_query.answer("✅ টাইমার শুরু হয়েছে! এখন লিংকে যান।")
    
    
    # Handler 3: 'I Have Visited (Check)' কলব্যাক
    @app.on_callback_query(filters.regex(f"check_task_{TASK_NAME.split('-')[1].lower()}"))
    async def check_task_completion_handler(client, callback_query):
        user_id = callback_query.from_user.id
        
        if await check_task_completion(user_id):
            await callback_query.answer("⚠️ আপনি আজকের টাস্কটি সম্পন্ন করেছেন।", show_alert=True)
            return

        start_time = TASK_STATE.get(user_id)
        current_time = time.time()
        
        if not start_time:
            await callback_query.answer("❌ প্রথমে 'START TIMER' বাটনে ক্লিক করুন।", show_alert=True)
            return

        elapsed_time = current_time - start_time
        remaining_time = int(VISIT_TIME_SECONDS - elapsed_time)
        
        if elapsed_time < VISIT_TIME_SECONDS:
            await callback_query.answer(f"⏳ অনুগ্রহ করে আরও {remaining_time} সেকেন্ড অপেক্ষা করুন।", show_alert=True)
            return

        # রিওয়ার্ড প্রদান
        await reward_user_for_task(user_id)

        if user_id in TASK_STATE:
            del TASK_STATE[user_id]

        # মেসেজ এডিট করে সফলতার বার্তা দেওয়া
        await callback_query.edit_message_text(
            f"🎉 অভিনন্দন! আপনি **{TASK_NAME}** সফলভাবে সম্পন্ন করেছেন এবং **{TASK_AMOUNT:.2f} টাকা** আপনার Task ব্যালেন্সে যোগ করা হয়েছে।\n\n"
            "আপনি এখন মেনুতে ফিরে যেতে পারেন।"
        )
        await callback_query.answer(f"টাস্ক {TASK_NAME} সম্পন্ন!")

