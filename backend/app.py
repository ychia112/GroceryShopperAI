print("🔥 Running backend version: 2025-11-23 00:00")
import os
import json
import asyncio
from typing import Optional, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status, Request, Body
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from dotenv import load_dotenv
from google.cloud import storage

from db import SessionLocal, init_db, User, Message, Room, RoomMember, Inventory, GroceryItem, ShoppingList
from auth import get_password_hash, verify_password, create_access_token, get_current_user_token
from websocket_manager import ConnectionManager
from llm import chat_completion, AVAILABLE_MODELS

# LLM modules
from llm_modules.llm_utils import format_chat_history
from llm_modules.planner import generate_group_plan
from llm_modules.matcher import suggest_invites
from llm_modules.inventory_analyzer import analyze_inventory
from llm_modules.menu_generator import generate_menu
from llm_modules.procurement_planner import generate_restock_plan
from llm_modules.chat_procurement_planner import generate_procurement_plan
from vector.recommend_utils import get_relevant_grocery_items

load_dotenv()

APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8000"))
GROCERY_CSV_PATH = os.getenv("GROCERY_CSV_PATH", "./GroceryDataset.csv")
CSV_HEADERS = ["Sub Category", " Price ", "Rating", "Title"]

# ========= Embeddings Initialization (Cloud Run + GCS Auto Download) =========
LOCAL_EMBEDDINGS_PATH = "/tmp/embeddings.sqlite"
EMBEDDINGS_BUCKET = "groceryshopperai-embeddings"
EMBEDDINGS_BLOB = "embeddings.sqlite"

def download_embeddings_if_needed():
    """
    Checks if the embeddings database exists locally (in /tmp).
    If not, downloads it from Google Cloud Storage.
    Required for Cloud Run which has an ephemeral filesystem.
    """
    if os.path.exists(LOCAL_EMBEDDINGS_PATH):
        print(f"[Startup] Found existing embeddings database at {LOCAL_EMBEDDINGS_PATH}")
        return

    print(f"[Startup] Downloading {EMBEDDINGS_BLOB} from bucket {EMBEDDINGS_BUCKET}...")
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(EMBEDDINGS_BUCKET)
        blob = bucket.blob(EMBEDDINGS_BLOB)
        blob.download_to_filename(LOCAL_EMBEDDINGS_PATH)
        print(f"[Startup] Download complete: {LOCAL_EMBEDDINGS_PATH}")
    except Exception as e:
        print(f"[Startup] ❌ Failed to download embeddings: {e}")
        # Depending on your logic, you might want to raise e here to stop the container

# ---------------------------------------------


