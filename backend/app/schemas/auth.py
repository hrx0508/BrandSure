from typing import Literal

from pydantic import BaseModel, Field


class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=200)
    password: str = Field(min_length=1, max_length=200)


class RegisterIn(BaseModel):
    organisation_name: str = Field(min_length=2, max_length=120)
    display_name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=200)
    password: str = Field(min_length=8, max_length=200)


class UserCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=200)
    password: str = Field(min_length=8, max_length=200)
    role: Literal["admin", "creator", "reviewer"]


class RefreshIn(BaseModel):
    refresh_token: str = Field(min_length=10, max_length=4000)
