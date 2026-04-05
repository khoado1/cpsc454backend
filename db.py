from datetime import datetime, timezone

import bcrypt
import gridfs
from bson.errors import InvalidId
from bson.objectid import ObjectId
from pymongo import MongoClient

from config import get_mongodb_uri, get_mongodb_with_cred_uri

MONGODB_URI = get_mongodb_uri()
MONGODB_WITH_CRED_URI = get_mongodb_with_cred_uri()
APP_DB_NAME = "app_data"
USERS_COLLECTION_NAME = "users"

db_client = MongoClient(MONGODB_URI)
db = db_client[APP_DB_NAME]
users = db[USERS_COLLECTION_NAME]
fs = gridfs.GridFS(db)
fs_files = db["fs.files"]

# For testing purposes, we can connect to the database with credentials if needed
def authenticate_user(username: str, password: str) -> dict | None:
    user = users.find_one({"username": username})
    if user is None:
        return None

    stored_hash = user.get("password_hash")
    if stored_hash is None:
        return None

    if isinstance(stored_hash, str):
        stored_hash = stored_hash.encode("utf-8")

    if not bcrypt.checkpw(password.encode("utf-8"), stored_hash):
        return None

    return user


def create_user(username: str, password: str) -> dict | None:
    if users.find_one({"username": username}):
        return None

    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    result = users.insert_one({"username": username, "password_hash": password_hash})

    return users.find_one({"_id": result.inserted_id})


def verify_user_password(username: str, password: str) -> bool:
    return authenticate_user(username, password) is not None


def store_binary_upload(
    data: bytes,
    sender_user_id: str,
    receiver_user_id: str,
    filename: str | None,
    content_type: str | None,
    request_id: str,
) -> str:
    object_id = fs.put(
        data,
        filename=filename or "upload",
        content_type=content_type,
        metadata={
            "sender_user_id": sender_user_id,
            "receiver_user_id": receiver_user_id,
            "is_read": 0,
            "created_at": datetime.now(timezone.utc),
            "request_id": request_id,
        },
    )
    return str(object_id)


def list_binary_uploads(
    user_id: str | None = None,
) -> list[dict]:
    metadata_filters = []
    if user_id:
        metadata_filters.append({"metadata.sender_user_id": user_id})
        metadata_filters.append({"metadata.receiver_user_id": user_id})

    query: dict = {}
    if metadata_filters:
        query = {"$or": metadata_filters}

    files: list[dict] = []
    for file_doc in fs_files.find(query).sort("uploadDate", -1):
        metadata = file_doc.get("metadata") or {}
        created_at = metadata.get("created_at")
        upload_date = file_doc.get("uploadDate")
        files.append(
            {
                "file_id": str(file_doc.get("_id")),
                "sender_user_id": metadata.get("sender_user_id"),
                "receiver_user_id": metadata.get("receiver_user_id"),
                "is_read": int(metadata.get("is_read", 0)),
                "filename": file_doc.get("filename"),
                "data_length": file_doc.get("length"),
                "content_type": file_doc.get("content_type"),
                "created_at": created_at.isoformat() if isinstance(created_at, datetime) else None,
                "upload_date": upload_date.isoformat() if isinstance(upload_date, datetime) else None,
                "request_id": metadata.get("request_id"),
            }
        )

    if user_id:
        files.sort(key=lambda f:(
            0 if f.get("receiver_user_id") == user_id  and f.get("is_read") == 0 else 1,
            0 if f.get("sender_user_id") == user_id else 1,
        ))

    return files


