from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from app.core.security import verify_token
from app.tools.prometheus import create_prometheus_client

router = APIRouter(prefix="/api/monitor", tags=["监控"], dependencies=[Depends(verify_token)])


class PrometheusQuery(BaseModel):
    query: str = Field(..., min_length=1, description="PromQL 查询语句")
    query_type: str = Field(default="instant", pattern="^(instant|range)$")
    start: Optional[str] = None
    end: Optional[str] = None
    step: Optional[str] = None


@router.post("/query")
def run_query(req: PrometheusQuery):
    client = create_prometheus_client()
    if req.query_type == "range":
        result = client.range_query(
            req.query,
            req.start or "-1h",
            req.end or "now",
            req.step or "1m",
        )
    else:
        result = client.instant_query(req.query)
    return result


@router.get("/targets")
def list_targets():
    client = create_prometheus_client()
    return client.list_targets()
