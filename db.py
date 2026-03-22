import os
from datetime import datetime, timezone

import bcrypt
import gridfs
from pymongo import MongoClient

MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/")
APP_DB_NAME = "app_data"
USERS_COLLECTION_NAME = "users"

db_client = MongoClient(MONGODB_URI)
db = db_client[APP_DB_NAME]
users = db[USERS_COLLECTION_NAME]
fs = gridfs.GridFS(db)


def verify_user_password(username: str, password: str) -> bool:
    user = users.find_one({"username": username})
    if user is None:
        return False

    stored_hash = user.get("password_hash")
    if stored_hash is None:
        return False

    if isinstance(stored_hash, str):
        stored_hash = stored_hash.encode("utf-8")

    return bcrypt.checkpw(password.encode("utf-8"), stored_hash)


def store_binary_upload(
    owner_username: str,
    request_id: str,
    payload_bytes: bytes,
    filename: str | None,
    content_type: str | None,
) -> str:
    file_id = fs.put(
        payload_bytes,
        filename=filename or "upload",
        content_type=content_type,
        metadata={
            "owner_username": owner_username,
            "request_id": request_id,
            "created_at": datetime.now(timezone.utc),
        },
    )
    return str(file_id)
