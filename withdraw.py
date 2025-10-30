from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    ReplyKeyboardMarkup, 
    KeyboardButton
)
import sqlite3
import os

# গ্লোবাল ভেরিয়েবল এবং ফাংশন ইমপোর্ট করার জন্য প্লেসহোল্ডার
MIN_WITHDRAW = 1500.00
WITHDRAW_FEE_PERCENT = 10.0
OWNER_ID = 7702378694

# উইথড্র করার জন্য প্রয়োজনীয় রেফারেল সংখ্যা
REQUIRED_REFERRALS = 20

# ডেটাবেস সংযোগ
conn = sqlite3.connect('user_data.db', check_same_thread=False)
cursor = conn.cursor()

# ইউজার স্টেট ট্র্যাক করার জন্য ডিকশনারি
USER_STATE = {}

# --- ফাংশন: ইউজার ব্যালেন্স এবং রেফারেল সংখ্যা চেক করা ---
def get_user_data(user_id):
    cursor.execute("SELECT task_balance, referral_balance, referral_count FROM users WHERE user_id = ?", (user_id,))
    data = cursor.fetchone()
    if data:
        return data[0] + data[1], data[2] # (মোট ব্যালেন্স, রেফারেল সংখ্যা)
    return 0.00, 0

# --- কীবোর্ড: উইথড্র মেথড বাটন ---
withdraw_method_keyboard = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton("🏦 BKASH", callback_data="w_method_BKASH"),
            InlineKeyboardButton("🏦 NAGAD", callback_data="w_method_NAGAD")
        ]
    ]
)

