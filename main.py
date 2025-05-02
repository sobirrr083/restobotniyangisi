import os
import logging
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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
VIEW_RESTAURANT = "view_restaurant"

# Restaurant data file
RESTAURANT_DATA_FILE = "restaurants.json"

# Load admin IDs from environment variable
ADMIN_IDS = [int(id) for id in os.getenv("ADMIN_IDS", "").split(",") if id.strip().isdigit()]

# Load restaurant data from file
def load_restaurant_data():
    if os.path.exists(RESTAURANT_DATA_FILE):
        with open(RESTAURANT_DATA_FILE, "r", encoding="utf-8") as file:
            try:
                return json.load(file)
            except json.JSONDecodeError:
                logger.error("Failed to decode restaurants.json")
                return {}
    return {}

# Save restaurant data to file
def save_restaurant_data(data):
    try:
        with open(RESTAURANT_DATA_FILE, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.error(f"Failed to save restaurant data: {e}")

# Check if user is admin
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

# Get main menu keyboard based on user role
def get_main_menu_keyboard(user_id: int) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("📋 Restoranlarni ko'rish", callback_data=VIEW_RESTAURANTS)],
        [InlineKeyboardButton("⭐ Tavsiya etilgan restoranlar", callback_data=RECOMMEND_RESTAURANTS)],
    ]
    if is_admin(user_id):
        keyboard.insert(0, [InlineKeyboardButton("🍽️ Restoran qo'shish", callback_data=ADD_RESTAURANT)])
        keyboard.append([InlineKeyboardButton("🗑️ Restoran o'chirish", callback_data=DELETE_RESTAURANT)])
    return InlineKeyboardMarkup(keyboard)

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Send welcome message and show main menu."""
    user_id = update.effective_user.id
    reply_markup = get_main_menu_keyboard(user_id)
    
    welcome_text = "Assalomu alaykum! Restoran joylashuvi botiga xush kelibsiz!\n"
    if is_admin(user_id):
        welcome_text += "Admin sifatida /admin buyrug'ini ishlatib restoranlarni boshqarishingiz mumkin.\n"
    welcome_text += "Quyidagi amallardan birini tanlang:"
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    
    return SELECTING_ACTION

# Stop command handler
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """End the conversation."""
    await update.message.reply_text("Bot to'xtatildi. Qayta boshlash uchun /start ni bosing.")
    return ConversationHandler.END

# Help command handler
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Provide help information."""
    help_text = (
        "📖 Yordam:\n\n"
        "Bu bot restoranlarni boshqarish va tavsiya qilish uchun ishlatiladi.\n"
        "Quyidagi buyruqlar mavjud:\n"
        "/start - Botni boshlash\n"
        "/stop - Botni to'xtatish\n"
        "/help - Ushbu yordam xabarini ko'rish\n"
    )
    if is_admin(update.effective_user.id):
        help_text += "/admin - Admin panelini ochish\n"
    await update.message.reply_text(help_text)

