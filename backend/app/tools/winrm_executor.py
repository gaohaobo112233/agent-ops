from winrm.protocol import Protocol


class WinRMExecutor:
    def __init__(self, host: str, port: int = 5985, username: str = "Administrator",
                 password: str = "", timeout: int = 30):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout

    def _get_endpoint(self) -> str:
        return f"http://{self.host}:{self.port}/wsman"

    def execute(self, command: str) -> dict:
        try:
            p = Protocol(
                endpoint=self._get_endpoint(),
                transport="ntlm",
                username=self.username,
                password=self.password,
                server_cert_validation="ignore",
                read_timeout=self.timeout,
                operation_timeout=self.timeout,
            )
            shell_id = p.open_shell()
            command_id = p.run_command(shell_id, command)
            stdout_text = b""
            stderr_text = b""
            exit_code = None

            while True:
                std_out, std_err, done = p.get_command_output(shell_id, command_id)
                stdout_text += std_out
                stderr_text += std_err
                if done:
                    exit_code = done
                    break

            p.cleanup_command(shell_id, command_id)
            p.close_shell(shell_id)
            p.close()

            stdout_decoded = stdout_text.decode("utf-8", errors="replace")
            stderr_decoded = stderr_text.decode("utf-8", errors="replace")
            return {
                "success": exit_code == 0,
                "exit_code": exit_code,
                "stdout": stdout_decoded.strip() or "(no output)",
                "stderr": stderr_decoded.strip() or "",
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

    def test_connection(self) -> dict:
        result = self.execute("echo WINRM_OK")
        if result["success"] and "WINRM_OK" in result["stdout"]:
            return {"connected": True, "message": f"WinRM 连接 {self.host} 成功"}
        return {"connected": False, "message": result["stderr"]}


def create_winrm_executor(host: str, port: int, username: str, password: str) -> WinRMExecutor:
    return WinRMExecutor(host=host, port=port, username=username, password=password)