def fetch_binary_upload(user_id: str, file_id: str) -> dict | None:
    try:
        object_id = ObjectId(file_id)
    except (InvalidId, TypeError):
        return None

    try:
        grid_out = fs.get(object_id)
    except gridfs.errors.NoFile:
        return None

    metadata = grid_out.metadata or {}
    sender_user_id = metadata.get("sender_user_id")
    receiver_user_id = metadata.get("receiver_user_id")

    if user_id not in {sender_user_id, receiver_user_id}:
        return None

    if user_id == receiver_user_id and int(metadata.get("is_read", 0)) == 0:
        fs_files.update_one(
            {"_id": object_id},
            {"$set": {"metadata.is_read": 1, "metadata.read_at": datetime.now(timezone.utc)}},
        )

    return {
        "request_id": metadata.get("request_id"),
        "sender_user_id": sender_user_id,
        "receiver_user_id": receiver_user_id,
        "is_read": 1 if user_id == receiver_user_id else int(metadata.get("is_read", 0)),
        "data": grid_out.read(),
        "file_id": str(grid_out._id),
        "filename": grid_out.filename,
        "content_type": getattr(grid_out, "content_type", None) or "application/octet-stream",
    }


def mark_binary_upload_as_read(file_id: str, user_id: str, is_read: int) -> dict:
    try:
        object_id = ObjectId(file_id)
    except (InvalidId, TypeError):
        return {"status": "not_found"}

    file_doc = fs_files.find_one({"_id": object_id}, {"metadata": 1})
    if file_doc is None:
        return {"status": "not_found"}

    metadata = file_doc.get("metadata") or {}
    receiver_user_id = metadata.get("receiver_user_id")
    if user_id != receiver_user_id:
        return {"status": "forbidden"}

    if is_read:
        read_at = datetime.now(timezone.utc)
        update_fields = {"$set": {"metadata.is_read": is_read, "metadata.read_at": read_at}}
    else:
        read_at = None
        update_fields = {"$set": {"metadata.is_read": is_read}, "$unset": {"metadata.read_at": read_at}}
    
    fs_files.update_one({"_id": object_id}, update_fields)
    
    return {
        "file_id": str(object_id),
        "is_read": is_read,
        "read_at": read_at.isoformat() if read_at else None,
        "status": "updated",
    }

def store_user_key_material(
    user_id: str,
    public_key_base64: str,
    encrypted_private_key_base64: str,
    salt_base64: str,
    iv_base64: str,
) -> bool:
    try:
        object_id = ObjectId(user_id)
    except (InvalidId, TypeError):
        return False

    result = users.update_one(
        {"_id": object_id},
        {
            "$set": {
                "key_material.public_key_base64": public_key_base64,
                "key_material.encrypted_private_key_base64": encrypted_private_key_base64,
                "key_material.salt_base64": salt_base64,
                "key_material.iv_base64": iv_base64,
                "key_material.updated_at": datetime.now(timezone.utc),
            }
        },
    )
    return result.matched_count == 1


def fetch_user_key_material(user_id: str) -> dict | None:
    try:
        object_id = ObjectId(user_id)
    except (InvalidId, TypeError):
        return None

    user = users.find_one({"_id": object_id}, {"key_material": 1})
    if user is None:
        return None

    key_material = user.get("key_material") or {}
    public_key_base64 = key_material.get("public_key_base64")
    encrypted_private_key_base64 = key_material.get("encrypted_private_key_base64")
    salt_base64 = key_material.get("salt_base64")
    iv_base64 = key_material.get("iv_base64")

    if not all([public_key_base64, encrypted_private_key_base64, salt_base64, iv_base64]):
        return None

    result = {
        "public_key_base64": public_key_base64,
        "encrypted_private_key_base64": encrypted_private_key_base64,
        "salt_base64": salt_base64,
        "iv_base64": iv_base64,
    }

    updated_at = key_material.get("updated_at")
    if isinstance(updated_at, datetime):
        result["updated_at"] = updated_at.isoformat()

    return result

# These are my changes
def list_users() -> list[dict]:
    userList = []
    for user in users.find():
        userList.append(
            {
                "user_id": str(user["_id"]),
                "username": user["username"],
                "public_key_base64": user.get("key_material", {}).get("public_key_base64"),
            }
        )

    return userList