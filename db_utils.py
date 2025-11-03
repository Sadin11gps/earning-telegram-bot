import os
import psycopg2 

DATABASE_URL = os.environ.get("DATABASE_URL")

# গ্লোবাল সংযোগ অবজেক্ট
conn = None
cursor = None

def get_db_connection():
    global conn, cursor
    if conn is None:
        if not DATABASE_URL:
            print("Error: DATABASE_URL not set.")
            return False
            
        try:
            # PostgreSQL সংযোগ (sslmode='require' সহ)
            conn = psycopg2.connect(DATABASE_URL, sslmode='require') 
            cursor = conn.cursor()
            print("Database connection successful.")
            
            # CRITICAL: সব টেবিল তৈরি করার লজিক এখানে নিয়ে আসা হলো
            # ইউজার টেবিল
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    task_balance REAL DEFAULT 0.00,
                    referral_balance REAL DEFAULT 0.00,
                    referral_count INTEGER DEFAULT 0,
                    referred_by BIGINT,
                    is_blocked INTEGER DEFAULT 0,
                    last_bonus_time INTEGER DEFAULT 0
                )
            ''')
            # Task Status টেবিল
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_status (
                    user_id BIGINT,
                    task_name TEXT,
                    completed_at TEXT,
                    PRIMARY KEY (user_id, task_name, completed_at)
                )
            ''')
            # উইথড্র হিস্টরি টেবিল
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS withdraw_history (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    amount REAL,
                    method TEXT,
                    account_number TEXT,
                    status TEXT DEFAULT 'Pending',
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
            return True
        except Exception as e:
            print(f"Database connection or table creation failed: {e}")
            return False
    return True
