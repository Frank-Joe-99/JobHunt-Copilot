"""
全网/批量岗位机会雷达业务调度器 (Job Radar Handler)
支持批量评估岗位 JD，按契合度智能排名，提炼跨岗位共性缺口，并导出深度战略决策报告。
"""

from collections import Counter
from datetime import datetime
from pathlib import Path

from core.config import load_user_profile
from core.state import UserProfile, RankedOpportunity, JobRadarReport
from skills.jd_matcher.handler import parse_jd, match_profile_with_jd

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _determine_tier_and_verdict(score: int) -> tuple[str, str]:
    """根据匹配得分划分机会层级与一句话投递决策建议"""
    if score >= 80:
        return "优先主投", "🟢 契合度极高，核心硬性技术与项目经历高度重合，建议优先重点投递"
    elif score >= 65:
        return "微调冲刺", "🟡 具备良好基本盘但存在局部技能短板，建议针对性优化简历经历后投递"
    else:
        return "暂缓考虑", "🔴 核心技术栈与业务场景差距较大，短期内投递性价比较低，建议暂缓"


def _analyze_common_gaps(opportunities: list[RankedOpportunity]) -> list[dict[str, int | str]]:
    """统计跨岗位的共性高频技能缺口，帮助求职者精准定位当前最值得突击的短板"""
    all_gaps = []
    for opp in opportunities:
        for gap in opp.key_gaps:
            all_gaps.append(gap.strip())

    counts = Counter(all_gaps)
    result = []
    for skill, count in counts.most_common(5):
        importance = "🔥 紧急攻坚" if count >= 2 else "📌 重点复习"
        result.append({"skill": skill, "count": count, "importance": importance})
    return result


def scan_opportunities(
    jd_texts: list[str],
    profile: UserProfile | None = None,
    provider: str | None = None,
) -> list[RankedOpportunity]:
    """
    核心入口 1：接收 JD 纯文本列表，批量解析打分并按匹配度降序返回排名列表。

    Args:
        jd_texts: 原始岗位 JD 文本字符串列表
        profile: 候选人档案（若不传自动从 config/profile.yaml 读取）
        provider: 大模型供应商名称 (如 deepseek, openai)
    """
    if not jd_texts:
        return []

    if profile is None:
        profile = load_user_profile()

    evaluated: list[tuple[int, RankedOpportunity]] = []

    for raw_text in jd_texts:
        clean_text = raw_text.strip()
        if not clean_text:
            continue

        # 1. 结构化解析 JD
        parsed_jd = parse_jd(clean_text, provider=provider)
        # 2. 深度穿透比对
        match_res = match_profile_with_jd(profile, parsed_jd, provider=provider)

        tier, verdict = _determine_tier_and_verdict(match_res.score)

        opp = RankedOpportunity(
            rank=0,  # 稍后排序后统一赋予排名序号
            company=parsed_jd.company,
            role=parsed_jd.role,
            department=parsed_jd.department,
            score=match_res.score,
            tier=tier,
            verdict=verdict,
            top_matches=[s.skill for s in match_res.matched_skills[:3]],
            key_gaps=[s.skill for s in match_res.missing_skills[:3]],
            overview=match_res.overview,
            tuning_advice=match_res.resume_tuning_advice,
        )
        evaluated.append((match_res.score, opp))

    # 按分数从高到低排序
    evaluated.sort(key=lambda item: item[0], reverse=True)

    ranked_list: list[RankedOpportunity] = []
    for rank_idx, (_, opp) in enumerate(evaluated, start=1):
        opp.rank = rank_idx
        ranked_list.append(opp)

    return ranked_list


def scan_from_directory(
    dir_path: str | Path = "storage/raw_jds",
    profile: UserProfile | None = None,
    provider: str | None = None,
) -> list[RankedOpportunity]:
    """
    核心入口 2：从指定本地文件夹中批量读取所有 .txt 岗位文本并进行雷达扫描。
    """
    target_dir = Path(dir_path)
    if not target_dir.is_absolute():
        target_dir = PROJECT_ROOT / target_dir

    if not target_dir.exists():
        target_dir.mkdir(parents=True, exist_ok=True)
        return []

    txt_files = sorted(target_dir.glob("*.txt"))
    jd_texts = []
    for f in txt_files:
        try:
            content = f.read_text(encoding="utf-8")
            if content.strip():
                jd_texts.append(content)
        except Exception:
            continue

    return scan_opportunities(jd_texts, profile=profile, provider=provider)


