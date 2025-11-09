import os
import asyncio
from typing import Optional, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from dotenv import load_dotenv

from db import SessionLocal, init_db, User, Message, Room, RoomMember
from auth import get_password_hash, verify_password, create_access_token, get_current_user_token
from websocket_manager import ConnectionManager
from llm import chat_completion, check_tinyllama_available

load_dotenv()

APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8000"))
GROCERY_CSV_PATH = os.getenv("GROCERY_CSV_PATH", "./GroceryDataset.csv")
CSV_HEADERS = ["Sub Category", " Price ", "Rating", "Title"]

app = FastAPI(title="Group Chat with LLM Bot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

manager = ConnectionManager()

# Global progress tracking
download_progress = {
    "status": "idle",  # idle, downloading, completed, failed
    "progress": 0,     # 0-100
    "message": ""
}

# --------- Schemas ---------
class AuthPayload(BaseModel):
    username: str
    password: str

class MessagePayload(BaseModel):
    content: str

class RoomPayload(BaseModel):
    name: str

class InvitePayload(BaseModel):
    username: str

# --------- Dependencies ---------
async def get_db() -> AsyncSession:
    async with SessionLocal() as session:
        yield session

# --------- Utilities ---------
async def broadcast_message(session: AsyncSession, msg: Message, room_id: int):
    """Broadcast a message to all WebSocket clients connected to a room"""
    username = None
    if msg.user_id:
        u = await session.get(User, msg.user_id)
        username = u.username if u else "unknown"
    await manager.broadcast({
        "type": "message",
        "room_id": room_id,
        "message": {
            "id": msg.id,
            "username": username if not msg.is_bot else "LLM Bot",
            "content": msg.content,
            "is_bot": msg.is_bot,
            "created_at": str(msg.created_at)
        }
    }, room_id)

async def maybe_answer_with_llm(content: str, room_id: int, user_id: int):
    """Generate an LLM response if message mentions @gro"""
    if "@gro" not in content:
        return
    # Remove @gro tag from content before sending to LLM
    llm_content = content.replace("@gro", "").strip()
    system_prompt = (
        "You are a helpful assistant participating in a small group chat. "
        "Provide concise, accurate answers suitable for a shared chat context. "
        "Cite facts succinctly when helpful and avoid extremely long messages."
    )
    
    # Get user's preferred LLM model
    async with SessionLocal() as temp_session:
        user = await temp_session.get(User, user_id)
        if user and user.preferred_llm_model:
            model_name = user.preferred_llm_model
        else:
            model_name = "gemini"
    
    try:
        reply_text = await chat_completion([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": llm_content}
        ], model_name=model_name)
    except Exception as e:
        reply_text = f"(LLM error) {e}"
    
    # Create new session for this async task
    async with SessionLocal() as session:
        bot_msg = Message(room_id=room_id, user_id=None, content=reply_text, is_bot=True)
        session.add(bot_msg)
        await session.commit()
        await session.refresh(bot_msg)
        await broadcast_message(session, bot_msg, room_id)

# --------- Routes ---------
@app.on_event("startup")
async def on_startup():
    await init_db()

@app.post("/api/signup")
async def signup(payload: AuthPayload, session: AsyncSession = Depends(get_db)):
    """Create a new user"""
    existing = await session.execute(select(User).where(User.username == payload.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already taken")
    
    u = User(
        username=payload.username, 
        password_hash=get_password_hash(payload.password),
        preferred_llm_model="openai"  # Set default to OpenAI for reliability
    )
    session.add(u)
    await session.commit()
    await session.refresh(u)
    
    token = create_access_token({"sub": u.username})
    return {"ok": True, "token": token}

@app.post("/api/login")
async def login(payload: AuthPayload, session: AsyncSession = Depends(get_db)):
    """Login and return authentication token"""
    res = await session.execute(select(User).where(User.username == payload.username))
    u = res.scalar_one_or_none()
    if not u or not verify_password(payload.password, u.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": u.username})
    return {"ok": True, "token": token}

@app.get("/api/rooms")
async def get_rooms(username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db)):
    """Get all rooms that the user is a member of"""
    res = await session.execute(select(User).where(User.username == username))
    u = res.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=401, detail="Invalid user")
    
    # Get all rooms this user is a member of
    member_res = await session.execute(
        select(Room).join(RoomMember).where(RoomMember.user_id == u.id)
    )
    rooms = member_res.scalars().all()
    return {
        "rooms": [{"id": r.id, "name": r.name, "created_at": str(r.created_at)} for r in rooms]
    }

@app.post("/api/rooms")
async def create_room(payload: RoomPayload, username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db)):
    """Create a new room"""
    res = await session.execute(select(User).where(User.username == username))
    u = res.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=401, detail="Invalid user")
    
    # Check if room name already exists
    existing = await session.execute(select(Room).where(Room.name == payload.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Room name already taken")
    
    # Create room
    room = Room(name=payload.name, owner_id=u.id)
    session.add(room)
    await session.commit()
    await session.refresh(room)
    
    # Add creator to room
    member = RoomMember(room_id=room.id, user_id=u.id)
    session.add(member)
    await session.commit()
    
    return {"ok": True, "room": {"id": room.id, "name": room.name}}

@app.get("/api/rooms/{room_id}/members")
async def get_room_members(room_id: int, session: AsyncSession = Depends(get_db)):
    """Get members of a room"""
    room = await session.get(Room, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    members_res = await session.execute(
        select(User).join(RoomMember).where(RoomMember.room_id == room_id)
    )
    members = members_res.scalars().all()
    return {
        "members": [{"id": m.id, "username": m.username} for m in members]
    }

@app.post("/api/rooms/{room_id}/invite")
async def invite_to_room(room_id: int, payload: InvitePayload, username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db)):
    """Invite a user to a room"""
    # Check if invoker is room owner
    room = await session.get(Room, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    res = await session.execute(select(User).where(User.username == username))
    u = res.scalar_one_or_none()
    if not u or room.owner_id != u.id:
        raise HTTPException(status_code=403, detail="Only room owner can invite")
    
    # Get user to invite
    invite_res = await session.execute(select(User).where(User.username == payload.username))
    invite_user = invite_res.scalar_one_or_none()
    if not invite_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if already member
    member_check = await session.execute(
        select(RoomMember).where(
            (RoomMember.room_id == room_id) & 
            (RoomMember.user_id == invite_user.id)
        )
    )
    if member_check.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User already in room")
    
    # Add user to room
    member = RoomMember(room_id=room_id, user_id=invite_user.id)
    session.add(member)
    await session.commit()
    
    return {"ok": True, "message": f"User {payload.username} added to room"}

@app.get("/api/rooms/{room_id}/messages")
async def get_room_messages(room_id: int, limit: int = 50, session: AsyncSession = Depends(get_db)):
    """Get messages from a specific room"""
    room = await session.get(Room, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    res = await session.execute(
        select(Message)
        .where(Message.room_id == room_id)
        .order_by(desc(Message.created_at))
        .limit(limit)
    )
    items = list(reversed(res.scalars().all()))
    out = []
    for m in items:
        username = None
        if not m.is_bot and m.user_id:
            u = await session.get(User, m.user_id)
            username = u.username if u else "unknown"
        out.append({
            "id": m.id,
            "username": "LLM Bot" if m.is_bot else (username or "unknown"),
            "content": m.content,
            "is_bot": m.is_bot,
            "created_at": str(m.created_at)
        })
    return {"messages": out}

@app.post("/api/rooms/{room_id}/messages")
async def post_room_message(room_id: int, payload: MessagePayload, username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db)):
    """Post a message to a specific room"""
    try:
        # Check if room exists
        room = await session.get(Room, room_id)
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
        
        # Get user
        res = await session.execute(select(User).where(User.username == username))
        u = res.scalar_one_or_none()
        if not u:
            raise HTTPException(status_code=401, detail="Invalid user")
        
        # Check if user is member of room
        member_check = await session.execute(
            select(RoomMember).where(
                (RoomMember.room_id == room_id) & 
                (RoomMember.user_id == u.id)
            )
        )
        if not member_check.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Not a member of this room")
        
        # Create message
        m = Message(room_id=room_id, user_id=u.id, content=payload.content, is_bot=False)
        session.add(m)
        await session.commit()
        await session.refresh(m)
        
        await broadcast_message(session, m, room_id)
        asyncio.create_task(maybe_answer_with_llm(payload.content, room_id, u.id))
        
        return {"ok": True, "id": m.id}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in post_room_message: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/users/llm-model")
async def update_llm_model(payload: dict, username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db)):
    """Update user's preferred LLM model"""
    model_name = payload.get("model")
    if not model_name:
        raise HTTPException(status_code=400, detail="model is required")
    
    # Validate if model exists
    valid_models = ["tinyllama", "openai", "gemini"]
    if model_name not in valid_models:
        raise HTTPException(status_code=400, detail=f"Invalid model. Choose from: {valid_models}")
    
    # If tinyllama is selected, check if it's downloaded
    if model_name == "tinyllama":
        tinyllama_available = await check_tinyllama_available()
        if not tinyllama_available:
            raise HTTPException(
                status_code=400, 
                detail="tinyllama model not found. Please download it first with: /opt/homebrew/bin/ollama pull tinyllama"
            )
    
    # If gemini is selected, check if API key is set
    if model_name == "gemini":
        gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not gemini_api_key:
            raise HTTPException(
                status_code=400, 
                detail="gemini model not available. Please set GEMINI_API_KEY in backend env"
            )
    
    # Get user and update model preference
    res = await session.execute(select(User).where(User.username == username))
    u = res.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=401, detail="Invalid user")
    
    u.preferred_llm_model = model_name
    session.add(u)
    await session.commit()
    
    return {"ok": True, "model": model_name}

@app.get("/api/models/download-progress")
async def get_download_progress(username: str = Depends(get_current_user_token)):
    """Get current download progress"""
    return download_progress

@app.get("/api/users/llm-model")
async def get_llm_model(username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db), platform: str = "desktop"):
    """Get user's preferred LLM model and check availability
    
    platform: 'ios', 'android', 'web', or 'desktop' (default)
    - iOS/Android: only return openai (no local LLM support)
    - Web/Desktop: return both tinyllama and openai (if Ollama available)
    """
    res = await session.execute(select(User).where(User.username == username))
    u = res.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=401, detail="Invalid user")
    
    # Determine available models based on platform
    is_mobile = platform.lower() in ["ios", "android"]
    
    if is_mobile:
        # iOS/Android support OpenAI and Gemini
        available_models = ["openai"]
        tinyllama_available = False
        # Gemini availability based on environment/config
        gemini_available = bool(os.getenv("GEMINI_API_KEY"))
        if gemini_available:
            available_models.append("gemini")
        # If user preference is tinyllama, change to openai
        current_model = "openai" if u.preferred_llm_model == "tinyllama" else u.preferred_llm_model
    else:
        # Desktop/Web support tinyllama, openai and Gemini
        available_models = ["tinyllama", "openai"]
        tinyllama_available = await check_tinyllama_available()
        # Gemini availability based on environment/config
        gemini_available = bool(os.getenv("GEMINI_API_KEY"))
        if gemini_available:
            available_models.append("gemini")
        current_model = u.preferred_llm_model
    
    return {
        "model": current_model,
        "available_models": available_models,
        "tinyllama_available": tinyllama_available,
        "tinyllama_download_command": "/opt/homebrew/bin/ollama pull tinyllama",
        "gemini_available": gemini_available if 'gemini_available' in locals() else False,
        "gemini_instructions": "Set GEMINI_API_KEY and GEMINI_MODEL in backend env to enable Gemini",
        "platform": platform
    }

