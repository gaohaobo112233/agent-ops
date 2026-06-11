import re
import logging
from app.tools.ssh_executor import create_ssh_executor

logger = logging.getLogger(__name__)

# Patterns for commands that modify files
FILE_MODIFY_PATTERNS = [
    (r'(?:^|\s)sed\s+.*\s+(\S+)', 'sed 修改文件'),       # sed -i file
    (r'>>\s*(\S+)', '追加文件'),                           # >> file
    (r'(?:^|\s)>\s*(\S+)', '覆盖文件'),                    # > file  (not >>, not 2>)
    (r'(?:^|\s)rm\s+.*\s+(\S+)', '删除文件'),              # rm file
    (r'(?:^|\s)mv\s+(\S+)', '移动/重命名文件'),            # mv source dest
    (r'(?:^|\s)cp\s+.*\s+(\S+)', '复制覆盖文件'),          # cp source dest
]

# Patterns for commands that are read-only (no backup needed)
READONLY_PATTERNS = [
    r'^(df|du|free|top|ps|ls|cat|head|tail|less|grep|find|which|echo|whoami|hostname|date|uptime|uname|who|w|netstat|ss|ifconfig|ip\s+addr|ping|curl|wget\s+-O-|systemctl\s+status|journalctl)',
]


class RollbackManager:
    """Manage rollback backups for file-modifying commands."""

    BACKUP_DIR = "/tmp/agent-ops-rollback"

    def __init__(self, ssh_host: str, ssh_port: int, ssh_user: str, ssh_password: str):
        self.host = ssh_host
        self.port = ssh_port
        self.username = ssh_user
        self.password = ssh_password

    def _exec(self, command: str, timeout: int = 10) -> dict:
        exe = create_ssh_executor(self.host, self.port, self.username, self.password)
        return exe.execute(command)

    def _detect_affected_files(self, command: str) -> list:
        """Detect which files might be modified by the command."""
        affected = []
        for pattern, desc in FILE_MODIFY_PATTERNS:
            matches = re.findall(pattern, command)
            for m in matches:
                if m and not m.startswith('/dev/') and not m.startswith('/proc/') and not m.startswith('/sys/'):
                    affected.append({"path": m, "operation": desc})
        return affected

    def is_readonly(self, command: str) -> bool:
        """Check if a command is read-only (no backup needed)."""
        for pattern in READONLY_PATTERNS:
            if re.match(pattern, command.strip()):
                return True
        return False

    def backup_before_execute(self, command: str) -> dict:
        """Backup files that might be modified by the command. Returns backup info."""
        if self.is_readonly(command):
            return {"backup_needed": False, "reason": "只读操作，无需备份"}

        affected = self._detect_affected_files(command)
        if not affected:
            return {"backup_needed": False, "reason": "未检测到文件修改操作"}

        backup_id = f"rb_{id(command) % 1000000:06d}"
        backup_path = f"{self.BACKUP_DIR}/{backup_id}"
        backed_up = []
        failed = []

        self._exec(f"mkdir -p {backup_path}", timeout=5)

        for f_info in affected:
            filepath = f_info["path"]
            result = self._exec(f"test -f {filepath} && cp -p {filepath} {backup_path}/$(echo {filepath} | tr '/' '_') && echo OK || echo SKIP", timeout=5)
            if "OK" in result.get("stdout", ""):
                backed_up.append({"path": filepath, "operation": f_info["operation"]})
            else:
                failed.append(filepath)

        if backed_up:
            self._exec(f"chmod -R 700 {backup_path}", timeout=5)

        return {
            "backup_needed": True,
            "backup_id": backup_id,
            "backup_path": backup_path,
            "backed_up": backed_up,
            "failed": failed,
        }

    def restore(self, backup_id: str) -> dict:
        """Restore files from a backup."""
        backup_path = f"{self.BACKUP_DIR}/{backup_id}"
        result = self._exec(f"ls {backup_path} 2>&1", timeout=5)
        if "No such file" in result.get("stderr", "") or "cannot access" in result.get("stderr", ""):
            return {"success": False, "error": f"备份 {backup_id} 不存在，可能已被清理"}

        restore_result = self._exec(
            f'for f in {backup_path}/*; do '
            f'original=$(echo "$(basename $f)" | tr "_" "/"); '
            f'cp -p "$f" "/$original" && echo "RESTORED: /$original"; '
            f'done && rm -rf {backup_path}',
            timeout=30)
        return {
            "success": restore_result["success"],
            "output": restore_result["stdout"],
            "error": restore_result["stderr"],
        }

    def get_backup_info(self, backup_id: str) -> dict:
        """Get info about a backup."""
        backup_path = f"{self.BACKUP_DIR}/{backup_id}"
        result = self._exec(f"ls -la {backup_path} 2>&1 && echo '---' && cat {backup_path}/* 2>&1 | head -50", timeout=5)
        return {"files": result.get("stdout", "")}

    def cleanup_old_backups(self, max_age_hours: int = 24):
        """Clean up backups older than N hours."""
        self._exec(f"find {self.BACKUP_DIR} -type d -mmin +{max_age_hours * 60} -exec rm -rf {{}} + 2>/dev/null", timeout=5)
