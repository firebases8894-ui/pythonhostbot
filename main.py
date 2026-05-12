import os
import subprocess
import sqlite3
import telebot
import threading
import time
import uuid
import signal
import random
import platform
import zipfile
import json
import shutil
import schedule
from pathlib import Path
from telebot import types
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from flask import Flask, send_file, jsonify

# ================== Configuration ==================
class Config:
    TOKEN = os.environ.get('BOT_TOKEN', '8642538812:AAEzSokDnzA421fpsjz2UBtEy3VZwr_1MZg')
    ADMIN_ID = int(os.environ.get('ADMIN_ID', 6799848229))
    PROJECT_DIR = 'projects'
    DB_NAME = 'cyber_v2.db'
    PORT = int(os.environ.get('PORT', 10000))
    MAINTENANCE = False
    
    ADMIN_USERNAME = 'aurponmodz' 
    BOT_USERNAME = "@Dex2cprobot" 
    SUPPORT_ID = "@aurponmodz" 
    BRAND_NAME = "💎𝐀𝐔𝐑𝐏𝐎𝐍💎" 
    
    MAX_FILE_SIZE = 5.5 * 1024 * 1024 

bot = telebot.TeleBot(Config.TOKEN, parse_mode="HTML")
project_path = Path(Config.PROJECT_DIR)
project_path.mkdir(exist_ok=True)
app = Flask(__name__)

# ================== Admin Security Check ==================
# এই ডেকোরেটরটি নিশ্চিত করবে যে অন্য কেউ মেসেজ দিলে বট কোনো উত্তর দিবে না
@bot.message_handler(func=lambda message: message.from_user.id != Config.ADMIN_ID)
def ignore_others(message):
    return # কোনো রিপ্লাই দিবে না, সবাই ভাববে বট অফলাইন।

