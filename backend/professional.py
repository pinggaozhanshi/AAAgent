"""Professional-mode API: profile management, planning, DAG execution and telemetry."""

from __future__ import annotations

import asyncio
import json
import re
import time
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from database import connect_database
from prompts import build_executor_messages, build_planner_messages

router = APIRouter(prefix="/api", tags=["professional"])
MAX_PROFILES = 10
MAX_TASKS = 8
TIMEOUT_SECONDS = 120.0
credential_cache: dict[str, str] = {}
active_runs: dict[str, asyncio.Event] = {}


class ProfileRequest(BaseModel):
    id: str | None = None
    name: str = Field(min_length=1, max_length=80)
    role: Literal["planner", "executor", "both"] = "both"
    provider: str = Field(min_length=1, max_length=40)
    baseUrl: str = Field(min_length=8, max_length=500)
    model: str = Field(min_length=1, max_length=160)
    temperature: float = Field(default=0.7, ge=0, le=2)
    maxTokens: int = Field(default=2048, ge=1, le=16384)
    apiKey: str | None = Field(default=None, max_length=500)


class RunRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=30000)
    sessionId: str | None = None
    plannerProfileId: str | None = None
    executorProfileId: str
    mode: Literal["casual", "professional"] = "professional"
    tokenBudget: int | None = Field(default=None, ge=0)
    maxConcurrency: int = Field(default=2, ge=1, le=4)


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def rows(query: str, values: tuple = ()) -> list[dict[str, Any]]:
    with connect_database() as db:
        return [dict(row) for row in db.execute(query, values).fetchall()]


def row(query: str, values: tuple = ()) -> dict[str, Any] | None:
    result = rows(query, values)
    return result[0] if result else None


def execute(query: str, values: tuple = ()) -> None:
    with connect_database() as db:
        db.execute(query, values)


