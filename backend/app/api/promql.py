from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from openai import OpenAI
from app.core.config import settings
from app.core.security import verify_token

router = APIRouter(prefix="/api/promql", tags=["PromQL生成"], dependencies=[Depends(verify_token)])

PROMPT_TEMPLATE = """你是一个 PromQL 专家。根据用户的自然语言描述，生成对应的 PromQL 查询语句。

## 常用指标
- CPU: node_cpu_seconds_total{mode="idle"}，使用率 = 100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)
- 内存: node_memory_MemTotal_bytes, node_memory_MemAvailable_bytes
- 磁盘: node_filesystem_size_bytes, node_filesystem_avail_bytes
- 网络: node_network_receive_bytes_total, node_network_transmit_bytes_total
- 磁盘IO: node_disk_read_bytes_total, node_disk_written_bytes_total
- 负载: node_load1, node_load5, node_load15
- 实例状态: up
- 按主机过滤用 {instance="IP:9100"}

## 要求
1. 只输出 PromQL 语句，不要解释，不要用markdown格式
2. 确保语法正确
3. 如果不确定用户意图，生成最合理的默认查询

## 用户需求
{user_input}"""


class PromQLRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=500, description="自然语言描述")


class PromQLResponse(BaseModel):
    promql: str
    explanation: Optional[str] = None


@router.post("/generate", response_model=PromQLResponse)
def generate_promql(req: PromQLRequest):
    client = OpenAI(
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_BASE_URL,
    )

    prompt = PROMPT_TEMPLATE.replace("{user_input}", req.text)

    try:
        response = client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": "你是一个 PromQL 专家，只输出 PromQL 语句，不解释。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=500,
        )
        promql = response.choices[0].message.content.strip()
        # Clean up markdown code blocks if LLM still adds them
        if promql.startswith("```"):
            lines = promql.split("\n")
            promql = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])
        promql = promql.strip()

        return PromQLResponse(promql=promql)
    except Exception as e:
        return PromQLResponse(
            promql=f"# 生成失败: {str(e)}",
            explanation=str(e),
        )
