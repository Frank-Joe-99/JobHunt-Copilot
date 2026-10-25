"""
JobHunt-Copilot 核心业务编排流水线 (Core Workflow Orchestrator)
串联 JD 深度解析、技术匹配、开源补短板、经历 STAR 润色、定制简历编译与全套交付大礼包生成。
严格遵循零污染原则：所有经历润色与定制仅在内存快照中进行，绝对不篡改主档案 profile.yaml。
"""

from collections.abc import Callable
import json
import logging
import time
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

from core.config import load_user_profile, PROJECT_ROOT
from core.resume_edits import apply_resume_edits, build_resume_snapshot, build_diff_markdown
from core.state import (
    UserProfile,
    Objective,
    ResumeSnapshot,
    JobDescription,
    MatchResult,
    ProjectRecommendationReport,
    ResumePolishReport,
    TailoredApplicationPackage,
    ApplicationStatus,
)
from skills.jd_matcher.handler import parse_jd, match_profile_with_jd
from skills.project_recommender.handler import recommend_projects_report
from skills.resume_polisher.handler import polish_experiences
from skills.resume_generator.handler import generate_resume
from skills.application_tracker.handler import add_application


def _sanitize_name(name: str, fallback: str) -> str:
    cleaned = "".join(c for c in name if c.isalnum() or c in ("_", "-"))
    return cleaned if cleaned else fallback


def _resolve_jd_text(jd_input: str | Path) -> str:
    """解析 JD 输入：支持直接传入字符串或本地文件路径"""
    if isinstance(jd_input, Path):
        if jd_input.exists():
            return jd_input.read_text(encoding="utf-8")
        raise FileNotFoundError(f"指定的 JD 文件不存在: {jd_input}")

    if isinstance(jd_input, str):
        if "\n" not in jd_input and len(jd_input) < 260:
            try:
                path_candidate = Path(jd_input)
                if path_candidate.is_file():
                    return path_candidate.read_text(encoding="utf-8")
            except OSError:
                pass
        return jd_input

    raise ValueError(f"不支持的 JD 输入类型: {type(jd_input)}")


def _apply_polish_to_profile(
    profile: UserProfile, polish_report: ResumePolishReport, snapshot: ResumeSnapshot,
) -> int:
    """严格快照定位；存疑提案不应用，所有结构校验先于写入。"""
    return apply_resume_edits(profile, polish_report, snapshot)


