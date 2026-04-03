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


class StoreUserKeyMaterialRequest(BaseModel):
    publicKeyBase64: str
    encryptedPrivateKeyBase64: str
    saltBase64: str
    ivBase64: str


class BinaryFileInfo(BaseModel):
    upload_id: str
    request_id: str | None
    owner_user_id: str | None
    recipient_user_id: str | None
    is_read: int
    filename: str | None
    content_type: str | None
    data_length: int | None
    created_at: str | None
    upload_date: str | None


class MarkBinaryFileReadResponse(BaseModel):
    status: str
    upload_id: str
    is_read: int
    read_at: str | None


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

@app.post("/binary-files")
async def store_binary_data(
    id: str = Form(...),
    recipient_user_id: str = Form(...),
    binary_data: UploadFile = File(...),
    current_user_id: str = Depends(get_current_user_id),
):
    binary_data_bytes = await binary_data.read()
    inserted_id = store_binary_upload(
        owner_user_id=current_user_id,
        recipient_user_id=recipient_user_id,
        request_id=id,
        payload_bytes=binary_data_bytes,
        filename=binary_data.filename,
        content_type=binary_data.content_type,
    )

    print(
        "Received request id %s with binary data bytes=%s for user=%s"
        % (id, len(binary_data_bytes), current_user_id)
    )
    return {
        "status": "success",
        "id": id,
        "recipient_user_id": recipient_user_id,
        "is_read": 0,
        "data_length": len(binary_data_bytes),
        "content_type": binary_data.content_type,
        "filename": binary_data.filename,
        "upload_id": inserted_id,
        "user_id": current_user_id,
    }


@app.post("/user/key-material")
async def store_user_key_material_endpoint(
    request: StoreUserKeyMaterialRequest,
    current_user_id: str = Depends(get_current_user_id),
):
    stored = store_user_key_material(
        user_id=current_user_id,
        public_key_base64=request.publicKeyBase64,
        encrypted_private_key_base64=request.encryptedPrivateKeyBase64,
        salt_base64=request.saltBase64,
        iv_base64=request.ivBase64,
    )
    if not stored:
        raise HTTPException(status_code=404, detail="User not found")

    return {"status": "success", "user_id": current_user_id}


@app.get("/binary-files", response_model=list[BinaryFileInfo])
async def list_binary_file_infos(
    owner_user_id: str | None = Query(default=None),
    recipient_user_id: str | None = Query(default=None),
    current_user_id: str = Depends(get_current_user_id),
):
    if owner_user_id is None and recipient_user_id is None:
        uploads = list_binary_uploads()
        return [
            upload
            for upload in uploads
            if current_user_id in {upload.get("owner_user_id"), upload.get("recipient_user_id")}
        ]

    if current_user_id not in {owner_user_id, recipient_user_id}:
        raise HTTPException(status_code=403, detail="Not authorized to view these uploads")

    return list_binary_uploads(
        owner_user_id=owner_user_id,
        recipient_user_id=recipient_user_id,
    )


@app.get("/binary-files/{upload_id}/data")
async def fetch_binary_file_data(
    upload_id: str,
    current_user_id: str = Depends(get_current_user_id),
):
    upload = fetch_binary_upload(upload_id, current_user_id)
    if upload is None:
        raise HTTPException(status_code=404, detail="Binary upload not found")

    filename = upload.get("filename") or "download.bin"
    return Response(
        content=upload["payload_bytes"],
        media_type=upload.get("content_type") or "application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Request-Id": str(upload.get("request_id") or ""),
            "X-Owner-User-Id": str(upload.get("owner_user_id") or ""),
            "X-Recipient-User-Id": str(upload.get("recipient_user_id") or ""),
            "X-Is-Read": str(upload.get("is_read", 0)),
        },
    )


@app.patch("/binary-files/{upload_id}/read", response_model=MarkBinaryFileReadResponse)
async def mark_binary_file_read(
    upload_id: str,
    current_user_id: str = Depends(get_current_user_id),
):
    result = mark_binary_upload_as_read(upload_id, current_user_id)
    if result["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Binary upload not found")
    if result["status"] == "forbidden":
        raise HTTPException(status_code=403, detail="Only the recipient can mark this upload as read")

    return result


@app.get("/user/key-material")
async def fetch_user_key_material_endpoint(
    current_user_id: str = Depends(get_current_user_id),
):
    key_material = fetch_user_key_material(current_user_id)
    if key_material is None:
        raise HTTPException(status_code=404, detail="Key material not found")

    return key_material