from typing import Any, Annotated
from fastapi import FastAPI, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
import bleach

comments = []
app = FastAPI()
app.mount("/static", StaticFiles(directory="../static"), name="static")
templates = Jinja2Templates(directory="../templates")

def clean_text(text):
    return bleach.clean(text, tags=['b', 'i', 'u', 'em', 'strong'], attributes={}, strip=True)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    policy = (
        "default-src 'self'; "
        "script-src 'self' https://cdn.jsdelivr.net; "
        "style-src 'self' https://cdn.jsdelivr.net; "
        "img-src 'self' data:;"
    )

    response.headers["Content-Security-Policy"] = policy
    return response
@app.get("/comments")
def read_comments(request: Request):
    # ОПАСНО: передаем данные в шаблон
    return templates.TemplateResponse("comments.html", {"request": request, "comments": comments})

@app.post("/comments")
def make_comment(comment: Annotated[str, Form()]):
    global comments
    comments.append(clean_text(comment))
    return RedirectResponse(app.url_path_for('read_comments'), status_code=303)
