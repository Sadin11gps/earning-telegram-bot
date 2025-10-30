import sqlite3
from pyrogram import Client, filters
from pyrogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
import re # রেগুলার এক্সপ্রেশন ব্যবহার করা হবে পরিমাণের ভ্যালিডেশনের জন্য

# --- Database & Global Setup ---
# bot.py থেকে কানেকশন নেওয়া হচ্ছে
conn = sqlite3.connect('user_data.db', check_same_thread=False)
cursor = conn.cursor()

# NOTE: USER_STATE, REFER_BONUS, MIN_WITHDRAW, REQUIRED_REFERRALS
# ভেরিয়েবলগুলো bot.py থেকে আসে। setup_withdraw_handlers ফাংশনে USER_STATE পাস করা হয়।

# উইথড্র মেনুর কীবোর্ড
WITHDRAW_MENU_KEYBOARD = ReplyKeyboardMarkup(
    [
        [KeyboardButton("BKASH"), KeyboardButton("NAGAD")],
        [KeyboardButton("CANCEL")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

# মূল মেনুর কীবোর্ড (ফেরত যাওয়ার জন্য)
MAIN_MENU_KEYBOARD_LITE = ReplyKeyboardMarkup(
    [
        [KeyboardButton("💰 Daily Bonus"), KeyboardButton("🔗 Refer & Earn")],
        [KeyboardButton("Withdraw"), KeyboardButton("👤 My Account")],
        [KeyboardButton("🧾 History"), KeyboardButton("👑 Status (Admin)")]
    ],
    resize_keyboard=True
)


def get_user_data(user_id):
    """Fetches user balance and referral count."""
    cursor.execute("SELECT task_balance, referral_balance, referral_count FROM users WHERE user_id = ?", (user_id,))
    data = cursor.fetchone()
    if data:
        task_balance, referral_balance, ref_count = data
        total_balance = task_balance + referral_balance
        return total_balance, ref_count
    return 0.00, 0

def update_user_balance_after_withdraw(user_id, amount):
    """Deducts the withdrawn amount from user's balances (pro-rata deduction)."""
    total_balance, _ = get_user_data(user_id)
    if amount > total_balance:
        return False # Should not happen if checked correctly before
        
    cursor.execute("SELECT task_balance, referral_balance FROM users WHERE user_id = ?", (user_id,))
    t_bal, r_bal = cursor.fetchone()

    # Calculate proportional deduction (সরলীকরণ)
    
    # প্রথমে রেফারেল ব্যালেন্স থেকে কাটুন
    deduct_from_referral = min(amount, r_bal)
    remaining_amount_to_deduct = amount - deduct_from_referral
    
    # বাকিটা টাস্ক ব্যালেন্স থেকে কাটুন
    deduct_from_task = min(remaining_amount_to_deduct, t_bal)

    new_r_bal = r_bal - deduct_from_referral
    new_t_bal = t_bal - deduct_from_task

    cursor.execute("UPDATE users SET task_balance = ?, referral_balance = ? WHERE user_id = ?", (new_t_bal, new_r_bal, user_id))
    conn.commit()
    return True


# --- Handler Setup Function ---
def setup_withdraw_handlers(app: Client, user_state_dict: dict, group=0):
    """Initializes all withdraw handlers and uses the shared USER_STATE dictionary."""
    
    # bot.py থেকে global variables লোড করা (সেরা অনুশীলনের জন্য)
    # যেহেতু এগুলো bot.py-এ গ্লোবালি আছে, আমরা ধরে নিচ্ছি এখানে অ্যাক্সেসযোগ্য।
    global USER_STATE # যদিও এটি ফাংশন প্যারামিটার হিসেবে আছে, ডিক্ট পরিবর্তন করার জন্য গ্লোবাল দরকার নেই।
    
    # গ্লোবাল ভ্যালুগুলো bot.py থেকে নিতে হবে (এই মডিউলে সরাসরি অ্যাক্সেস না পেলে NameError হবে)
    # এখানে আমরা এই মডিউলের নিজস্ব MIN_WITHDRAW, REQUIRED_REFERRALS ব্যবহার না করে bot.py এরটা ব্যবহার করব।
    # সাময়িকভাবে, bot.py থেকে MIN_WITHDRAW এবং REQUIRED_REFERRALS ভ্যালুগুলো
    # এই মডিউলে ডিক্লেয়ার করার প্রয়োজন হতে পারে যদি সেগুলো এখানে না পাওয়া যায়।
    # ধরে নিচ্ছি bot.py-এর কোডগুলো গ্লোবাল স্কোপে আছে।
    # নিরাপত্তা ও কার্যকারিতার জন্য, আমরা এখানে bot.py এর ভ্যালুগুলোকে hardcode করলাম।
    MIN_WITHDRAW = 1500.00
    REQUIRED_REFERRALS = 20
    OWNER_ID = 7702378694 # Admin ID
    WITHDRAW_FEE_PERCENT = 10.0
    
    
    # ----------------------------------------------------------------------
    # Handler 1: 'Withdraw' বাটন ক্লিক (ফ্লো শুরু)
    # ----------------------------------------------------------------------
    @app.on_message(filters.regex("^Withdraw$") & filters.private, group=group)
    async def start_withdraw_flow(client, message):
        user_id = message.from_user.id
        total_balance, ref_count = get_user_data(user_id)
        
        # 1. যোগ্যতা যাচাই
        if total_balance < MIN_WITHDRAW:
            await message.reply_text(f"❌ উইথড্র করতে আপনার ন্যূনতম **{MIN_WITHDRAW:.2f} ৳** প্রয়োজন। আপনার আছে: **{total_balance:.2f} ৳**")
            return

        if ref_count < REQUIRED_REFERRALS:
            await message.reply_text(f"❌ উইথড্র করতে আপনার ন্যূনতম **{REQUIRED_REFERRALS} জন রেফারেল** প্রয়োজন। আপনার আছে: **{ref_count} জন**")
            return
            
        # 2. ফ্লো শুরু করা
        user_state_dict[user_id] = {'step': 'SELECT_METHOD', 'amount': None, 'method': None, 'number': None}
        
        await message.reply_text(
            "✅ অনুগ্রহ করে আপনার পেমেন্ট মেথডটি নির্বাচন করুন অথবা বাতিল করতে **'CANCEL'** টিপুন:",
            reply_markup=WITHDRAW_MENU_KEYBOARD
        )

    # ----------------------------------------------------------------------
    # Handler 2: 'CANCEL' বাটন ক্লিক (ফ্লো বাতিল)
    # ----------------------------------------------------------------------
    @app.on_message(filters.regex("^CANCEL$") & filters.private, group=group)
    async def cancel_withdraw_flow(client, message):
        user_id = message.from_user.id
        if user_id in user_state_dict:
            del user_state_dict[user_id]
            
        await message.reply_text(
            "✅ উইথড্র রিকোয়েস্ট বাতিল করা হয়েছে।",
            reply_markup=MAIN_MENU_KEYBOARD_LITE 
        )

    # ----------------------------------------------------------------------
    # Handler 3: BKASH/NAGAD মেথড নির্বাচন
    # ----------------------------------------------------------------------
    @app.on_message(filters.regex("^(BKASH|NAGAD)$") & filters.private, group=group)
    async def select_method(client, message):
        user_id = message.from_user.id
        method = message.text.upper()
        
        if user_id in user_state_dict and user_state_dict[user_id]['step'] == 'SELECT_METHOD':
            user_state_dict[user_id]['method'] = method
            user_state_dict[user_id]['step'] = 'ENTER_NUMBER'
            
            await message.reply_text(
                f"🏦 আপনি **{method}** নির্বাচন করেছেন।\n"
                f"➡️ এবার অনুগ্রহ করে আপনার **{method} অ্যাকাউন্ট নম্বরটি** (যেখানে টাকা নিতে চান) দিন:",
                reply_markup=ReplyKeyboardMarkup([[KeyboardButton("CANCEL")]], resize_keyboard=True, one_time_keyboard=True)
            )
        else:
            # যদি ভুল স্টেটে থাকে, ফ্লো শুরু করতে বলে
            await message.reply_text("❌ অনুগ্রহ করে প্রথমে 'Withdraw' বাটনে ক্লিক করে ফ্লো শুরু করুন।", reply_markup=MAIN_MENU_KEYBOARD_LITE)


    # ----------------------------------------------------------------------
    # Handler 4: অ্যাকাউন্ট নম্বর গ্রহণ ও পরিমাণের জন্য জিজ্ঞাসা
    # ----------------------------------------------------------------------
    @app.on_message(filters.private & filters.text & ~filters.regex("^(BKASH|NAGAD|Withdraw|CANCEL)$"), group=group)
    async def handle_withdraw_input(client, message):
        user_id = message.from_user.id
        
        if user_id not in user_state_dict:
            # যদি ইউজার স্টেট না থাকে, মেসেজটি bot.py-এর ফরওয়ার্ড হ্যান্ডলার ধরবে
            return 
            
        current_state = user_state_dict[user_id]
        
        if current_state['step'] == 'ENTER_NUMBER':
            # স্টেপ 2: অ্যাকাউন্ট নম্বর গ্রহণ
            account_number = message.text.strip()
            if not re.match(r'^\d{11,}$', account_number):
                await message.reply_text("❌ অনুগ্রহ করে একটি সঠিক অ্যাকাউন্ট নম্বর দিন (কমপক্ষে ১১ ডিজিট):")
                return

            current_state['number'] = account_number
            current_state['step'] = 'ENTER_AMOUNT'
            
            total_balance, _ = get_user_data(user_id)
            
            await message.reply_text(
                f"💰 আপনার বর্তমান ব্যালেন্স: **{total_balance:.2f} ৳**\n"
                f"➡️ এবার আপনি কত টাকা উইথড্র করতে চান, সেই **পরিমাণটি** লিখুন (ন্যূনতম {MIN_WITHDRAW:.2f} ৳):"
            )
            
        elif current_state['step'] == 'ENTER_AMOUNT':
            # স্টেপ 3: পরিমাণের গ্রহণ ও চূড়ান্ত সাবমিশন
            try:
                amount_requested = float(message.text.strip())
            except ValueError:
                await message.reply_text("❌ অনুগ্রহ করে পরিমাণের জন্য শুধুমাত্র সঠিক সংখ্যা লিখুন:")
                return
            
            total_balance, ref_count = get_user_data(user_id)
            
            # চূড়ান্ত ভ্যালিডেশন
            if amount_requested < MIN_WITHDRAW:
                await message.reply_text(f"❌ উইথড্র অ্যামাউন্ট **{MIN_WITHDRAW:.2f} ৳** এর কম হতে পারবে না। সঠিক সংখ্যা লিখুন:")
                return

            if amount_requested > total_balance:
                await message.reply_text(f"❌ আপনার অ্যাকাউন্টে পর্যাপ্ত ব্যালেন্স নেই ({total_balance:.2f} ৳)। সঠিক সংখ্যা লিখুন:")
                return
            
            # উইথড্র ফী ও নেট অ্যামাউন্ট গণনা
            fee_amount = (amount_requested * WITHDRAW_FEE_PERCENT) / 100
            net_amount = amount_requested - fee_amount
            
            # ডেটাবেসে আপডেট
            if not update_user_balance_after_withdraw(user_id, amount_requested):
                 # এটা সাধারণত হওয়া উচিত না
                 await message.reply_text("❌ ব্যালেন্স আপডেটে সমস্যা হয়েছে। আবার চেষ্টা করুন বা এডমিনকে জানান।")
                 del user_state_dict[user_id]
                 return
                 
            # উইথড্র হিস্টরি টেবলে রেকর্ড করা
            cursor.execute("""
                INSERT INTO withdraw_history (user_id, amount, method, account_number, status) 
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, amount_requested, current_state['method'], current_state['number'], 'Pending'))
            conn.commit()

            # অ্যাডমিনের কাছে নোটিফিকেশন পাঠানো
            admin_notification = (
                f"🚨 **নতুন উইথড্র রিকোয়েস্ট** 🚨\n"
                f"👤 ইউজার ID: `{user_id}`\n"
                f"💸 রিকোয়েস্ট: **{amount_requested:.2f} ৳**\n"
                f"📉 ফী ({WITHDRAW_FEE_PERCENT}%): **{fee_amount:.2f} ৳**\n"
                f"✅ নেট পেমেন্ট: **{net_amount:.2f} ৳**\n"
                f"🏦 মেথড: **{current_state['method']}**\n"
                f"🔢 অ্যাকাউন্ট: `{current_state['number']}`\n"
            )
            await client.send_message(OWNER_ID, admin_notification)
            
            # ইউজারকে চূড়ান্ত মেসেজ
            await message.reply_text(
                f"✅ আপনার উইথড্র রিকোয়েস্ট সফলভাবে সাবমিট করা হয়েছে!\n"
                f"💰 অনুরোধকৃত: **{amount_requested:.2f} ৳**\n"
                f"💸 ফী: **{fee_amount:.2f} ৳**\n"
                f"🚀 আপনি পাবেন: **{net_amount:.2f} ৳**\n"
                f"⏳ আপনার রিকোয়েস্টটি প্রক্রিয়াধীন রয়েছে।",
                reply_markup=MAIN_MENU_KEYBOARD_LITE
            )
            
            # স্টেট পরিষ্কার করা
            del user_state_dict[user_id]
            
        else:
            # কোনো অজানা স্টেটে থাকলে, তাকে মূল মেনুতে পাঠানো
            await message.reply_text("❌ উইথড্র ফ্লোটি সঠিকভাবে শুরু হয়নি। দয়া করে আবার চেষ্টা করুন।", reply_markup=MAIN_MENU_KEYBOARD_LITE)


# ----------------------------------------------------------------------
# NOTE: এই ফাইলটি bot.py-এ এই ফাংশন দিয়ে লোড করা হয়:
# withdraw_mod.setup_withdraw_handlers(app, USER_STATE, group=-1) 
# ----------------------------------------------------------------------
