import os
import uuid
import shutil
import filetype
from typing import Any, Annotated
from dotenv import load_dotenv  # type: ignore
from fastapi import Depends, FastAPI, Request, Form, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import HTTPException
from fastapi.responses import RedirectResponse, FileResponse
from schemas import UserCreate, UserEnum
from starlette import status
from starlette.middleware.sessions import SessionMiddleware
import bleach

load_dotenv()

if os.getenv("APP_SECRET") is None:
    raise ValueError("APP_SECRET environment variable is not set")

comments = []
app = FastAPI()
templates = Jinja2Templates(directory="../templates")
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("APP_SECRET"),  # type: ignore
    https_only=True,
)

users_db = [
    {"name": "alice", "age": 20, "role": UserEnum.user, "password": "P@ssW0rd"},
    {"name": "bob", "age": 24, "role": UserEnum.user, "password": "P@ssW0rdButC00l3r"},
    {"name": "admin", "age": 37, "role": UserEnum.admin, "password": "Adm!n123"},
]
file_db = []

def clean_text(text):
    return bleach.clean(text, tags=['b', 'i', 'u', 'em', 'strong'], attributes={}, strip=True)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    policy = (
        "default-src 'self'; "
        "script-src 'self' https://cdn.jsdelivr.net 'sha256-QOOQu4W1oxGqd2nbXbxiA1Di6OHQOLQD+o+G9oWL8YY='; "
        "style-src 'self' https://cdn.jsdelivr.net; "
        "img-src 'self' data: https://fastapi.tiangolo.com;"
    )

    response.headers["Content-Security-Policy"] = policy
    return response

@app.get("/comments")
def read_comments(request: Request):
    global comments
    return templates.TemplateResponse(request=request,name="comments.html", context={"comments": comments})

@app.post("/comments")
def make_comment(comment: Annotated[str, Form()]):
    global comments
    comments.append(clean_text(comment))
    return RedirectResponse(app.url_path_for('read_comments'), status_code=303)

@app.post("/set-session")
def set_session(request: Request, name: str) -> dict:
    if name not in [u["name"] for u in users_db]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid login"
        )
    request.session["name"] = name
    return {"message": "Session set successfully"}

@app.get("/get-session")
def get_session(request: Request) -> Any:
    if "name" not in request.session:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Need to set session first",
        )
    name = request.session["name"]
    return {"name": name}

@app.get("/drop-session")
def drop_session(request: Request) -> Any:
    request.session.clear()
    return {"message": "Session cleared successfully"}

def current_user(request: Request) -> dict | None:
    user = next(
        (
            u
            for u in users_db
            if u["name"] == request.session.get("name", None)
        ),
        None,
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized"
        )
    return user

def get_file(file_ind: int) -> dict | None:
    file = next((f for f in file_db if f["id"] == file_ind), None)
    return file

def check_file_permissions(user: Annotated[dict | None, Depends(current_user)], file: Annotated[dict | None, Depends(get_file)]) -> dict:
    if file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )
    if file["owner"] != user["name"] and user["role"]!=UserEnum.admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )
    return file

@app.get("/files/{file_ind}")
def get_file(file: Annotated[dict | None, Depends(check_file_permissions)]) -> dict:
    return file

@app.delete("/files/{file_ind}")
def remove_file(file: Annotated[dict | None, Depends(check_file_permissions)]) -> dict:
    file_db.remove(file)
    return {"message": "Removed file"}

@app.get("/myfiles")
def get_file(user: Annotated[dict | None, Depends(current_user)]) -> dict | list:
    files = [u for u in file_db if u["owner"]==user["name"]]
    if not files:
        return {"Message": "No files found!"}
    return files

@app.get("/allfiles")
def get_file(user: Annotated[dict | None, Depends(current_user)]) -> list:
    if user["role"] != UserEnum.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized"
        )
    return file_db

@app.get("/users")
def show_users(user: Annotated[dict | None, Depends(current_user)]) -> list:
    if user["role"] != UserEnum.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized"
        )
    unpassworder=[]
    for i in users_db:
        unpassworder.append({"name": i["name"], "age": i["age"], "role": i["role"]})
    return unpassworder

@app.post("/register")
def index(user: UserCreate) -> dict[str, Any]:
    users_db.append({"name": user.username, "age": user.age, "role": user.role, "password": user.password})
    return {"message": "user created", "user": user.username}

def check_file_type(file: UploadFile, types: list[str]) -> bool:
    head = file.file.read(2048)
    kind = filetype.guess(head)

    if kind is None or kind.mime not in types:
        return False
    file.file.seek(0)
    return True

@app.post("/upload")
def upload_file(request: Request, file: UploadFile) -> dict[str, Any]:
    user = current_user(request)
    if not check_file_type(file, ["image/png", "image/jpeg"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is not a valid image",
        )
    name = uuid.uuid4()
    limit = 1024*1024*2
    chunk_size = 1024
    cur_size = 0
    flag = False
    with open(f"storage/{name}", "wb") as f:
        while True:
            chunk = file.file.read(chunk_size)
            if not chunk:
                break
            cur_size+=len(chunk)
            if cur_size>limit:
                flag = True
                break
            f.write(chunk)
    if flag:
        os.remove(f"storage/{name}")
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Uploaded file is longer than the 2 MB limit"
        )
    file_db.append(
        {"id": len(file_db) + 1, "owner": user["name"], "name": name, "src_name": file.filename, "size": cur_size}
    )
    return {"message": "File created"}

@app.get("/files/download/{file_ind}")
def download_file(file: Annotated[dict | None, Depends(check_file_permissions)]):
    return FileResponse(f"storage/{file["name"]}", filename=file["src_name"])
