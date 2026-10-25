"""简历快照、定位校验和保守的事实检查；不访问配置或调用外部服务。"""

import hashlib
import json
import re
from uuid import uuid4

from core.state import HighlightTarget, ResumePolishReport, ResumeSnapshot, UserProfile


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _profile_hash(profile: UserProfile) -> str:
    return _digest(json.dumps(
        profile.model_dump(mode="json"), ensure_ascii=False, sort_keys=True,
    ))


def build_resume_snapshot(profile: UserProfile) -> ResumeSnapshot:
    targets = []
    for section, label in (("internships", "实习"), ("projects", "项目"), ("research", "科研")):
        for index, item in enumerate(getattr(profile, section)):
            title = item.company if section == "internships" else item.name
            source = f"{label}-{title}" + (f"({item.role})" if item.role else "")
            for highlight_index, original in enumerate(item.highlights):
                targets.append(HighlightTarget(
                    target_ref=f"{section}[{index}].highlights[{highlight_index}]",
                    section=section, item_index=index, highlight_index=highlight_index,
                    source=source, original=original, original_hash=_digest(original),
                ))
    return ResumeSnapshot(
        snapshot_id=uuid4().hex, profile_hash=_profile_hash(profile), targets=tuple(targets),
    )


def review_polish_report(
    profile: UserProfile, report: ResumePolishReport, snapshot: ResumeSnapshot,
) -> ResumePolishReport:
    """先校验全部定位，再标注风险。任何非法定位都不会造成部分写入。"""
    if _profile_hash(profile) != snapshot.profile_hash:
        raise ValueError("简历快照已过期，请基于当前档案重新生成修改提案。")
    if report.snapshot_id != snapshot.snapshot_id:
        raise ValueError("润色报告的 snapshot_id 与当前快照不符。")
    target_map = {item.target_ref: item for item in snapshot.targets}
    seen = set()
    for item in report.items:
        target = target_map.get(item.target_ref)
        if target is None or item.target_ref in seen:
            raise ValueError("润色报告包含未知或重复的 target_ref。")
        if item.snapshot_id != snapshot.snapshot_id or item.expected_original_hash != target.original_hash:
            raise ValueError("润色条目的快照或原文版本不符。")
        if not item.polished.strip():
            raise ValueError("润色条目不能为空。")
        seen.add(item.target_ref)

    for item in report.items:
        target = target_map[item.target_ref]
        original = target.original
        source_item = getattr(profile, target.section)[target.item_index]
        source_text = original + " " + " ".join(getattr(source_item, "tech_stack", []))
        reasons = list(item.review_reasons)
        # 这些检查用于发现疑点，不代替人工语义核实。
        numbers = lambda text: set(re.findall(r"(?<![A-Za-z_])\d+(?:\.\d+)?", text))
        if numbers(item.polished) - numbers(source_text):
            reasons.append("出现原始亮点或技术栈未支持的数字，需核实指标与口径")
        terms = lambda text: {
            term.casefold() for term in re.findall(r"[A-Za-z][A-Za-z0-9_+#.-]*", text)
        }
        if terms(item.polished) - terms(source_text):
            reasons.append("出现新的英文技术名或术语，需核实使用范围")
        if re.search(r"参与|协助", original) and re.search(r"主导|独立|负责人|核心开发", item.polished):
            if not re.search(r"主导|独立|负责人|核心开发", original):
                reasons.append("个人职责可能被扩大")
        boundaries = r"学习|教程|复现|计划|拟|尚未|未完成|进行中|未测|待确认"
        if re.search(boundaries, original) and not re.search(boundaries, item.polished):
            reasons.append("学习、计划或未完成的边界可能丢失")
        if re.search(r"待确认|待核实|\[待", item.polished):
            reasons.append("改写包含待确认信息")
        item.review_reasons = list(dict.fromkeys(reasons))
        item.needs_confirmation = item.needs_confirmation or bool(reasons)
        # 对比报告使用应用层的原文，不能信任模型重新抄写的 original/source。
        item.original = original
        item.source = target.source
    report.needs_confirmation = report.needs_confirmation or any(
        item.needs_confirmation for item in report.items
    )
    return report


def apply_resume_edits(
    profile: UserProfile, report: ResumePolishReport, snapshot: ResumeSnapshot,
) -> int:
    review_polish_report(profile, report, snapshot)
    target_map = {item.target_ref: item for item in snapshot.targets}
    applied = 0
    for item in report.items:
        if item.needs_confirmation:
            continue  # 存疑的建议仅展示，成品保留原文。
        target = target_map[item.target_ref]
        getattr(profile, target.section)[target.item_index].highlights[target.highlight_index] = item.polished
        applied += 1
    return applied


def build_diff_markdown(report: ResumePolishReport) -> str:
    lines = [
        "# 定制简历修改对比（草稿）", "",
        "机器检查不能证明事实真实性。标记待核实的建议未应用，简历保留对应原文。",
        f"快照：{report.snapshot_id}", "",
    ]
    for item in report.items:
        status = "待核实，未应用" if item.needs_confirmation else "已应用到定制草稿，仍请核对事实"
        lines.extend([
            f"## {item.target_ref} · {item.source}", "",
            f"- 状态：{status}", f"- 原文：{item.original}",
            f"- 建议：{item.polished}", f"- 理由：{item.improvement_reason}",
            "- 核实项：" + ("；".join(item.review_reasons) or "无自动检测到的疑点"), "",
        ])
    return "\n".join(lines)
