import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from flask import Flask
from threading import Thread

# --- CONFIGURATION ---
# These read the secrets from your Render Dashboard.
# If testing locally, replace the second value with your real strings.
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8380836963:AAFFltwM5n10dIo5poWaJLL_cXXo55ZtV_Q")
AMAZON_TAG = os.environ.get("AMAZON_TAG", "eshwardeals-21")

# Set up logging to see what's happening
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- BOT HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Triggered by /start. Shows the Category Menu.
    """
    user_first_name = update.effective_user.first_name
    
    # Reset any previous category choice
    context.user_data['category_code'] = None 
    
    disclaimer = (
        "⚠️ *Disclaimer:* As an Amazon Associate, I earn from qualifying purchases.\n"
    )
    
    # Define the menu buttons (Text -> Amazon Category Code)
    keyboard = [
        [
            InlineKeyboardButton("👕 Fashion", callback_data='apparel'), 
            InlineKeyboardButton("📱 Tech", callback_data='electronics')
        ],
        [
            InlineKeyboardButton("📚 Books", callback_data='stripbooks'), 
            InlineKeyboardButton("🏠 Home", callback_data='kitchen')
        ],
        [
            InlineKeyboardButton("🔍 Search Everything", callback_data='all')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Hi {user_first_name}! I am your Deal Finder.\n\n{disclaimer}\n\n👇 **Select a category to start:**",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Triggered when a user clicks a Category button.
    """
    query = update.callback_query
    await query.answer() # Stop the loading animation
    
    selected_code = query.data
    
    # Save the choice. If 'all', we set it to None so the URL is generic.
    context.user_data['category_code'] = None if selected_code == 'all' else selected_code
    
    # Create a nice name for display
    name_map = {
        'apparel': 'Fashion 👕',
        'electronics': 'Electronics 📱',
        'stripbooks': 'Books 📚',
        'kitchen': 'Home 🏠',
        'all': 'All Categories 🔍'
    }
    cat_name = name_map.get(selected_code, 'All Categories')

    # Confirm the selection
    await query.edit_message_text(
        text=f"✅ Category set to: **{cat_name}**\n\nNow type what you are looking for (e.g., 'Running Shoes' or 'iPhone 15').",
        parse_mode='Markdown'
    )

async def search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Triggered when the user sends text (the search query).
    """
    user_text = update.message.text
    cat_code = context.user_data.get('category_code')
    
    # 1. Construct the Amazon Affiliate URL
    # format: amazon.in/s?k=QUERY&tag=YOURTAG
    base_url = f"https://www.amazon.in/s?k={user_text.replace(' ', '+')}&tag={AMAZON_TAG}"
    
    # 2. Add Category Filter if selected
    if cat_code:
        base_url += f"&i={cat_code}"
    
    # 3. Create a clickable button
    keyboard = [[InlineKeyboardButton("🛒 View Best Deals on Amazon", url=base_url)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # 4. Reply to the user
    await update.message.reply_text(
        f"🔎 **Results for:** '{user_text}'\n\n"
        f"Click the button below to see available products, prices, and reviews on Amazon.\n",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# --- FLASK KEEP-ALIVE SERVER (For Render Free Tier) ---
app = Flask('')

@app.route('/')
def home():
    return "I am alive! The bot is running."

def run_http():
    # Render assigns a random PORT via env variable. Default to 8080 if not found.
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    # Run Flask in a background thread so it doesn't stop the bot
    t = Thread(target=run_http)
    t.start()

# --- MAIN EXECUTION ---
if __name__ == '__main__':
    # 1. Start the fake website
    keep_alive()
    
    # 2. Start the Telegram Bot
    print("Bot is starting...")
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), search_handler))

    application.run_polling()
