import requests


# Login call
login_data = {"username": "admin", "password": "password"}
response = requests.post("http://localhost:8000/login", json=login_data)

data = response.json()
if "token" in data:
    token = data["token"]
    print(f"Logged in with token: {token}")
else:
    print(f"Login failed: {data.get('message', 'Unknown error')}")



# Sample data
id_str = "example_id"
byte_array = b"some binary data here"

response = requests.post("http://localhost:8000/process", json={"id": id_str, "data": byte_array.decode('latin-1')}, headers={"Authorization": f"Bearer {token}"})
print(response.json())

data = response.json()
if data.get("status") == "success":
    print(f"Processed ID: {data['id']}, Data length: {data['data_length']}")
else:
    print("Process failed")