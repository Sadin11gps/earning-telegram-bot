import sqlite3
from pyrogram import Client, filters
from pyrogram.types import ReplyKeyboardMarkup, KeyboardButton

# --- Database সেটআপ (bot.py-এর সাথে সামঞ্জস্যপূর্ণ) ---
conn = sqlite3.connect('user_data.db', check_same_thread=False)
cursor = conn.cursor()

# --- গ্লোবাল স্টেট ---
# USER_STATE কে bot.py থেকে শেয়ার করা হয়
USER_STATE = {} 

# --- ব্যবসায়িক লজিক ভেরিয়েবল (bot.py থেকে ডুপ্লিকেট করা) ---
MIN_WITHDRAW = 1500.00       
REQUIRED_REFERRALS = 20      
WITHDRAW_FEE_PERCENT = 10.0  
OWNER_ID = 7702378694 # Admin ID 


# --- কীবোর্ড সেটআপ ---
withdraw_method_keyboard = ReplyKeyboardMarkup(
    [
        [KeyboardButton("BKASH"), KeyboardButton("NAGAD")],
        [KeyboardButton("CANCEL")]
    ],
    resize_keyboard=True
)

main_menu_keyboard = ReplyKeyboardMarkup(
    [
        [KeyboardButton("💰 Daily Bonus"), KeyboardButton("🔗 Refer & Earn")],
        [KeyboardButton("💳 Withdraw"), KeyboardButton("👤 My Account")],
        [KeyboardButton("🧾 History"), KeyboardButton("👑 Status (Admin)")]
    ],
    resize_keyboard=True
)


