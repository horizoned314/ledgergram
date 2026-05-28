#!/bin/bash
# Start FastAPI backend in the background
uvicorn api.main:app --host 127.0.0.1 --port 8000 --workers 1 &

# Wait a few seconds for the API to boot
sleep 3

# Start the aiogram Bot in the foreground
python -m bot.bot