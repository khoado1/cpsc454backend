import argparse
import os
import uuid

import requests


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Login and upload binary data to /binary-files")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--username", default="user1", help="Login username")
    parser.add_argument("--password", default="password1", help="Login password")
    parser.add_argument(
        "--file",
        dest="file_path",
        default=None,
        help="Optional path to a file to upload. If omitted, sends sample bytes.",
    )
    parser.add_argument(
        "--request-id",
        default=None,
        help="Optional request id. Defaults to a generated UUID.",
    )
    parser.add_argument(
        "--recipient-user-id",
        required=True,
        help="Recipient user id stored with the upload metadata.",
    )
    parser.add_argument(
        "--content-type",
        default="application/octet-stream",
        help="Content type to use when uploading sample bytes.",
    )
    return parser.parse_args()


def login(base_url: str, username: str, password: str) -> str:
    login_data = {"username": username, "password": password}
    response = requests.post(f"{base_url}/login", json=login_data)

    if response.status_code != 200:
        print(f"Login failed ({response.status_code}): {response.text}")
        raise SystemExit(1)

    data = response.json()
    token = data.get("access_token")
    if not token:
        print(f"Login response missing access_token: {data}")
        raise SystemExit(1)

    print("Login successful.")
    return token


def build_upload_payload(args: argparse.Namespace) -> tuple[dict, dict]:
    request_id = args.request_id or str(uuid.uuid4())

    if args.file_path:
        filename = os.path.basename(args.file_path)
        with open(args.file_path, "rb") as input_file:
            binary_payload = input_file.read()
        content_type = args.content_type
    else:
        filename = "sample.bin"
        binary_payload = b"sample binary payload for upload testing"
        content_type = args.content_type

    multipart_form = {
        "id": request_id,
        "recipient_user_id": args.recipient_user_id,
    }
    multipart_files = {
        "binary_data": (filename, binary_payload, content_type),
    }
    return multipart_form, multipart_files


def main() -> None:
    args = parse_args()
    token = login(args.base_url, args.username, args.password)
    multipart_form, multipart_files = build_upload_payload(args)

    response = requests.post(
        f"{args.base_url}/binary-files",
        data=multipart_form,
        files=multipart_files,
        headers={"Authorization": f"Bearer {token}"},
    )

    if response.status_code != 200:
        print(f"Upload failed ({response.status_code}): {response.text}")
        raise SystemExit(1)

    data = response.json()
    print(data)

    if data.get("status") == "success":
        print(
            f"Processed ID: {data['id']}, Data length: {data['data_length']}, Upload ID: {data['upload_id']}"
        )
    else:
        print("Process failed")


if __name__ == "__main__":
    main()
