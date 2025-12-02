import logging
import requests
import os
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from flask import Flask
from threading import Thread

# --- CONFIGURATION ---
# On Render, these values come from "Environment Variables".
# Locally, you can replace the second argument with your actual strings if testing manually.
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8380836963:AAFFltwM5n10dIo5poWaJLL_cXXo55ZtV_Q")
AMAZON_TAG = os.environ.get("AMAZON_TAG", "eshwardeals-21")

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- ENGINE: THE SCRAPER ---
def search_amazon(query):
    """
    Searches Amazon India for the query and returns a list of top 3 products.
    """
    base_url = "https://www.amazon.in/s?k="
    search_term = query.replace(" ", "+")
    url = base_url + search_term

    # Fake a browser to avoid being blocked
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }

    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return None 

        soup = BeautifulSoup(response.content, "html.parser")
        results = []
        
        # Target standard search result containers
        products = soup.find_all("div", {"data-component-type": "s-search-result"})

        for item in products[:3]: # Limit to top 3
            try:
                # Extract Title
                h2 = item.find("h2")
                title = h2.text.strip() if h2 else "Unknown Product"
                
                # Extract Link & Add Affiliate Tag
                link_suffix = h2.a["href"]
                if "?" in link_suffix:
                    full_link = f"https://www.amazon.in{link_suffix}&tag={AMAZON_TAG}"
                else:
                    full_link = f"https://www.amazon.in{link_suffix}?tag={AMAZON_TAG}"

                # Extract Price
                price_whole = item.find("span", {"class": "a-price-whole"})
                price = f"₹{price_whole.text}" if price_whole else "Check Price"

                results.append({
                    "title": title,
                    "price": price,
                    "link": full_link
                })
            except Exception:
                continue 

        return results

    except Exception as e:
        print(f"Error scraping Amazon: {e}")
        return None

# --- BOT HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_first_name = update.effective_user.first_name
    
    # REQUIRED DISCLAIMER
    disclaimer = (
        "⚠️ *Disclaimer:* As an Amazon Associate, I earn from qualifying purchases.\n"
        "This helps keep this bot free for you!"
    )
    
    keyboard = [
        [InlineKeyboardButton("👕 Fashion", callback_data='cat_fashion'), InlineKeyboardButton("📱 Tech", callback_data='cat_tech')],
        [InlineKeyboardButton("📚 Books", callback_data='cat_books'), InlineKeyboardButton("🏠 Home", callback_data='cat_home')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Hi {user_first_name}! I can find the best deals for you.\n\n{disclaimer}\n\nChoose a category to start:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['current_category'] = query.data
    await query.edit_message_text(
        text=f"Selected Category: **{query.data}**\n\nNow type a keyword (e.g., 'iPhone 13' or 'Running shoes').",
        parse_mode='Markdown'
    )

async def search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    chat_id = update.effective_chat.id
    
    status_msg = await context.bot.send_message(chat_id=chat_id, text="🔍 Searching Amazon... please wait.")

    products = search_amazon(user_text)

    await context.bot.delete_message(chat_id=chat_id, message_id=status_msg.message_id)

    if not products:
        # Fallback link if scraping fails
        affiliate_search_link = f"https://www.amazon.in/s?k={user_text.replace(' ', '+')}&tag={AMAZON_TAG}"
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"😕 I couldn't fetch details directly (Amazon security is strict!), but here is the direct search link:\n\n[Click here to view '{user_text}' on Amazon]({affiliate_search_link})",
            parse_mode='Markdown'
        )
    else:
        for p in products:
            message = (
                f"🛍️ **{p['title']}**\n"
                f"💰 **{p['price']}**\n\n"
                f"[View on Amazon]({p['link']})"
            )
            await context.bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
        
        await context.bot.send_message(chat_id=chat_id, text="✨ Click the links to buy!")

# --- THE FAKE WEBSITE (FOR RENDER FREE TIER) ---
app = Flask('')

@app.route('/')
def home():
    return "I am alive! The bot is running."

def run_http():
    # Render assigns a random PORT via environment variable
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_http)
    t.start()

# --- MAIN EXECUTION ---
if __name__ == '__main__':
    # 1. Start the fake website (Workaround for Render Web Service)
    keep_alive()
    
    # 2. Start the bot
    print("Bot is starting...")
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), search_handler))

    application.run_polling()
