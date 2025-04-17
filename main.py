# main.py
import os
import logging
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters, ContextTypes
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# States for conversation
SELECTING_ACTION, ADDING_NAME, ADDING_LOCATION, WAITING_FOR_RATING = range(4)

# Callback data
ADD_RESTAURANT = "add_restaurant"
VIEW_RESTAURANTS = "view_restaurants"
RECOMMEND_RESTAURANTS = "recommend_restaurants"
DELETE_RESTAURANT = "delete_restaurant"
CONFIRM_DELETE = "confirm_delete"
CANCEL = "cancel"
RATE = "rate"

# Restaurant data file
RESTAURANT_DATA_FILE = "restaurants.json"

# Load restaurant data from file
def load_restaurant_data():
    if os.path.exists(RESTAURANT_DATA_FILE):
        with open(RESTAURANT_DATA_FILE, "r", encoding="utf-8") as file:
            try:
                return json.load(file)
            except json.JSONDecodeError:
                return {}
    return {}

# Save restaurant data to file
def save_restaurant_data(data):
    with open(RESTAURANT_DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Send welcome message and show main menu."""
    keyboard = [
        [InlineKeyboardButton("🍽️ Restoran qo'shish", callback_data=ADD_RESTAURANT)],
        [InlineKeyboardButton("📋 Restoranlarni ko'rish", callback_data=VIEW_RESTAURANTS)],
        [InlineKeyboardButton("⭐ Tavsiya etilgan restoranlar", callback_data=RECOMMEND_RESTAURANTS)],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Assalomu alaykum! Restoran joylashuvi botiga xush kelibsiz!\n"
        "Quyidagi amallardan birini tanlang:",
        reply_markup=reply_markup
    )
    
    return SELECTING_ACTION

# Handle menu selection
async def menu_actions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    if query.data == ADD_RESTAURANT:
        await query.edit_message_text("Restoran nomini kiriting:")
        return ADDING_NAME
    
    elif query.data == VIEW_RESTAURANTS:
        restaurants = load_restaurant_data()
        if not restaurants:
            keyboard = [[InlineKeyboardButton("🔙 Orqaga", callback_data=CANCEL)]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("Hech qanday restoran topilmadi.", reply_markup=reply_markup)
            return SELECTING_ACTION
        
        restaurant_list = "📋 Restoranlar ro'yxati:\n\n"
        for name, info in restaurants.items():
            rating_text = f"{info.get('rating', 'Baholanmagan')} ⭐" if info.get('rating') else "Baholanmagan"
            restaurant_list += f"🍽️ *{name}*\n📍 Manzil: {info['location']}\n⭐ Baho: {rating_text}\n\n"
        
        keyboard = []
        for name in restaurants.keys():
            keyboard.append([InlineKeyboardButton(f"❌ {name} - o'chirish", callback_data=f"{DELETE_RESTAURANT}:{name}")])
            keyboard.append([InlineKeyboardButton(f"⭐ {name} - baholash", callback_data=f"{RATE}:{name}")])
        
        keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data=CANCEL)])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(restaurant_list, reply_markup=reply_markup, parse_mode="Markdown")
        return SELECTING_ACTION
    
    elif query.data == RECOMMEND_RESTAURANTS:
        restaurants = load_restaurant_data()
        if not restaurants:
            keyboard = [[InlineKeyboardButton("🔙 Orqaga", callback_data=CANCEL)]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("Hech qanday restoran topilmadi.", reply_markup=reply_markup)
            return SELECTING_ACTION
        
        # Filter restaurants with ratings and sort by rating (highest first)
        rated_restaurants = {name: info for name, info in restaurants.items() if info.get('rating')}
        if not rated_restaurants:
            keyboard = [[InlineKeyboardButton("🔙 Orqaga", callback_data=CANCEL)]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("Hech qanday baholangan restoran topilmadi.", reply_markup=reply_markup)
            return SELECTING_ACTION
            
        sorted_restaurants = sorted(
            rated_restaurants.items(), 
            key=lambda x: float(x[1].get('rating', 0)), 
            reverse=True
        )
        
        recommendations = "⭐ Tavsiya etilgan restoranlar:\n\n"
        for name, info in sorted_restaurants:
            if float(info.get('rating', 0)) >= 4.0:
                recommendations += f"🏆 *{name}* - {info['rating']}⭐\n📍 Manzil: {info['location']}\n\n"
            else:
                recommendations += f"🍽️ *{name}* - {info['rating']}⭐\n📍 Manzil: {info['location']}\n\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Orqaga", callback_data=CANCEL)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(recommendations, reply_markup=reply_markup, parse_mode="Markdown")
        return SELECTING_ACTION
    
    elif query.data == CANCEL:
        keyboard = [
            [InlineKeyboardButton("🍽️ Restoran qo'shish", callback_data=ADD_RESTAURANT)],
            [InlineKeyboardButton("📋 Restoranlarni ko'rish", callback_data=VIEW_RESTAURANTS)],
            [InlineKeyboardButton("⭐ Tavsiya etilgan restoranlar", callback_data=RECOMMEND_RESTAURANTS)],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "Asosiy menyu:\nQuyidagi amallardan birini tanlang:",
            reply_markup=reply_markup
        )
        return SELECTING_ACTION
    
    elif query.data.startswith(DELETE_RESTAURANT):
        restaurant_name = query.data.split(":", 1)[1]
        keyboard = [
            [
                InlineKeyboardButton("✅ Ha", callback_data=f"{CONFIRM_DELETE}:{restaurant_name}"),
                InlineKeyboardButton("❌ Yo'q", callback_data=CANCEL)
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"Siz rostdan ham '{restaurant_name}' restoranini o'chirmoqchimisiz?",
            reply_markup=reply_markup
        )
        return SELECTING_ACTION
    
    elif query.data.startswith(CONFIRM_DELETE):
        restaurant_name = query.data.split(":", 1)[1]
        restaurants = load_restaurant_data()
        if restaurant_name in restaurants:
            del restaurants[restaurant_name]
            save_restaurant_data(restaurants)
            await query.edit_message_text(f"'{restaurant_name}' restoran muvaffaqiyatli o'chirildi!")
        else:
            await query.edit_message_text("Bunday restoran topilmadi.")
        
        # Return to main menu after short delay
        keyboard = [
            [InlineKeyboardButton("🔙 Asosiy menyu", callback_data=CANCEL)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Restoran o'chirildi. Asosiy menyuga qaytish uchun tugmani bosing.", reply_markup=reply_markup)
        return SELECTING_ACTION
        
    elif query.data.startswith(RATE):
        restaurant_name = query.data.split(":", 1)[1]
        context.user_data["rating_restaurant"] = restaurant_name
        
        keyboard = [
            [
                InlineKeyboardButton("1⭐", callback_data="rate:1"),
                InlineKeyboardButton("2⭐", callback_data="rate:2"),
                InlineKeyboardButton("3⭐", callback_data="rate:3"),
                InlineKeyboardButton("4⭐", callback_data="rate:4"),
                InlineKeyboardButton("5⭐", callback_data="rate:5"),
            ],
            [InlineKeyboardButton("🔙 Bekor qilish", callback_data=CANCEL)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"'{restaurant_name}' restorani uchun 1 dan 5 gacha baho bering:",
            reply_markup=reply_markup
        )
        return WAITING_FOR_RATING
    
    elif query.data.startswith("rate:"):
        rating = query.data.split(":", 1)[1]
        restaurant_name = context.user_data.get("rating_restaurant")
        
        if restaurant_name:
            restaurants = load_restaurant_data()
            if restaurant_name in restaurants:
                restaurants[restaurant_name]["rating"] = rating
                save_restaurant_data(restaurants)
                await query.edit_message_text(f"'{restaurant_name}' restoran {rating}⭐ bilan baholandi!")
            else:
                await query.edit_message_text("Bunday restoran topilmadi.")
        
        # Return to main menu after short delay
        keyboard = [
            [InlineKeyboardButton("🔙 Asosiy menyu", callback_data=CANCEL)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Restoran baholandi. Asosiy menyuga qaytish uchun tugmani bosing.", reply_markup=reply_markup)
        return SELECTING_ACTION
    
    return SELECTING_ACTION

# Handle restaurant name input
async def add_restaurant_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["restaurant_name"] = update.message.text
    await update.message.reply_text("Endi restoran joylashuvini (manzilini) kiriting:")
    return ADDING_LOCATION

# Handle restaurant location input
async def add_restaurant_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = context.user_data["restaurant_name"]
    location = update.message.text
    
    restaurants = load_restaurant_data()
    restaurants[name] = {"location": location}
    save_restaurant_data(restaurants)
    
    keyboard = [
        [InlineKeyboardButton("🔙 Asosiy menyu", callback_data=CANCEL)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"Restoran muvaffaqiyatli qo'shildi!\n\n"
        f"📝 Nomi: {name}\n"
        f"📍 Manzil: {location}",
        reply_markup=reply_markup
    )
    
    return SELECTING_ACTION

# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a message to the user."""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    
    if update.effective_message:
        await update.effective_message.reply_text(
            "Xatolik yuz berdi. Iltimos qaytadan urinib ko'ring."
        )

def main() -> None:
    """Start the bot."""
    # Create the Application
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("No token provided. Set TELEGRAM_BOT_TOKEN environment variable.")
        return
    
    application = Application.builder().token(token).build()

    # Create conversation handler with the states
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECTING_ACTION: [
                CallbackQueryHandler(menu_actions),
            ],
            ADDING_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_restaurant_name),
            ],
            ADDING_LOCATION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_restaurant_location),
            ],
            WAITING_FOR_RATING: [
                CallbackQueryHandler(menu_actions),
            ],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    application.add_handler(conv_handler)
    application.add_error_handler(error_handler)

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
