from pydantic import BaseModel, Field


class AdminLoginRequest(BaseModel):
    password: str = Field(..., min_length=1)


class AdminLoginResponse(BaseModel):
    token: str
