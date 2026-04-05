from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from auth import JWT_EXPIRES_MINUTES, create_access_token, get_current_user_id
from config import get_cors_allow_origins
from db import (
    authenticate_user,
    create_user,
    fetch_binary_upload,
    fetch_user_key_material,
    list_binary_uploads,
    list_users,
    mark_binary_upload_as_read,
    store_binary_upload,
    store_user_key_material,
)

class LoginRequest(BaseModel):
    username: str  # or email: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str

class UserInfo(BaseModel):
    user_id: str
    username: str
    public_key_base64: str | None

class UserKeyMaterialInfo(BaseModel):
    public_key_base64: str
    encrypted_private_key_base64: str
    salt_base64: str
    iv_base64: str

class MessageInfo(BaseModel):
    file_id: str
    sender_user_id: str | None
    receiver_user_id: str | None
    is_read: int
    filename: str | None
    data_length: int | None
    content_type: str | None
    created_at: str | None
    upload_date: str | None
    request_id: str | None

class MessageInfoIsReadRequest(BaseModel):
    is_read: bool

class MessageInfoIsRead(BaseModel):
    file_id: str
    is_read: int
    read_at: str | None
    status: str

app = FastAPI()

# Configure CORS to allow requests from the client frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_allow_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/register")
async def register(request: RegisterRequest):
    user = create_user(request.username, request.password)
    if user is None:
        raise HTTPException(status_code=409, detail="Username already exists")

    user_id = str(user.get("_id"))
    access_token = create_access_token(user_id=user_id, username=request.username)
    return {
        "user_id": user_id,
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": JWT_EXPIRES_MINUTES * 60,
    }

@app.post("/login")
async def login(request: LoginRequest):
    user = authenticate_user(request.username, request.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user_id = str(user.get("_id"))
    access_token = create_access_token(user_id=user_id, username=request.username)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": JWT_EXPIRES_MINUTES * 60,
    }

# These are my changes
@app.get("/users", response_model=list[UserInfo])
async def list_users_endpoint():
    users = list_users()
    return sorted(
        users,
        key=lambda i: i.get("username", "").lower() if i.get("username") else ""
    )

@app.post("/users/me/key-material")
async def store_user_key_material_endpoint(
    request: UserKeyMaterialInfo,
    user_id: str = Depends(get_current_user_id),
):
    stored = store_user_key_material(
        user_id=user_id,
        public_key_base64=request.public_key_base64,
        encrypted_private_key_base64=request.encrypted_private_key_base64,
        salt_base64=request.salt_base64,
        iv_base64=request.iv_base64,
    )
    if not stored:
        raise HTTPException(status_code=404, detail="User not found")

    return {"status": "success", "user_id": user_id}

@app.get("/users/me/key-material")
async def fetch_user_key_material_endpoint(
    user_id: str = Depends(get_current_user_id),
):
    user_key_material = fetch_user_key_material(user_id)
    if user_key_material is None:
        raise HTTPException(status_code=404, detail="Key material not found")

    return user_key_material

# This endpoint allows an authenticated user to upload binary data (e.g., a file) and associate it with a specific receiver and request ID. The uploaded data is stored in the database, and metadata about the upload is returned in the response.
@app.post("/messages")
async def store_binary_data(
    request_id: str = Form(...),
    receiver_user_id: str = Form(...),
    data: UploadFile = File(...),
    current_user_id: str = Depends(get_current_user_id),
):
    data = await data.read()
    file_id = store_binary_upload(
        data=data,
        sender_user_id=current_user_id,
        receiver_user_id=receiver_user_id,
        filename=data.filename,
        content_type=data.content_type,
        request_id=request_id,
    )

    print(
        "Received request id %s with binary data bytes=%s for user=%s"
        % (request_id, len(data), current_user_id)
    )
    return {
        "file_id": file_id,
        "sender_user_id": current_user_id,
        "receiver_user_id": receiver_user_id,
        "is_read": 0,
        "filename": data.filename,
        "data_length": len(data),
        "content_type": data.content_type,
        "request_id": request_id,
        "status": "success",
    }

@app.get("/messages", response_model=list[MessageInfo])
async def list_binary_file_infos(
    user_id: str = Depends(get_current_user_id),
):
    return list_binary_uploads(user_id)

@app.get("/messages/{file_id}")
async def fetch_binary_file_data(
    file_id: str,
    user_id: str = Depends(get_current_user_id),
):
    message = fetch_binary_upload(user_id, file_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Binary upload not found")

    filename = message.get("filename") or "download.bin"
    return Response(
        content=message["data"],
        media_type=message.get("content_type") or "application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Request-Id": str(message.get("request_id") or ""),
            "X-Sender-User-Id": str(message.get("sender_user_id") or ""),
            "X-Receiver-User-Id": str(message.get("receiver_user_id") or ""),
            "X-Is-Read": str(message.get("is_read", 0)),
        },
    )

@app.patch("/messages/{file_id}", response_model=MessageInfoIsRead)
async def mark_binary_file_read(
    file_id: str,
    request: MessageInfoIsReadRequest,
    current_user_id: str = Depends(get_current_user_id),
):
    result = mark_binary_upload_as_read(file_id, current_user_id, int(request.is_read))
    if result["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Binary upload not found")
    if result["status"] == "forbidden":
        raise HTTPException(status_code=403, detail="Only the recipient can mark this upload as read")

    return result
