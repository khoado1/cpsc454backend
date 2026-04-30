CPSC 454 Backend — Quick Start

Prerequisites
- Python 3.10+ and virtualenv
- Docker and Docker Compose for MongoDB, or a local MongoDB instance on localhost:27017

Setup

1. Copy the example env file and set your local values:

  cp .env.local.example .env.local

2. Start MongoDB in Docker:

  docker compose up -d mongodb

   The service uses the credentials from `.env.local` and stores data in a named volume.

3. Create and activate a virtual environment, then install dependencies from `requirements.txt`:

  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt

   Important env variables (set in `.env.local`):
  - `MONGO_INITDB_ROOT_USERNAME`
  - `MONGO_INITDB_ROOT_PASSWORD`
  - `CORS_ALLOW_ORIGINS` (comma-separated origins, e.g. http://localhost:3000)
  - `JWT_EXPIRES_MINUTES`
  - `JWT_SECRET`
  - `MONGODB_URI` (default: mongodb://admin:password@localhost:27017/?authSource=admin)
  - `MONGODB_WITH_CRED_URI` (used by `create_user.py`)

4. Create a test user:

  python3 create_user.py alice alicepassword

5. Run the API:

  uvicorn server:app --reload --port 9001

6. Open the API docs and try a login or upload flow:

  http://localhost:9001/docs

If you want live feedback while iterating, keep `docker compose logs -f mongodb` open in one terminal and let Uvicorn auto-reload in another.

MongoDB troubleshooting:

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