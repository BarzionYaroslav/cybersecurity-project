import os
from typing import Any, Annotated
from dotenv import load_dotenv  # type: ignore
from fastapi import Depends, FastAPI, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import HTTPException
from fastapi.responses import RedirectResponse
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
file_db = [
    {"id": 1, "filename": "report_alice.pdf", "owner": "alice", "size": 1024},
    {"id": 2, "filename": "photo_bob.jpg", "owner": "bob", "size": 2048},
    {"id": 3, "filename": "admin_keys.txt", "owner": "admin", "size": 12},
]

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
