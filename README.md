CPSC 454 Backend — Quick Start

Prerequisites
- Python 3.10+ and virtualenv
- Docker and Docker Compose for MongoDB, or a local MongoDB instance on localhost:27017

Setup

1. Create and activate a virtual environment:

  python3 -m venv .venv
  source .venv/bin/activate

2. Install dependencies:

  pip install -r requirements.txt

3. Copy example env file and edit if needed:

  cp .env.local.example .env.local

  Important env variables (set in `.env.local`):
  - `MONGO_INITDB_ROOT_USERNAME`
  - `MONGO_INITDB_ROOT_PASSWORD`
  - `CORS_ALLOW_ORIGINS` (comma-separated origins, e.g. http://localhost:3000)
  - `JWT_EXPIRES_MINUTES`
  - `JWT_SECRET_KEY`
  - `MONGODB_URI` (default: mongodb://admin:password@localhost:27017/?authSource=admin)
  - `MONGODB_WITH_CRED_URI` (used by `create_user.py`)

Creating initial users

Use the provided script to create test users:

  python3 create_user.py alice alicepassword
  python3 create_user.py bob bobpassword

Running MongoDB with Docker

Start MongoDB in Docker:

  docker compose up -d mongodb

The service uses the credentials from `.env.local` and stores data in a named volume.

Check the logs if it does not start cleanly:

  docker compose logs -f mongodb

Verify the database is reachable with `mongosh`:

  mongosh -u admin -p password --authenticationDatabase admin

To stop MongoDB and remove its data volume:

  docker compose down -v

Run the server

Start the FastAPI app locally:

  uvicorn server:app --reload --port 9001

API docs

Swagger UI: http://localhost:9001/docs

Binary upload endpoint

Endpoint: POST /binary-files

Example client usage

  python3 client.py \
    --base-url http://localhost:9001 \
    --username user1 \
    --password password1 \
    --recipient-user-id <recipient_user_id> \
    --file ~/path/to/file.webm \
    --content-type application/octet-stream

Database inspection (mongodb)

From `mongosh`:

  use cpsc454
  db.users.find().pretty()
  db.fs.files.find().pretty()

Troubleshooting

- CORS: `CORS_ALLOW_ORIGINS` is read from environment; add your frontend origin to `.env.local`.
- If you get auth/access issues with MongoDB, ensure the Docker container is running and that the credentials in `.env.local` match the container's root credentials.

Cleaning test data (examples)

  db.users.deleteMany({})
  db.fs.files.deleteMany({})

Next steps

- Commit this updated README or convert it to `README.md` for GitHub rendering.
- Want me to make that change and create a commit?
