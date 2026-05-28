import os
from dotenv import load_dotenv
import time
import httpx
from io import BytesIO
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command, CommandObject
import asyncio
import datetime

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("API_KEY")
ALLOWED_USERS = set(int(u) for u in os.getenv("ALLOWED_USERS", "").split(",") if u.strip())
FASTAPI_URL = "http://127.0.0.1:8000"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# In-memory Rate Limit DB (user_id -> timestamp)
rate_limit_db = {}

# --- Middleware-like Checks ---
def is_authorized(user_id: int) -> bool:
    return user_id in ALLOWED_USERS

def check_rate_limit(user_id: int) -> bool:
    now = time.time()
    if user_id in rate_limit_db:
        if now - rate_limit_db[user_id] < 5:
            return False
    rate_limit_db[user_id] = now
    return True

# --- Handlers ---
@dp.message(Command("start", "help"))
async def send_welcome(message: Message):
    if not is_authorized(message.from_user.id):
        return await message.reply("❌ Unauthorized")
    
    await message.reply(
        "🧾 **Ledgergram Bot** \n\n"
        "Send me an image or document (uncompressed) of a receipt, and I will extract the details.\n"
        "Commands:\n"
        "/summary - View total income/expenses."
    )

@dp.message(Command("summary"))
async def get_summary_handler(message: Message):
    if not is_authorized(message.from_user.id):
        return await message.reply("❌ Unauthorized")
    
    from api.db import get_summary
    
    summary = get_summary()
    if not summary:
        return await message.reply("No transactions found.")
        
    total_income = 0.0
    total_expense = 0.0
    
    text = "📊 **Transaction Summary:**\n\n"
    
    # Parse the database results
    for row in summary:
        tx_type = row[0].lower()
        amount = row[1]
        
        if tx_type == 'income':
            total_income = amount
        elif tx_type == 'expense':
            total_expense = amount
            
        # Added "Rp " before the formatted amount
        text += f"🔹 **{tx_type.capitalize()}**: Rp {amount:,.2f}\n"
    
    # Calculate the net balance
    current_money = total_income - total_expense
    
    # Choose emoji based on positive or negative balance
    balance_emoji = "🟢" if current_money >= 0 else "🔴"
    
    text += "➖➖➖➖➖➖➖➖➖➖\n"
    # Added "Rp " before the formatted balance
    text += f"{balance_emoji} **Current Balance**: Rp {current_money:,.2f}"
    
    await message.reply(text, parse_mode="Markdown")

@dp.message(Command("add"))
async def add_manual_transaction(message: Message, command: CommandObject):
    user_id = message.from_user.id
    if not is_authorized(user_id):
        return await message.reply("❌ Unauthorized")

    # Check if the user actually typed arguments after /add
    if not command.args:
        return await message.reply(
            "⚠️ **Usage:** `/add <amount> <income/expense> <merchant>`\n"
            "**Example:** `/add 50000 expense Starbucks`",
            parse_mode="Markdown"
        )

    # Split the text into exactly 3 parts: amount, type, and the rest becomes the merchant
    args = command.args.split(maxsplit=2)
    if len(args) < 3:
        return await message.reply("❌ Missing details. Please provide amount, type, and merchant.")

    amount_str, tx_type, merchant = args
    tx_type = tx_type.lower()

    # Validate the data
    try:
        amount = float(amount_str)
    except ValueError:
        return await message.reply("❌ Amount must be a number.")

    if tx_type not in ['income', 'expense']:
        return await message.reply("❌ Type must be exactly 'income' or 'expense'.")

    # Save directly to the database
    from api.db import save_transaction
    today = datetime.datetime.now().strftime("%d/%m/%Y")

    try:
        save_transaction(
            amount=amount,
            tx_type=tx_type,
            merchant=merchant,
            date=today,
            raw_text="MANUAL ENTRY"
        )
        
        await message.reply(
            "✅ **Manual Entry Saved**\n"
            f"🏬 Merchant: {merchant}\n"
            f"📅 Date: {today}\n"
            f"💰 Amount: {amount}\n"
            f"📂 Type: {tx_type.capitalize()}"
        )
    except Exception as e:
        await message.reply(f"❌ Database Error: {e}")

@dp.message(F.photo | F.document)
async def handle_receipt(message: Message):
    user_id = message.from_user.id
    
    if not is_authorized(user_id):
        return await message.reply("❌ Unauthorized")
    
    if not check_rate_limit(user_id):
        return await message.reply("⏳ Please wait 5 seconds between requests.")

    processing_msg = await message.reply("⚙️ Processing image...")

    # Download original file
    try:
        if message.photo:
            file_id = message.photo[-1].file_id # Highest resolution
        else:
            if not message.document.mime_type.startswith('image/'):
                return await processing_msg.edit_text("❌ Please send an image file.")
            file_id = message.document.file_id

        file_info = await bot.get_file(file_id)
        file_bytes_io = BytesIO()
        await bot.download_file(file_info.file_path, file_bytes_io)
        file_bytes = file_bytes_io.getvalue()
        
        # Send to FastAPI Microservice
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{FASTAPI_URL}/ocr",
                headers={"X-API-KEY": API_KEY},
                files={"file": ("receipt.jpg", file_bytes, "image/jpeg")},
                timeout=20.0
            )
            
            if response.status_code != 200:
                return await processing_msg.edit_text(f"❌ API Error: {response.text}")
                
            result = response.json()
            data = result["data"]
            
            fallback_warning = "\n*(⚠️ Tesseract Fallback Used)*" if result["used_fallback"] else ""
            
            reply_text = (
                "✅ **Receipt Processed**\n"
                f"🏬 Merchant: {data['merchant']}\n"
                f"📅 Date: {data['date']}\n"
                f"💰 Total: {data['total']}\n"
                f"📂 Type: {data['type'].capitalize()}"
                f"{fallback_warning}"
            )
            
            await processing_msg.edit_text(reply_text, parse_mode="Markdown")
            
    except Exception as e:
        await processing_msg.edit_text(f"❌ Error processing file: {str(e)}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())