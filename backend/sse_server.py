"""
AAAgent SSE Backend
FastAPI server with Server-Sent Events (SSE) for streaming LLM responses.
"""

import json
import os
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from database import initialize_database
from professional import router as professional_router

load_dotenv()

# ========== 配置 ==========
DEFAULT_BASE_URL = os.getenv("AAAGENT_BASE_URL", "https://api.openai.com/v1")
DEFAULT_API_KEY = os.getenv("AAAGENT_API_KEY", "")
DEFAULT_MODEL = os.getenv("AAAGENT_MODEL", "gpt-4o-mini")
MAX_TIMEOUT = 120.0  # 秒

# 存储活跃连接，用于中断生成
active_streams: dict[str, asyncio.Event] = {}


# ========== 数据模型 ==========
class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    provider: str = "openai"
    baseUrl: Optional[str] = None
    apiKey: Optional[str] = None
    model: Optional[str] = None
    temperature: float = 0.7
    maxTokens: int = 2048
    stream: bool = True
    sessionId: Optional[str] = None  # 用于中断


class StreamChunk(BaseModel):
    type: str = "chunk"
    content: str = ""
    done: bool = False
    usage: Optional[dict] = None
    error: Optional[str] = None


# ========== 生命周期 ==========
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动/关闭生命周期"""
    initialize_database()
    print("AAAgent SSE Backend started")
    yield
    # 关闭时取消所有活跃流
    for event in active_streams.values():
        event.set()
    active_streams.clear()
    print("AAAgent SSE Backend stopped")


app = FastAPI(
    title="AAAgent SSE Backend",
    description="Streaming LLM API via Server-Sent Events",
    version="0.1.3",
    lifespan=lifespan,
)

# CORS 配置 — 允许前端跨域访问
app.include_router(professional_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制为具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== 辅助函数 ==========
def get_config(req: ChatRequest) -> tuple[str, str, str]:
    """解析请求中的配置，使用默认值填充"""
    base_url = (req.baseUrl or DEFAULT_BASE_URL).rstrip("/")
    api_key = req.apiKey or DEFAULT_API_KEY
    model = req.model or DEFAULT_MODEL
    if not api_key:
        raise ValueError("API Key is required. Set it in request or environment variable AAAGENT_API_KEY.")
    return base_url, api_key, model


async def stream_llm(
    client: httpx.AsyncClient,
    endpoint: str,
    headers: dict,
    payload: dict,
    stop_event: asyncio.Event,
) -> AsyncGenerator[str, None]:
    """
    调用 LLM API 并逐块转发 SSE 数据
    """
    try:
        async with client.stream("POST", endpoint, headers=headers, json=payload, timeout=MAX_TIMEOUT) as response:
            if response.status_code != 200:
                error_text = await response.aread()
                yield f"data: {json.dumps({'type': 'error', 'error': f'API returned {response.status_code}: {error_text.decode()}'})}\n\n"
                return

            # 逐行读取 SSE 流
            async for line in response.aiter_lines():
                # 检查是否收到中断信号
                if stop_event.is_set():
                    yield f"data: {json.dumps({'type': 'chunk', 'content': '', 'done': True, 'interrupted': True})}\n\n"
                    return

                if not line.strip():
                    continue
                if line.startswith("data: "):
                    data = line[6:].strip()
                    if data == "[DONE]":
                        yield f"data: {json.dumps({'type': 'chunk', 'content': '', 'done': True})}\n\n"
                        return
                    try:
                        chunk = json.loads(data)
                        # OpenAI 格式: choices[0].delta.content
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield f"data: {json.dumps({'type': 'chunk', 'content': content, 'done': False})}\n\n"
                    except json.JSONDecodeError:
                        continue

    except httpx.ConnectError as e:
        yield f"data: {json.dumps({'type': 'error', 'error': f'Connection failed: {str(e)}'})}\n\n"
    except httpx.TimeoutException:
        yield f"data: {json.dumps({'type': 'error', 'error': 'Request timeout. The model took too long to respond.'})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'error': f'Unexpected error: {str(e)}'})}\n\n"


# ========== SSE 端点 ==========
@app.post("/chat/stream")
async def chat_stream(request: Request, req: ChatRequest):
    """
    SSE 流式对话端点
    接收 ChatRequest，通过 SSE 逐字返回 LLM 输出
    """
    try:
        base_url, api_key, model = get_config(req)
    except ValueError as e:
        return StreamingResponse(
            iter([f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"]),
            media_type="text/event-stream",
        )

    # 准备请求体
    endpoint = f"{base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": m.role, "content": m.content} for m in req.messages],
        "temperature": req.temperature,
        "max_tokens": req.maxTokens,
        "stream": True,
    }

    # 为当前会话创建中断事件
    session_id = req.sessionId or f"anon_{id(request)}"
    stop_event = asyncio.Event()
    active_streams[session_id] = stop_event

    async def event_generator():
        async with httpx.AsyncClient() as client:
            try:
                async for chunk in stream_llm(client, endpoint, headers, payload, stop_event):
                    yield chunk
            finally:
                active_streams.pop(session_id, None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
        },
    )


@app.post("/chat/stop")
async def stop_generation(req: ChatRequest):
    """
    中断指定会话的生成
    """
    session_id = req.sessionId or ""
    event = active_streams.get(session_id)
    if event:
        event.set()
        active_streams.pop(session_id, None)
        return {"success": True, "message": "Generation stopped."}
    return {"success": False, "message": "No active stream found for this session."}


# ========== 健康检查 ==========
@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.3"}


# ========== 静态文件服务（前端）==========
import os
frontend_dir = os.path.join(os.path.dirname(__file__), '..', 'src', 'ui')
if os.path.exists(frontend_dir):
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="static")

# ========== 运行入口 ==========
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "sse_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
