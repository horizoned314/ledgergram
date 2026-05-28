# Ledgergram (receipt OCR telegram bot) 🧾

A lightweight, asynchronous Telegram bot and microservice for extracting information from receipts. Designed to run comfortably in environments with `<= 1GB RAM`.

## 🛠 Features
- **OCR Engine:** Primary extraction via `OCR.space API`, with an automated lightweight fallback to `Tesseract`.
- **Regex Parsing:** Deterministic, non-ML extraction of Merchant, Date, Total, and Transaction Type.
- **Microservice Arch:** Separation of concerns. Bot communicates with a FastAPI backend securely via local routing and `X-API-KEY`.
- **Security:** In-memory Rate Limiting (1 req/5sec), Hardcoded Telegram UID Whitelisting.

## 🚀 Deployment

1. **Clone & Configure:**
   ```bash
   cp .env.example .env
   # Edit .env with your tokens and comma-separated Telegram User IDs