@app.post("/api/models/download-tinyllama")
async def download_tinyllama(username: str = Depends(get_current_user_token)):
    """Trigger tinyllama model download with progress tracking"""
    import subprocess
    import platform
    
    try:
        # Check if already downloaded
        tinyllama_available = await check_tinyllama_available()
        if tinyllama_available:
            download_progress["status"] = "completed"
            download_progress["progress"] = 100
            download_progress["message"] = "TinyLlama is already downloaded"
            return {
                "ok": True,
                "message": "TinyLlama is already downloaded",
                "status": "already_installed"
            }
        
        # If download is already in progress, return current status
        if download_progress["status"] == "downloading":
            return {
                "ok": True,
                "message": "Download already in progress",
                "status": "downloading"
            }
        
        # Find the location of ollama command
        ollama_cmd = None
        
        # Try direct execution
        try:
            subprocess.run(["ollama", "--version"], capture_output=True, check=True)
            ollama_cmd = "ollama"
        except Exception:
            pass
        
        # Try macOS Homebrew path
        if not ollama_cmd and platform.system() == "Darwin":
            try:
                subprocess.run(["/opt/homebrew/bin/ollama", "--version"], capture_output=True, check=True)
                ollama_cmd = "/opt/homebrew/bin/ollama"
            except Exception:
                pass
        
        if not ollama_cmd:
            raise HTTPException(
                status_code=400,
                detail="Ollama not found. Please install Ollama first: https://ollama.ai"
            )
        
        # Set download status to in progress
        download_progress["status"] = "downloading"
        download_progress["progress"] = 0
        download_progress["message"] = "Starting download..."
        
        # Run download in background task
        asyncio.create_task(run_download_task(ollama_cmd))
        
        return {
            "ok": True,
            "message": "TinyLlama download started",
            "status": "downloading"
        }
    
    except Exception as e:
        download_progress["status"] = "failed"
        download_progress["message"] = str(e)
        print(f"Error starting download: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start download: {str(e)}"
        )

