import requests
import math
from app.core.config import settings


class PrometheusClient:
    """Query Prometheus API for metrics."""

    def __init__(self, base_url: str = "http://127.0.0.1:9090", timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _get(self, endpoint: str, params: dict = None) -> dict:
        url = f"{self.base_url}/api/v1/{endpoint}"
        try:
            r = requests.get(url, params=params, timeout=self.timeout)
            r.raise_for_status()
            return {"success": True, "data": r.json()}
        except requests.ConnectionError:
            return {"success": False, "error": f"无法连接 Prometheus: {self.base_url}，请确认 Prometheus 已启动且地址正确"}
        except Exception as e:
            return {"success": False, "error": f"Prometheus 查询失败: {str(e)}"}

    def instant_query(self, query: str) -> dict:
        """Run an instant PromQL query."""
        return self._get("query", {"query": query})

    def range_query(self, query: str, start: str, end: str, step: str = "1m") -> dict:
        """Run a range PromQL query. Time format: Unix timestamp or RFC3339."""
        return self._get("query_range", {
            "query": query,
            "start": start,
            "end": end,
            "step": step,
        })

    def list_targets(self) -> dict:
        """List all scrape targets and their health status."""
        return self._get("targets")

    def list_metrics(self, limit: int = 50) -> dict:
        """List available metric names."""
        result = self._get("label/__name__/values")
        if result["success"]:
            names = result["data"].get("data", [])
            result["data"] = names[:limit]
        return result


# Common PromQL snippets for easier use
METRIC_HELP = """
常用 PromQL 查询:
- CPU使用率: 100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)
- 内存使用率: (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100
- 磁盘使用率: (1 - (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"})) * 100
- 磁盘读写: rate(node_disk_read_bytes_total[5m]) 和 rate(node_disk_written_bytes_total[5m])
- 网络流量: rate(node_network_receive_bytes_total[5m]) 和 rate(node_network_transmit_bytes_total[5m])
- 系统负载: node_load1, node_load5, node_load15
- 按IP过滤: 在所有查询后加 {instance="IP:9100"}，如 node_cpu_seconds_total{instance="192.168.1.10:9100"}
"""


def create_prometheus_client(base_url: str = None) -> PrometheusClient:
    url = base_url or getattr(settings, 'PROMETHEUS_URL', 'http://127.0.0.1:9090')
    return PrometheusClient(base_url=url)
