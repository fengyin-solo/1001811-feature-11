"""公众诉求业务规则：状态流转、字段校验与筛选口径都收在这里。"""
from __future__ import annotations

from datetime import date
from typing import Any

from app.store import store

MODULE = "complaint"
REQUIRED_FIELDS = ["诉求编号", "诉求来源", "诉求内容"]
OPTIONAL_FIELDS = ["涉及管段", "受理人员", "处理措施", "办理期限"]
STATUS_ORDER = ["待受理", "办理中", "已回复", "已关闭"]
TODO_STATUSES = {"待受理", "办理中", "已回复"}
ACTION_RULES = {"受理诉求": "办理中", "提交回复": "已回复", "关闭诉求": "已关闭"}
NEGATIVE_ACTIONS = []


class ComplaintService:
    def list_entries(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        scope: str = "todo",
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        self.sync_rows()
        rows = [dict(row) for row in store.rows(MODULE)]
        keyword = (keyword or "").strip()
        if keyword:
            rows = [
                row
                for row in rows
                if keyword in str(row.get("诉求编号", ""))
                or keyword in str(row.get("诉求来源", ""))
                or keyword in str(row.get("诉求内容", ""))
            ]
        status = (status or "").strip()
        if status:
            rows = [row for row in rows if row.get("status") == status]
        if scope == "todo":
            rows = [row for row in rows if row.get("status") in TODO_STATUSES]

        total = len(rows)
        page = max(page, 1)
        start = (page - 1) * size
        return rows[start:start + size], total

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        self.sync_rows()
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None
        return self.normalize_entry(entry)

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        missing = [field for field in REQUIRED_FIELDS if not str(values.get(field) or "").strip()]
        if missing:
            return None, missing
        rows = store.rows(MODULE)
        entry: dict[str, Any] = {"id": max((int(row.get("id", 0)) for row in rows), default=0) + 1}
        for field in [*REQUIRED_FIELDS, *OPTIONAL_FIELDS]:
            if field in values:
                entry[field] = values.get(field)
        entry["status"] = STATUS_ORDER[0]
        rows.append(entry)
        return self.normalize_entry(entry), []

    def run_action(
        self,
        entry_id: int,
        action: str,
        values: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any] | None, str]:
        self.sync_rows()
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"诉求记录 {entry_id} 不存在或已归档"
        self.normalize_entry(entry)
        values = values or {}
        if action not in ACTION_RULES:
            return None, f"动作「{action}」不属于公众诉求可执行范围"

        current_status = str(entry.get("status") or STATUS_ORDER[0])
        if action == "受理诉求":
            if current_status != "待受理":
                return None, "该诉求已受理或已进入后续环节，重复受理不会再次生效"
            measure = str(values.get("处理措施") or "").strip()
            if not measure:
                return None, "请先填写处理措施后再提交受理"
            entry["处理措施"] = measure
            handler = str(values.get("受理人员") or "").strip()
            if handler:
                entry["受理人员"] = handler
        elif action == "提交回复" and current_status != "办理中":
            return None, "只有办理中的诉求可以提交回复"
        elif action == "关闭诉求" and current_status != "已回复":
            return None, "只有已回复的诉求可以关闭"

        target = ACTION_RULES[action]
        entry["status"] = target
        self.normalize_entry(entry)
        return entry, f"诉求记录已{action}"

    @classmethod
    def sync_rows(cls) -> None:
        """读取或汇总前规整诉求状态，保证列表、详情与运营概览使用同一口径。"""
        for row in store.rows(MODULE):
            cls.normalize_entry(row)

    @classmethod
    def normalize_entry(cls, entry: dict[str, Any]) -> dict[str, Any]:
        """同步内部状态与列表字段，并计算来源缺失、超期等异常原因。"""
        status = entry.get("status")
        if status not in STATUS_ORDER:
            field_status = entry.get("诉求状态")
            status = field_status if field_status in STATUS_ORDER else STATUS_ORDER[0]
        entry["status"] = status
        entry["诉求状态"] = status

        reasons: list[str] = []
        source = str(entry.get("诉求来源") or "").strip()
        if not source:
            entry["诉求来源"] = ""
            reasons.append("诉求来源缺失")

        deadline_text = str(entry.get("办理期限") or "").strip()
        deadline = cls._parse_date(deadline_text)
        if deadline is not None and deadline < date.today():
            reasons.append(f"办理期限已过（{deadline_text}）")

        entry["abnormal_reasons"] = reasons
        entry["abnormal"] = bool(reasons)
        entry["pending"] = status in TODO_STATUSES
        return entry

    @staticmethod
    def _parse_date(value: str) -> date | None:
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