async def run_download_task(ollama_cmd: str):
    """Background task: Run download and update progress"""
    import subprocess
    
    try:
        # Execute ollama pull tinyllama-1.1b-chat-v1.0.Q4_K_M
        process = subprocess.Popen(
            [ollama_cmd, "pull", "tinyllama-1.1b-chat-v1.0.Q4_K_M"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        # Simulate progress update (actual ollama output will tell us progress)
        download_progress["progress"] = 10
        download_progress["message"] = "Downloading model layers..."
        
        for line in process.stdout:
            line = line.strip()
            if line:
                download_progress["message"] = line
                
                # Update progress based on output
                if "pulling" in line.lower():
                    # Try to extract percentage from output
                    if "%" in line:
                        try:
                            percent = int(''.join(filter(str.isdigit, line.split('%')[0].split()[-1])))
                            download_progress["progress"] = min(percent, 95)
                        except:
                            pass
        
        # Wait for process to complete
        process.wait()
        
        if process.returncode == 0:
            # Verify download successful
            await asyncio.sleep(1)
            tinyllama_available = await check_tinyllama_available()
            
            if tinyllama_available:
                download_progress["status"] = "completed"
                download_progress["progress"] = 100
                download_progress["message"] = "TinyLlama downloaded successfully!"
                print("TinyLlama download completed successfully")
            else:
                download_progress["status"] = "failed"
                download_progress["message"] = "Download completed but model not found"
        else:
            download_progress["status"] = "failed"
            download_progress["message"] = f"Download failed with return code {process.returncode}"
            
    except Exception as e:
        download_progress["status"] = "failed"
        download_progress["message"] = f"Error: {str(e)}"
        print(f"Download task error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error: {str(e)}"
        )

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint that groups connections by room_id"""
    # Extract room_id from query parameters
    room_id_str = websocket.query_params.get("room_id")
    if not room_id_str:
        await websocket.close(code=1008, reason="room_id required")
        return
    
    try:
        room_id = int(room_id_str)
    except ValueError:
        await websocket.close(code=1008, reason="room_id must be integer")
        return
    
    try:
        await manager.connect(websocket, room_id)
        try:
            while True:
                await websocket.receive_text()
        except Exception as e:
            print(f"WebSocket error: {e}")
    finally:
        manager.disconnect(websocket, room_id)

# Frontend is now served via Flutter (flutter_frontend/)
# This FastAPI backend only provides REST API and WebSocket endpoints
# No need to serve static files here