# --- হ্যান্ডলার: 💳 Withdraw (স্টেপ ১: উইথড্র শুরু করা) ---
def setup_withdraw_handlers(app, USER_STATE_REF):
    global USER_STATE
    USER_STATE = USER_STATE_REF

    @app.on_message(filters.regex("💳 Withdraw"))
    async def withdraw_start(client, message):
        user_id = message.from_user.id
        
        total_balance, referral_count = get_user_data(user_id)
        
        # 1. সর্বনিম্ন লিমিট এবং রেফারেল শর্ত দেখান
        text = (
            "💬 **সঠিকভাবে Withdraw করার জন্য আপনার method + account number ভালোভাবে চেক করে দিন**\n\n"
            f"🏦 MINIMUM WITHDRAW: **{MIN_WITHDRAW:.2f} TK**\n"
            f"🖌️ FEE : **{WITHDRAW_FEE_PERCENT:.0f}%**\n\n"
            f"📜 Tip: উইথড্র করার জন্য **{REQUIRED_REFERRALS} টি রেফার** প্রয়োজন। (বর্তমানে আপনার আছে: **{referral_count} জন**)\n\n"
            "✳️ **আপনি কিসের মাধ্যমে Withdraw করতে চান?** ✳️"
        )
        
        # প্রাথমিক চেক: ব্যালেন্স বা রেফারেল শর্ত পূরণ না হলে শুরু করা হবে না
        if total_balance < MIN_WITHDRAW:
            await message.reply_text(
                f"❌ দুঃখিত! উইথড্র করার জন্য আপনার অ্যাকাউন্টে সর্বনিম্ন **{MIN_WITHDRAW:.2f} টাকা** ব্যালেন্স থাকা দরকার।\n"
                f"বর্তমানে আছে: **{total_balance:.2f} টাকা**"
            )
            return
        
        if referral_count < REQUIRED_REFERRALS:
            await message.reply_text(
                f"❌ দুঃখিত! উইথড্র করার জন্য আপনার অ্যাকাউন্টে **{REQUIRED_REFERRALS} টি রেফার** থাকা দরকার।\n"
                f"বর্তমানে আপনার আছে: **{referral_count} জন**। আরও রেফার করুন।"
            )
            return

        # 2. শর্ত পূরণ হলে, প্রসেস শুরু করা
        USER_STATE[user_id] = {'step': 'started', 'amount': 0, 'method': '', 'number': ''}
        await message.reply_text(text, reply_markup=withdraw_method_keyboard)

    # --- হ্যান্ডলার: ক্যোয়ারি হ্যান্ডলার (স্টেপ ২: মেথড নির্বাচন) ---
    @app.on_callback_query(filters.regex("^w_method_"))
    async def withdraw_method_select(client, callback_query):
        user_id = callback_query.from_user.id
        method = callback_query.data.split('_')[-1]
        
        if USER_STATE.get(user_id) and USER_STATE[user_id]['step'] == 'started':
            USER_STATE[user_id]['method'] = method
            USER_STATE[user_id]['step'] = 'awaiting_number'
            
            # 1. মেসেজ এডিট করা (বাটনগুলো চলে যাবে)
            await callback_query.edit_message_text(
                f"✅ আপনি **{method}** নির্বাচন করেছেন।\n"
                f"🖌️ **আপনার {method} নাম্বারটি লিখুন। 👇**"
            )
            
            await callback_query.answer("নম্বর লিখুন।")
            
        else:
            await callback_query.answer("❌ আপনার উইথড্র প্রসেসটি বাতিল হয়ে গেছে। আবার চেষ্টা করুন।")
            # নিরাপত্তা নিশ্চিত করতে স্টেট ক্লিয়ার
            if user_id in USER_STATE: del USER_STATE[user_id]


    # --- হ্যান্ডলার: উইথড্র নাম্বার এবং অ্যামাউন্ট নেওয়া (স্টেপ ৩ এবং ৪) ---
    @app.on_message(filters.text & filters.private, group=1) # High Priority
    async def withdraw_details_process(client, message):
        user_id = message.from_user.id
        user_input = message.text
        
        if user_id not in USER_STATE:
            return False # অন্য হ্যান্ডলারে ছেড়ে দাও
            
        current_state = USER_STATE[user_id]
        total_balance, referral_count = get_user_data(user_id)


        if current_state['step'] == 'awaiting_number':
            # স্টেপ ৩: নম্বর ইনপুট
            account_number = user_input.strip()
            
            if not account_number.isdigit() or len(account_number) < 11:
                await message.reply_text("❌ দয়া করে একটি বৈধ ১১-সংখ্যার মোবাইল নম্বর দিন।")
                return True
                
            USER_STATE[user_id]['number'] = account_number
            USER_STATE[user_id]['step'] = 'awaiting_amount'
            
            await message.reply_text(
                f"💰 আপনার ব্যালেন্স: **{total_balance:.2f}৳**\n"
                f"✍️ **পরিমাণ লিখুন। 👇**"
            )
            return True
            
        elif current_state['step'] == 'awaiting_amount':
            # স্টেপ ৪: অ্যামাউন্ট ইনপুট ও ফাইনাল সাবমিট
            
            try:
                amount = float(user_input)
            except ValueError:
                await message.reply_text("❌ দয়া করে শুধুমাত্র সঠিক সংখ্যায় টাকার পরিমাণ লিখুন।")
                return True
                
            # 1. ব্যালেন্স কম আছে?
            if amount < MIN_WITHDRAW:
                await message.reply_text(f"⛔ আপনার উত্তোলন করা টাকার পরিমাণ সর্বনিম্ন সীমা **{MIN_WITHDRAW:.2f} টাকা** এর চেয়ে কম।")
                return True
                
            if amount > total_balance:
                await message.reply_text(f"⛔ **আপনার ব্যালেন্স কম আছে।** বর্তমান ব্যালেন্স: **{total_balance:.2f}৳**।")
                return True
            
            # 2. রেফারেল শর্ত পূরণ না হলে?
            if referral_count < REQUIRED_REFERRALS:
                await message.reply_text(f"❌ দুঃখিত! উইথড্র করার জন্য আপনার অ্যাকাউন্টে **{REQUIRED_REFERRALS} টি রেফার** থাকা দরকার।\n"
                                         f"📜 Tip: উইথড্র করার জন্য **{REQUIRED_REFERRALS} টি রেফার** প্রয়োজন।")
                return True

            # --- ট্রানজেকশন প্রসেসিং (শর্ত পূরণ হয়েছে) ---
            fee = (amount * WITHDRAW_FEE_PERCENT) / 100
            net_amount = amount - fee
            method = current_state['method']
            account_number = current_state['number']
            
            # ব্যালেন্স থেকে টাকা কাটা (Task Balance এবং Referral Balance থেকে)
            cursor.execute("SELECT task_balance, referral_balance FROM users WHERE user_id = ?", (user_id,))
            task_bal, ref_bal = cursor.fetchone()
            
            remaining_to_cut = amount
            new_task_bal = task_bal
            new_ref_bal = ref_bal
            
            if task_bal >= remaining_to_cut:
                new_task_bal = task_bal - remaining_to_cut
            else:
                new_task_bal = 0
                remaining_to_cut -= task_bal
                new_ref_bal = ref_bal - remaining_to_cut

            # Database এ আপডেট ও History যোগ
            cursor.execute("UPDATE users SET task_balance = ?, referral_balance = ? WHERE user_id = ?", 
                           (new_task_bal, new_ref_bal, user_id))
            cursor.execute("INSERT INTO withdraw_history (user_id, amount, method, account_number) VALUES (?, ?, ?, ?)",
                           (user_id, net_amount, method, account_number))
            conn.commit()
            
            # ইউজারকে ফাইনাল নোটিফিকেশন
            final_text = (
                f"🔔 **Notifications**\n\n"
                f"🔂 আপনার Withdraw **{net_amount:.2f} ৳** ({method}: {account_number}) পেন্ডিং আছে...\n"
                f"🙏 দয়া করে অপেক্ষা করুন।\n"
                f"🎟️ এডমিন চেক করার পর Approve করবেন\n"
                f"💕 **ধন্যবাদ** 💕"
            )
            await message.reply_text(final_text)
            
            # এডমিনকে নোটিফাই করা
            admin_message = (
                f"🔔 **নতুন উইথড্র রিকোয়েস্ট (Pending)**\n"
                f"👤 ইউজার ID: `{user_id}`\n"
                f"💰 রিকোয়েস্ট করা হয়েছে: **{amount:.2f} ৳** (নেট: {net_amount:.2f} ৳)\n"
                f"🏦 মেথড: {method}\n"
                f"🔢 নম্বর: {account_number}\n"
                f"👉 অ্যাডমিন প্যানেল থেকে `/withdraws` কমান্ড দিয়ে অনুমোদন করুন।"
            )
            await client.send_message(OWNER_ID, admin_message)
            
            # স্টেট ক্লিয়ার করা
            del USER_STATE[user_id]
            return True
            
        return False
