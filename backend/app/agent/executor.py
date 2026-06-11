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
from app.tools.prometheus import create_prometheus_client, METRIC_HELP
from app.tools.rollback import RollbackManager

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
    {
        "type": "function",
        "function": {
            "name": "query_prometheus",
            "description": f"查询 Prometheus 监控指标，获取服务器的 CPU、内存、磁盘、网络等时序数据。{METRIC_HELP}",
            "parameters": {
                "type": "object",
                "properties": {
                    "query_type": {
                        "type": "string",
                        "enum": ["instant", "range"],
                        "description": "instant=当前瞬时值, range=时间范围查询",
                    },
                    "promql": {
                        "type": "string",
                        "description": "PromQL 查询语句。如: node_cpu_seconds_total, node_memory_MemAvailable_bytes 等",
                    },
                    "start": {
                        "type": "string",
                        "description": "range查询的开始时间，如: -1h 表示1小时前，-30m 表示30分钟前",
                    },
                    "end": {
                        "type": "string",
                        "description": "range查询的结束时间，如: now",
                    },
                    "step": {
                        "type": "string",
                        "description": "采样间隔，如: 1m, 5m, 15m",
                    },
                },
                "required": ["query_type", "promql"],
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

            # Backup files before execution
            backup_info = {"backup_needed": False}
            mgr = RollbackManager(server.host, server.port, server.username, server.password)
            if not mgr.is_readonly(tool_args["command"]):
                backup_info = mgr.backup_before_execute(tool_args["command"])

            executor = create_ssh_executor(
                host=server.host, port=server.port,
                username=server.username, password=server.password,
            )
            result = executor.execute(tool_args["command"])
            if risk["risk"] == "warning":
                result["warning"] = f"注意: {risk['reason']}"
            result["backup_info"] = backup_info
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

        elif tool_name == "query_prometheus":
            client = create_prometheus_client()
            qtype = tool_args["query_type"]
            promql = tool_args["promql"]
            if qtype == "instant":
                result = client.instant_query(promql)
            else:
                start = tool_args.get("start", "-1h")
                end = tool_args.get("end", "now")
                step = tool_args.get("step", "1m")
                result = client.range_query(promql, start, end, step)
            # Simplify output - limit data points
            if result.get("success") and "data" in result:
                data = result["data"]
                if "data" in data and "result" in data["data"]:
                    results = data["data"]["result"]
                    # Truncate long time series
                    for r in results[:5]:
                        if "values" in r and len(r["values"]) > 30:
                            r["values"] = r["values"][:30]
                            r["truncated"] = True
            return result

        return {"success": False, "error": f"未知工具: {tool_name}"}

    def run(self, user_message: str, preview: bool = False) -> dict:
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
            max_iterations = 1 if preview else 5
            for _ in range(max_iterations):
                if not assistant_msg.tool_calls:
                    break

                for tool_call in assistant_msg.tool_calls:
                    func_name = tool_call.function.name
                    func_args = json.loads(tool_call.function.arguments)
                    logger.info(f"Tool call: {func_name}, args: {func_args}")

                    # Risk check before anything
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

                    # Preview mode: skip actual execution, mark as pending
                    if preview and func_name in ("ssh_execute", "winrm_execute"):
                        # Find server name for display
                        server = self.db.query(Server).filter(
                            Server.id == func_args.get("server_id")).first()
                        server_name = server.name if server else "未知"
                        tool_calls_log.append({
                            "tool": func_name,
                            "args": func_args,
                            "server": server_name,
                            "result": None,
                            "pending": True,
                        })
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(
                                {"status": "pending", "message": "等待确认执行"},
                                ensure_ascii=False),
                        })
                        continue

                    # Execute the tool
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
            has_pending = any(tc.get("pending") for tc in tool_calls_log)
            return {
                "reply": final_reply,
                "tool_calls": tool_calls_log,
                "success": True,
                "needs_approval": has_pending,
            }

        except Exception as e:
            logger.exception("Agent execution failed")
            return {
                "reply": f"执行出错: {str(e)}",
                "tool_calls": tool_calls_log,
                "success": False,
                "error": str(e),
            }
