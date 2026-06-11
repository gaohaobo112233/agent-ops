from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.api.schemas import ServerCreate, ServerUpdate, ServerResponse
from app.models.server import Server, OSType
from app.db.database import get_db
from app.core.security import verify_token
from datetime import datetime

router = APIRouter(prefix="/api/servers", tags=["服务器管理"], dependencies=[Depends(verify_token)])


@router.get("/", response_model=List[ServerResponse])
def list_servers(db: Session = Depends(get_db)):
    return db.query(Server).order_by(Server.created_at.desc()).all()


@router.post("/", response_model=ServerResponse)
def create_server(req: ServerCreate, db: Session = Depends(get_db)):
    server = Server(
        name=req.name,
        host=req.host,
        port=req.port,
        os_type=OSType(req.os_type),
        username=req.username,
        password=req.password,
        description=req.description,
    )
    db.add(server)
    db.commit()
    db.refresh(server)
    return server


@router.get("/{server_id}", response_model=ServerResponse)
def get_server(server_id: int, db: Session = Depends(get_db)):
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")
    return server


@router.put("/{server_id}", response_model=ServerResponse)
def update_server(server_id: int, req: ServerUpdate, db: Session = Depends(get_db)):
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")
    update_data = req.model_dump(exclude_none=True)
    if "os_type" in update_data and update_data["os_type"]:
        update_data["os_type"] = OSType(update_data["os_type"])
    for field, value in update_data.items():
        setattr(server, field, value)
    server.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(server)
    return server


@router.delete("/{server_id}")
def delete_server(server_id: int, db: Session = Depends(get_db)):
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")
    db.delete(server)
    db.commit()
    return {"message": f"服务器 {server.name} 已删除"}


@router.post("/{server_id}/test")
def test_connection(server_id: int, db: Session = Depends(get_db)):
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")
    if server.os_type == OSType.LINUX:
        from app.tools.ssh_executor import create_ssh_executor
        executor = create_ssh_executor(server.host, server.port, server.username, server.password)
    else:
        from app.tools.winrm_executor import create_winrm_executor
        executor = create_winrm_executor(server.host, server.port, server.username, server.password)
    return executor.test_connection()
