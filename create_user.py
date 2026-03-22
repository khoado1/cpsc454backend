"""
Run once to create a user in MongoDB:
  python create_user.py <username> <password>
"""
import sys
from db import MONGODB_WITH_CRED_URI, create_user


if not MONGODB_WITH_CRED_URI:
    print("Set MONGODB_WITH_CRED_URI or MONGODB_URI in your environment or .env.local before creating users.")
    sys.exit(1)

if len(sys.argv) != 3:
    print("Usage: python create_user.py <username> <password>")
    sys.exit(1)

username = sys.argv[1]
password = sys.argv[2]

user = create_user(username, password)
if user is None:
    print(f"User '{username}' already exists.")
    sys.exit(1)

print(f"User '{username}' created successfully.")