# --- হ্যান্ডলার সেটআপ ফাংশন (bot.py এই ফাংশনটি কল করে) ---
def setup_withdraw_handlers(app: Client, shared_user_state):
    global USER_STATE
    USER_STATE = shared_user_state
    
    
    # -----------------------------------------------------
    # হ্যান্ডলার ১: Withdraw কমান্ড শুরু (ইমোজি সহ)
    # -----------------------------------------------------
    # নিশ্চিত করুন: filters.regex("💳 Withdraw") ইমোজি সহ আছে
    @app.on_message(filters.regex("^💳 Withdraw$") & filters.private) 
    async def withdraw_start(client, message):
        user_id = message.from_user.id
        
        # 1. ব্যালেন্স এবং রেফার চেক
        cursor.execute("SELECT task_balance, referral_balance, referral_count FROM users WHERE user_id = ?", (user_id,))
        data = cursor.fetchone()
        
        if data is None:
            await message.reply_text("❌ আপনার অ্যাকাউন্ট পাওয়া যায়নি। /start কমান্ড দিয়ে শুরু করুন।", reply_markup=main_menu_keyboard)
            return

        task_balance, referral_balance, ref_count = data
        total_balance = task_balance + referral_balance
        
        error_message = ""
        if total_balance < MIN_WITHDRAW:
            error_message += f"❌ দুঃখিত! উইথড্র করার জন্য আপনার অ্যাকাউন্টে সর্বনিম্ন **{MIN_WITHDRAW:.2f} টাকা** ব্যালেন্স থাকা দরকার।\n"
        
        if ref_count < REQUIRED_REFERRALS:
            error_message += f"❌ দুঃখিত! উইথড্র করার জন্য আপনার অ্যাকাউন্টে **{REQUIRED_REFERRALS} টি রেফার** থাকা দরকার।\n"
        
        if error_message:
            # শর্ত পূরণ না হলে ভুল মেসেজ দেখিয়ে মূল মেনুতে ফিরিয়ে দিন
            await message.reply_text(error_message, reply_markup=main_menu_keyboard)
            
        else:
            # 2. শর্ত পূরণ হলে উইথড্র প্রসেস শুরু
            # প্রতিটি ইউজারের জন্য একটি স্টেট সেট করা
            USER_STATE[user_id] = 'asking_withdraw_amount'
            await message.reply_text(
                f"✅ আপনি উইথড্র করার যোগ্য!\n"
                f"💸 আপনার বর্তমান ব্যালেন্স: **{total_balance:.2f} টাকা**।\n\n"
                f"⚠️ **উত্তোলন ফি: {WITHDRAW_FEE_PERCENT:.1f}%**\n"
                f"আপনার উইথড্র করার পরিমাণ নিচে লিখুন। (সর্বনিম্ন {MIN_WITHDRAW:.2f} টাকা)",
                reply_markup=ReplyKeyboardMarkup([
                    [KeyboardButton("CANCEL")]
                ], resize_keyboard=True)
            )

    # -----------------------------------------------------
    # হ্যান্ডলার ২: উইথড্র অ্যামাউন্ট ইনপুট
    # -----------------------------------------------------
    @app.on_message(filters.text & filters.private & ~filters.regex("^(BKASH|NAGAD|CANCEL|💰 Daily Bonus|🔗 Refer & Earn|💳 Withdraw|👤 My Account|🧾 History|👑 Status \(Admin\))$"))
    async def process_withdraw_amount(client, message):
        user_id = message.from_user.id
        
        # নিশ্চিত করুন যে ইউজার সঠিক স্টেটে আছে
        if USER_STATE.get(user_id) == 'asking_withdraw_amount':
            try:
                amount = float(message.text)
                
                # ব্যালেন্স পুনরায় চেক
                cursor.execute("SELECT task_balance, referral_balance FROM users WHERE user_id = ?", (user_id,))
                data = cursor.fetchone()
                total_balance = data[0] + data[1]

                if amount < MIN_WITHDRAW:
                    await message.reply_text(f"❌ উইথড্র অ্যামাউন্ট সর্বনিম্ন **{MIN_WITHDRAW:.2f} টাকা** হতে হবে। আবার লিখুন।")
                elif amount > total_balance:
                    await message.reply_text(f"❌ আপনার অ্যাকাউন্টে পর্যাপ্ত ব্যালেন্স নেই। আপনার বর্তমান ব্যালেন্স: **{total_balance:.2f} টাকা**।")
                else:
                    # পরিমাণ বৈধ, মেথড নির্বাচন করতে বলুন
                    USER_STATE[user_id] = 'asking_withdraw_method'
                    USER_STATE[f'{user_id}_withdraw_amount'] = amount 
                    
                    final_amount = amount - (amount * WITHDRAW_FEE_PERCENT / 100)
                    
                    await message.reply_text(
                        f"💰 আপনি **{amount:.2f} টাকা** উইথড্র করতে চেয়েছেন।\n"
                        f"ফি ({WITHDRAW_FEE_PERCENT:.1f}%): **{(amount * WITHDRAW_FEE_PERCENT / 100):.2f} টাকা**।\n"
                        f"✅ আপনি পাবেন: **{final_amount:.2f} টাকা**।\n\n"
                        "আপনি কোন মেথডে টাকা নিতে চান, তা নির্বাচন করুন:",
                        reply_markup=withdraw_method_keyboard
                    )

            except ValueError:
                await message.reply_text("❌ শুধু সংখ্যা লিখুন। সঠিক পরিমাণ আবার লিখুন।")

    # -----------------------------------------------------
    # হ্যান্ডলার ৩: মেথড ইনপুট
    # -----------------------------------------------------
    @app.on_message(filters.regex("^(BKASH|NAGAD)$") & filters.private)
    async def process_withdraw_method(client, message):
        user_id = message.from_user.id
        
        if USER_STATE.get(user_id) == 'asking_withdraw_method':
            method = message.text
            USER_STATE[user_id] = 'asking_account_number'
            USER_STATE[f'{user_id}_withdraw_method'] = method 
            await message.reply_text(
                f"আপনি **{method}** নির্বাচন করেছেন।\n"
                f"দয়া করে আপনার {method} **নাম্বারটি** লিখুন:"
            )

    # -----------------------------------------------------
    # হ্যান্ডলার ৪: অ্যাকাউন্ট নাম্বার ইনপুট
    # -----------------------------------------------------
    # এই হ্যান্ডলারটি সমস্ত নন-কমান্ড টেক্সট ধরবে যখন ইউজার সঠিক স্টেটে থাকবে
    @app.on_message(filters.text & filters.private & ~filters.regex("^(BKASH|NAGAD|CANCEL|💰 Daily Bonus|🔗 Refer & Earn|💳 Withdraw|👤 My Account|🧾 History|👑 Status \(Admin\))$"))
    async def process_account_number(client, message):
        user_id = message.from_user.id
        
        if USER_STATE.get(user_id) == 'asking_account_number':
            account_number = message.text
            
            # ইউজার-নির্দিষ্ট কী থেকে ডেটা পুনরুদ্ধার
            amount = USER_STATE.pop(f'{user_id}_withdraw_amount', 0)
            method = USER_STATE.pop(f'{user_id}_withdraw_method', 'N/A')
            USER_STATE.pop(user_id) # স্টেট রিসেট

            if amount == 0:
                 await message.reply_text("❌ উইথড্র প্রসেসটি পুনরায় শুরু করুন (ডেটা ত্রুটি)।", reply_markup=main_menu_keyboard)
                 return

            final_amount = amount - (amount * WITHDRAW_FEE_PERCENT / 100)
            
            # --- ব্যালেন্স কমানোর লজিক ---
            cursor.execute("SELECT task_balance, referral_balance FROM users WHERE user_id = ?", (user_id,))
            t_bal, r_bal = cursor.fetchone()
            
            remaining_amount = amount
            
            # প্রথমে টাস্ক ব্যালেন্স থেকে কাটুন
            if t_bal >= remaining_amount:
                t_bal -= remaining_amount
                remaining_amount = 0
            else:
                remaining_amount -= t_bal
                t_bal = 0
                r_bal -= remaining_amount # বাকিটা রেফারেল ব্যালেন্স থেকে কাটুন
                
            cursor.execute("UPDATE users SET task_balance = ?, referral_balance = ? WHERE user_id = ?", (t_bal, r_bal, user_id))
            conn.commit()
            
            # 2. History তে যোগ করা
            cursor.execute(
                "INSERT INTO withdraw_history (user_id, amount, method, account_number, status) VALUES (?, ?, ?, ?, ?)",
                (user_id, amount, method, account_number, 'Pending')
            )
            conn.commit()
            
            # 3. ইউজারকে নিশ্চিত করা
            await message.reply_text(
                f"✅ আপনার উইথড্র রিকোয়েস্ট সফলভাবে সাবমিট করা হয়েছে!\n"
                f"💰 উইথড্র অ্যামাউন্ট: {amount:.2f} টাকা\n"
                f"🏦 মেথড: {method}\n"
                f"🔢 অ্যাকাউন্ট: {account_number}\n"
                f"⏱️ আপনার পেমেন্ট শীঘ্রই প্রসেস করা হবে।",
                reply_markup=main_menu_keyboard
            )
            
            # 4. অ্যাডমিনকে জানানো
            await client.send_message(
                OWNER_ID,
                f"🔔 **নতুন উইথড্র রিকোয়েস্ট**\n"
                f"🆔 User ID: `{user_id}`\n"
                f"👤 User: @{message.from_user.username or 'N/A'}\n"
                f"💰 Amount: {amount:.2f} টাকা\n"
                f"💸 Net Receive: {final_amount:.2f} টাকা (ফি {WITHDRAW_FEE_PERCENT:.1f}%)\n"
                f"🏦 Method: {method}\n"
                f"🔢 Account: {account_number}"
            )
            
    # -----------------------------------------------------
    # হ্যান্ডলার ৫: CANCEL কমান্ড
    # -----------------------------------------------------
    @app.on_message(filters.regex("CANCEL") & filters.private)
    async def withdraw_cancel(client, message):
        user_id = message.from_user.id
        
        if user_id in USER_STATE:
            # সমস্ত সংশ্লিষ্ট স্টেট পপ করা
            USER_STATE.pop(user_id, None)
            USER_STATE.pop(f'{user_id}_withdraw_amount', None)
            USER_STATE.pop(f'{user_id}_withdraw_method', None)
            await message.reply_text("❌ উইথড্র প্রসেস বাতিল করা হয়েছে।", reply_markup=main_menu_keyboard)
