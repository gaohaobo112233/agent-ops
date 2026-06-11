from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, DateTime, Boolean, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base
import enum


class OSType(str, enum.Enum):
    LINUX = "linux"
    WINDOWS = "windows"


class Server(Base):
    __tablename__ = "servers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="服务器名称")
    host: Mapped[str] = mapped_column(String(255), nullable=False, comment="IP/主机地址")
    port: Mapped[int] = mapped_column(Integer, default=22, comment="SSH/WinRM 端口")
    os_type: Mapped[OSType] = mapped_column(
        SAEnum(OSType), default=OSType.LINUX, comment="操作系统类型"
    )
    username: Mapped[str] = mapped_column(String(100), nullable=False, comment="登录用户")
    password: Mapped[str] = mapped_column(String(255), nullable=False, comment="登录密码")
    description: Mapped[Optional[str]] = mapped_column(String(500), default="", comment="备注")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
