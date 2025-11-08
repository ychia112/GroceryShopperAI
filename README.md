# Group Chat Web App + LLM Bot

FastAPI + MySQL + vanilla HTML/JS group chat with LLM bot (OpenAI-compatible server such as self-hosted Llama 3 via llama.cpp).

## Quick Start (Dev)

```bash
# 1) MySQL
# create DB & user, or run sql/schema.sql

# 2) Backend
cd backend
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# copy env and edit values
cp ../.env.example ../.env

# 3) Run app
uvicorn app:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000

## LLM Model Configuration

LLM endpoint defaults to http://localhost:8001/v1 (llama.cpp server). Set `LLM_API_BASE`, `LLM_MODEL`, `LLM_API_KEY` if needed in `.env`.

We have switched the model from a local Llama server to OpenAI’s gpt-4o-mini for better performance and reliability.

The following is the .env template used for configuration:
```bash
# .env template
DATABASE_URL=mysql+asyncmy://chatuser:chatpass@localhost:3306/groupchat
JWT_SECRET=replace-with-a-long-random-string-here-make-it-very-long-and-secure
JWT_EXPIRE_MINUTES=43200
# OpenAI API endpoint
LLM_API_BASE=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
LLM_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx(YOUR OpenAI API KEY)
APP_HOST=0.0.0.0
APP_PORT=8000

# For local llama.cpp
# LLM_API_BASE=http://localhost:8001/v1
# LLM_MODEL=tinyllama-1.1b-chat-v1.0.Q4_K_M
# LLM_API_KEY=
```
