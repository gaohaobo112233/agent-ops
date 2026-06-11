from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, JSON, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base
import enum


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    APPROVAL_REQUIRED = "approval_required"


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_input: Mapped[str] = mapped_column(Text, nullable=False, comment="用户输入")
    llm_response: Mapped[str | None] = mapped_column(Text, comment="LLM 最终回复")
    tool_calls: Mapped[dict | None] = mapped_column(JSON, comment="工具调用记录")
    status: Mapped[TaskStatus] = mapped_column(
        SAEnum(TaskStatus), default=TaskStatus.PENDING, comment="任务状态"
    )
    error_message: Mapped[str | None] = mapped_column(Text, comment="错误信息")
    server_id: Mapped[int | None] = mapped_column(Integer, comment="目标服务器ID")
    executed_commands: Mapped[str | None] = mapped_column(Text, comment="实际执行的命令")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, comment="完成时间")
