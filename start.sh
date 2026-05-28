#!/bin/bash

# Start FastAPI backend in the background (&)
uvicorn api.main:app --host 0.0.0.0 --port 8000 &

# Wait a few seconds for the API to boot up securely
sleep 3

# Start the aiogram Bot in the foreground
python -m bot.bot