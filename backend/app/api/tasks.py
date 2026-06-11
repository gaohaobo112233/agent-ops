from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List
from app.api.schemas import TaskResponse
from app.models.task import Task
from app.db.database import get_db
from app.core.security import verify_token

router = APIRouter(prefix="/api/tasks", tags=["任务历史"], dependencies=[Depends(verify_token)])


@router.get("/", response_model=List[TaskResponse])
def list_tasks(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    offset = (page - 1) * page_size
    return db.query(Task).order_by(Task.created_at.desc()).offset(offset).limit(page_size).all()


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="任务不存在")
    return task