app = FastAPI(title="GroceryShopperAI Chat Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

manager = ConnectionManager()

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
    
class AIPlanPayload(BaseModel):
    goal: Optional[str] = None
    
class AIMatchingPayload(BaseModel):
    goal: Optional[str] = None

class InventoryItemPayload(BaseModel):
    product_name: str
    stock: int
    safety_stock_level: int

class ShoppingListPayload(BaseModel):
    title: str
    items_json: str # JSON string of items list

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
    
async def broadcast_ai_event(room_id: int, event_type: str, narrative: str, payload: dict):
    """
    Sends a strutured AI event to frontend for rendering custom UI.
    """
    await manager.broadcast({
        "type": "ai_event",
        "event": event_type,  # e.g. "inventory_analysis", "menu_suggestions", "restock_plan", "procurement_plan"
        "room_id": room_id,
        "narrative": narrative,
        "payload": payload,
    }, room_id)
    

async def handle_inventory_command(content: str, room_id: int, user_id: int):
    """
    Handle @inventory messages:
    - If only '@inventory' → send instructions
    - If '@inventory' plus lines → parse and upsert into Inventory table
    """
    # Strip the trigger word
    cleaned = content.replace("@inventory", "").strip()

    # Case 1: Just '@inventory' → explain the format
    if not cleaned:
        reply_text = (
            "Let's load your inventory.\n\n"
            "Reply with a message in the following format:\n"
            "@inventory\n"
            "product_name, stock_quantity, safety_stock_level\n\n"
            "Example:\n"
            "@inventory\n"
            "Tomatoes, 50, 20   <-- Tomatoes = product name, 50 = current stock, 20 = safety stock threshold\n"
            "Olive oil, 10, 3   <-- Olive oil = product name, 10 = current stock, 3 = safety stock threshold\n"
            "Cheese, 5, 2\n\n"
            "Make sure each item is on a separate line."
        )
        async with SessionLocal() as session:
            bot_msg = Message(
                room_id=room_id,
                user_id=None,
                content=reply_text,
                is_bot=True,
            )
            session.add(bot_msg)
            await session.commit()
            await session.refresh(bot_msg)
            await broadcast_message(session, bot_msg, room_id)
        return

    # Case 2: @inventory plus data lines
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    parsed_items = []
    errors = []

    for line in lines:
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != 3:
            errors.append(f"- '{line}' (expected: name, stock, safety_stock)")
            continue

        name, stock_str, safety_str = parts
        try:
            stock_val = int(stock_str)
            safety_val = int(safety_str)
        except ValueError:
            errors.append(f"- '{line}' (stock and safety_stock must be integers)")
            continue

        parsed_items.append((name, stock_val, safety_val))

    async with SessionLocal() as session:
        # Upsert per product for this user
        for name, stock_val, safety_val in parsed_items:
            res = await session.execute(
                select(Inventory).where(
                    (Inventory.user_id == user_id)
                    & (Inventory.product_name == name)
                )
            )
            inv = res.scalar_one_or_none()
            if inv:
                inv.stock = stock_val
                inv.safety_stock_level = safety_val
            else:
                inv = Inventory(
                    user_id=user_id,
                    product_name=name,
                    stock=stock_val,
                    safety_stock_level=safety_val,
                )
                session.add(inv)

        await session.commit()

        # Build confirmation message
        msg_lines = []
        if parsed_items:
            msg_lines.append(f"✅ Saved/updated {len(parsed_items)} inventory item(s).")
        if errors:
            msg_lines.append("⚠️ Some lines could not be processed:\n" + "\n".join(errors))

        reply_text = "\n".join(msg_lines) if msg_lines else "No valid inventory lines were found."

        bot_msg = Message(
            room_id=room_id,
            user_id=None,
            content=reply_text,
            is_bot=True,
        )
        session.add(bot_msg)
        await session.commit()
        await session.refresh(bot_msg)
        await broadcast_message(session, bot_msg, room_id)
        
# AI Commands: @gro analyze / menu / restock (inventory + catalog)   
async def handle_gro_command(kind: str, room_id: int, user_id: int):
    """
    kind: "analyze", "menu", restock"
    Use inventory + grocery catalog (if needed), embeddings, and LLM modules.
    """
    async with SessionLocal() as session:
        # get user model
        user = await session.get(User, user_id)
        model_name = user.preferred_llm_model if user else "openai"
        
        # Load chat history for this room
        msgs_res = await session.execute(
            select(Message)
            .where(Message.room_id == room_id)
            .order_by(Message.created_at)
        )
        msgs = msgs_res.scalars().all()
        
        chat_history = [
            {"role": "assistant" if m.is_bot else "user", "content": m.content}
            for m in msgs
        ]
        
        # Load inventory
        inv_res = await session.execute(
            select(Inventory).where(Inventory.user_id == user_id)
        )
        inventory_items = [
            {
                "product_name": row.product_name,
                "stock": row.stock,
                "safety_stock_level": row.safety_stock_level
            }
            for row in inv_res.scalars().all()
        ]

        # ---- Classify - Build low stock + healthy list ----
        low_stock_items = [
            item for item in inventory_items
            if item["stock"] < item["safety_stock_level"]
        ]
        healthy_items = [
            item for item in inventory_items
            if item["stock"] >= item["safety_stock_level"]
        ]
        
        # ---- Embedding matching (RAG Core) ----
        # Strategies:
        # 1. If it's "analyze" or "restock": similar items of "low_stock"
        # 2. If it's "menu": we need to know the real items that correspond to "healthy_items"
        # We do vector search for all invetory items.
        
        search_targets = []
        if kind == "menu":
            search_targets = inventory_items
        else:
            search_targets = low_stock_items
        
        grocery_items = []
        for item in search_targets:
            matches = await get_relevant_grocery_items(session, item["product_name"], limit=5)
            for m in matches:
                grocery_items.append({
                    "title": m.title,
                    "sub_category": m.sub_category,
                    "price": float(m.price),
                    "rating": m.rating_value or 0.0,
                })

        # remove duplicates by title
        seen = set()
        merged = []
        for g in grocery_items:
            if g["title"] not in seen:
                seen.add(g["title"])
                merged.append(g)
        
        
        # Run AI Module
        if kind == "analyze":
            ai_result = await analyze_inventory(
                inventory_items=inventory_items, 
                low_stock_items=low_stock_items, 
                healthy_items=healthy_items, 
                grocery_items=merged, 
                chat_history=chat_history,
                model_name=model_name,
            )
            event_type = "inventory_analysis"
            
        elif kind == "restock":
            ai_result = await generate_restock_plan(
                low_stock_items=low_stock_items, 
                grocery_items=merged, 
                model_name=model_name
            )
            event_type = "restock_plan"
            
        elif kind == "menu":
            ai_result = await generate_menu(
                inventory_items=inventory_items, 
                grocery_items=merged,
                chat_history=chat_history,
                model_name=model_name
            )
            event_type = "menu_suggestions"

        else:
            ai_result = {"narrative": "Unknown command.", "data": {}}
            event_type = "unknown"
            
        narrative = ai_result.get("narrative", "AI suggestion generated.")
        
        await broadcast_ai_event(room_id, event_type, narrative, ai_result)
        
        # Send a short chat message as well
        msg_text_map = {
            "inventory_analysis": "Generated inventory analysis for your current stock.",
            "menu_suggestions": "Generated menu suggestions based on your inventory and items from grocery store.",
            "restock_plan": "Generated a suggested restock plan.",
        }
        bot_msg_text = msg_text_map.get(event_type, "AI suggestion generated.")
        
        bot_msg = Message(
            room_id=room_id,
            user_id=None,
            content=bot_msg_text,
            is_bot=True,
        )
        session.add(bot_msg)
        await session.commit()
        await session.refresh(bot_msg)
        await broadcast_message(session, bot_msg, room_id)

# Router for @inventory / @gro commands / default LLM Chat
async def maybe_answer_with_llm(content: str, room_id: int, user_id: int):
    """
    Central logic:
    - If message contains @inventory → handle inventory command (no LLM call)
    - @gro analyze/menu/restock -> AI modules + ai_event
    - @gro plan -> chat-based procurement_plan + ai_event
    - If message is plain @gro → call LLM as before
    """
    if not content:
        return
    
    # 1) Inventory flow
    if "@inventory" in content.lower():
        await handle_inventory_command(content, room_id, user_id)
        # You can still allow @gro in the same message if you want,
        # but simplest is to return here:
        return
    
    # ==== AI Commands ====
    if "@gro analyze" in content.lower():
        await handle_gro_command("analyze", room_id, user_id)
        return
    
    if "@gro menu" in content.lower():
        await handle_gro_command("menu", room_id, user_id)
        return
    
    if "@gro restock" in content.lower():
        await handle_gro_command("restock", room_id, user_id)
        return
    
    if "@gro plan" in content.lower():
        async with SessionLocal() as session:
            user = await session.get(User, user_id)
            model_name = user.preferred_llm_model if user else "openai"
            
            msgs_res = await session.execute(
                select(Message)
                .where(Message.room_id == room_id)
                .order_by(Message.created_at)
            )
            msgs = msgs_res.scalars().all()
            chat_history = [
                {"role": "assistant" if m.is_bot else "user", "content": m.content}
                for m in msgs
            ]
        
        result = await generate_procurement_plan(chat_history=chat_history, model_name=model_name)
        
        narrative = result.get("narrative", "Here is your procurement plan.")
        await broadcast_ai_event(room_id, "procurement_plan", narrative, result)
        return
    

    # 2) Regular LLM flow with @gro
    if "@gro" not in content.lower():
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
        reply_text = await chat_completion(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": llm_content},
            ],
            model_name=model_name,
        )
    except Exception as e:
        reply_text = f"(LLM error) {e}"

    # Create new session for this async task
    async with SessionLocal() as session:
        bot_msg = Message(
            room_id=room_id,
            user_id=None,
            content=reply_text,
            is_bot=True,
        )
        session.add(bot_msg)
        await session.commit()
        await session.refresh(bot_msg)
        await broadcast_message(session, bot_msg, room_id)
    

