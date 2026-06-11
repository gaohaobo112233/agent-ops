from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.security import verify_token
from app.db.database import get_db
from app.models.task import Task
from app.models.server import Server, OSType
from app.tools.rollback import RollbackManager

router = APIRouter(prefix="/api/rollback", tags=["回滚"], dependencies=[Depends(verify_token)])


class RollbackRequest(BaseModel):
    task_id: int


class RollbackResponse(BaseModel):
    success: bool
    message: str
    details: Optional[str] = None


@router.post("/execute", response_model=RollbackResponse)
def execute_rollback(req: RollbackRequest, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == req.task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    backup_info = task.backup_info
    if not backup_info or not backup_info.get("backup_id"):
        return RollbackResponse(
            success=False,
            message="此任务没有可回滚的备份。只读操作（如查看磁盘、CPU）不会产生备份。",
        )

    backup_id = backup_info["backup_id"]

    # Get server info
    server_id = task.server_id
    if not server_id:
        return RollbackResponse(success=False, message="无法确定目标服务器")

    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        return RollbackResponse(success=False, message="目标服务器不存在")

    # Execute rollback
    mgr = RollbackManager(
        ssh_host=server.host,
        ssh_port=server.port,
        ssh_user=server.username,
        ssh_password=server.password,
    )

    result = mgr.restore(backup_id)

    if result["success"]:
        return RollbackResponse(
            success=True,
            message="回滚成功！已从备份恢复文件。",
            details=result.get("output", ""),
        )
    else:
        return RollbackResponse(
            success=False,
            message=f"回滚失败: {result.get('error', '未知错误')}",
            details=result.get("output", ""),
        )


@router.get("/info/{task_id}", response_model=dict)
def get_rollback_info(task_id: int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if not task.backup_info:
        return {"has_backup": False, "message": "此任务无备份信息"}
    return {"has_backup": True, "backup_info": task.backup_info}
