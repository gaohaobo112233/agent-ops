from typing import Optional
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
    action: str = Field(default="preview", pattern="^(preview|execute)$")


class ChatResponse(BaseModel):
    reply: str
    tool_calls: list = []
    task_id: Optional[int] = None
    success: bool = True
    needs_approval: bool = False


class ServerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    host: str = Field(..., min_length=1, max_length=255)
    port: int = Field(default=22, ge=1, le=65535)
    os_type: str = Field(default="linux", pattern="^(linux|windows)$")
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class ServerUpdate(BaseModel):
    name: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    os_type: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class ServerResponse(BaseModel):
    id: int
    name: str
    host: str
    port: int
    os_type: str
    username: str
    description: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TaskResponse(BaseModel):
    id: int
    user_input: str
    llm_response: Optional[str]
    tool_calls: Optional[dict]
    status: str
    error_message: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True
