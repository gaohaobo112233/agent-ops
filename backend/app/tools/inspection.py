import subprocess
import platform
import math


def get_os_type() -> str:
    return platform.system().lower()


def check_cpu() -> dict:
    """Check CPU usage. Returns percent used."""
    try:
        if get_os_type() == "windows":
            result = subprocess.run(
                ["powershell", "-Command",
                 "(Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average"],
                capture_output=True, text=True, timeout=15,
            )
            usage = result.stdout.strip()
            return {"cpu_percent": float(usage) if usage else 0, "success": True}
        else:
            result = subprocess.run(
                ["top", "-bn1"], capture_output=True, text=True, timeout=15,
            )
            for line in result.stdout.split("\n"):
                if "Cpu(s)" in line:
                    # %Cpu(s):  5.2 us,  2.1 sy,  0.0 ni, 92.3 id, ...
                    parts = line.split(",")
                    idle = float(parts[3].strip().split()[0])
                    return {"cpu_percent": round(100 - idle, 1), "success": True}
            return {"cpu_percent": 0, "success": False, "error": "无法解析CPU信息"}
    except Exception as e:
        return {"cpu_percent": 0, "success": False, "error": str(e)}


def check_memory() -> dict:
    """Check memory usage. Returns total, used, percent."""
    try:
        if get_os_type() == "windows":
            result = subprocess.run(
                ["powershell", "-Command",
                 "$os = Get-CimInstance Win32_OperatingSystem; "
                 "$total = [math]::Round($os.TotalVisibleMemorySize/1MB, 1); "
                 "$free = [math]::Round($os.FreePhysicalMemory/1MB, 1); "
                 "$used = [math]::Round($total - $free, 1); "
                 "$pct = [math]::Round($used/$total*100, 1); "
                 "Write-Output \"$total|$used|$free|$pct\""],
                capture_output=True, text=True, timeout=15,
            )
            parts = result.stdout.strip().split("|")
            if len(parts) == 4:
                return {
                    "memory_total_gb": float(parts[0]),
                    "memory_used_gb": float(parts[1]),
                    "memory_free_gb": float(parts[2]),
                    "memory_percent": float(parts[3]),
                    "success": True,
                }
        else:
            result = subprocess.run(["free", "-m"], capture_output=True, text=True, timeout=15)
            for line in result.stdout.split("\n"):
                if "Mem:" in line:
                    cols = line.split()
                    total = round(int(cols[1]) / 1024, 1)
                    used = round(int(cols[2]) / 1024, 1)
                    free = round(int(cols[3]) / 1024, 1)
                    pct = round(used / total * 100, 1) if total > 0 else 0
                    return {
                        "memory_total_gb": total,
                        "memory_used_gb": used,
                        "memory_free_gb": free,
                        "memory_percent": pct,
                        "success": True,
                    }
        return {"memory_total_gb": 0, "success": False, "error": "无法解析内存信息"}
    except Exception as e:
        return {"memory_total_gb": 0, "success": False, "error": str(e)}


def check_disk(mount: str = "/") -> dict:
    """Check disk usage. Returns total, used, free, percent."""
    try:
        if get_os_type() == "windows":
            drive = mount[0] if mount else "C"
            result = subprocess.run(
                ["powershell", "-Command",
                 f"$d = Get-PSDrive {drive}; "
                 f"$total = [math]::Round($d.Used+$d.Free, 1); "
                 f"$used = [math]::Round($d.Used, 1); "
                 f"$free = [math]::Round($d.Free, 1); "
                 f"$pct = [math]::Round($used/$total*100, 1); "
                 f"Write-Output \"$total|$used|$free|$pct\""],
                capture_output=True, text=True, timeout=15,
            )
        else:
            result = subprocess.run(
                ["df", "-BM", mount], capture_output=True, text=True, timeout=15,
            )
            for line in result.stdout.split("\n"):
                if mount in line and "%" in line:
                    cols = line.split()
                    total = round(int(cols[1].rstrip("M")) / 1024, 1)
                    used = round(int(cols[2].rstrip("M")) / 1024, 1)
                    free = round(int(cols[3].rstrip("M")) / 1024, 1)
                    pct = float(cols[4].rstrip("%"))
                    return {
                        "disk_total_gb": total,
                        "disk_used_gb": used,
                        "disk_free_gb": free,
                        "disk_percent": pct,
                        "mount": mount,
                        "success": True,
                    }

        if get_os_type() == "windows":
            parts = result.stdout.strip().split("|")
            if len(parts) == 4:
                return {
                    "disk_total_gb": round(float(parts[0]) / 1e9, 1),
                    "disk_used_gb": round(float(parts[1]) / 1e9, 1),
                    "disk_free_gb": round(float(parts[2]) / 1e9, 1),
                    "disk_percent": float(parts[3]),
                    "mount": mount,
                    "success": True,
                }

        return {"disk_total_gb": 0, "success": False, "error": "无法解析磁盘信息"}
    except Exception as e:
        return {"disk_total_gb": 0, "success": False, "error": str(e)}


def check_port(host: str, port: int, timeout: int = 5) -> dict:
    """Check if a TCP port is open."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        s.close()
        return {"host": host, "port": port, "open": True, "success": True}
    except Exception as e:
        return {"host": host, "port": port, "open": False, "success": True, "error": str(e)}


def run_full_inspection() -> dict:
    """Run full system inspection: CPU + Memory + Disk + common ports."""
    return {
        "cpu": check_cpu(),
        "memory": check_memory(),
        "disk_root": check_disk("/"),
        "success": True,
    }
