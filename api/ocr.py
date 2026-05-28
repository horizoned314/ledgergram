import os
import httpx
import pytesseract
from PIL import Image, ImageOps
import io

OCRSPACE_API_KEY = os.getenv("OCRSPACE_API_KEY")

async def perform_ocr(image_bytes: bytes) -> tuple[str, bool]:
    """Returns extracted text and a boolean indicating if fallback was used."""
    try:
        # Step 1: Attempt OCR.space API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.ocr.space/parse/image",
                data={
                    "apikey": OCRSPACE_API_KEY,
                    "language": "eng",
                    "isOverlayRequired": "false",
                    "OCREngine": "2" 
                },
                files={"file": ("receipt.jpg", image_bytes, "image/jpeg")},
                timeout=15.0
            )
            response.raise_for_status()
            data = response.json()
            
            if not data.get("IsErroredOnProcessing") and data.get("ParsedResults"):
                parsed_text = data["ParsedResults"][0].get("ParsedText", "").strip()
                if parsed_text:
                    return parsed_text, False
    except Exception as e:
        print(f"OCR.space failed: {e}. Switching to Tesseract fallback.")

    # Step 2: Fallback to pytesseract
    return _tesseract_fallback(image_bytes), True

def _tesseract_fallback(image_bytes: bytes) -> str:
    try:
        image = Image.open(io.BytesIO(image_bytes))
        # Lightweight preprocessing: Grayscale
        gray_image = ImageOps.grayscale(image)
        text = pytesseract.image_to_string(gray_image)
        return text.strip()
    except Exception as e:
        print(f"Tesseract fallback failed: {e}")
        return ""