import logging
import sqlite3
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# إعدادات البوت - نستخدم متغيرات البيئة لأمان أفضل
BOT_TOKEN = os.getenv('BOT_TOKEN', '7748187948:AAHw97hJXiqnhC_7n7LigAbrMM-Mb-3dAAc')
CHANNEL_USERNAME = "@boxiify"
ADMIN_ID = 8353874553

# إعداد قاعدة البيانات
def init_db():
    conn = sqlite3.connect('/tmp/bot_database.db')  # استخدم /tmp لـ Render
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, username TEXT, points INTEGER DEFAULT 0, 
                  referral_code TEXT, referred_by INTEGER, join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS ads
                 (ad_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, ad_text TEXT, 
                  ad_type TEXT, points_cost INTEGER, status TEXT DEFAULT 'pending',
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS tasks
                 (task_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, task_type TEXT,
                  completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    conn.commit()
    conn.close()

init_db()

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

class PointsBot:
    def __init__(self):
        self.db_connection = sqlite3.connect('/tmp/bot_database.db', check_same_thread=False)
    
    def get_user_points(self, user_id):
        c = self.db_connection.cursor()
        c.execute("SELECT points FROM users WHERE user_id = ?", (user_id,))
        result = c.fetchone()
        return result[0] if result else 0
    
    def add_user(self, user_id, username, referral_code=None):
        c = self.db_connection.cursor()
        try:
            c.execute("INSERT OR IGNORE INTO users (user_id, username, points, referral_code) VALUES (?, ?, ?, ?)",
                     (user_id, username, 50, f"ref_{user_id}"))
            
            if referral_code and referral_code.startswith('ref_'):
                referred_user_id = int(referral_code[4:])
                c.execute("UPDATE users SET points = points + 100 WHERE user_id = ?", (referred_user_id,))
                c.execute("UPDATE users SET referred_by = ? WHERE user_id = ?", (referred_user_id, user_id))
            
            self.db_connection.commit()
        except Exception as e:
            print(f"Error adding user: {e}")
    
    def add_points(self, user_id, points):
        c = self.db_connection.cursor()
        c.execute("UPDATE users SET points = points + ? WHERE user_id = ?", (points, user_id))
        self.db_connection.commit()
    
    def deduct_points(self, user_id, points):
        current_points = self.get_user_points(user_id)
        if current_points >= points:
            c = self.db_connection.cursor()
            c.execute("UPDATE users SET points = points - ? WHERE user_id = ?", (points, user_id))
            self.db_connection.commit()
            return True
        return False

bot_manager = PointsBot()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or f"user_{user_id}"
    
    referral_code = None
    if context.args:
        referral_code = context.args[0]
    
    bot_manager.add_user(user_id, username, referral_code)
    
    welcome_text = f"""
🚀 **Welcome to Boxiify Promotion Bot!**

📊 **Your Points:** {bot_manager.get_user_points(user_id)}
🎯 **Your Mission:** Help grow {CHANNEL_USERNAME}

💡 **How to Earn Points:**
✅ Join channels & groups - 10 points each
📺 Watch YouTube videos - 5 points each  
👥 Refer friends - 100 points per referral
🎁 Daily bonus - 5 points

📢 **Your Referral Link:**
`https://t.me/{(await context.bot.get_me()).username}?start=ref_{user_id}`

Use /menu to see all options!
    """
    
    keyboard = [
        [InlineKeyboardButton("🎯 Earn Points", callback_data="earn_points")],
        [InlineKeyboardButton("📢 Place Ad", callback_data="place_ad")],
        [InlineKeyboardButton("📊 My Stats", callback_data="my_stats")],
        [InlineKeyboardButton("👥 Refer Friends", callback_data="refer_friends")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎯 Earn Points", callback_data="earn_points")],
        [InlineKeyboardButton("📢 Place Ad", callback_data="place_ad")],
        [InlineKeyboardButton("📊 My Stats", callback_data="my_stats")],
        [InlineKeyboardButton("👥 Refer Friends", callback_data="refer_friends")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📱 **Main Menu**", reply_markup=reply_markup, parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if query.data == "earn_points":
        keyboard = [
            [InlineKeyboardButton("Join Channel (10 points)", callback_data="task_join_channel")],
            [InlineKeyboardButton("Watch YouTube (5 points)", callback_data="task_watch_youtube")],
            [InlineKeyboardButton("Daily Bonus (5 points)", callback_data="task_daily_bonus")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("🎯 **Choose tasks to earn points:**", reply_markup=reply_markup, parse_mode='Markdown')
    
    elif query.data == "place_ad":
        user_points = bot_manager.get_user_points(user_id)
        ad_cost = 200
        
        if user_points >= ad_cost:
            keyboard = [[InlineKeyboardButton("📝 Write Your Ad", callback_data="write_ad")],
                       [InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(f"📢 **Place Your Ad**\n\nCost: {ad_cost} points\nYour Points: {user_points}\n\nYour ad will be shown to all bot users!", reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await query.edit_message_text(f"❌ Not enough points!\nYou need {ad_cost} points, but you have {user_points}.\n\nComplete tasks to earn more points!")
    
    elif query.data == "my_stats":
        user_points = bot_manager.get_user_points(user_id)
        c = bot_manager.db_connection.cursor()
        c.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (user_id,))
        referrals_count = c.fetchone()[0]
        
        stats_text = f"""
📊 **Your Statistics:**

💎 Points: {user_points}
👥 Referrals: {referrals_count}
📈 Total Earnings: {user_points + (referrals_count * 100)}

🎯 Keep earning to promote {CHANNEL_USERNAME}!
        """
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(stats_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    elif query.data == "refer_friends":
        referral_link = f"https://t.me/{(await context.bot.get_me()).username}?start=ref_{user_id}"
        ref_text = f"""
👥 **Refer Friends & Earn!**

Invite your friends and get **100 points** for each friend who joins!

📤 **Your Referral Link:**
`{referral_link}`

📢 **Share this message:**
\"Join @boxiify promotion bot! Earn free points and promote your channels! Use my link: {referral_link}\"
        """
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(ref_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    elif query.data == "back_to_menu":
        await menu(update, context)
    
    elif query.data.startswith("task_"):
        task_type = query.data[5:]
        c = bot_manager.db_connection.cursor()
        
        c.execute("SELECT * FROM tasks WHERE user_id = ? AND task_type = ? AND DATE(completed_at) = DATE('now')", (user_id, task_type))
        if c.fetchone():
            await query.edit_message_text("❌ You've already completed this task today!")
            return
        
        if task_type == "join_channel":
            bot_manager.add_points(user_id, 10)
            points_earned = 10
            task_desc = "joining our channel"
        elif task_type == "watch_youtube":
            bot_manager.add_points(user_id, 5)
            points_earned = 5
            task_desc = "watching YouTube video"
        elif task_type == "daily_bonus":
            bot_manager.add_points(user_id, 5)
            points_earned = 5
            task_desc = "daily bonus"
        
        c.execute("INSERT INTO tasks (user_id, task_type) VALUES (?, ?)", (user_id, task_type))
        bot_manager.db_connection.commit()
        
        await query.edit_message_text(f"✅ Task completed!\nYou earned {points_earned} points for {task_desc}!\n\nTotal points: {bot_manager.get_user_points(user_id)}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🆘 **Help Guide**

🤔 **How it works:**
1. Earn points by completing tasks
2. Use points to advertise your channel
3. Grow your audience for FREE!

📋 **Available Commands:**
/start - Start the bot
/menu - Main menu
/help - This help message

🎯 **Tasks:**
- Join channels: 10 points
- Watch videos: 5 points  
- Daily bonus: 5 points
- Refer friends: 100 points

📢 **Advertising:**
Cost: 200 points
Your ad will be shown to all bot users!

Need help? Contact admin!
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

def main():
    # التحقق من وجود التوكن
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ ERROR: Please set BOT_TOKEN environment variable")
        return
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    print("🤖 Bot is running on Render...")
    application.run_polling()

if __name__ == '__main__':
    main()