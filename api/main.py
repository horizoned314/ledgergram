import os
from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, Header, HTTPException
from api.ocr import perform_ocr
from api.parser import parse_receipt_text
from api.db import init_db, save_transaction

app = FastAPI()

load_dotenv()

API_KEY = os.getenv("API_KEY")

@app.on_event("startup")
def startup_event():
    init_db()

def verify_api_key(x_api_key: str = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Unauthorized API Key")

@app.post("/ocr")
async def process_receipt(file: UploadFile = File(...), x_api_key: str = Header(None)):
    verify_api_key(x_api_key)
    
    image_bytes = await file.read()
    
    # 1. OCR Extraction
    raw_text, used_fallback = await perform_ocr(image_bytes)
    
    if not raw_text:
        raise HTTPException(status_code=400, detail="Could not extract text from image.")

    # 2. Parsing
    parsed_data = parse_receipt_text(raw_text)

    # 3. Database Storage
    tx_id = save_transaction(
        amount=parsed_data["total"],
        tx_type=parsed_data["type"],
        merchant=parsed_data["merchant"],
        date=parsed_data["date"],
        raw_text=raw_text
    )

    return {
        "id": tx_id,
        "used_fallback": used_fallback,
        "data": parsed_data
    }