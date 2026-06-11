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
    is_preview = req.action == "preview"

    task = Task(
        user_input=req.message,
        status=TaskStatus.RUNNING,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    executor = AgentExecutor(db)
    result = executor.run(req.message, preview=is_preview)

    if is_preview and result.get("needs_approval"):
        task.status = TaskStatus.APPROVAL_REQUIRED
    elif result["success"]:
        task.status = TaskStatus.COMPLETED
    else:
        task.status = TaskStatus.FAILED

    task.llm_response = result["reply"]
    task.tool_calls = result.get("tool_calls", [])
    task.error_message = result.get("error")
    task.completed_at = datetime.utcnow()

    # Save backup info from tool calls for rollback
    for tc in result.get("tool_calls", []):
        if tc.get("result") and isinstance(tc["result"], dict):
            bi = tc["result"].get("backup_info")
            if bi and bi.get("backup_needed"):
                task.backup_info = bi
                task.server_id = tc.get("args", {}).get("server_id")
                break

    db.commit()

    return ChatResponse(
        reply=result["reply"],
        tool_calls=result.get("tool_calls", []),
        task_id=task.id,
        success=result["success"],
        needs_approval=result.get("needs_approval", False),
    )