# Admin panel command
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show admin panel with options."""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("Sizda admin huquqlari yo'q!")
        return ConversationHandler.END
    
    keyboard = [
        [InlineKeyboardButton("🍽️ Restoran qo'shish", callback_data=ADD_RESTAURANT)],
        [InlineKeyboardButton("🗑️ Restoran o'chirish", callback_data=DELETE_RESTAURANT)],
        [InlineKeyboardButton("📋 Restoranlarni ko'rish", callback_data=VIEW_RESTAURANTS)],
        [InlineKeyboardButton("🔙 Asosiy menyu", callback_data=CANCEL)],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Admin paneli:\nQuyidagi amallardan birini tanlang:",
        reply_markup=reply_markup
    )
    
    return SELECTING_ACTION

# Handle menu selection
async def menu_actions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if query.data == ADD_RESTAURANT:
        if not is_admin(user_id):
            await query.edit_message_text("Sizda restoran qo'shish huquqi yo'q!")
            return SELECTING_ACTION
        await query.edit_message_text("Restoran nomini kiriting:")
        return ADDING_NAME
    
    elif query.data == VIEW_RESTAURANTS:
        restaurants = load_restaurant_data()
        if not restaurants:
            keyboard = [[InlineKeyboardButton("🔙 Orqaga", callback_data=CANCEL)]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("Hech qanday restoran topilmadi.", reply_markup=reply_markup)
            return SELECTING_ACTION
        
        keyboard = []
        for name in restaurants.keys():
            keyboard.append([InlineKeyboardButton(f"🍽️ {name}", callback_data=f"{VIEW_RESTAURANT}:{name}")])
        keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data=CANCEL)])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text("Restoranlarni tanlang:", reply_markup=reply_markup)
        return SELECTING_ACTION
    
    elif query.data.startswith(VIEW_RESTAURANT):
        restaurant_name = query.data.split(":", 1)[1]
        restaurants = load_restaurant_data()
        if restaurant_name in restaurants:
            info = restaurants[restaurant_name]
            rating_text = f"{info.get('rating', 'Baholanmagan')} ⭐" if info.get('rating') else "Baholanmagan"
            restaurant_info = (
                f"🍽️ *{restaurant_name}*\n"
                f"📍 Manzil: {info['location']}\n"
                f"⭐ Baho: {rating_text}\n"
            )
            
            keyboard = [
                [InlineKeyboardButton(f"⭐ Baholash", callback_data=f"{RATE}:{restaurant_name}")]
            ]
            if is_admin(user_id):
                keyboard.append([InlineKeyboardButton(f"❌ O'chirish", callback_data=f"{CONFIRM_DELETE}:{restaurant_name}")])
            keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data=VIEW_RESTAURANTS)])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(restaurant_info, reply_markup=reply_markup, parse_mode="Markdown")
        else:
            await query.edit_message_text("Bunday restoran topilmadi.")
        return SELECTING_ACTION
    
    elif query.data == RECOMMEND_RESTAURANTS:
        restaurants = load_restaurant_data()
        if not restaurants:
            keyboard = [[InlineKeyboardButton("🔙 Orqaga", callback_data=CANCEL)]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("Hech qanday restoran topilmadi.", reply_markup=reply_markup)
            return SELECTING_ACTION
        
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
        reply_markup = get_main_menu_keyboard(user_id)
        await query.edit_message_text(
            "Asosiy menyu:\nQuyidagi amallardan birini tanlang:",
            reply_markup=reply_markup
        )
        return SELECTING_ACTION
    
    elif query.data == DELETE_RESTAURANT:
        if not is_admin(user_id):
            await query.edit_message_text("Sizda restoran o'chirish huquqi yo'q!")
            return SELECTING_ACTION
        restaurants = load_restaurant_data()
        if not restaurants:
            keyboard = [[InlineKeyboardButton("🔙 Orqaga", callback_data=CANCEL)]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("Hech qanday restoran topilmadi.", reply_markup=reply_markup)
            return SELECTING_ACTION
        
        keyboard = []
        for name in restaurants.keys():
            keyboard.append([InlineKeyboardButton(f"❌ {name}", callback_data=f"{CONFIRM_DELETE}:{name}")])
        keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data=CANCEL)])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text("O'chirmoqchi bo'lgan restoraningizni tanlang:", reply_markup=reply_markup)
        return SELECTING_ACTION
    
    elif query.data.startswith(CONFIRM_DELETE):
        if not is_admin(user_id):
            await query.edit_message_text("Sizda restoran o'chirish huquqi yo'q!")
            return SELECTING_ACTION
        restaurant_name = query.data.split(":", 1)[1]
        restaurants = load_restaurant_data()
        if restaurant_name in restaurants:
            del restaurants[restaurant_name]
            save_restaurant_data(restaurants)
            await query.edit_message_text(f"'{restaurant_name}' restoran muvaffaqiyatli o'chirildi!")
        else:
            await query.edit_message_text("Bunday restoran topilmadi.")
        
        reply_markup = get_main_menu_keyboard(user_id)
        await query.edit_message_text(
            "Restoran o'chirildi. Asosiy menyuga qaytish uchun tugmani bosing.",
            reply_markup=reply_markup
        )
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
        
        reply_markup = get_main_menu_keyboard(user_id)
        await query.edit_message_text(
            "Restoran baholandi. Asosiy menyuga qaytish uchun tugmani bosing.",
            reply_markup=reply_markup
        )
        return SELECTING_ACTION
    
    return SELECTING_ACTION

# Handle restaurant name input
async def add_restaurant_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Sizda restoran qo'shish huquqi yo'q!")
        return SELECTING_ACTION
    context.user_data["restaurant_name"] = update.message.text
    await update.message.reply_text("Endi restoran joylashuvini (manzilini) kiriting:")
    return ADDING_LOCATION

# Handle restaurant location input
async def add_restaurant_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Sizda restoran qo'shish huquqi yo'q!")
        return SELECTING_ACTION
    name = context.user_data["restaurant_name"]
    location = update.message.text
    
    restaurants = load_restaurant_data()
    restaurants[name] = {"location": location}
    save_restaurant_data(restaurants)
    
    reply_markup = get_main_menu_keyboard(update.effective_user.id)
    
    await update.message.reply_text(
        f"Restoran muvaffaqiyatli qo'shildi!\n\n"
        f"📝 Nomi: {name}\n"
        f"📍 Manzil: {location}",
        reply_markup=reply_markup
    )
    
    return SELECTING_ACTION

# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a message to the user if possible."""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    
    # Check if update and effective_message exist before replying
    if update and hasattr(update, 'effective_message') and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "Xatolik yuz berdi. Iltimos qaytadan urinib ko'ring."
            )
        except Exception as e:
            logger.error(f"Failed to send error message: {e}")
    else:
        logger.warning("Cannot send error message: No effective message available")

def main() -> None:
    """Start the bot."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("No token provided. Set TELEGRAM_BOT_TOKEN environment variable.")
        return
    
    application = Application.builder().token(token).build()

    # Delete webhook before starting polling
    try:
        application.bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhook deleted successfully")
    except Exception as e:
        logger.error(f"Failed to delete webhook: {e}")

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("admin", admin_panel),
        ],
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
        fallbacks=[
            CommandHandler("start", start),
            CommandHandler("stop", stop),
            CommandHandler("help", help_command),
        ],
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("help", help_command))
    application.add_error_handler(error_handler)

    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
    except Exception as e:
        logger.error(f"Failed to start polling: {e}")
        raise

if __name__ == "__main__":
    main()
