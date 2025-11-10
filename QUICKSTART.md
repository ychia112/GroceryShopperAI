# GroceryShopperAI - Quick Start Guide

Get the entire application running in 5 simple steps.

---

## Prerequisites

- macOS with Homebrew (or equivalent on your OS)
- Python 3.11+
- MySQL 8.0+
- Flutter SDK 3.x (for mobile/web frontend)
- Git

---

## Step 1: Clone & Navigate

```bash
cd /Users/ychia/GroceryShopperAI
# or your project directory
```

---

## Step 2: Setup Database (2 minutes)

```bash
# Create database and user
mysql -u root -p < sql/schema.sql

# When prompted, enter your MySQL root password
```

**That's it!** Database, tables, and user are now created.

---

## Step 3: Setup Backend (3 minutes)

```bash
# Create Python environment
conda create -n groceryai python=3.11 -y
conda activate groceryai

# Install dependencies
pip install -r requirements.txt

# Create .env file
nano .env
```

### Edit .env and add your API keys (optional):

```.env``` template:

```bash
# Database Configuration
DATABASE_URL=mysql+asyncmy://chatuser:password@localhost/groceryshopperai

# OpenAI Configuration (for gpt-4o-mini)
LLM_API_BASE=https://api.openai.com/v1 
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=your_openai_api_key_here

# Google Gemini Configuration (Optional - for free Gemini model)
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=models/gemini-2.5-flash

# LLM Model Configuration
LLM_MODEL=tinyllama
# Options: tinyllama (local), openai (requires OPENAI_API_KEY), gemini (requires GEMINI_API_KEY)
```

---

## Step 4: Start Backend

**Terminal 1: Backend Server**

```bash
cd backend
conda activate groceryai
python -m uvicorn app:app --host 0.0.0.0 --port 8000
```

Expected output:

```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

✅ Backend is ready at `http://localhost:8000`

---

## Step 5: Run Frontend

### Flutter Installation
Set up Flutter quickly on macOS, Windows, or Linux (Ubuntu) with the easiest available methods.

#### Mac OS
```bash
brew install flutter
```

Verify Setup
```bash
flutter doctor
```

#### Linux / Ubuntu
```bash
sudo snap install flutter --classic
```

Verify Setup
```bash
flutter doctor
```

#### Windows
**1. Download Flutter SDK**

- Go to Flutter for Windows https://docs.flutter.dev/get-started
- Download the latest Stable Channel ZIP
- Extract it to:
```makefile
C:\src\flutter
```

**2. Add Flutter to PATH**

- Search “Edit the system environment variables” → Environment Variables...
- Add:
```makefile
C:\src\flutter\bin
```

Verify Setup
```bash
flutter doctor
```

---
Choose ONE of the following:

### Option A: iOS (macOS only)

**Terminal 2: Flutter iOS**

```bash
cd flutter_frontend
flutter pub get
flutter run -d "iPhone 14"
```

### Option B: Android

**Terminal 2: Flutter Android**

```bash
cd flutter_frontend
flutter pub get
flutter run
```

### Option C: Web

**Terminal 2: Flutter Web**

```bash
cd flutter_frontend
flutter pub get
flutter run -d chrome
```

---

## 🎉 Done!

You now have:

- ✅ MySQL database running
- ✅ FastAPI backend at http://localhost:8000
- ✅ Flutter app running on your device/emulator

### Test the app:

1. Open the app
2. **Sign up** with username & password
3. **Create a room** or join existing one
4. **Send a message** - type anything
5. **@gro** - mention the bot to get AI response

---

## Common Commands

```bash
# Stop backend (Ctrl+C)
# Stop Flutter app (q in terminal)

# Restart everything:
# Terminal 1: python -m uvicorn app:app --host 0.0.0.0 --port 8000
# Terminal 2: flutter run -d <device-id>

# List available devices
flutter devices

# Clean build (if issues)
flutter clean
flutter pub get
flutter run -d <device-id>
```

---

## API Endpoints (for reference)

- `POST /api/signup` - Create account
- `POST /api/login` - Login
- `GET /api/rooms` - List rooms
- `POST /api/rooms` - Create room
- `POST /api/rooms/{room_id}/messages` - Send message
- `WS /ws?room_id={room_id}` - WebSocket chat

---

## Troubleshooting

### Backend won't start on port 8000

```bash
# Check if port is in use
lsof -i :8000

# Kill the process
lsof -ti:8000 | xargs kill -9

# Restart
python -m uvicorn app:app --host 0.0.0.0 --port 8000
```

### MySQL connection error

```bash
# Check MySQL is running
mysql -u root -p -e "SELECT 1"

# Verify credentials in backend/.env match database setup
```

### Flutter build fails

```bash
cd flutter_frontend
flutter clean
flutter pub get
flutter run -d <device-id>
```

---

## Next Steps

- Read `README.md` for detailed documentation
- Check `sql/schema.sql` for database structure
- Explore `backend/app.py` for API implementation
- Review `flutter_frontend/lib/main.dart` for UI code

---

## Need Help?

Check these files:

- Backend logs: Terminal 1 output
- Flutter logs: Terminal 2 output
- Database: `mysql -u chatuser -p -e "SELECT * FROM users;"`
- Environment: `backend/.env` (make sure keys are set)

---

**Happy coding!** 🚀
