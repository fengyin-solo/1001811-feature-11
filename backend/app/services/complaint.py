"""公众诉求业务规则：状态流转、字段校验、异常标记与筛选口径都收在这里。

状态序列：待受理 → 办理中 → 已回复 → 已关闭。
- 受理 / 回复 / 关闭只能按顺序向前流转，重复提交同一动作不会再次生效（幂等）。
- 诉求来源缺失、办理期限已过属于数据异常，读取时统一算出异常原因，
  列表与详情走同一个装饰逻辑，保证两处口径一致。
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from app.store import store

MODULE = "complaint"
REQUIRED_FIELDS = ["诉求编号", "诉求来源", "诉求内容"]
STATUS_ORDER = ["待受理", "办理中", "已回复", "已关闭"]
ACTION_RULES = {"受理诉求": "办理中", "提交回复": "已回复", "关闭诉求": "已关闭"}
# 每个动作允许发起时所处的状态：不在该状态下提交即视为重复/越序，直接拦下。
ACTION_ALLOWED_FROM = {"受理诉求": "待受理", "提交回复": "办理中", "关闭诉求": "已回复"}
# 重复提交同一动作时给用户的说明：该动作此前已经生效过一次。
ACTION_DONE_HINT = {"受理诉求": "已受理", "提交回复": "已回复", "关闭诉求": "已关闭"}
# 受理时必须随单提交的字段，缺了要把原因告诉前端，不能静默吞掉。
ACCEPT_REQUIRED = ["受理人员", "处理措施"]
REPLY_REQUIRED = ["回复内容"]
REPLIED_STATUS = "已回复"


def _parse_deadline(value: Any) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def anomaly_reasons(entry: dict[str, Any], *, today: date | None = None) -> list[str]:
    """算出一条诉求的异常原因：来源缺失、办理期限已过。"""
    today = today or date.today()
    reasons: list[str] = []
    if not str(entry.get("诉求来源") or "").strip():
        reasons.append("诉求来源缺失")
    deadline = str(entry.get("办理期限") or "").strip()
    due = _parse_deadline(deadline)
    if due is not None and due < today:
        reasons.append(f"办理期限已过（期限：{deadline}）")
    return reasons


class ComplaintService:
    # ---- 读取 ----------------------------------------------------------

    def _decorate(self, entry: dict[str, Any], *, today: date | None = None) -> dict[str, Any]:
        """给记录补上派生字段（异常原因、统一状态展示），不改动仓库里的原记录。"""
        view = dict(entry)
        reasons = anomaly_reasons(entry, today=today)
        view["abnormal"] = bool(reasons)
        view["abnormal_reasons"] = reasons
        view["overdue"] = any(reason.startswith("办理期限已过") for reason in reasons)
        # 列表的「诉求状态」列与详情都以 status 为准，避免两处各显示各的。
        view["诉求状态"] = entry.get("status")
        return view

    def list_entries(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
        today: date | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = store.rows(MODULE)
        if keyword:
            rows = [row for row in rows if keyword in str(row.get("诉求编号", ""))]
        if status:
            rows = [row for row in rows if row.get("status") == status]
        total = len(rows)
        start = max(page - 1, 0) * size
        page_rows = [self._decorate(row, today=today) for row in rows[start:start + size]]
        return page_rows, total

    def get_entry(self, entry_id: int, *, today: date | None = None) -> dict[str, Any] | None:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None
        return self._decorate(entry, today=today)

    def todo_entries(self, *, today: date | None = None) -> tuple[list[dict[str, Any]], int]:
        """待办清单：已回复、待跟进的诉求。

        直接复用 status=已回复 的列表查询，待办条数与诉求列表按该状态
        筛选出来的条数天然一致，不会出现两个口径各算各的。
        """
        return self.list_entries(status=REPLIED_STATUS, page=1, size=10000, today=today)

    # ---- 写入 ----------------------------------------------------------

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        missing = [field for field in REQUIRED_FIELDS if not str(values.get(field) or "").strip()]
        if missing:
            return None, missing
        rows = store.rows(MODULE)
        entry = {"id": max((int(row.get("id", 0)) for row in rows), default=0) + 1}
        entry.update({field: values.get(field) for field in REQUIRED_FIELDS})
        for optional in ("涉及管段", "受理人员", "处理措施", "办理期限"):
            if values.get(optional) is not None:
                entry[optional] = values.get(optional)
        entry["status"] = STATUS_ORDER[0]
        entry["pending"] = True
        entry["abnormal"] = bool(anomaly_reasons(entry))
        rows.append(entry)
        return self._decorate(entry), []

    def run_action(
        self,
        entry_id: int,
        action: str,
        values: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any] | None, str]:
        values = values or {}
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"诉求记录 {entry_id} 不存在或已归档"
        if action not in ACTION_RULES:
            return None, f"动作「{action}」不属于公众诉求可执行范围"

        current = str(entry.get("status") or "")
        allowed_from = ACTION_ALLOWED_FROM[action]
        target = ACTION_RULES[action]
        if current != allowed_from:
            if current == target:
                # 同一条诉求重复受理/回复/关闭：明确告知已生效过，不重复落状态。
                return None, f"该诉求{ACTION_DONE_HINT[action]}，当前状态为「{current}」，重复操作不会再次生效"
            return None, f"该诉求当前状态为「{current}」，不能执行「{action}」（需先处于「{allowed_from}」）"

        if action == "受理诉求":
            missing = [field for field in ACCEPT_REQUIRED if not str(values.get(field) or "").strip()]
            if missing:
                return None, f"受理失败，缺少必填内容：{'、'.join(missing)}"
            entry["受理人员"] = str(values.get("受理人员")).strip()
            entry["处理措施"] = str(values.get("处理措施")).strip()
        elif action == "提交回复":
            missing = [field for field in REPLY_REQUIRED if not str(values.get(field) or "").strip()]
            if missing:
                return None, f"回复失败，缺少必填内容：{'、'.join(missing)}"
            entry["回复内容"] = str(values.get("回复内容")).strip()
            entry["回复时间"] = datetime.now().strftime("%Y-%m-%d %H:%M")

        entry["status"] = target
        entry["pending"] = target != STATUS_ORDER[-1]
        # 来源缺失、超期这类异常不随状态流转消失，落库的异常标记同步刷新。
        entry["abnormal"] = bool(anomaly_reasons(entry))
        return self._decorate(entry), f"诉求记录已{action}"
