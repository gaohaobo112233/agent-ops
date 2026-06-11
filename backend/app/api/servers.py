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

    if server.use_tunnel and server.tunnel_port > 0:
        host, port = "127.0.0.1", server.tunnel_port
    else:
        host, port = server.host, server.port

    if server.os_type == OSType.LINUX:
        from app.tools.ssh_executor import create_ssh_executor
        executor = create_ssh_executor(host, port, server.username, server.password)
    else:
        from app.tools.winrm_executor import create_winrm_executor
        executor = create_winrm_executor(host, port, server.username, server.password)

    result = executor.test_connection()
    if server.use_tunnel:
        result["tunnel_port"] = server.tunnel_port
    return result


@router.get("/{server_id}/tunnel-command")
def get_tunnel_command(server_id: int, db: Session = Depends(get_db)):
    """Generate the reverse SSH tunnel command to run on the target server."""
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")
    if not server.use_tunnel or not server.tunnel_port:
        raise HTTPException(status_code=400, detail="服务器未启用隧道模式")

    command = (
        f"ssh -o ServerAliveInterval=60 -o ExitOnForwardFailure=yes "
        f"-R {server.tunnel_port}:localhost:{server.port} "
        f"-N root@8.147.62.135"
    )
    persistent = (
        f"[Unit]\n"
        f"Description=SSH Tunnel for {server.name}\n"
        f"After=network.target\n\n"
        f"[Service]\n"
        f"Type=simple\n"
        f"ExecStart=/usr/bin/ssh -o ServerAliveInterval=60 -o ExitOnForwardFailure=yes "
        f"-o StrictHostKeyChecking=no "
        f"-R {server.tunnel_port}:localhost:{server.port} "
        f"-N root@8.147.62.135\n"
        f"Restart=always\n"
        f"RestartSec=10\n\n"
        f"[Install]\n"
        f"WantedBy=multi-user.target"
    )
    return {
        "quick_command": command,
        "systemd_service": persistent,
        "tunnel_port": server.tunnel_port,
        "agent_server": "8.147.62.135",
    }
