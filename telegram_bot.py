import os
import logging
from dotenv import load_dotenv  # Import this

# Load keys from .env file
load_dotenv()

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai
from keep_alive import keep_alive
from scraper import get_all_cinemas_data
# --- BACKGROUND JOB: AUTO-REFRESH ---
import asyncio

keep_alive()

# --- CONFIGURATION ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# --- SETUP AI ---
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
try:
    model = genai.GenerativeModel('gemini-2.5-flash-lite')
except:
    model = genai.GenerativeModel('gemini-flash-lite-latest')

# --- LOGGING ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

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


async def refresh_data_job(context: ContextTypes.DEFAULT_TYPE):
    """Runs every 12 hours to update data"""
    global CINEMA_DATA
    logger.info("🔄 Job Queue: Starting scheduled data refresh...")
    
    # 1. Scrape new data (This might take 10-20 seconds)
    # Run the blocking scraper in a separate thread so it doesn't block the async event loop
    loop = asyncio.get_running_loop()
    new_data_list = await loop.run_in_executor(None, get_all_cinemas_data)
    
    if new_data_list:
        # 2. Save to file and update global variable
        CINEMA_DATA = save_data_to_file(new_data_list)
        logger.info("✅ Job Queue: Data refreshed and saved successfully!")

    else:
        logger.warning("⚠️ Job Queue: Failed to scrape data. Keeping old data.")

# --- AI FUNCTION ---
async def ask_gemini_async(user_query, context_text):
    prompt = f"""
    You are a premium Movie Assistant for Alexandria, Egypt.
    
    INSTRUCTIONS:
    1. Answer using ONLY the "CINEMA SCHEDULE" below.
    2. Format your response elegantly using Telegram-supported HTML tags (<b>bold</b>, <i>italic</i>, <code>monospace</code>).
    3. CRITICAL: Use LOTS of spacing and new lines. DO NOT group showtimes on the same line with commas.
    4. Each experience type and its times must be beautifully spaced. For example:
       
       <b>🎬 Movie Title</b>
       
       📍 <i>Cinema Name</i>
       
       🔸 <b>Standard [2D]</b>
       ⏰ 10:30 ص 💵 150 EGP
       ⏰ 01:00 م 💵 150 EGP
       
       🔸 <b>VIP [2D]</b>
       ⏰ 01:15 م 💵 275 EGP
       
    5. Use emojis generously to make the output visually appealing.
    6. Always add a blank empty line between different cinemas to keep the chat clean.
    7. CRITICAL: Do NOT use markdown asterisks (** or *). Use ONLY HTML tags like <b> and <i>.

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
        "👋 Hello! I am your Alexandria Cinema Bot.\n\n"
        "I have access to ALL movie schedules and showtimes from cinemas across Alexandria! 🎬\n\n"
        "Try asking me:\n"
        "• 'What movies are playing?'\n"
        "• 'Where can I watch [movie name]?'\n"
        "• 'What are the showtimes for [movie name]?'\n"
        "• 'How much are tickets for [movie name]?'\n"
        "• 'Which cinema has the cheapest tickets?'\n"
        "• 'Show me available Cinemas'\n\n"
        "Data updates automatically every 12 hours. ⏰"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CINEMA_DATA
    
    if not CINEMA_DATA:
        await update.message.reply_text("⚠️ My data is currently loading. Please try again in 1 minute.")
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    ai_reply = await ask_gemini_async(update.message.text, CINEMA_DATA)
    try:
        await update.message.reply_text(ai_reply, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"HTML Parse Error: {e}. Falling back to plain text.")
        await update.message.reply_text(ai_reply)

# --- ERROR HANDLER ---
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    if update and hasattr(update, 'message') and update.message:
        await update.message.reply_text("⚠️ An unexpected error occurred. My developers have been notified.")

# --- MAIN ---
if __name__ == '__main__':
    # 1. Initial Load (Try to load from file first for instant start)
    CINEMA_DATA = load_data_from_file()
    
    if not CINEMA_DATA:
        logger.warning("⚠️ No local file found. Scraper will run immediately after bot starts.")
    else:
        logger.info("✅ Loaded initial data from file.")

    logger.info("🤖 Telegram Bot is starting...")
    
    # 2. Build Application
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # 3. Add Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_error_handler(error_handler)

    # 4. Schedule the Refresh Job
    job_queue = app.job_queue
    # Run once immediately (after 5 seconds) to ensure we have fresh data
    job_queue.run_once(refresh_data_job, 5)
    # Then run every 12 hours (43200 seconds)
    job_queue.run_repeating(refresh_data_job, interval=43200, first=43200)

    # 5. Run
    app.run_polling()