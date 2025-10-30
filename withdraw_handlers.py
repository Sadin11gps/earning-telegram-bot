import sqlite3
import datetime
from pyrogram import Client, filters
from pyrogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

# --- Database সেটআপ (bot.py-এর সাথে সামঞ্জস্যপূর্ণ) ---
conn = sqlite3.connect('user_data.db', check_same_thread=False)
cursor = conn.cursor()

# --- ব্যবসায়িক লজিক ভেরিয়েবল ---
MIN_WITHDRAW = 1500.00
REQUIRED_REFERRALS = 20
WITHDRAW_FEE_PERCENT = 10.0
OWNER_ID = 7702378694 # Admin ID (আপনার Telegram ID দিয়ে প্রতিস্থাপন করুন)

# --- কীবোর্ড সেটআপ ---
withdraw_method_keyboard = ReplyKeyboardMarkup(
    [
        [KeyboardButton("BKASH"), KeyboardButton("NAGAD")],
        [KeyboardButton("CANCEL")]
    ],
    resize_keyboard=True
)

# --- Handler Setup Function ---
def setup_withdraw_handlers(app: Client, shared_user_state: dict, group: int):
    
    # --- Handler 1: উইথড্র প্রক্রিয়া শুরু (WITHDRAW_NOW) ---
    @app.on_message(filters.regex("WITHDRAW_NOW", flags=filters.re.IGNORECASE) & filters.private, group=group) 
    async def withdraw_start(client: Client, message: Message):
        user_id = message.from_user.id
        
        # প্রাথমিক চেক (DEBUG এর জন্য)
        await message.reply_text("✅ WITHDRAW HANDLER CALLED. Checking balance...") 
        
        # ১. ব্যালেন্স এবং রেফারের শর্ত যাচাই
        cursor.execute("SELECT balance, (SELECT COUNT(*) FROM users WHERE referrer_id = ?) AS referrals FROM users WHERE user_id = ?", (user_id, user_id))
        result = cursor.fetchone()
        
        if not result:
            await message.reply_text("❌ দুঃখিত! আপনার অ্যাকাউন্টে কোনো ডেটা খুঁজে পাওয়া যায়নি। /start কমান্ড দিন।")
            return
            
        balance, referrals = result
        can_withdraw = True
        response_text = "⚠️ **উইথড্র করার জন্য নিম্নলিখিত শর্তাবলী পূরণ করতে হবে:**\n"
        
        if balance < MIN_WITHDRAW:
            can_withdraw = False
            response_text += f"❌ দুঃখিত! উইথড্র করার জন্য আপনার অ্যাকাউন্টে সর্বনিম্ন **{MIN_WITHDRAW:.2f} টাকা** ব্যালেন্স থাকা দরকার।\n"
            
        if referrals < REQUIRED_REFERRALS:
            can_withdraw = False
            response_text += f"❌ দুঃখিত! উইথড্র করার জন্য আপনার অ্যাকাউন্টে **{REQUIRED_REFERRALS} টি রেফার** থাকা দরকার।\n"

        if not can_withdraw:
            # যদি শর্ত পূরণ না হয়
            await message.reply_text(response_text)
            return
        
        # ২. যদি শর্ত পূরণ হয়, উইথড্র প্রক্রিয়া শুরু
        shared_user_state[user_id] = {'step': 'awaiting_amount', 'balance': balance}
        
        await message.reply_text(
            f"🎉 **শর্ত পূরণ হয়েছে!** আপনার ব্যালেন্স: {balance:.2f} টাকা।\n"
            f"আপনি সর্বনিম্ন {MIN_WITHDRAW:.2f} টাকা উইথড্র করতে পারবেন।\n\n"
            f"💰 অনুগ্রহ করে আপনি কত টাকা উইথড্র করতে চান তা লিখুন:",
            reply_markup=ReplyKeyboardMarkup([
                [KeyboardButton("CANCEL")]
            ], resize_keyboard=True)
        )

    # --- Handler 2: উইথড্র অ্যামাউন্ট প্রক্রিয়া করা ---
    # এই হ্যান্ডলারটি শুধুমাত্র টেক্সট মেসেজ ধরে, যা কোনো বাটন নয়, যখন ইউজার 'awaiting_amount' স্টেজে থাকে
    @app.on_message(filters.text & filters.private & ~filters.regex("^(BKASH|NAGAD|CANCEL|Daily Bonus|Refer & Earn|WITHDRAW_NOW|My Account|History|Status \(Admin\)|TASK-\d+)$", flags=filters.re.IGNORECASE), group=group) 
    async def process_withdraw_amount(client: Client, message: Message):
        user_id = message.from_user.id
        
        if shared_user_state.get(user_id, {}).get('step') != 'awaiting_amount':
            return 
            
        try:
            amount = float(message.text)
        except ValueError:
            await message.reply_text("❌ অনুগ্রহ করে সঠিক সংখ্যায় অ্যামাউন্ট লিখুন।")
            return

        user_balance = shared_user_state[user_id]['balance']
        
        if amount < MIN_WITHDRAW:
            await message.reply_text(f"❌ উইথড্র অ্যামাউন্ট সর্বনিম্ন **{MIN_WITHDRAW:.2f} টাকা** হতে হবে।")
            return
            
        if amount > user_balance:
            await message.reply_text(f"❌ আপনার অ্যাকাউন্টে **{user_balance:.2f} টাকা** আছে। আপনি এর বেশি উইথড্র করতে পারবেন না।")
            return

        # অ্যামাউন্ট বৈধ: ফী গণনা এবং স্টেট আপডেট
        fee = amount * (WITHDRAW_FEE_PERCENT / 100)
        final_amount = amount - fee
        
        shared_user_state[user_id].update({
            'step': 'awaiting_method',
            'amount': amount,
            'fee': fee,
            'final_amount': final_amount
        })

        await message.reply_text(
            f"✅ আপনি উইথড্র করছেন: **{amount:.2f} টাকা**\n"
            f"💸 ফি ({WITHDRAW_FEE_PERCENT:.0f}%): **{fee:.2f} টাকা**\n"
            f"➡️ আপনি পাবেন: **{final_amount:.2f} টাকা**\n\n"
            f"কোন মাধ্যমে উইথড্র করতে চান, তা নির্বাচন করুন:",
            reply_markup=withdraw_method_keyboard
        )

    # --- Handler 3: উইথড্র মেথড প্রক্রিয়া করা ---
    @app.on_message(filters.regex("^(BKASH|NAGAD)$", flags=filters.re.IGNORECASE) & filters.private, group=group)
    async def process_withdraw_method(client: Client, message: Message):
        user_id = message.from_user.id
        
        if shared_user_state.get(user_id, {}).get('step') != 'awaiting_method':
            return
            
        method = message.text.upper()
        
        shared_user_state[user_id]['step'] = 'awaiting_account'
        shared_user_state[user_id]['method'] = method

        await message.reply_text(
            f"✅ আপনি **{method}** নির্বাচন করেছেন।\n\n"
            f"📞 অনুগ্রহ করে আপনার **{method} অ্যাকাউন্ট নাম্বারটি** লিখুন:",
            reply_markup=ReplyKeyboardMarkup([
                [KeyboardButton("CANCEL")]
            ], resize_keyboard=True)
        )


    # --- Handler 4: অ্যাকাউন্ট নাম্বার প্রক্রিয়া করা এবং নিশ্চিতকরণ ---
    # এই হ্যান্ডলারটিও শুধুমাত্র টেক্সট মেসেজ ধরে যখন ইউজার 'awaiting_account' স্টেজে থাকে
    @app.on_message(filters.text & filters.private & ~filters.regex("^(BKASH|NAGAD|CANCEL|Daily Bonus|Refer & Earn|WITHDRAW_NOW|My Account|History|Status \(Admin\)|TASK-\d+)$", flags=filters.re.IGNORECASE), group=group) 
    async def process_account_number(client: Client, message: Message):
        user_id = message.from_user.id
        
        if shared_user_state.get(user_id, {}).get('step') != 'awaiting_account':
            return
            
        account_number = message.text.strip()
        
        if not account_number.isdigit() or len(account_number) < 10 or len(account_number) > 15: # প্রাথমিক চেক
            await message.reply_text("❌ অনুগ্রহ করে একটি বৈধ অ্যাকাউন্ট নাম্বার দিন (সাধারণত ১০-১৫ সংখ্যা)।")
            return
            
        state = shared_user_state[user_id]
        
        # চূড়ান্ত সাবমিশন: ডাটাবেসে উইথড্র রিকোয়েস্ট সেভ করা
        try:
            # ব্যালেন্স থেকে অ্যামাউন্ট বিয়োগ করা
            cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (state['amount'], user_id))
            
            # উইথড্র রিকোয়েস্ট withdrawals টেবিলে সেভ করা
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                INSERT INTO withdrawals (user_id, amount, method, account_number, timestamp) 
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, state['amount'], state['method'], account_number, current_time))
            
            conn.commit()
            
            # অ্যাডমিনকে নোটিফিকেশন পাঠানো
            admin_message = (
                f"🚨 **NEW WITHDRAW REQUEST!** 🚨\n"
                f"👤 User ID: `{user_id}`\n"
                f"🏷️ Username: @{message.from_user.username or 'N/A'}\n"
                f"💸 Amount: {state['amount']:.2f} টাকা\n"
                f"➖ Fee: {state['fee']:.2f} টাকা\n"
                f"💰 Payout: {state['final_amount']:.2f} টাকা\n"
                f"🏦 Method: {state['method']}\n"
                f"🔢 Account: `{account_number}`"
            )
            await client.send_message(OWNER_ID, admin_message)

            # ইউজারকে চূড়ান্ত নিশ্চিতকরণ মেসেজ পাঠানো
            cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
            new_balance = cursor.fetchone()[0]
            await message.reply_text(
                f"✅ **আপনার উইথড্র রিকোয়েস্ট সফলভাবে সাবমিট হয়েছে!**\n\n"
                f"আমরা আপনার রিকোয়েস্টটি যাচাই করছি। পেমেন্ট সম্পন্ন হলে আপনাকে জানানো হবে।\n"
                f"আপনার বর্তমান ব্যালেন্স: **{new_balance:.2f} টাকা**।"
            )
            
        except Exception as e:
            await message.reply_text(f"❌ উইথড্র সাবমিট করার সময় একটি ত্রুটি হয়েছে: {e}")
            
        finally:
            # স্টেট রিসেট করা
            if user_id in shared_user_state:
                del shared_user_state[user_id]

    # --- Handler 5: উইথড্র বাতিল (CANCEL) ---
    @app.on_message(filters.regex("CANCEL") & filters.private, group=group)
    async def withdraw_cancel(client: Client, message: Message):
        user_id = message.from_user.id
        
        if user_id in shared_user_state:
            del shared_user_state[user_id]
            await message.reply_text("❌ উইথড্র প্রক্রিয়া বাতিল করা হয়েছে।")
        else:
            await message.reply_text("মেনুতে ফিরে যেতে যেকোনো বাটন ব্যবহার করুন।")
