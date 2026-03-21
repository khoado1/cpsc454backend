from fastapi import FastAPI, Body
from pydantic import BaseModel

app = FastAPI()

class LoginRequest(BaseModel):
    username: str  # or email: str
    password: str

@app.post("/login")
async def login(request: LoginRequest):
    # Authenticate user here (e.g., check against database)
    # For demo, assume success
    if request.username == "admin" and request.password == "password":
        return {"message": "Login successful", "token": "fake_jwt_token"}
    else:
        return {"message": "Invalid credentials"}

@app.post("/process")
async def process_data(id: str = Body(...), data: bytes = Body(...)):
    # Process the id and byte array here
    # Example: save to file or encrypt
    print(f"Received ID: {id}, Data length: {len(data)}")
    return {"status": "success", "id": id, "data_length": len(data)}