# --------- Routes ---------
@app.on_event("startup")
async def on_startup():
    try:
        # Download the vector DB first
        download_embeddings_if_needed()
        
        await init_db()
        print("DB initialized successfully")
    except Exception as e:
        print(f"Startup failed: {e}")

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
    """Get all rooms that the user is a member of (excluding soft-deleted)"""
    try:
        print(f"[GetRooms] Fetching rooms for user: {username}")
        
        res = await session.execute(select(User).where(User.username == username))
        u = res.scalar_one_or_none()
        if not u:
            print(f"[GetRooms] User {username} not found")
            raise HTTPException(status_code=401, detail="Invalid user")
        
        print(f"[GetRooms] User {username} (id={u.id}) found")
        
        # Get all rooms this user is a member of and NOT deleted
        member_res = await session.execute(
            select(Room).join(RoomMember).where(
                (RoomMember.user_id == u.id) & (RoomMember.deleted_at == None)
            )
        )
        rooms = member_res.scalars().all()
        print(f"[GetRooms] Found {len(rooms)} active rooms for user {username}")
        
        return {
            "rooms": [{"id": r.id, "name": r.name, "created_at": str(r.created_at)} for r in rooms]
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[GetRooms] ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to fetch rooms: {str(e)}")

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

@app.delete("/api/rooms/{room_id}")
async def delete_room(room_id: int, username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db)):
    """
    Soft-delete a room for the current user
    - Marks the room as deleted for this user (deleted_at = now())
    - Room reappears if other users send messages
    - Room is permanently deleted if all members have deleted it
    """
    from datetime import datetime
    
    try:
        print(f"[DeleteRoom] User {username} attempting to delete room {room_id}")
        
        # Get current user
        res = await session.execute(select(User).where(User.username == username))
        user = res.scalar_one_or_none()
        if not user:
            print(f"[DeleteRoom] User {username} not found")
            raise HTTPException(status_code=401, detail="Invalid user")
        
        print(f"[DeleteRoom] Found user: {user.username} (id={user.id})")
        
        # Check if room exists
        room = await session.get(Room, room_id)
        if not room:
            print(f"[DeleteRoom] Room {room_id} not found")
            raise HTTPException(status_code=404, detail="Room not found")
        
        print(f"[DeleteRoom] Found room: {room.name} (id={room.id})")
        
        # Get the room member entry for this user
        member_res = await session.execute(
            select(RoomMember).where(
                (RoomMember.room_id == room_id) & (RoomMember.user_id == user.id)
            )
        )
        member = member_res.scalar_one_or_none()
        if not member:
            print(f"[DeleteRoom] User {user.id} is not a member of room {room_id}")
            raise HTTPException(status_code=404, detail="User is not a member of this room")
        
        print(f"[DeleteRoom] Found membership: room_id={member.room_id}, user_id={member.user_id}")
        
        # Soft-delete: mark as deleted
        print(f"[DeleteRoom] Marking room {room_id} as deleted for user {user.id}")
        member.deleted_at = datetime.utcnow()
        session.add(member)
        await session.commit()
        print(f"[DeleteRoom] Successfully marked room {room_id} as deleted for user {user.id}")
        
        # Check if all members have deleted this room
        active_members = await session.execute(
            select(RoomMember).where(
                (RoomMember.room_id == room_id) & (RoomMember.deleted_at == None)
            )
        )
        active_members_list = active_members.scalars().all()
        
        print(f"[DeleteRoom] Active members count: {len(active_members_list)}")
        
        if not active_members_list:
            # No active members, delete room and all messages
            print(f"[DeleteRoom] No active members left, permanently deleting room {room_id}")
            await session.delete(room)
            await session.commit()
            print(f"[DeleteRoom] Room {room_id} permanently deleted")
        
        print(f"[DeleteRoom] Operation completed successfully for room {room_id}")
        return {"ok": True, "message": "Room deleted for you"}
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"[DeleteRoom] ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to delete room: {str(e)}")

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
        
        # Check if user is member of room (including soft-deleted members)
        member_check = await session.execute(
            select(RoomMember).where(
                (RoomMember.room_id == room_id) & 
                (RoomMember.user_id == u.id)
            )
        )
        member = member_check.scalar_one_or_none()
        if not member:
            raise HTTPException(status_code=403, detail="Not a member of this room")
        
        # If user had deleted this room, reactivate it (undelete)
        if member.deleted_at is not None:
            member.deleted_at = None
            session.add(member)
            await session.commit()
        
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

