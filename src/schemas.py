from typing_extensions import Self
from pydantic import BaseModel, Field, field_validator, model_validator, EmailStr
from enum import Enum
import re

MIN_AGE = 18
MAX_AGE = 100
PASSWORD_LEN = 8
MIN_NAME_LEN = 3
MAX_NAME_LEN = 48

class UserEnum(str, Enum):
    admin = 'admin'
    user = 'user'
    guest = 'guest'

class UserCreate(BaseModel):
    username: str = Field(
        ...,
        description="User's username",
        min_length=MIN_NAME_LEN,
        max_length=MAX_NAME_LEN,
        pattern=r"^[a-zA-Z0-9]+$"
        )
    email: EmailStr = Field(
        ...,
        description="User's Email"
        )
    password: str = Field(
        ...,
        description="User's Password",
        min_length=PASSWORD_LEN
        )
    confirm_password: str = Field(
        ...,
        description="User's Password Confirmation",
        min_length=PASSWORD_LEN
        )
    age: int = Field(
        ...,
        description="User's age",
        ge=MIN_AGE,
        le=MAX_AGE
        )
    role: UserEnum = Field(
        ...,
        description="User Role"
    )


    @field_validator("password")
    @classmethod
    def password_validator(cls, value: str) -> str:
        if not value:
            raise ValueError("Password cannot be empty")
        if not re.search(r"[A-Z]+", value):
            raise ValueError("Password needs at least one uppercase letter")
        if not re.search(r"[0-9]+", value):
            raise ValueError("Password needs at least one digit")
        if not re.search(r"[!@#$%^&*]+", value):
            raise ValueError("Password needs at least one special symbol (!@#$%^&*)")
        return value

    @model_validator(mode='after')
    def password_confirmation(self) -> Self:
        if self.password != self.confirm_password:
            raise ValueError(f"Password and password confirm don't match! {self.password} != {self.confirm_password}")
        return self
