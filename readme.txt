python3 -m venv myenv
source myenv/bin/activate

pip install fastapi uvicorn requests pydantic

uvicorn server:app --reload