def export_radar_report(
    opportunities: list[RankedOpportunity],
    output_dir: str | Path = "storage/radar_reports",
    filename: str | None = None,
) -> JobRadarReport:
    """
    核心入口 3：将机会排名列表渲染为排版精美的战略简报，并导出为 Markdown 文件。
    """
    target_dir = Path(output_dir)
    if not target_dir.is_absolute():
        target_dir = PROJECT_ROOT / target_dir
    target_dir.mkdir(parents=True, exist_ok=True)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    file_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = filename or f"radar_report_{file_timestamp}.md"
    report_path = target_dir / report_filename

    common_gaps = _analyze_common_gaps(opportunities)

    # 统计梯队数量
    tier_counts = Counter(opp.tier for opp in opportunities)
    strategic_advice = (
        f"本次扫描共评估 {len(opportunities)} 个岗位机会。"
        f"其中【优先主投】{tier_counts.get('优先主投', 0)} 个，"
        f"【微调冲刺】{tier_counts.get('微调冲刺', 0)} 个，"
        f"【暂缓考虑】{tier_counts.get('暂缓考虑', 0)} 个。"
    )
    if common_gaps:
        top_gap = common_gaps[0]["skill"]
        strategic_advice += f" 建议当前首要攻坚共性技术短板：【{top_gap}】，可显著提升跨岗位命中率。"

    # 渲染 Markdown 报告正文
    md_lines = [
        "# 📡 机会雷达：多岗位深度评估与投递战略简报",
        f"> **生成时间**：{now_str}  |  **扫描岗位数**：{len(opportunities)}  |  **评估引擎**：JobHunt-Copilot AI Radar",
        "",
        "## 🧭 总体投递战略综述",
        strategic_advice,
        "",
        "---",
        "",
        "## 📊 岗位综合契合度排行榜",
        "",
        "| 排名 | 招聘企业 | 目标岗位 | 匹配度得分 | 机会梯队 | 核心策略建议 |",
        "| :---: | :--- | :--- | :---: | :---: | :--- |",
    ]

    for opp in opportunities:
        dept = f" ({opp.department})" if opp.department else ""
        tier_badge = (
            "🟢 优先主投" if opp.tier == "优先主投" else ("🟡 微调冲刺" if opp.tier == "微调冲刺" else "🔴 暂缓考虑")
        )
        md_lines.append(
            f"| **#{opp.rank}** | **{opp.company}** | {opp.role}{dept} | `{opp.score} 分` | {tier_badge} | {opp.verdict} |"
        )

    md_lines.extend([
        "",
        "---",
        "",
        "## 🎯 跨岗位共性技能短板 (攻坚优先级)",
        "以下为本次扫描中跨企业出现频率最高的技能缺口，优先补齐它们可实现“一通百通”的高效提升：",
        "",
    ])

    if common_gaps:
        md_lines.append("| 关注级别 | 共性缺口技能 | 关联岗位数量 | 突破建议 |")
        md_lines.append("| :---: | :--- | :---: | :--- |")
        for g in common_gaps:
            md_lines.append(
                f"| {g['importance']} | **{g['skill']}** | 命中 {g['count']} 个岗位 | 建议结合 project_recommender 挑选对应开源项目速成 |"
            )
    else:
        md_lines.append("🎉 候选人当前技能已高度覆盖全部扫描岗位的核心要求，未发现明显的共性短板！")

    md_lines.extend([
        "",
        "---",
        "",
        "## 🔍 逐岗全景深度剖析与微调指南",
        "",
    ])

    for opp in opportunities:
        tier_badge = (
            "🟢 优先主投" if opp.tier == "优先主投" else ("🟡 微调冲刺" if opp.tier == "微调冲刺" else "🔴 暂缓考虑")
        )
        md_lines.extend([
            f"### #{opp.rank} [{opp.company}] - {opp.role} （匹配度：{opp.score} 分 / {tier_badge}）",
            f"- **岗位评述**：{opp.overview}",
            "- **核心命中优势**：" + ("、".join(f"`{m}`" for m in opp.top_matches) if opp.top_matches else "无明显优势"),
            "- **主要技能短板**：" + ("、".join(f"`{g}`" for g in opp.key_gaps) if opp.key_gaps else "无明显短板"),
            "- **一岗一策微调建议**：",
        ])
        if opp.tuning_advice:
            for advice in opp.tuning_advice:
                md_lines.append(f"  - 💡 {advice}")
        else:
            md_lines.append("  - 💡 保持当前经历排版直接投递即可。")
        md_lines.append("")

    # 写入文件
    report_path.write_text("\n".join(md_lines), encoding="utf-8")

    return JobRadarReport(
        created_at=now_str,
        total_scanned=len(opportunities),
        opportunities=opportunities,
        common_skill_gaps=common_gaps,
        strategic_advice=strategic_advice,
        report_file_path=str(report_path),
    )


def run_radar_pipeline(
    dir_path: str | Path = "storage/raw_jds",
    profile: UserProfile | None = None,
    provider: str | None = None,
) -> JobRadarReport:
    """
    一键门面快捷函数：扫描文件夹 -> 批量比对 -> 自动导出 Markdown 战略报告。
    """
    opportunities = scan_from_directory(dir_path=dir_path, profile=profile, provider=provider)
    return export_radar_report(opportunities)

