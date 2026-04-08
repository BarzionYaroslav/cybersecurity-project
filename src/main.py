from typing import Any, Annotated
from fastapi import FastAPI, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from schemas import UserCreate, UserEnum
import bleach

comments = []
app = FastAPI()
app.mount("/static", StaticFiles(directory="../static"), name="static")
templates = Jinja2Templates(directory="../templates")

users_db = {}
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

@app.get("/users")
def show_users(request: Request):
    return users_db

@app.post("/register")
def index(user: UserCreate) -> dict[str, Any]:
    users_db.update({user.username: {"name": user.username, "age": user.age, "role": user.role, "password": user.password}})
    return {"message": "user created", "user": user.username}