def _build_package_markdown(
    package: TailoredApplicationPackage,
    project_report: ProjectRecommendationReport | None,
    polish_report: ResumePolishReport | None,
) -> str:
    """组装生成《一键定向投递综合战报》Markdown 文本"""
    match_result = package.match_result
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. 技能匹配条目
    matched_str = (
        "\n".join(f"- **{m.skill}**：{m.evidence}" for m in match_result.matched_skills)
        if match_result.matched_skills
        else "- 暂无显著完全匹配技能"
    )
    missing_str = (
        "\n".join(f"- **{g.skill}**（{g.status}）：{g.suggestion}" for g in match_result.missing_skills)
        if match_result.missing_skills
        else "- 本次未列出缺口，不代表所有要求都已得到验证"
    )
    advice_str = (
        "\n".join(f"- {a}" for a in match_result.resume_tuning_advice)
        if match_result.resume_tuning_advice
        else "- 本次未提供额外调优建议"
    )

    # 2. 开源项目推荐条目
    if project_report and project_report.recommendations:
        proj_recs_md = []
        for idx, r in enumerate(project_report.recommendations, start=1):
            evidence_text = "；".join(
                f"{e.kind} · {e.fetched_at} · {e.cache_status} · {e.source_url}"
                for e in r.evidence
            )
            proj_recs_md.append(
                f"### {idx}. [{r.repo_name}]({r.repo_url}) (⭐ {r.stars})\n"
                f"- **推荐理由**：{r.why_recommended}\n"
                f"- **学习攻坚路径**：{r.learning_path}\n"
                f"- **面试高频考点**：{r.interview_tips}\n"
                f"- **资料来源**：{evidence_text or '未提供验证资料'}\n"
                f"> **简历 STAR 转化范文**：\n>\n> {r.star_resume_sample}\n"
            )
        project_section_str = "\n".join(proj_recs_md)
    else:
        status = project_report.status if project_report else "unavailable"
        project_section_str = {
            "disabled": "用户已关闭开源推荐。",
            "unavailable": "服务不可用，已跳过推荐；请结合技能缺口判断。",
            "no_match": "未找到合适的公开项目；请调整搜索条件。",
            "no_gaps": "暂无已确认缺口；未提供证据的部分仍需核实。",
        }.get(status, "本次未生成有效推荐。")

    if project_report:
        project_section_str = (
            f"推荐状态：{project_report.status}；网络请求 {project_report.request_count} 次，"
            f"缓存命中 {project_report.cache_hits} 次。\n\n" + project_section_str
        )
        if project_report.notices:
            project_section_str += "\n\n降级说明：" + "、".join(project_report.notices)

    # 3. 润色提分条目
    if polish_report and polish_report.items:
        polish_items_md = []
        for idx, item in enumerate(polish_report.items[:4], start=1):
            polish_items_md.append(
                f"**经历亮点 {idx}（{item.source}）**\n"
                f"- 原始描述：`{item.original}`\n"
                f"- **改写建议（{'待核实，未应用' if item.needs_confirmation else '已应用到草稿'}）**：{item.polished}\n"
                f"- *提分理由*：{item.improvement_reason}\n"
            )
        polish_section_str = "\n".join(polish_items_md)
    else:
        polish_section_str = "本次未提出额外改写建议，仍请结合岗位核对材料。"

    pdf_path_obj = Path(package.resume_files.get("pdf", ""))
    docx_path_obj = Path(package.resume_files.get("docx", ""))

    pdf_link_str = f"[{pdf_path_obj.name}]({pdf_path_obj.resolve().as_uri()})" if pdf_path_obj.name else "无"
    docx_link_str = f"[{docx_path_obj.name}]({docx_path_obj.resolve().as_uri()})" if docx_path_obj.name else "无"

    return f"""# 📦 一键定向求职物料交付大礼包 (Tailored Application Package)

- **生成时间**：{timestamp_str}
- **目标企业**：**{package.target_company}**
- **目标岗位**：**{package.target_role}**
- **岗位契合度**：**{match_result.score} / 100**（练习诊断，不是录用概率）
- **物料状态**：草稿；{'存在待核实建议，相关亮点保留原文' if package.review_required else '请核对事实后使用'}
- **完整修改对比**：{package.resume_diff_path}
- **原始快照备份**：{package.resume_snapshot_path}

---

## 🎯 定制版双格式简历成品 (Generated Resumes)

针对本岗位的简历草稿已编译。生成物料不表示已经投递；机器检查不替代事实核实。
- 📄 **PDF 草稿（核实后使用）**：{pdf_link_str}
- 📝 **Word 格式（可二次微调）**：{docx_link_str}

---

## ✉️ 针对该岗位的定制自荐信草稿 (Customized Cover Letter)

> **适用场景**：核实内容后可用于招聘平台沟通或邮件网申附言。

```text
{match_result.cover_letter_draft}
```

---

## 📊 岗位深度契合与差距诊断报告 (Job Match Analysis)

### 1. 优势匹配技能 (Matched Competencies)
{matched_str}

### 2. 存在短板或缺口技能 (Skill Gaps)
{missing_str}

### 3. 定向优化战略建议 (Strategic Advice)
{advice_str}

---

## 🚀 补短板开源实战练手项目推荐 (Open Source Recommendations)

{project_section_str}

---

## 💎 重点经历定制化 STAR 提分对比 (Experience Enhancements)

{polish_section_str}

---

*交付物由 JobHunt-Copilot AI 自动化生成，已确保本地 Master Profile 零污染。祝您投递顺利，斩获心仪 Offer！*
"""


