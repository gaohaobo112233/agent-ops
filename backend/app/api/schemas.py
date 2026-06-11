from pydantic import BaseModel, Field
from datetime import datetime


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    token_type: str = "bearer"


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    reply: str
    tool_calls: list = []
    task_id: int | None = None
    success: bool = True


class ServerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    host: str = Field(..., min_length=1, max_length=255)
    port: int = Field(default=22, ge=1, le=65535)
    os_type: str = Field(default="linux", pattern="^(linux|windows)$")
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class ServerUpdate(BaseModel):
    name: str | None = None
    host: str | None = None
    port: int | None = None
    os_type: str | None = None
    username: str | None = None
    password: str | None = None
    description: str | None = None
    is_active: bool | None = None


class ServerResponse(BaseModel):
    id: int
    name: str
    host: str
    port: int
    os_type: str
    username: str
    description: str | None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TaskResponse(BaseModel):
    id: int
    user_input: str
    llm_response: str | None
    tool_calls: dict | None
    status: str
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None

    class Config:
        from_attributes = True
