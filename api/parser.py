import re

def parse_receipt_text(text: str) -> dict:
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    # 1. Merchant: Assume first non-empty line
    merchant = lines[0] if lines else "Unknown"

    # 2. Total: Scan from bottom-up for robustness against item prices
    total = 0.0
    # Regex looks for Total, Jumlah, or Rp followed by digits (ignoring punctuation inside digits)
    total_pattern = r'(?i)(?:total|jumlah|amount|rp)\s*[:=-]?\s*(?:rp\.?)?\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?|\d+)'
    
    for line in reversed(lines):
        match = re.search(total_pattern, line)
        if match:
            raw_num = match.group(1)
            # Normalize digits (remove all non-numeric chars except last punctuation if it's a decimal separator)
            clean_num = re.sub(r'[^\d]', '', raw_num)
            if clean_num:
                total = float(clean_num)
                break

    # 3. Date: DD/MM/YYYY or YYYY-MM-DD
    date_str = "Unknown"
    date_pattern = r'\b(\d{2}[-/.]\d{2}[-/.]\d{2,4}|\d{4}[-/.]\d{2}[-/.]\d{2})\b'
    for line in lines:
        match = re.search(date_pattern, line)
        if match:
            date_str = match.group(1)
            break

    # 4. Type: Simple keyword classification
    text_lower = text.lower()
    tx_type = 'income' if any(word in text_lower for word in ['refund', 'income', 'deposit']) else 'expense'

    return {
        "merchant": merchant,
        "total": total,
        "date": date_str,
        "type": tx_type
    }