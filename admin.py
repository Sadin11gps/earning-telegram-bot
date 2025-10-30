from pyrogram import Client, filters
import sqlite3

# গ্লোবাল ভেরিয়েবল সেটআপ
conn = sqlite3.connect('user_data.db', check_same_thread=False)
cursor = conn.cursor()
OWNER_ID = 7702378694 # আপনার অ্যাডমিন আইডি

# --- ফাংশন: ইউজার ব্লক করা আছে কিনা চেক করা ---
def is_user_blocked(user_id):
    cursor.execute("SELECT is_blocked FROM users WHERE user_id = ?", (user_id,))
    data = cursor.fetchone()
    if data and data[0] == 1:
        return True
    return False

# --- অ্যাডমিন হ্যান্ডলার সেটআপ ফাংশন ---
def setup_admin_handlers(app: Client):
    
    # -----------------------------
    # /block <user_id>
    # -----------------------------
    @app.on_message(filters.command("block") & filters.private)
    async def block_user_command(client, message):
        if message.from_user.id != OWNER_ID: return

        try:
            user_id_to_block = int(message.command[1])
            cursor.execute("UPDATE users SET is_blocked = 1 WHERE user_id = ?", (user_id_to_block,))
            conn.commit()
            
            await client.send_message(user_id_to_block, "❌ দুঃখিত! অ্যাডমিন আপনাকে বটটি ব্যবহার থেকে ব্লক করেছেন।")
            await message.reply_text(f"✅ ইউজার `{user_id_to_block}` কে সফলভাবে ব্লক করা হয়েছে।")
        except:
            await message.reply_text("❌ ব্যবহার: `/block <user_id>`")

    # -----------------------------
    # /unblock <user_id>
    # -----------------------------
    @app.on_message(filters.command("unblock") & filters.private)
    async def unblock_user_command(client, message):
        if message.from_user.id != OWNER_ID: return

        try:
            user_id_to_unblock = int(message.command[1])
            cursor.execute("UPDATE users SET is_blocked = 0 WHERE user_id = ?", (user_id_to_unblock,))
            conn.commit()
            
            await client.send_message(user_id_to_unblock, "✅ অভিনন্দন! অ্যাডমিন আপনাকে আনব্লক করেছেন।")
            await message.reply_text(f"✅ ইউজার `{user_id_to_unblock}` কে সফলভাবে আনব্লক করা হয়েছে।")
        except:
            await message.reply_text("❌ ব্যবহার: `/unblock <user_id>`")

    # -----------------------------
    # /withdraws (উইথড্র হিস্টরি দেখানো)
    # -----------------------------
    @app.on_message(filters.command("withdraws") & filters.private)
    async def list_pending_withdraws(client, message):
        if message.from_user.id != OWNER_ID: return

        cursor.execute(
            "SELECT id, user_id, amount, method, account_number, timestamp FROM withdraw_history WHERE status = 'Pending' ORDER BY timestamp ASC"
        )
        pending_withdraws = cursor.fetchall()
        
        if not pending_withdraws:
            await message.reply_text("🎉 কোনো পেন্ডিং উইথড্র রিকোয়েস্ট নেই।")
            return

        response = "⏳ **পেন্ডিং উইথড্র রিকোয়েস্ট**\n\n"
        for item in pending_withdraws:
            (w_id, user_id, amount, method, number, timestamp) = item
            
            # Approve/Reject বাটন তৈরি
            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("✅ Approve", callback_data=f"w_approve_{w_id}"),
                        InlineKeyboardButton("❌ Reject", callback_data=f"w_reject_{w_id}")
                    ]
                ]
            )
            
            response += (
                f"**ID: {w_id}** (ইউজার: `{user_id}`)\n"
                f"💰 পরিমাণ: {amount:.2f} ৳ (নেট)\n"
                f"🏦 মেথড: {method} - `{number}`\n"
                f"📅 রিকোয়েস্ট: {timestamp[:16]}\n"
            )
            
            await message.reply_text(response, reply_markup=keyboard)
            response = "--------------------------------------\n" # পরবর্তী রিকোয়েস্টের জন্য পরিষ্কার করা

    # -----------------------------
    # কলব্যাক হ্যান্ডলার (Approve/Reject)
    # -----------------------------
    @app.on_callback_query(filters.regex("^(w_approve_|w_reject_)"))
    async def handle_withdraw_action(client, callback_query):
        if callback_query.from_user.id != OWNER_ID: 
            await callback_query.answer("❌ আপনি অ্যাডমিন নন।")
            return
            
        action, w_id_str = callback_query.data.split('_', 1)
        w_id = int(w_id_str)
        status = "Approved" if action == "w_approve" else "Rejected"
        
        cursor.execute("SELECT user_id, amount, status FROM withdraw_history WHERE id = ?", (w_id,))
        withdraw_data = cursor.fetchone()
        
        if not withdraw_data:
            await callback_query.edit_message_text("❌ এই রিকোয়েস্টটি পাওয়া যায়নি।")
            return

        user_id, net_amount, current_status = withdraw_data
        
        if current_status != 'Pending':
            await callback_query.edit_message_text(f"❌ এই রিকোয়েস্টটি ইতিমধ্যেই {current_status} করা হয়েছে।")
            return

        cursor.execute("UPDATE withdraw_history SET status = ? WHERE id = ?", (status, w_id))
        
        # রিজেক্ট হলে টাকা ফেরত
        if status == "Rejected":
            # টাকা ফেরত দেওয়ার লজিক (সাধারণত Referral Balance এ যোগ করা হয়)
            # আমরা এখানে নেট উইথড্র অ্যামাউন্টটি টাস্ক ব্যালেন্সে ফেরত দিচ্ছি (যাতে রেফারে বিভ্রান্তি না হয়)
            cursor.execute("UPDATE users SET task_balance = task_balance + ? WHERE user_id = ?", (net_amount, user_id))
            conn.commit()
            
            # ইউজারকে নোটিফাই করা
            await client.send_message(user_id, f"❌ দুঃখিত! আপনার **{net_amount:.2f} ৳** উইথড্র রিকোয়েস্টটি অ্যাডমিন দ্বারা **বাতিল** করা হয়েছে এবং টাকা আপনার অ্যাকাউন্টে ফেরত দেওয়া হয়েছে।")
            await callback_query.edit_message_text(f"❌ উইথড্র ID {w_id} ({net_amount:.2f} ৳) সফলভাবে বাতিল করা হয়েছে এবং টাকা ইউজারকে ফেরত দেওয়া হয়েছে।")

        # অ্যাপ্রুভ হলে 
        else:
            conn.commit()
            await client.send_message(user_id, f"✅ অভিনন্দন! আপনার **{net_amount:.2f} ৳** উইথড্র রিকোয়েস্টটি অ্যাডমিন দ্বারা **অনুমোদন** করা হয়েছে।")
            await callback_query.edit_message_text(f"✅ উইথড্র ID {w_id} ({net_amount:.2f} ৳) সফলভাবে অনুমোদন করা হয়েছে।")

        await callback_query.answer(f"উইথড্র ID {w_id} {status}")
