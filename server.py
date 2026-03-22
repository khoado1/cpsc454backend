from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from auth import JWT_EXPIRES_MINUTES, create_access_token, get_current_username
from db import store_binary_upload, verify_user_password

class LoginRequest(BaseModel):
    username: str  # or email: str
    password: str


app = FastAPI()

# Configure CORS to allow requests from the client frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/login")
async def login(request: LoginRequest):
    if not verify_user_password(request.username, request.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(request.username)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": JWT_EXPIRES_MINUTES * 60,
    }

@app.post("/process")
async def process_data(
    id: str = Form(...),
    binary_data: UploadFile = File(...),
    current_username: str = Depends(get_current_username),
):
    binary_data_bytes = await binary_data.read()
    inserted_id = store_binary_upload(
        owner_username=current_username,
        request_id=id,
        payload_bytes=binary_data_bytes,
        filename=binary_data.filename,
        content_type=binary_data.content_type,
    )

    print(
        "Received request id %s with binary data bytes=%s for user=%s"
        % (id, len(binary_data_bytes), current_username)
    )
    return {
        "status": "success",
        "id": id,
        "data_length": len(binary_data_bytes),
        "content_type": binary_data.content_type,
        "filename": binary_data.filename,
        "upload_id": inserted_id,
        "user": current_username,
    }