@app.get("/api/users/llm-model")
async def get_llm_model(username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db), platform: str = "desktop"):
    """Get user's preferred LLM model and check availability
    
    models: openai, gemini
    """
    res = await session.execute(select(User).where(User.username == username))
    u = res.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=401, detail="Invalid user")
    
    available_models = list(AVAILABLE_MODELS.keys())
    gemini_available = bool(AVAILABLE_MODELS.get("gemini", {}).get("api_key"))
    
    current_model = "openai" if u.preferred_llm_model not in available_models else u.preferred_llm_model
    
    return {
        "model": current_model,
        "available_models": available_models,
        "gemini_available": gemini_available,
        "platform": platform,
        "gemini_instructions": "Set GEMINI_API_KEY and GEMINI_MODEL in backend env to enable Gemini"
    }

@app.put("/api/users/llm-model")
async def update_llm_model(payload: dict, username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db)):
    """Update user's preferred LLM model"""
    model_name = payload.get("model")
    if not model_name:
        raise HTTPException(status_code=400, detail="model is required")
    
    # Validate if model exists
    valid_models = list(AVAILABLE_MODELS.keys())
    if model_name not in valid_models:
        raise HTTPException(status_code=400, detail=f"Invalid model. Choose from: {valid_models}")
    
    # Get user and update model preference
    res = await session.execute(select(User).where(User.username == username))
    u = res.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=401, detail="Invalid user")
    
    u.preferred_llm_model = model_name
    session.add(u)
    await session.commit()
    
    return {"ok": True, "model": model_name}

