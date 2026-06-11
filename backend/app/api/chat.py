from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.schemas import ChatRequest, ChatResponse
from app.agent.executor import AgentExecutor
from app.db.database import get_db
from app.models.task import Task, TaskStatus
from app.core.security import verify_token
from datetime import datetime

router = APIRouter(prefix="/api", tags=["对话"])


@router.post("/chat", response_model=ChatResponse, dependencies=[Depends(verify_token)])
def chat(req: ChatRequest, db: Session = Depends(get_db)):
    # Create task record
    task = Task(
        user_input=req.message,
        status=TaskStatus.RUNNING,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # Run agent
    executor = AgentExecutor(db)
    result = executor.run(req.message)

    # Update task record
    task.llm_response = result["reply"]
    task.tool_calls = result.get("tool_calls", [])
    task.status = TaskStatus.COMPLETED if result["success"] else TaskStatus.FAILED
    task.error_message = result.get("error")
    task.completed_at = datetime.utcnow()
    db.commit()

    return ChatResponse(
        reply=result["reply"],
        tool_calls=result.get("tool_calls", []),
        task_id=task.id,
        success=result["success"],
    )
