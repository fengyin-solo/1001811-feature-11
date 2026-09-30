"""公众诉求接口：维护诉求记录，覆盖受理诉求、提交回复、关闭诉求等动作。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.schemas import ActionResult, EntryPayload, PageResult
from app.services.complaint import ComplaintService

router = APIRouter(prefix="/api/complaint", tags=["公众诉求"])

service = ComplaintService()

LIST_FIELDS = ["诉求编号", "诉求来源", "诉求内容", "涉及管段", "受理人员", "处理措施", "办理期限", "诉求状态"]
STATUSES = ["待受理", "办理中", "已回复", "已关闭"]


@router.get("", response_model=PageResult[dict])
def list_entries(
    keyword: str | None = Query(default=None, description="按诉求编号、来源或内容检索"),
    status: str | None = Query(default=None, description="待受理、办理中、已回复、已关闭"),
    scope: str = Query(default="todo", description="todo 为待办清单，all 为全部诉求"),
    page: int = 1,
    size: int = 20,
) -> PageResult[dict]:
    """按关键词、状态与清单范围过滤公众诉求；没有数据时返回空页，不报错。"""
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    if scope not in {"todo", "all"}:
        scope = "todo"
    items, total = service.list_entries(
        keyword=keyword,
        status=status,
        scope=scope,
        page=page,
        size=size,
    )
    return PageResult(items=items, total=total, page=page, size=size)


@router.get("/export")
def export_entries() -> dict[str, Any]:
    """导出公众诉求清单：返回当前默认待办范围的全量数据。"""
    items, total = service.list_entries(scope="todo", page=1, size=10000)
    return {"module": "complaint", "total": total, "items": items}


@router.get("/{entry_id}", response_model=dict)
def get_entry(entry_id: int) -> dict:
    """读取单条诉求记录明细；不存在时给出可读的错误说明。"""
    entry = service.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"诉求记录 {entry_id} 不存在或已归档")
    return entry


@router.post("", response_model=ActionResult)
def create_entry(payload: EntryPayload) -> ActionResult:
    """登记一条诉求记录，缺字段时说明原因而不是静默丢弃。"""
    entry, missing = service.create_entry(payload.values)
    if missing:
        return ActionResult(ok=False, message=f"缺少必填字段：{'、'.join(missing)}")
    return ActionResult(ok=True, message="诉求记录已登记", entry=entry)


@router.post("/{entry_id}/actions", response_model=ActionResult)
def run_action(entry_id: int, payload: EntryPayload) -> ActionResult:
    """对单条诉求执行受理、回复或关闭；重复受理与越态流转只返回一次明确失败。"""
    action = str(payload.values.get("action") or "").strip()
    entry, message = service.run_action(entry_id, action, payload.values)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)