def event(run_id: str, kind: str, task_id: str | None = None, payload: dict | None = None) -> None:
    execute("INSERT INTO run_events(id, run_id, task_id, event_type, payload_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (str(uuid4()), run_id, task_id, kind, json.dumps(payload or {}, ensure_ascii=False), now()))


def public_profile(profile: dict[str, Any]) -> dict[str, Any]:
    output = dict(profile)
    output.pop("credential_ref", None)
    output["parameters"] = json.loads(output.pop("parameters_json", "{}"))
    output["hasSecret"] = bool(credential_cache.get(output["id"]))
    return output


def profile_for(profile_id: str | None, required_role: str) -> dict[str, Any]:
    if not profile_id:
        raise HTTPException(status_code=400, detail=f"请选择{required_role}方案。")
    profile = row("SELECT * FROM api_profiles WHERE id = ? AND is_archived = 0", (profile_id,))
    if not profile:
        raise HTTPException(status_code=404, detail="模型方案不存在。")
    if profile["role"] not in (required_role, "both"):
        raise HTTPException(status_code=400, detail="模型方案角色不匹配。")
    key = credential_cache.get(profile_id)
    if not key:
        raise HTTPException(status_code=400, detail="该方案的密钥仅在内存中保存。请在设置中重新输入 API Key 后保存。")
    profile["api_key"] = key
    profile["parameters"] = json.loads(profile["parameters_json"] or "{}")
    return profile


def snapshot(profile: dict[str, Any]) -> dict[str, Any]:
    return {"id": profile["id"], "name": profile["name"], "provider": profile["provider"],
            "baseUrl": profile["base_url"], "model": profile["model"], "parameters": profile["parameters"]}


@router.get("/profiles")
def list_profiles():
    return [public_profile(item) for item in rows("SELECT * FROM api_profiles WHERE is_archived = 0 ORDER BY updated_at DESC")]


@router.post("/profiles")
def save_profile(request: ProfileRequest):
    profile_id = request.id or str(uuid4())
    exists = row("SELECT id FROM api_profiles WHERE id = ?", (profile_id,))
    if not exists and row("SELECT COUNT(*) AS count FROM api_profiles WHERE is_archived = 0")["count"] >= MAX_PROFILES:
        raise HTTPException(status_code=400, detail=f"最多保存 {MAX_PROFILES} 个方案。")
    if request.apiKey and request.apiKey.strip():
        credential_cache[profile_id] = request.apiKey.strip()
    parameters = json.dumps({"temperature": request.temperature, "maxTokens": request.maxTokens})
    values = (request.name.strip(), request.role, request.provider.strip(), request.baseUrl.rstrip("/"), request.model.strip(), parameters, f"memory:{profile_id}", now())
    if exists:
        execute("UPDATE api_profiles SET name=?, role=?, provider=?, base_url=?, model=?, parameters_json=?, credential_ref=?, updated_at=? WHERE id=?", values + (profile_id,))
    else:
        execute("INSERT INTO api_profiles(id,name,role,provider,base_url,model,parameters_json,credential_ref,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)", (profile_id,) + values + (now(),))
    return public_profile(row("SELECT * FROM api_profiles WHERE id = ?", (profile_id,)))


@router.delete("/profiles/{profile_id}")
def archive_profile(profile_id: str):
    execute("UPDATE api_profiles SET is_archived=1, updated_at=? WHERE id=?", (now(), profile_id))
    credential_cache.pop(profile_id, None)
    return {"success": True}


@router.post("/profiles/{profile_id}/verify")
async def verify_profile(profile_id: str):
    profile = row("SELECT role FROM api_profiles WHERE id = ?", (profile_id,))
    target = profile_for(profile_id, "planner" if profile and profile["role"] == "planner" else "executor")
    try:
        data, _ = await model_call(target, [{"role": "user", "content": "Reply only with OK."}])
        execute("UPDATE api_profiles SET last_verified_at=?, last_error=NULL WHERE id=?", (now(), profile_id))
        return {"success": True, "reply": data.get("choices", [{}])[0].get("message", {}).get("content", "")[:80]}
    except Exception as exc:
        execute("UPDATE api_profiles SET last_error=? WHERE id=?", (str(exc)[:500], profile_id))
        raise HTTPException(status_code=400, detail=str(exc)) from exc
async def model_call(profile: dict[str, Any], messages: list[dict], json_mode: bool = False) -> tuple[dict, int]:
    parameters = profile["parameters"]
    max_tokens = parameters.get("maxTokens", 2048)
    payload = {"model": profile["model"], "messages": messages, "temperature": parameters.get("temperature", 0.7), "max_tokens": min(max_tokens, 1600) if json_mode else max_tokens, "stream": False}
    if json_mode and "deepseek.com" in profile["base_url"]:
        payload["response_format"] = {"type": "json_object"}
    started = time.perf_counter()
    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
        response = await client.post(f"{profile['base_url'].rstrip('/')}/chat/completions", headers={"Authorization": f"Bearer {profile['api_key']}", "Content-Type": "application/json"}, json=payload)
    latency = int((time.perf_counter() - started) * 1000)
    if response.status_code >= 400:
        raise RuntimeError(f"模型服务返回 {response.status_code}: {response.text[:400]}")
    return response.json(), latency


def usage(run_id: str, task_id: str | None, role: str, profile: dict[str, Any], payload: dict, latency: int) -> dict[str, Any]:
    raw = payload.get("usage") or {}
    input_tokens = raw.get("prompt_tokens", raw.get("input_tokens"))
    output_tokens = raw.get("completion_tokens", raw.get("output_tokens"))
    total_tokens = raw.get("total_tokens")
    if total_tokens is None and input_tokens is not None and output_tokens is not None:
        total_tokens = input_tokens + output_tokens
    source = "provider_reported" if total_tokens is not None else "estimated"
    item = {"id": str(uuid4()), "run_id": run_id, "task_id": task_id, "usage_role": role, "provider": profile["provider"], "model": profile["model"], "input_tokens": input_tokens, "output_tokens": output_tokens, "total_tokens": total_tokens, "usage_source": source, "latency_ms": latency, "completed_at": now()}
    execute("INSERT INTO usage_records(id,run_id,task_id,usage_role,provider,model,input_tokens,output_tokens,total_tokens,usage_source,latency_ms,completed_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", tuple(item.values()))
    event(run_id, "usage_recorded", task_id, item)
    return item


def fallback_graph(prompt: str) -> dict[str, Any]:
    """Produce a useful local DAG when planning is unavailable or malformed."""
    planning_words = ("计划", "步骤", "方案", "实现", "分析", "前端", "后端", "测试", "发布", "先", "再", "最后")
    if any(word in prompt for word in planning_words):
        return {"version": "1.0", "goal": prompt, "tasks": [
            {"id": "analysis", "title": "分析目标与约束", "instruction": "提取用户目标、核心功能、范围和关键限制。", "dependsOn": [], "acceptanceCriteria": ["列出核心目标", "明确约束"], "expectedOutput": "markdown", "riskLevel": "read_only"},
            {"id": "frontend", "title": "拆分前端任务", "instruction": "根据分析结果拆分界面、交互和状态管理任务。", "dependsOn": ["analysis"], "acceptanceCriteria": ["列出前端模块"], "expectedOutput": "markdown", "riskLevel": "read_only"},
            {"id": "backend", "title": "拆分后端任务", "instruction": "根据分析结果拆分接口、数据、服务和调度任务。", "dependsOn": ["analysis"], "acceptanceCriteria": ["列出后端模块"], "expectedOutput": "markdown", "riskLevel": "read_only"},
            {"id": "verify", "title": "制定验证与交付", "instruction": "整合前端和后端结果，制定测试、验收和发布步骤。", "dependsOn": ["frontend", "backend"], "acceptanceCriteria": ["给出测试清单", "给出交付顺序"], "expectedOutput": "markdown", "riskLevel": "read_only"}
        ]}
    return {"version": "1.0", "goal": prompt, "tasks": [{"id": "answer", "title": "完成用户请求", "instruction": prompt, "dependsOn": [], "acceptanceCriteria": ["直接回应用户目标并说明限制"], "expectedOutput": "markdown", "riskLevel": "read_only"}]}

def needs_plan(prompt: str) -> bool:
    words = ("计划", "步骤", "方案", "实现", "对比", "分析", "调研", "整理", "文件", "然后")
    return len(prompt) > 100 or any(word in prompt for word in words)


def parse_graph(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.I)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start >= 0 and end > start:
        cleaned = cleaned[start:end + 1]
    return validate_graph(json.loads(cleaned))


def validate_graph(graph: Any) -> dict[str, Any]:
    if not isinstance(graph, dict) or graph.get("version") != "1.0" or not isinstance(graph.get("goal"), str):
        raise ValueError("规划结果不是合法 TaskGraph。")
    tasks = graph.get("tasks")
    if not isinstance(tasks, list) or not 1 <= len(tasks) <= MAX_TASKS:
        raise ValueError("任务数量必须在 1 到 8 之间。")
    identifiers: set[str] = set()
    output: list[dict[str, Any]] = []
    for index, task in enumerate(tasks):
        identifier = task.get("id") if isinstance(task, dict) else None
        dependencies = task.get("dependsOn", []) if isinstance(task, dict) else []
        criteria = task.get("acceptanceCriteria", []) if isinstance(task, dict) else []
        if not isinstance(identifier, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", identifier) or identifier in identifiers:
            raise ValueError("任务 id 不合法或重复。")
        if not all(isinstance(item, str) for item in dependencies) or not isinstance(criteria, list) or not criteria:
            raise ValueError(f"任务 {identifier} 的依赖或验收标准不合法。")
        if not isinstance(task.get("title"), str) or not isinstance(task.get("instruction"), str):
            raise ValueError(f"任务 {identifier} 缺少标题或指令。")
        expected = task.get("expectedOutput", "markdown")
        risk = task.get("riskLevel", "read_only")
        if expected not in {"text", "markdown", "file", "structured_data"} or risk not in {"read_only", "confirm_before_write", "dangerous"}:
            raise ValueError(f"任务 {identifier} 的类型不支持。")
        identifiers.add(identifier)
        output.append({"id": identifier, "title": task["title"].strip()[:120], "instruction": task["instruction"].strip()[:6000], "dependsOn": dependencies, "acceptanceCriteria": [str(item).strip()[:500] for item in criteria], "expectedOutput": expected, "riskLevel": risk, "sequenceHint": index})
    mapping = {item["id"]: item for item in output}
    for item in output:
        if any(dep not in mapping or dep == item["id"] for dep in item["dependsOn"]):
            raise ValueError(f"任务 {item['id']} 存在不存在的依赖。")
    visiting, visited = set(), set()
    def visit(identifier: str) -> None:
        if identifier in visiting:
            raise ValueError("任务图存在循环依赖。")
        if identifier in visited:
            return
        visiting.add(identifier)
        for dependency in mapping[identifier]["dependsOn"]:
            visit(dependency)
        visiting.remove(identifier)
        visited.add(identifier)
    for identifier in mapping:
        visit(identifier)
    return {"version": "1.0", "goal": graph["goal"].strip()[:30000], "tasks": output}


def save_graph(run_id: str, graph: dict[str, Any]) -> None:
    public_graph = {**graph, "tasks": [{key: value for key, value in task.items() if key != "sequenceHint"} for task in graph["tasks"]]}
    readable = "\n\n".join([f"# 任务计划\n\n目标：{graph['goal']}"] + [f"## {task['title']}\n依赖：{'、'.join(task['dependsOn']) or '无'}\n验收：{'；'.join(task['acceptanceCriteria'])}" for task in graph["tasks"]])
    with connect_database() as db:
        db.execute("INSERT INTO task_graphs(id,run_id,graph_version,graph_json,readable_plan_markdown,validation_result_json,created_at) VALUES (?,?,?,?,?,?,?)", (str(uuid4()), run_id, "1.0", json.dumps(public_graph, ensure_ascii=False), readable, '{"valid":true}', now()))
        ids = {task["id"]: str(uuid4()) for task in graph["tasks"]}
        for index, task in enumerate(graph["tasks"]):
            db.execute("INSERT INTO tasks(id,run_id,sequence_hint,title,instruction,acceptance_criteria_json,expected_output,risk_level,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)", (ids[task["id"]], run_id, task.get("sequenceHint", index), task["title"], task["instruction"], json.dumps(task["acceptanceCriteria"], ensure_ascii=False), task["expectedOutput"], task["riskLevel"], "planned", now(), now()))
        for task in graph["tasks"]:
            for dependency in task["dependsOn"]:
                db.execute("INSERT INTO task_dependencies(task_id,prerequisite_task_id,created_at) VALUES (?,?,?)", (ids[task["id"]], ids[dependency], now()))
def build_visual_graph(tasks: list[dict[str, Any]], dependencies: list[dict[str, str]]) -> dict[str, Any]:
    """Create deterministic layered DAG layout data for the renderer."""
    prerequisites: dict[str, list[str]] = {task["id"]: [] for task in tasks}
    for edge in dependencies:
        prerequisites.setdefault(edge["task_id"], []).append(edge["prerequisite_task_id"])
    by_id = {task["id"]: task for task in tasks}
    levels: dict[str, int] = {}

    def level(task_id: str) -> int:
        if task_id in levels:
            return levels[task_id]
        parents = prerequisites.get(task_id, [])
        levels[task_id] = 0 if not parents else max(level(parent) + 1 for parent in parents)
        return levels[task_id]

    lanes: dict[int, list[str]] = {}
    for task in tasks:
        lanes.setdefault(level(task["id"]), []).append(task["id"])
    nodes = []
    for lane, task_ids in lanes.items():
        for row_index, task_id in enumerate(task_ids):
            task = by_id[task_id]
            nodes.append({"id": task_id, "x": 48 + lane * 268, "y": 48 + row_index * 154, "width": 220, "height": 112, "status": task["status"], "title": task["title"], "durationMs": task["duration_ms"]})
    edges = []
    for edge in dependencies:
        source = by_id[edge["prerequisite_task_id"]]
        target = by_id[edge["task_id"]]
        if source["status"] == "completed":
            state = "complete"
        elif target["status"] == "running":
            state = "active"
        else:
            state = "pending"
        edges.append({"source": source["id"], "target": target["id"], "state": state})
    return {"nodes": nodes, "edges": edges, "width": max(560, 96 + (max(lanes, default=0) + 1) * 268), "height": max(260, 96 + max((len(items) for items in lanes.values()), default=1) * 154)}

def graph_view(run_id: str) -> dict[str, Any]:
    graph = row("SELECT * FROM task_graphs WHERE run_id=?", (run_id,))
    if not graph:
        raise HTTPException(status_code=404, detail="任务图不存在。")
    task_rows = rows("SELECT * FROM tasks WHERE run_id=? ORDER BY sequence_hint", (run_id,))
    for task in task_rows:
        task["acceptanceCriteria"] = json.loads(task.pop("acceptance_criteria_json"))
    dependencies = rows("SELECT task_id,prerequisite_task_id FROM task_dependencies WHERE task_id IN (SELECT id FROM tasks WHERE run_id=?)", (run_id,))
    return {"runId": run_id, "graph": json.loads(graph["graph_json"]), "tasks": task_rows, "dependencies": dependencies, "visual": build_visual_graph(task_rows, dependencies)}


@router.get("/runs/{run_id}/graph")
def get_graph(run_id: str):
    return graph_view(run_id)


@router.get("/runs/{run_id}/usage")
def get_usage(run_id: str):
    records = rows("SELECT * FROM usage_records WHERE run_id=? ORDER BY completed_at", (run_id,))
    return {"records": records, "totalTokens": sum(item["total_tokens"] or 0 for item in records)}


def ready_tasks(run_id: str) -> list[dict[str, Any]]:
    return rows("""SELECT t.* FROM tasks t WHERE t.run_id=? AND t.status='planned'
                   AND NOT EXISTS (SELECT 1 FROM task_dependencies d JOIN tasks p ON p.id=d.prerequisite_task_id
                   WHERE d.task_id=t.id AND p.status<>'completed') ORDER BY t.sequence_hint""", (run_id,))


def dependency_summaries(task_id: str) -> list[str]:
    results = rows("""SELECT p.title,p.output_summary FROM task_dependencies d JOIN tasks p ON p.id=d.prerequisite_task_id
                      WHERE d.task_id=? ORDER BY p.sequence_hint""", (task_id,))
    return [f"{item['title']}: {item['output_summary'] or '无摘要'}" for item in results]


async def execute_task(run_id: str, task: dict[str, Any], executor: dict[str, Any], goal: str, stop: asyncio.Event) -> tuple[str, dict[str, Any]]:
    execute("UPDATE tasks SET status='running',attempt_count=attempt_count+1,started_at=?,updated_at=? WHERE id=?", (now(), now(), task["id"]))
    event(run_id, "task_started", task["id"], {"title": task["title"]})
    contract = {"title": task["title"], "instruction": task["instruction"], "acceptance_criteria": json.loads(task["acceptance_criteria_json"]), "expected_output": task["expected_output"]}
    started = time.perf_counter()
    data, latency = await model_call(executor, build_executor_messages(contract, dependency_summaries(task["id"]), goal))
    if stop.is_set():
        raise asyncio.CancelledError()
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    if not content:
        raise RuntimeError("执行模型没有返回内容。")
    duration = int((time.perf_counter() - started) * 1000)
    record = usage(run_id, task["id"], "executor", executor, data, latency)
    with connect_database() as db:
        db.execute("UPDATE tasks SET status='completed',output_summary=?,finished_at=?,duration_ms=?,updated_at=? WHERE id=?", (content[:1000], now(), duration, now(), task["id"]))
        db.execute("INSERT INTO task_artifacts(id,task_id,kind,content_text,summary,created_at) VALUES (?,?,'markdown',?,?,?)", (str(uuid4()), task["id"], content, content[:500], now()))
    event(run_id, "task_completed", task["id"], {"durationMs": duration, "summary": content[:500]})
    return content, record


@router.post("/runs/{run_id}/cancel")
def cancel_run(run_id: str):
    stop = active_runs.get(run_id)
    if stop:
        stop.set()
    execute("UPDATE runs SET status='cancelled',cancel_requested_at=?,finished_at=? WHERE id=? AND status IN ('planning','running','awaiting_approval')", (now(), now(), run_id))
    event(run_id, "run_cancelled")
    return {"success": True}


@router.post("/runs/stream")
async def stream_run(request: RunRequest):
    planner = profile_for(request.plannerProfileId, "planner") if request.plannerProfileId else None
    executor = profile_for(request.executorProfileId, "executor")
    session_id = request.sessionId or str(uuid4())
    if not row("SELECT id FROM sessions WHERE id=?", (session_id,)):
        execute("INSERT INTO sessions(id,title,mode,created_at,updated_at) VALUES (?,?,?,?,?)", (session_id, request.prompt[:48], request.mode, now(), now()))
    else:
        execute("UPDATE sessions SET updated_at=? WHERE id=?", (now(), session_id))
    user_message_id = str(uuid4())
    execute("INSERT INTO messages(id,session_id,role,content,metadata_json,created_at) VALUES (?,?, 'user', ?, '{}', ?)", (user_message_id, session_id, request.prompt, now()))
    run_id = str(uuid4())
    execute("INSERT INTO runs(id,session_id,user_message_id,mode,status,planner_profile_id,executor_profile_id,planner_profile_snapshot_json,executor_profile_snapshot_json,token_budget,started_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)", (run_id, session_id, user_message_id, request.mode, "planning", request.plannerProfileId, request.executorProfileId, json.dumps(snapshot(planner), ensure_ascii=False) if planner else None, json.dumps(snapshot(executor), ensure_ascii=False), request.tokenBudget, now()))
    event(run_id, "run_started", payload={"sessionId": session_id})
    stop = asyncio.Event()
    active_runs[run_id] = stop

    async def stream():
        def emit(kind: str, payload: dict) -> str:
            return f"data: {json.dumps({'type': kind, **payload}, ensure_ascii=False)}\n\n"
        try:
            yield emit("run", {"runId": run_id, "sessionId": session_id, "status": "planning"})
            graph = fallback_graph(request.prompt)
            planner_usage = None
            if planner and request.mode == "professional":
                try:
                    data, latency = await model_call(planner, build_planner_messages(request.prompt, request.prompt[:12000]), json_mode=True)
                    planner_usage = usage(run_id, None, "planner", planner, data, latency)
                    graph = parse_graph(data.get("choices", [{}])[0].get("message", {}).get("content", ""))
                    event(run_id, "plan_created", payload={"source": "planner", "taskCount": len(graph["tasks"])})
                except Exception as exc:
                    event(run_id, "plan_invalid", payload={"error": str(exc)[:500]})
                    event(run_id, "plan_created", payload={"source": "local_fallback", "taskCount": len(graph["tasks"])})
            else:
                event(run_id, "plan_created", payload={"source": "fallback", "taskCount": 1})
            if stop.is_set():
                raise asyncio.CancelledError()
            save_graph(run_id, graph)
            yield emit("graph", graph_view(run_id))
            if planner_usage:
                yield emit("usage", planner_usage)
            execute("UPDATE runs SET status='running' WHERE id=?", (run_id,))
            outputs: list[str] = []
            while not stop.is_set():
                batch = ready_tasks(run_id)[:request.maxConcurrency]
                if not batch:
                    break
                for task in batch:
                    execute("UPDATE tasks SET status='ready',updated_at=? WHERE id=?", (now(), task["id"]))
                    event(run_id, "task_ready", task["id"], {"title": task["title"]})
                    yield emit("task", {"taskId": task["id"], "status": "ready", "title": task["title"]})
                    yield emit("task", {"taskId": task["id"], "status": "running", "title": task["title"]})
                results = await asyncio.gather(*(execute_task(run_id, task, executor, request.prompt, stop) for task in batch), return_exceptions=True)
                failed = False
                for task, result in zip(batch, results):
                    if isinstance(result, asyncio.CancelledError):
                        raise result
                    if isinstance(result, Exception):
                        failed = True
                        execute("UPDATE tasks SET status='failed',error_summary=?,finished_at=?,updated_at=? WHERE id=?", (str(result)[:500], now(), now(), task["id"]))
                        event(run_id, "task_failed", task["id"], {"error": str(result)[:500]})
                        yield emit("task", {"taskId": task["id"], "status": "failed", "error": str(result)[:500]})
                    else:
                        content, record = result
                        outputs.append(content)
                        yield emit("task", {"taskId": task["id"], "status": "completed", "title": task["title"], "summary": content[:1000]})
                        yield emit("usage", record)
                if failed:
                    execute("UPDATE tasks SET status='blocked',updated_at=? WHERE run_id=? AND status='planned'", (now(), run_id))
                    break
            if stop.is_set():
                execute("UPDATE tasks SET status='cancelled',updated_at=? WHERE run_id=? AND status IN ('planned','ready','running')", (now(), run_id))
                execute("UPDATE runs SET status='cancelled',finished_at=? WHERE id=?", (now(), run_id))
                yield emit("done", {"runId": run_id, "interrupted": True})
                return
            if row("SELECT COUNT(*) AS count FROM tasks WHERE run_id=? AND status='failed'", (run_id,))["count"]:
                execute("UPDATE runs SET status='failed',finished_at=?,error_summary=? WHERE id=?", (now(), "至少一个任务执行失败。", run_id))
                yield emit("error", {"runId": run_id, "error": "任务执行失败，请查看任务图。"})
                return
            answer = "\n\n".join(outputs) or "任务没有返回可展示的结果。"
            execute("INSERT INTO messages(id,session_id,role,content,metadata_json,created_at) VALUES (?,?, 'assistant', ?, ?, ?)", (str(uuid4()), session_id, answer, json.dumps({"runId": run_id}), now()))
            execute("UPDATE runs SET status='completed',finished_at=? WHERE id=?", (now(), run_id))
            event(run_id, "run_completed", payload={"taskCount": len(outputs)})
            yield emit("chunk", {"content": answer})
            yield emit("done", {"runId": run_id, "interrupted": False})
        except asyncio.CancelledError:
            execute("UPDATE runs SET status='cancelled',finished_at=? WHERE id=?", (now(), run_id))
            yield emit("done", {"runId": run_id, "interrupted": True})
        except Exception as exc:
            execute("UPDATE runs SET status='failed',finished_at=?,error_summary=? WHERE id=?", (now(), str(exc)[:500], run_id))
            event(run_id, "run_failed", payload={"error": str(exc)[:500]})
            yield emit("error", {"runId": run_id, "error": str(exc)[:500]})
        finally:
            active_runs.pop(run_id, None)

    from fastapi.responses import StreamingResponse
    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
