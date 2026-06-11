import paramiko
import time


class SSHExecutor:
    def __init__(self, host: str, port: int = 22, username: str = "root",
                 password: str = "", timeout: int = 30):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout

    def execute(self, command: str) -> dict:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=self.timeout,
            )
            stdin, stdout, stderr = client.exec_command(command, timeout=60)
            exit_code = stdout.channel.recv_exit_status()
            stdout_text = stdout.read().decode("utf-8", errors="replace")
            stderr_text = stderr.read().decode("utf-8", errors="replace")
            return {
                "success": exit_code == 0,
                "exit_code": exit_code,
                "stdout": stdout_text.strip() or "(no output)",
                "stderr": stderr_text.strip() or "",
                "host": self.host,
            }
        except Exception as e:
            return {
                "success": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
                "host": self.host,
            }
        finally:
            client.close()

    def test_connection(self) -> dict:
        result = self.execute("echo 'SSH_OK'")
        if result["success"] and "SSH_OK" in result["stdout"]:
            return {"connected": True, "message": f"SSH 连接 {self.host} 成功"}
        return {"connected": False, "message": result["stderr"]}


def create_ssh_executor(host: str, port: int, username: str, password: str) -> SSHExecutor:
    return SSHExecutor(host=host, port=port, username=username, password=password)
