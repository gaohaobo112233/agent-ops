import re

DANGEROUS_PATTERNS = [
    r"rm\s+-rf\s+/",
    r"rm\s+-rf\s+--no-preserve-root",
    r"mkfs\.",
    r"mkfs\s",
    r"format\s+[a-zA-Z]:",
    r"dd\s+if=",
    r">\s*/dev/sd",
    r"DROP\s+DATABASE",
    r"DROP\s+TABLE",
    r"TRUNCATE\s+TABLE",
    r"DELETE\s+FROM\s+\w+\s*;",
    r"shutdown\s+-",
    r"reboot",
    r"init\s+[06]",
    r"chmod\s+-R\s+777\s+/",
    r"chown\s+-R\s+\S+\s+/",
]

WARNING_PATTERNS = [
    (r"rm\s+", "删除文件操作"),
    (r"kill\s+-9", "强制杀进程"),
    (r"systemctl\s+stop", "停止服务"),
    (r"systemctl\s+restart", "重启服务"),
    (r"service\s+\S+\s+stop", "停止服务"),
    (r"service\s+\S+\s+restart", "重启服务"),
    (r"iptables\s+-", "修改防火墙规则"),
    (r"docker\s+rm", "删除容器"),
    (r"docker\s+rmi", "删除镜像"),
    (r"ALTER\s+TABLE", "修改数据库表结构"),
]


def check_command_risk(command: str) -> dict:
    """Check if a command is dangerous and requires approval.
    Returns: {"risk": "dangerous"|"warning"|"safe", "reason": "..."}
    """
    cmd_upper = command.upper()
    cmd_original = command

    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return {
                "risk": "dangerous",
                "reason": f"检测到高危命令模式: {pattern}",
                "blocked": True,
            }

    for pattern, desc in WARNING_PATTERNS:
        if re.search(pattern, cmd_original, re.IGNORECASE):
            return {
                "risk": "warning",
                "reason": desc,
                "blocked": False,
            }

    return {"risk": "safe", "reason": "", "blocked": False}