@app.get("/api/inventory")
async def get_inventory(username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db)):
    """Get user's inventory"""
    res = await session.execute(select(User).where(User.username == username))
    u = res.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=401, detail="Invalid user")
    
    inv_res = await session.execute(
        select(Inventory).where(Inventory.user_id == u.id).order_by(Inventory.product_name)
    )
    items = inv_res.scalars().all()
    
    return {
        "items": [
            {
                "product_id": item.product_id,
                "product_name": item.product_name,
                "stock": item.stock,
                "safety_stock_level": item.safety_stock_level
            }
            for item in items
        ]
    }

@app.post("/api/inventory")
async def upsert_inventory_item(payload: InventoryItemPayload, username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db)):
    """Add or update an inventory item"""
    res = await session.execute(select(User).where(User.username == username))
    u = res.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=401, detail="Invalid user")
    
    # Check if item exists
    existing_res = await session.execute(
        select(Inventory).where(
            (Inventory.user_id == u.id) & (Inventory.product_name == payload.product_name)
        )
    )
    existing = existing_res.scalar_one_or_none()
    
    if existing:
        existing.stock = payload.stock
        existing.safety_stock_level = payload.safety_stock_level
        session.add(existing)
    else:
        new_item = Inventory(
            user_id=u.id,
            product_name=payload.product_name,
            stock=payload.stock,
            safety_stock_level=payload.safety_stock_level
        )
        session.add(new_item)
    
    await session.commit()
    return {"ok": True}

@app.delete("/api/inventory/{product_id}")
async def delete_inventory_item(product_id: int, username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db)):
    """Delete an inventory item"""
    res = await session.execute(select(User).where(User.username == username))
    u = res.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=401, detail="Invalid user")
    
    item = await session.get(Inventory, product_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
        
    if item.user_id != u.id:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    await session.delete(item)
    await session.commit()
    return {"ok": True}
    return {"ok": True}

@app.get("/api/shopping-lists")
async def get_shopping_lists(username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db)):
    """Get user's shopping lists"""
    res = await session.execute(select(User).where(User.username == username))
    u = res.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=401, detail="Invalid user")
    
    lists_res = await session.execute(
        select(ShoppingList)
        .where((ShoppingList.user_id == u.id) & (ShoppingList.is_archived == False))
        .order_by(desc(ShoppingList.created_at))
    )
    lists = lists_res.scalars().all()
    
    return {
        "lists": [
            {
                "id": l.id,
                "title": l.title,
                "items_json": l.items_json,
                "created_at": str(l.created_at)
            }
            for l in lists
        ]
    }

