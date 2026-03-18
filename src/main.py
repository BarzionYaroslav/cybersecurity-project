from typing import Any
from fastapi import FastAPI
from schemas import UserCreate

app = FastAPI()


@app.post("/register")
def index(user: UserCreate) -> dict[str, Any]:
    return {"message": "user created", "user": user.username}