def tailor_application_flow(
    jd_input: str | Path,
    profile: UserProfile | None = None,
    output_name: str | None = None,
    template: str = "modern",
    provider: str | None = None,
    enable_github_search: bool = True,
    auto_track: bool = True,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> TailoredApplicationPackage:
    """
    一键岗位定向求职全套交付流水线 (One-Click Tailored Delivery Workflow)

    【端到端业务全流程】：
    1. [JD 解析与穿透比对] 解析岗位画像，打出契合度得分、缺口清单与自荐信
    2. [开源实战赋能] 针对技能缺口检索 GitHub 开源项目并给出速成学习路线
    3. [经历 STAR 定向强化] 结合目标岗位核心考点对经历进行提分强化（内存深拷贝零污染）
    4. [简历生成] 调用 resume_generator，编译输出针对该企业的专属 Word + PDF 双格式简历
    5. [打包战报] 生成 Markdown 格式《一键定向投递综合战报》，汇总自荐信、缺口补强与简历路径
    6. [自动看板追踪] 如开启 auto_track，自动将本次物料准备登记为心愿单，不标记已投递
    """
    start_time = time.time()
    if profile is None:
        profile = load_user_profile()

    jd_text = _resolve_jd_text(jd_input)
    if not jd_text:
        raise ValueError("传入的岗位招聘 JD 内容为空，请检查输入或文件路径。")

    if progress_callback:
        progress_callback(1, 5, "正在深度穿透解析岗位 JD 并进行全维度技术比对...")
    logger.info("[Step 1/5] 正在深度穿透解析岗位 JD 并进行全维度技术比对...")
    parsed_jd = parse_jd(jd_text, provider=provider)
    match_result = match_profile_with_jd(profile, parsed_jd, provider=provider)
    logger.info("  └─ JD 解析与匹配完成 (契合度: %s/100)", match_result.score)

    # 步骤 2：开源赋能（针对技能缺口搜索 GitHub 项目）
    project_report: ProjectRecommendationReport | None = None
    if enable_github_search and match_result.missing_skills:
        if progress_callback:
            progress_callback(2, 5, "正在针对检测到的技术缺口检索 GitHub 开源实战项目...")
        logger.info("[Step 2/5] 正在针对检测到的技术缺口检索 GitHub 开源实战项目...")
        try:
            pref_lang = (
                profile.skills.programming_languages[0].name
                if profile.skills and profile.skills.programming_languages
                else "python"
            )
            project_report = recommend_projects_report(
                skills_gaps=match_result.missing_skills,
                language=pref_lang,
                provider=provider,
            )
            logger.info(f"  └─ 已智能推荐 {len(project_report.recommendations)} 个开源实战补强项目")
        except Exception as e:
            logger.warning("开源推荐不可用，主流程继续 (%s)", type(e).__name__)
            project_report = ProjectRecommendationReport(status="unavailable", overview="服务不可用，已跳过推荐。")
    else:
        project_report = ProjectRecommendationReport(
            status="disabled" if not enable_github_search else "no_gaps",
            overview="用户关闭推荐" if not enable_github_search else "暂无已确认的缺口",
        )
        if progress_callback:
            progress_callback(2, 5, "无显著技能缺口或已跳过开源项目检索。")
        logger.info("[Step 2/5] 无显著技能缺口或已跳过开源项目检索。")

    # 步骤 3：经历定向 STAR 提分与内存快照定制（零污染原则）
    if progress_callback:
        progress_callback(3, 5, "正在针对该岗位关键技术考点进行经历 STAR 提分与装配...")
    logger.info("[Step 3/5] 正在针对该岗位关键技术考点进行经历 STAR 提分与装配...")
    # 深拷贝主档案，确保原版 profile.yaml 绝对干净不受污染
    tailored_profile = profile.model_copy(deep=True)
    if tailored_profile.objective:
        tailored_profile.objective.target_role = parsed_jd.role
    else:
        tailored_profile.objective = Objective(target_role=parsed_jd.role)

    original_profile = tailored_profile.model_copy(deep=True)
    snapshot = build_resume_snapshot(tailored_profile)
    polish_report = polish_experiences(
        profile=tailored_profile, provider=provider, job_description=parsed_jd,
        match_result=match_result, jd_text=jd_text, snapshot=snapshot,
    )
    applied_count = _apply_polish_to_profile(tailored_profile, polish_report, snapshot)
    logger.info("已生成 %s 条建议，应用 %s 条到定制草稿", len(polish_report.items), applied_count)

    # 步骤 4：编译专属双格式简历
    if progress_callback:
        progress_callback(4, 5, "正在调用排版引擎编译生成定制版 PDF 与 Word 简历...")
    logger.info("[Step 4/5] 正在调用排版引擎编译生成定制版 PDF 与 Word 简历...")
    if not output_name:
        clean_company = _sanitize_name(parsed_jd.company, "target")
        clean_role = _sanitize_name(parsed_jd.role, "role")
        output_name = f"resume_{clean_company}_{clean_role}_tailored"

    resume_paths = generate_resume(
        profile=tailored_profile,
        output_name=output_name,
        template=template,
    )
    logger.info(f"  └─ 定制版简历已输出: {resume_paths['pdf'].name} & {resume_paths['docx'].name}")

    # 步骤 5：封装一键定向投递综合战报
    if progress_callback:
        progress_callback(5, 5, "正在封装一键定向投递综合战报...")
    logger.info("[Step 5/5] 正在封装一键定向投递综合战报...")
    exports_dir = PROJECT_ROOT / "storage" / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)

    timestamp_file = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_company = _sanitize_name(parsed_jd.company, "公司")
    clean_role = _sanitize_name(parsed_jd.role, "岗位")
    report_filename = f"package_{clean_company}_{clean_role}_{timestamp_file}_{snapshot.snapshot_id[:8]}.md"
    report_path = exports_dir / report_filename
    diff_path = exports_dir / f"resume_diff_{snapshot.snapshot_id}.md"
    snapshot_path = exports_dir / f"resume_snapshot_{snapshot.snapshot_id}.json"
    diff_path.write_text(build_diff_markdown(polish_report), encoding="utf-8")
    snapshot_path.write_text(json.dumps({
        "snapshot": snapshot.model_dump(mode="json"),
        "profile": original_profile.model_dump(mode="json"),
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    package = TailoredApplicationPackage(
        target_company=parsed_jd.company,
        target_role=parsed_jd.role,
        job_description=parsed_jd,
        match_result=match_result,
        project_recommendations=project_report,
        tailored_experiences_summary=f"生成 {len(polish_report.items)} 条建议，应用 {applied_count} 条到定制草稿；存疑项保留原文",
        resume_files={
            "pdf": str(resume_paths["pdf"].resolve()),
            "docx": str(resume_paths["docx"].resolve()),
        },
        package_report_path=str(report_path.resolve()),
        resume_diff_path=str(diff_path.resolve()),
        resume_snapshot_path=str(snapshot_path.resolve()),
        review_required=polish_report.needs_confirmation,
    )

    report_markdown = _build_package_markdown(package, project_report, polish_report)
    report_path.write_text(report_markdown, encoding="utf-8")
    logger.info(f"  └─ 综合交付物料战报已落盘: {report_path.name}")

    # 联动投递追踪器: 自动登记入库
    if auto_track:
        try:
            record = add_application(
                company=package.target_company,
                role=package.target_role,
                status=ApplicationStatus.WISHLIST,
                resume_path=str(resume_paths["pdf"].resolve()),
                note=f"已准备简历草稿，尚未确认投递；岗位匹配度: {match_result.score}/100",
            )
            logger.info(f"  └─ [✓ 看板联动] 已自动登记入本地投递看板 (Record ID: #{record.id})")
        except Exception as e:
            logger.warning("准备记录登记失败 (%s)", type(e).__name__)

    elapsed = time.time() - start_time
    if progress_callback:
        progress_callback(5, 5, f"一键交付流水线顺利完成，总耗时: {elapsed:.2f}s")
    logger.info(f"[✓] 一键岗位定向全套交付流水线顺利完成！总耗时: {elapsed:.2f}s\n")
    return package