@app.post("/api/shopping-lists")
async def create_shopping_list(payload: ShoppingListPayload, username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db)):
    """Create a new shopping list"""
    res = await session.execute(select(User).where(User.username == username))
    u = res.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=401, detail="Invalid user")
    
    new_list = ShoppingList(
        user_id=u.id,
        title=payload.title,
        items_json=payload.items_json
    )
    session.add(new_list)
    await session.commit()
    await session.refresh(new_list)
    
    return {"ok": True, "id": new_list.id}

@app.delete("/api/shopping-lists/{list_id}")
async def archive_shopping_list(list_id: int, username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db)):
    """Archive (soft delete) a shopping list"""
    res = await session.execute(select(User).where(User.username == username))
    u = res.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=401, detail="Invalid user")
    
    lst = await session.get(ShoppingList, list_id)
    if not lst:
        raise HTTPException(status_code=404, detail="List not found")
        
    if lst.user_id != u.id:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    lst.is_archived = True
    session.add(lst)
    await session.commit()
    return {"ok": True}
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


# --------- LLM functions ---------
# Planning
@app.post("/api/rooms/{room_id}/ai-plan")
async def api_generate_plan(room_id: int, payload: AIPlanPayload = Body(...), username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db),):
    """
    Generate an AI-generated group plan for a room.
    Goal is optional - if not provided, it will be inferred from chat history.
    """
    
    override_goal = payload.goal  # optional override from frontend
    
    res = await session.execute(select(User).where(User.username == username))
    user = res.scalar_one_or_none()
    model_name = user.preferred_llm_model if user else "openai"
    
    members_res = await session.execute(
        select(User.username)
        .join(RoomMember, RoomMember.user_id == User.id)
        .where(RoomMember.room_id == room_id)
    )
    members = [row[0] for row in members_res.fetchall()]
    
    msgs_res = await session.execute(
        select(Message)
        .where(Message.room_id == room_id)
        .order_by(Message.created_at)
    )
    msgs = msgs_res.scalars().all()
    
    chat_history = []
    for m in msgs:
        role = "assistant" if m.is_bot else "user"
        chat_history.append({"role": role, "content": m.content})
        
    plan = await generate_group_plan(
        chat_history=chat_history,
        goal=override_goal,
        members=members,
        model_name=model_name,
    )
    
    return {"plan": plan}

# Matching Suggestion
@app.post("/api/rooms/{room_id}/ai-matching")
async def api_generate_matching(room_id: int, payload: AIMatchingPayload = Body(...), username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db),):
    """
    AI Matching Suggestion module:
    - Extract goal automatically unless provided by frontend
    - Detect assigned members from chat history
    - Suggest available members or missing roles
    """
    
    override_goal = payload.goal
    
    res = await session.execute(select(User).where(User.username == username))
    user = res.scalar_one_or_none()
    model_name = user.preferred_llm_model if user else "openai"
    
    members_res = await session.execute(
        select(User.username)
        .join(RoomMember, RoomMember.user_id == User.id)
        .where(RoomMember.room_id == room_id)
    )
    members = [row[0] for row in members_res.fetchall()]
    
    # Get chat history
    msgs_res = await session.execute(
        select(Message)
        .where(Message.room_id == room_id)
        .order_by(Message.created_at) 
    )
    msgs = msgs_res.scalars().all()
    
    chat_history = []
    for m in msgs:
        role = "assistant" if m.is_bot else "user"
        chat_history.append({"role": role, "content": m.content})
        
    # Generate suggestion
    suggestions = await suggest_invites(
        members=members,
        chat_history=chat_history,
        goal=override_goal,
        model_name=model_name,
    )
    
    return {"suggestions": suggestions}