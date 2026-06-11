import json
import logging
import math
from openai import OpenAI
from sqlalchemy.orm import Session
from app.core.config import settings
from app.agent.prompt import SYSTEM_PROMPT, USER_CONTEXT_TEMPLATE
from app.agent.approval import check_command_risk
from app.models.server import Server, OSType
from app.tools.ssh_executor import create_ssh_executor
from app.tools.winrm_executor import create_winrm_executor
from app.tools.inspection import check_cpu, check_memory, check_disk, check_port

logger = logging.getLogger(__name__)


def _sanitize_for_json(obj):
    """Replace NaN/Infinity values with None for JSON serialization."""
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return 0
    return obj


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "ssh_execute",
            "description": "在 Linux 服务器上远程执行 Shell 命令。用于查看服务器状态、管理文件、查看日志等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "integer",
                        "description": "目标服务器ID（从可用服务器列表中选择）",
                    },
                    "command": {
                        "type": "string",
                        "description": "要执行的 Shell 命令，如 df -h、free -m、ps aux 等",
                    },
                },
                "required": ["server_id", "command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "winrm_execute",
            "description": "在 Windows 服务器上远程执行 PowerShell 命令。用于管理 Windows 服务器。",
            "parameters": {
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "integer",
                        "description": "目标服务器ID（从可用服务器列表中选择）",
                    },
                    "command": {
                        "type": "string",
                        "description": "要执行的 PowerShell 命令，如 Get-Service、Get-Process 等",
                    },
                },
                "required": ["server_id", "command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_local_inspection",
            "description": "在本地服务器执行系统巡检，包括 CPU 使用率、内存使用、磁盘空间。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_port_status",
            "description": "检查指定主机的 TCP 端口是否开放。",
            "parameters": {
                "type": "object",
                "properties": {
                    "host": {
                        "type": "string",
                        "description": "目标主机 IP 地址",
                    },
                    "port": {
                        "type": "integer",
                        "description": "要检查的端口号，如 80、443、3306 等",
                    },
                },
                "required": ["host", "port"],
            },
        },
    },
]


class AgentExecutor:
    def __init__(self, db: Session):
        self.db = db
        self.client = OpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
        )

    def _get_servers_context(self) -> str:
        servers = self.db.query(Server).filter(Server.is_active == True).all()
        if not servers:
            return "暂无可用服务器"
        lines = []
        for s in servers:
            lines.append(
                f"  ID={s.id} | 名称={s.name} | IP={s.host} | "
                f"系统={s.os_type.value} | 备注={s.description or '无'}"
            )
        return "\n".join(lines)

    def _execute_tool(self, tool_name: str, tool_args: dict) -> dict:
        if tool_name == "ssh_execute":
            server = self.db.query(Server).filter(Server.id == tool_args["server_id"]).first()
            if not server:
                return {"success": False, "error": f"服务器 ID={tool_args['server_id']} 不存在"}
            if server.os_type != OSType.LINUX:
                return {"success": False, "error": f"服务器 {server.name} 不是 Linux，请使用 winrm_execute"}

            risk = check_command_risk(tool_args["command"])
            if risk["blocked"]:
                return {"success": False, "error": f"高危命令被拦截: {risk['reason']}", "risk": risk}

            executor = create_ssh_executor(
                host=server.host, port=server.port,
                username=server.username, password=server.password,
            )
            result = executor.execute(tool_args["command"])
            if risk["risk"] == "warning":
                result["warning"] = f"注意: {risk['reason']}"
            return result

        elif tool_name == "winrm_execute":
            server = self.db.query(Server).filter(Server.id == tool_args["server_id"]).first()
            if not server:
                return {"success": False, "error": f"服务器 ID={tool_args['server_id']} 不存在"}
            if server.os_type != OSType.WINDOWS:
                return {"success": False, "error": f"服务器 {server.name} 不是 Windows，请使用 ssh_execute"}

            risk = check_command_risk(tool_args["command"])
            if risk["blocked"]:
                return {"success": False, "error": f"高危命令被拦截: {risk['reason']}", "risk": risk}

            executor = create_winrm_executor(
                host=server.host, port=server.port,
                username=server.username, password=server.password,
            )
            result = executor.execute(tool_args["command"])
            if risk["risk"] == "warning":
                result["warning"] = f"注意: {risk['reason']}"
            return result

        elif tool_name == "run_local_inspection":
            return {
                "cpu": check_cpu(),
                "memory": check_memory(),
                "disk_root": check_disk("/"),
                "success": True,
            }

        elif tool_name == "check_port_status":
            return check_port(tool_args["host"], tool_args["port"])

        return {"success": False, "error": f"未知工具: {tool_name}"}

    def run(self, user_message: str) -> dict:
        servers_context = self._get_servers_context()
        user_content = USER_CONTEXT_TEMPLATE.format(
            servers_list=servers_context,
            user_message=user_message,
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

        tool_calls_log = []

        try:
            # First LLM call
            response = self.client.chat.completions.create(
                model=settings.DEEPSEEK_MODEL,
                messages=messages,
                tools=TOOLS,
                temperature=0.3,
            )

            assistant_msg = response.choices[0].message
            messages.append(assistant_msg.model_dump(exclude_none=True))

            # Loop for tool calls
            max_iterations = 5
            for _ in range(max_iterations):
                if not assistant_msg.tool_calls:
                    break

                for tool_call in assistant_msg.tool_calls:
                    func_name = tool_call.function.name
                    func_args = json.loads(tool_call.function.arguments)
                    logger.info(f"Tool call: {func_name}, args: {func_args}")

                    # Check risk before execution
                    if func_name in ("ssh_execute", "winrm_execute"):
                        risk = check_command_risk(func_args.get("command", ""))
                        if risk["blocked"]:
                            tool_calls_log.append({
                                "tool": func_name, "args": func_args,
                                "result": risk, "blocked": True,
                            })
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": json.dumps(risk, ensure_ascii=False),
                            })
                            continue

                    result = self._execute_tool(func_name, func_args)
                    tool_calls_log.append({
                        "tool": func_name, "args": func_args, "result": result,
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(_sanitize_for_json(result), ensure_ascii=False, default=str),
                    })

                # Second LLM call with tool results
                response = self.client.chat.completions.create(
                    model=settings.DEEPSEEK_MODEL,
                    messages=messages,
                    tools=TOOLS,
                    temperature=0.3,
                )
                assistant_msg = response.choices[0].message
                messages.append(assistant_msg.model_dump(exclude_none=True))

            final_reply = assistant_msg.content or ""
            return {
                "reply": final_reply,
                "tool_calls": tool_calls_log,
                "success": True,
            }

        except Exception as e:
            logger.exception("Agent execution failed")
            return {
                "reply": f"执行出错: {str(e)}",
                "tool_calls": tool_calls_log,
                "success": False,
                "error": str(e),
            }
