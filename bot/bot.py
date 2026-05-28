import os
import time
import httpx
from io import BytesIO
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command
import asyncio

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
        "🧾 **Receipt OCR Bot**\n\n"
        "Send me an image or document (uncompressed) of a receipt, and I will extract the details.\n"
        "Commands:\n"
        "/summary - View total income/expenses."
    )

@dp.message(Command("summary"))
async def get_summary_handler(message: Message):
    if not is_authorized(message.from_user.id):
        return await message.reply("❌ Unauthorized")
    
    # We query SQLite via a quick internal call (or we could expose an endpoint)
    # For speed and single-container architecture, querying the db module directly is acceptable here
    from api.db import get_summary
    
    summary = get_summary()
    if not summary:
        return await message.reply("No transactions found.")
        
    text = "📊 **Transaction Summary:**\n"
    for row in summary:
        text += f"- {row[0].capitalize()}: {row[1]:.2f}\n"
    
    await message.reply(text)

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