# ================== Database Functions ==================
def init_db():
    conn = sqlite3.connect(Config.DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                (id INTEGER PRIMARY KEY, username TEXT, expiry TEXT, file_limit INTEGER, 
                 is_prime INTEGER, join_date TEXT, last_renewal TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS keys 
                (key TEXT PRIMARY KEY, duration_days INTEGER, file_limit INTEGER, created_date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS deployments 
                (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, bot_name TEXT, 
                 filename TEXT, pid INTEGER, start_time TEXT, status TEXT, 
                 cpu_usage REAL, ram_usage REAL, last_active TEXT)''')
    
    join_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    expiry_date = (datetime.now() + timedelta(days=3650)).strftime('%Y-%m-%d %H:%M:%S')
    c.execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?, ?, ?, ?)", 
             (Config.ADMIN_ID, 'admin', expiry_date, 100, 1, join_date, join_date))
    conn.commit()
    conn.close()

init_db()

# ================== Helper Functions ==================
def get_user(user_id):
    conn = sqlite3.connect(Config.DB_NAME)
    c = conn.cursor()
    user = c.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    return user

def is_prime(user_id):
    user = get_user(user_id)
    if user and user[2]:
        try:
            expiry = datetime.strptime(user[2], '%Y-%m-%d %H:%M:%S')
            return expiry > datetime.now()
        except:
            return False
    return False

def get_user_bots(user_id):
    conn = sqlite3.connect(Config.DB_NAME)
    c = conn.cursor()
    bots = c.execute("SELECT id, bot_name, filename, pid, start_time, status FROM deployments WHERE user_id=?", (user_id,)).fetchall()
    conn.close()
    return bots

def create_progress_bar(percentage):
    bars = int(percentage / 10)
    return "🔵" * bars + "⚪" * (10 - bars)

def get_system_stats():
    return {
        'cpu_percent': random.randint(10, 60),
        'ram_percent': random.randint(20, 70),
        'disk_percent': random.randint(30, 80)
    }

def create_zip_file(bot_id, bot_name, filename, user_id):
    try:
        export_dir = Path('exports')
        export_dir.mkdir(exist_ok=True)
        zip_filename = f"bot_export_{bot_id}_{int(time.time())}.zip"
        zip_path = export_dir / zip_filename
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            bot_file_path = project_path / filename
            if bot_file_path.exists():
                zipf.write(bot_file_path, arcname=filename)
            metadata = {
                'bot_id': bot_id, 'bot_name': bot_name, 'filename': filename, 'user_id': user_id,
                'export_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'version': '3.0.1'
            }
            zipf.writestr('metadata.json', json.dumps(metadata, indent=4))
        return zip_path
    except Exception as e:
        return None

def check_prime_expiry(user_id):
    user = get_user(user_id)
    if user and user[2]:
        try:
            expiry = datetime.strptime(user[2], '%Y-%m-%d %H:%M:%S')
            now = datetime.now()
            if expiry > now:
                days_left = (expiry - now).days
                return {'expired': False, 'days_left': days_left, 'expiry_date': expiry.strftime('%Y-%m-%d %H:%M:%S')}
            else:
                return {'expired': True, 'expiry_date': expiry.strftime('%Y-%m-%d %H:%M:%S'), 'message': 'Expired'}
        except:
            return {'expired': True, 'message': 'Invalid expiry'}
    return {'expired': True, 'message': 'No Prime'}

# ================== Keyboards ==================
def main_menu_reply(user_id):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton("📤 𝗨𝗽𝗹𝗼𝗮𝗱 𝗕𝗼𝘁 𝗙𝗶𝗹𝗲")
    btn2 = types.KeyboardButton("🤖 𝗠𝘆 𝗕𝗼𝘁𝘀 𝗟𝗶𝘀𝘁")
    btn3 = types.KeyboardButton("🚀 𝗗𝗲𝗽𝗹𝗼𝘆 𝗡𝗲𝘄 𝗕𝗼𝘁")
    btn4 = types.KeyboardButton("📊 𝗗𝗮𝘀𝗵𝗯𝗼𝗮𝗿𝗱")
    markup.add(btn1, btn2, btn3, btn4)
    return markup

# ================== Command Handlers ==================
@bot.message_handler(commands=['start'])
def welcome(message):
    uid = message.from_user.id
    username = message.from_user.username or "Admin"
    user = get_user(uid)
    
    prime_status = check_prime_expiry(uid)
    status = "👑 𝗣𝗥𝗜𝗠𝗘 𝗔𝗗𝗠𝗜𝗡"
    
    text = f"""
✨ <b>{Config.BRAND_NAME}</b> ✨
<b>━━━━━━━━━━━━━━━━━━━━━━</b>
👤 <b>𝗨𝘀𝗲𝗿: @{username}</b>
🆔 <b>𝗜𝗗:</b> <code>{uid}</code>
💎 <b>𝗦𝘁𝗮𝘁𝘂𝘀: {status}</b>
📅 <b>𝗝𝗼𝗶𝗻 𝗗𝗮𝘁𝗲: {user[5]}</b>
<b>━━━━━━━━━━━━━━━━━━━━━━</b>
📊 <b>𝗔𝗰𝗰𝗼𝘂𝗻𝘁 𝗗𝗲𝘁𝗮𝗶𝗹𝘀:</b>
• <b>𝗣𝗹𝗮𝗻: Premium</b>
• <b>𝗙𝗶𝗹𝗲 𝗟𝗶𝗺𝗶𝘁:</b> <code>{user[3]}</code> <b>files</b>
• <b>𝗘𝘅𝗽𝗶𝗿𝘆: Lifetime (Admin Access)</b>
<b>━━━━━━━━━━━━━━━━━━━━━━</b>
"""
    bot.send_message(message.chat.id, text, reply_markup=main_menu_reply(uid))

@bot.message_handler(func=lambda message: message.text == "🏠 𝗠𝗮𝗶𝗻 𝗠𝗲𝗻𝘂")
def back_to_main(message):
    welcome(message)

@bot.message_handler(func=lambda message: message.text == "📤 𝗨𝗽𝗹𝗼𝗮𝗱 𝗕𝗼𝘁 𝗙𝗶𝗹𝗲")
def upload_handler(message):
    msg = bot.reply_to(message, "<b>📤 𝗨𝗣𝗟𝗢𝗔𝗗 𝗕𝗢𝗧 𝗙𝗜𝗟𝗘</b>\n<b>━━━━━━━━━━━━━━━━━━━━━━</b>\n<b>𝗣𝗹𝗲𝗮𝘀𝗲 𝘀𝗲𝗻𝗱 𝘆𝗼𝘂𝗿 .𝗽𝘆 𝗼𝗿 .𝘇𝗶𝗽 𝗳𝗶𝗹𝗲 (𝗠𝗮𝘅 𝟱.𝟱𝗠𝗕).</b>")
    bot.register_next_step_handler(msg, upload_file_step)

def upload_file_step(message):
    uid = message.from_user.id
    chat_id = message.chat.id
    if message.content_type == 'document':
        try:
            file_name = message.document.file_name.lower()
            if not (file_name.endswith('.py') or file_name.endswith('.zip')):
                bot.send_message(chat_id, "<b>❌ 𝗢𝗻𝗹𝘆 𝗣𝘆𝘁𝗵𝗼𝗻 (.𝗽𝘆) 𝗼𝗿 𝗭𝗜𝗣 (.𝘇𝗶𝗽) 𝗳𝗶𝗹𝗲𝘀 𝗮𝗹𝗹𝗼𝘄𝗲𝗱.</b>")
                return
            
            bot.send_message(chat_id, "<b>📥 𝗗𝗼𝘄𝗻𝗹𝗼𝗮𝗱𝗶𝗻𝗴 𝗳𝗶𝗹𝗲...</b>")
            file_info = bot.get_file(message.document.file_id)
            downloaded = bot.download_file(file_info.file_path)
            
            safe_name = secure_filename(message.document.file_name)
            file_path = project_path / safe_name
            file_path.write_bytes(downloaded)
            
            msg = bot.send_message(chat_id, "<b>🤖 𝗘𝗻𝘁𝗲𝗿 𝗮 𝗻𝗮𝗺𝗲 𝗳𝗼𝗿 𝘆𝗼𝘂𝗿 𝗯𝗼𝘁:</b>")
            bot.register_next_step_handler(msg, save_bot_name, safe_name)
        except Exception as e:
            bot.send_message(chat_id, f"<b>❌ 𝗘𝗿𝗿𝗼𝗿: {str(e)}</b>")
    else:
        bot.send_message(chat_id, "<b>❌ 𝗣𝗹𝗲𝗮𝘀𝗲 𝘀𝗲𝗻𝗱 𝗮 𝘃𝗮𝗹𝗶𝗱 𝗳𝗶𝗹𝗲.</b>")

def save_bot_name(message, safe_name):
    uid = message.from_user.id
    bot_name = message.text.strip()[:50]
    conn = sqlite3.connect(Config.DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO deployments (user_id, bot_name, filename, pid, start_time, status, last_active) VALUES (?, ?, ?, ?, ?, ?, ?)",
             (uid, bot_name, safe_name, 0, None, "Uploaded", datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📚 𝗜𝗻𝘀𝘁𝗮𝗹𝗹 𝗟𝗶𝗯𝗿𝗮𝗿𝗶𝗲𝘀", "🤖 𝗠𝘆 𝗕𝗼𝘁𝘀 𝗟𝗶𝘀𝘁", "🏠 𝗠𝗮𝗶𝗻 𝗠𝗲𝗻𝘂")
    bot.send_message(message.chat.id, f"<b>✅ 𝗕𝗼𝘁 '{bot_name}' 𝘂𝗽𝗹𝗼𝗮𝗱𝗲𝗱! 𝗖𝗹𝗶𝗰𝗸 𝗯𝗲𝗹𝗼𝘄 𝘁𝗼 𝗶𝗻𝘀𝘁𝗮𝗹𝗹 𝗹𝗶𝗯𝗿𝗮𝗿𝗶𝗲𝘀.</b>", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "📚 𝗜𝗻𝘀𝘁𝗮𝗹𝗹 𝗟𝗶𝗯𝗿𝗮𝗿𝗶𝗲𝘀")
def ask_for_libraries(message):
    msg = bot.reply_to(message, "<b>📚 𝗜𝗡𝗦𝗧𝗔𝗟𝗟 𝗟𝗜𝗕𝗥𝗔𝗥𝗜𝗘𝗦</b>\n<b>𝗘𝗻𝘁𝗲𝗿 𝗹𝗶𝗯𝗿𝗮𝗿𝘆 𝗰𝗼𝗺𝗺𝗮𝗻𝗱𝘀 (𝗲.𝗴., 𝗽𝗶𝗽 𝗶𝗻𝘀𝘁𝗮𝗹𝗹 𝗿𝗲𝗾𝘂𝗲𝘀𝘁𝘀).</b>")
    bot.register_next_step_handler(msg, install_libraries_step)

def install_libraries_step(message):
    commands = [cmd.strip() for cmd in message.text.strip().split('\n') if cmd.strip()]
    bot.send_message(message.chat.id, "<b>🛠 𝗜𝗻𝘀𝘁𝗮𝗹𝗹𝗶𝗻𝗴 𝗹𝗶𝗯𝗿𝗮𝗿𝗶𝗲𝘀... 𝗣𝗹𝗲𝗮𝘀𝗲 𝘄𝗮𝗶𝘁.</b>")
    results = []
    for cmd in commands:
        if "pip install" in cmd:
            res = subprocess.run(cmd.split(), capture_output=True, text=True)
            results.append(f"<b>✅ {cmd}</b>" if res.returncode == 0 else f"<b>❌ {cmd} 𝗙𝗮𝗶𝗹𝗲𝗱</b>")
    bot.send_message(message.chat.id, "<b>📊 𝗜𝗻𝘀𝘁𝗮𝗹𝗹𝗮𝘁𝗶𝗼𝗻 𝗥𝗲𝘀𝘂𝗹𝘁:</b>\n" + "\n".join(results))

@bot.message_handler(func=lambda message: message.text == "🤖 𝗠𝘆 𝗕𝗼𝘁𝘀 𝗟𝗶𝘀𝘁")
def show_my_bots_reply(message):
    uid = message.from_user.id
    bots = get_user_bots(uid)
    if not bots:
        bot.reply_to(message, "<b>🤖 𝗡𝗼 𝗯𝗼𝘁𝘀 𝗳𝗼𝘂𝗻𝗱 𝗶𝗻 𝘆𝗼𝘂𝗿 𝗹𝗶𝘀𝘁.</b>")
        return
    text = "<b>🤖 𝗠𝗬 𝗗𝗘𝗣𝗟𝗢𝗬𝗘𝗗 𝗕𝗢𝗧𝗦:</b>\n<b>━━━━━━━━━━━━━━━━━━━━━━</b>\n"
    for idx, b in enumerate(bots, 1):
        status = "🟢" if b[5] == "Running" else "🔴"
        text += f"<b>{idx}. {status} {b[1]}</b>\n"
    msg = bot.reply_to(message, text + "\n<b>𝗘𝗻𝘁𝗲𝗿 𝗯𝗼𝘁 𝗻𝘂𝗺𝗯𝗲𝗿 𝘁𝗼 𝘃𝗶𝗲𝘄 𝗱𝗲𝘁𝗮𝗶𝗹𝘀.</b>")
    bot.register_next_step_handler(msg, process_bot_selection, bots)

def process_bot_selection(message, bots):
    try:
        choice = int(message.text.strip())
        bot_id = bots[choice-1][0]
        show_bot_details(message, bot_id)
    except:
        bot.send_message(message.chat.id, "<b>❌ 𝗜𝗻𝘃𝗮𝗹𝗶𝗱 𝘀𝗲𝗹𝗲𝗰𝘁𝗶𝗼𝗻.</b>")

def show_bot_details(message, bot_id):
    conn = sqlite3.connect(Config.DB_NAME)
    c = conn.cursor()
    bot_info = c.execute("SELECT * FROM deployments WHERE id=?", (bot_id,)).fetchone()
    conn.close()
    if not bot_info: return
    
    text = f"""
<b>🤖 𝗕𝗢𝗧 𝗖𝗢𝗡𝗧𝗥𝗢𝗟 𝗣𝗔𝗡𝗘𝗟</b>
<b>━━━━━━━━━━━━━━━━━━━━━━</b>
<b>𝗡𝗮𝗺𝗲: {bot_info[2]}</b>
<b>𝗙𝗶𝗹𝗲:</b> <code>{bot_info[3]}</code>
<b>𝗦𝘁𝗮𝘁𝘂𝘀: {bot_info[6]}</b>
<b>𝗦𝘁𝗮𝗿𝘁𝗲𝗱: {bot_info[5] or "N/A"}</b>
<b>━━━━━━━━━━━━━━━━━━━━━━</b>
<b>𝗔𝗰𝘁𝗶𝗼𝗻𝘀: /stop_{bot_id} | /delete_{bot_id} | /export_{bot_id}</b>
"""
    bot.send_message(message.chat.id, text)

@bot.message_handler(regexp=r'^/(stop|delete|export)_(\d+)$')
def handle_bot_actions(message):
    action = message.text.split('_')[0][1:]
    bot_id = message.text.split('_')[1]
    uid = message.from_user.id
    
    conn = sqlite3.connect(Config.DB_NAME)
    c = conn.cursor()
    bot_info = c.execute("SELECT pid, user_id, filename, bot_name FROM deployments WHERE id=?", (bot_id,)).fetchone()
    
    if not bot_info or bot_info[1] != uid:
        bot.reply_to(message, "<b>❌ 𝗔𝗰𝗰𝗲𝘀𝘀 𝗗𝗲𝗻𝗶𝗲𝗱!</b>")
        conn.close()
        return

    if action == "stop":
        if bot_info[0]:
            try: os.kill(bot_info[0], signal.SIGTERM)
            except: pass
        c.execute("UPDATE deployments SET status='Stopped', pid=0 WHERE id=?", (bot_id,))
        bot.reply_to(message, "<b>✅ 𝗕𝗼𝘁 𝗦𝘁𝗼𝗽𝗽𝗲𝗱 𝗦𝘂𝗰𝗰𝗲𝘀𝘀𝗳𝘂𝗹𝗹𝘆!</b>")
    
    elif action == "delete":
        if bot_info[0]:
            try: os.kill(bot_info[0], signal.SIGKILL)
            except: pass
        file_path = project_path / bot_info[2]
        if file_path.exists(): file_path.unlink()
        c.execute("DELETE FROM deployments WHERE id=?", (bot_id,))
        bot.reply_to(message, "<b>✅ 𝗕𝗼𝘁 𝗗𝗲𝗹𝗲𝘁𝗲𝗱 𝗳𝗿𝗼𝗺 𝗦𝗲𝗿𝘃𝗲𝗿!</b>")

    elif action == "export":
        zip_path = create_zip_file(bot_id, bot_info[3], bot_info[2], uid)
        if zip_path:
            with open(zip_path, 'rb') as f:
                bot.send_document(message.chat.id, f, caption=f"<b>📦 𝗘𝘅𝗽𝗼𝗿𝘁𝗲𝗱 𝗕𝗼𝘁: {bot_info[3]}</b>")
            zip_path.unlink()
    
    conn.commit()
    conn.close()

@bot.message_handler(func=lambda message: message.text == "🚀 𝗗𝗲𝗽𝗹𝗼𝘆 𝗡𝗲𝘄 𝗕𝗼𝘁")
def deploy_new_handler(message):
    uid = message.from_user.id
    conn = sqlite3.connect(Config.DB_NAME)
    c = conn.cursor()
    files = c.execute("SELECT id, bot_name, filename FROM deployments WHERE user_id=? AND (pid=0 OR pid IS NULL)", (uid,)).fetchall()
    conn.close()
    if not files:
        bot.reply_to(message, "<b>📭 𝗡𝗼 𝗳𝗶𝗹𝗲𝘀 𝗮𝘃𝗮𝗶𝗹𝗮𝗯𝗹𝗲 𝗳𝗼𝗿 𝗱𝗲𝗽𝗹𝗼𝘆𝗺𝗲𝗻𝘁.</b>")
        return
    text = "<b>🚀 𝗦𝗲𝗹𝗲𝗰𝘁 𝗮 𝗯𝗼𝘁 𝘁𝗼 𝗱𝗲𝗽𝗹𝗼𝘆:</b>\n"
    for idx, f in enumerate(files, 1):
        text += f"<b>{idx}. {f[1]} (<code>{f[2]}</code>)</b>\n"
    msg = bot.reply_to(message, text)
    bot.register_next_step_handler(msg, process_deploy_selection, files)

def process_deploy_selection(message, files):
    try:
        choice = int(message.text.strip())
        bot_id, bot_name, filename = files[choice-1]
        
        progress_msg = bot.send_message(message.chat.id, f"<b>🚀 𝗗𝗲𝗽𝗹𝗼𝘆𝗶𝗻𝗴 {bot_name}... 𝗣𝗹𝗲𝗮𝘀𝗲 𝘄𝗮𝗶𝘁.</b>")
        file_path = project_path / filename
        start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        proc = subprocess.Popen(['python', str(file_path)], start_new_session=True)
        
        conn = sqlite3.connect(Config.DB_NAME)
        c = conn.cursor()
        c.execute("UPDATE deployments SET pid=?, start_time=?, status='Running' WHERE id=?", (proc.pid, start_time, bot_id))
        conn.commit()
        conn.close()
        bot.edit_message_text(f"<b>✅ {bot_name} 𝗶𝘀 𝗻𝗼𝘄 𝗥𝗨𝗡𝗡𝗜𝗡𝗚!</b>\n<b>𝗣𝗜𝗗:</b> <code>{proc.pid}</code>", message.chat.id, progress_msg.message_id)
    except Exception as e:
        bot.send_message(message.chat.id, f"<b>❌ 𝗗𝗲𝗽𝗹𝗼𝘆𝗺𝗲𝗻𝘁 𝗳𝗮𝗶𝗹𝗲𝗱: {e}</b>")

@bot.message_handler(func=lambda message: message.text == "📊 𝗗𝗮𝘀𝗵𝗯𝗼𝗮𝗿𝗱")
def show_dashboard_reply(message):
    uid = message.from_user.id
    user = get_user(uid)
    stats = get_system_stats()
    text = f"""
<b>📊 𝗦𝗬𝗦𝗧𝗘𝗠 𝗗𝗔𝗦𝗛𝗕𝗢𝗔𝗥𝗗</b>
<b>━━━━━━━━━━━━━━━━━━━━━━</b>
👤 <b>𝗔𝗰𝗰𝗼𝘂𝗻𝘁: 👑 𝗣𝗥𝗜𝗠𝗘 𝗔𝗗𝗠𝗜𝗡</b>
📦 <b>𝗙𝗶𝗹𝗲 𝗟𝗶𝗺𝗶𝘁: {user[3]} 𝗳𝗶𝗹𝗲𝘀</b>
<b>━━━━━━━━━━━━━━━━━━━━━━</b>
🖥️ <b>𝗦𝗲𝗿𝘃𝗲𝗿 𝗦𝘁𝗮𝘁𝘂𝘀:</b>
• <b>𝗖𝗣𝗨: {create_progress_bar(stats['cpu_percent'])} {stats['cpu_percent']}%</b>
• <b>𝗥𝗔𝗠: {create_progress_bar(stats['ram_percent'])} {stats['ram_percent']}%</b>
<b>━━━━━━━━━━━━━━━━━━━━━━</b>
"""
    bot.send_message(message.chat.id, text)

# ================== Flask & Polling ==================
@app.route('/')
def home():
    return {"status": "online", "brand": Config.BRAND_NAME}

def start_bot():
    print("🤖 Bot is starting for Admin Only...")
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except:
            time.sleep(5)

if __name__ == '__main__':
    threading.Thread(target=start_bot, daemon=True).start()
    app.run(host='0.0.0.0', port=Config.PORT)
