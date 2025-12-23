from keep_alive import keep_alive
keep_alive()  # Starts the web server in the background

import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai


# Import your scraper function directly
# Make sure scraper.py is in the same folder and has the 'get_all_cinemas_data' function
from scraper import get_all_cinemas_data 

# --- CONFIGURATION ---
os.environ["GOOGLE_API_KEY"] = "AIzaSyAxeXa0q_4yrIE_X5UTcj-P_htwT4Z-9B4"

TELEGRAM_TOKEN = "8535124656:AAHfyWkzYboZmwOYUzidgz10BosPbdtcWFE"

# --- SETUP AI ---
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
try:
    model = genai.GenerativeModel('gemini-flash-latest')
except:
    model = genai.GenerativeModel('gemini-1.5-flash')

# --- LOGGING ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- GLOBAL DATA STORE ---
# We use a global variable so the bot can access the latest data in memory
CINEMA_DATA = None

# --- HELPER: SAVE DATA TO FILE ---
def save_data_to_file(data_list):
    """Takes the list from scraper and saves it as text file"""
    file_content = ""
    for cinema in data_list:
        file_content += f"📍 {cinema['cinema_name'].upper()}\n"
        file_content += "="*40 + "\n"
        for m in cinema['movies']:
            file_content += f"🎬 {m['movie']}\n"
            file_content += f"💵 {', '.join(m['shows'])}\n"
            file_content += "-" * 20 + "\n"
        file_content += "\n"

    with open("cinema_data.txt", "w", encoding="utf-8") as f:
        f.write(file_content)
    return file_content

# --- HELPER: LOAD DATA FROM FILE ---
def load_data_from_file():
    try:
        with open("cinema_data.txt", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return None

# --- BACKGROUND JOB: AUTO-REFRESH ---
async def refresh_data_job(context: ContextTypes.DEFAULT_TYPE):
    """Runs every 12 hours to update data"""
    global CINEMA_DATA
    print("🔄 Job Queue: Starting scheduled data refresh...")
    
    # 1. Scrape new data (This might take 10-20 seconds)
    # We run it in a way that doesn't block the bot
    new_data_list = get_all_cinemas_data()
    
    if new_data_list:
        # 2. Save to file and update global variable
        CINEMA_DATA = save_data_to_file(new_data_list)
        print("✅ Job Queue: Data refreshed and saved successfully!")
        
        # Optional: Send a message to you (the admin) confirming update
        # await context.bot.send_message(chat_id="YOUR_PERSONAL_CHAT_ID", text="✅ Schedules updated!")
    else:
        print("⚠️ Job Queue: Failed to scrape data. Keeping old data.")

# --- AI FUNCTION ---
async def ask_gemini_async(user_query, context_text):
    prompt = f"""
    You are a helpful Movie Assistant for Alexandria, Egypt.
    
    INSTRUCTIONS:
    1. Answer using ONLY the "CINEMA SCHEDULE" below.
    2. If the user asks for a specific movie, list the cinemas and times clearly.
    3. If the user asks for recommendations (e.g., "cheap tickets"), compare the prices.
    4. If the info is missing, say "I don't have that info in the current schedule."
    5. Keep answers short and chat-friendly. Use emojis (🎬, ⏰, 💵).

    --- CINEMA SCHEDULE START ---
    {context_text}
    --- CINEMA SCHEDULE END ---

    USER QUESTION: "{user_query}"
    """
    try:
        response = await model.generate_content_async(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ AI Error: {e}"

# --- TELEGRAM HANDLERS ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hello! I am your Alexandria Cinema Bot.\n"
        "I update my data automatically every 12 hours.\n\n"
        "Ask me: 'What is playing at San Stefano?'"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CINEMA_DATA
    
    if not CINEMA_DATA:
        await update.message.reply_text("⚠️ My data is currently loading. Please try again in 1 minute.")
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    ai_reply = await ask_gemini_async(update.message.text, CINEMA_DATA)
    await update.message.reply_text(ai_reply)

# --- MAIN ---
if __name__ == '__main__':
    # 1. Initial Load (Try to load from file first for instant start)
    CINEMA_DATA = load_data_from_file()
    
    if not CINEMA_DATA:
        print("⚠️ No local file found. Scraper will run immediately after bot starts.")
    else:
        print("✅ Loaded initial data from file.")

    print("🤖 Telegram Bot is starting...")
    
    # 2. Build Application
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # 3. Add Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    # 4. Schedule the Refresh Job
    job_queue = app.job_queue
    # Run once immediately (after 5 seconds) to ensure we have fresh data
    job_queue.run_once(refresh_data_job, 5)
    # Then run every 12 hours (43200 seconds)
    job_queue.run_repeating(refresh_data_job, interval=43200, first=43200)

    # 5. Run
    app.run_polling()