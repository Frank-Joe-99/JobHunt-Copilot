"""
JobHunt-Copilot 核心业务编排流水线 (Core Workflow Orchestrator)
串联 JD 深度解析、技术匹配、开源补短板、经历 STAR 润色、定制简历编译与全套交付大礼包生成。
严格遵循零污染原则：所有经历润色与定制仅在内存快照中进行，绝对不篡改主档案 profile.yaml。
"""

import time
from datetime import datetime
from pathlib import Path

from core.config import load_user_profile
from core.state import (
    UserProfile,
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


def _resolve_jd_text(jd_input: str | Path) -> str:
    """解析 JD 输入：支持直接传入字符串或本地文件路径"""
    if isinstance(jd_input, Path):
        if jd_input.exists():
            return jd_input.read_text(encoding="utf-8")
        raise FileNotFoundError(f"指定的 JD 文件不存在: {jd_input}")

    if isinstance(jd_input, str):
        path_candidate = Path(jd_input)
        if path_candidate.exists() and path_candidate.is_file():
            return path_candidate.read_text(encoding="utf-8")
        return jd_input

    raise ValueError(f"不支持的 JD 输入类型: {type(jd_input)}")


def _apply_polish_to_profile(profile: UserProfile, polish_report: ResumePolishReport) -> None:
    """
    将润色后的 STAR 亮点应用到深拷贝后的内存 Profile 中。
    保持零污染：仅修改内存实例，不回写磁盘。
    """
    polish_map = {item.original.strip(): item.polished.strip() for item in polish_report.items}

    # 替换实习经历中的 highlights
    for intern in profile.internships:
        new_highlights = []
        for h in intern.highlights:
            h_strip = h.strip()
            new_highlights.append(polish_map.get(h_strip, h))
        intern.highlights = new_highlights

    # 替换项目经历中的 highlights
    for proj in profile.projects:
        new_highlights = []
        for h in proj.highlights:
            h_strip = h.strip()
            new_highlights.append(polish_map.get(h_strip, h))
        proj.highlights = new_highlights

    # 替换科研经历中的 highlights
    for research in profile.research_experiences:
        new_highlights = []
        for h in research.highlights:
            h_strip = h.strip()
            new_highlights.append(polish_map.get(h_strip, h))
        research.highlights = new_highlights


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
        else "- 无明显硬伤技能缺口"
    )
    advice_str = (
        "\n".join(f"- {a}" for a in match_result.resume_tuning_advice)
        if match_result.resume_tuning_advice
        else "- 简历整体与岗位高度贴合"
    )

    # 2. 开源项目推荐条目
    if project_report and project_report.recommendations:
        proj_recs_md = []
        for idx, r in enumerate(project_report.recommendations, start=1):
            proj_recs_md.append(
                f"### {idx}. [{r.repo_name}]({r.repo_url}) (⭐ {r.stars})\n"
                f"- **推荐理由**：{r.why_recommended}\n"
                f"- **学习攻坚路径**：{r.learning_path}\n"
                f"- **面试高频考点**：{r.interview_tips}\n"
                f"> **简历 STAR 转化范文**：\n>\n> {r.star_resume_sample}\n"
            )
        project_section_str = "\n".join(proj_recs_md)
    else:
        project_section_str = "当前技能已基本覆盖目标岗位，无需额外补充开源实战项目。"

    # 3. 润色提分条目
    if polish_report and polish_report.items:
        polish_items_md = []
        for idx, item in enumerate(polish_report.items[:4], start=1):
            polish_items_md.append(
                f"**经历亮点 {idx}（{item.source}）**\n"
                f"- 原始描述：`{item.original}`\n"
                f"- **STAR 强化**：{item.polished}\n"
                f"- *提分理由*：{item.improvement_reason}\n"
            )
        polish_section_str = "\n".join(polish_items_md)
    else:
        polish_section_str = "未执行额外润色或经历已处于最优状态。"

    pdf_path_obj = Path(package.resume_files.get("pdf", ""))
    docx_path_obj = Path(package.resume_files.get("docx", ""))

    pdf_link_str = f"[{pdf_path_obj.name}]({pdf_path_obj.resolve().as_uri()})" if pdf_path_obj.name else "无"
    docx_link_str = f"[{docx_path_obj.name}]({docx_path_obj.resolve().as_uri()})" if docx_path_obj.name else "无"

    return f"""# 📦 一键定向求职物料交付大礼包 (Tailored Application Package)

- **生成时间**：{timestamp_str}
- **目标企业**：**{package.target_company}**
- **目标岗位**：**{package.target_role}**
- **岗位契合度**：**{match_result.score} / 100**

---

## 🎯 定制版双格式简历成品 (Generated Resumes)

针对本岗位定向优化排版的简历已编译完成，点击直接查看：
- 📄 **PDF 格式（推荐直投）**：{pdf_link_str}
- 📝 **Word 格式（可二次微调）**：{docx_link_str}

---

## ✉️ 针对该岗位的定制自荐信草稿 (Customized Cover Letter)

> **适用场景**：可直接粘贴至招聘平台（BOSS直聘/拉勾）开场白沟通消息、或邮件网申附言中。

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
) -> TailoredApplicationPackage:
    """
    一键岗位定向求职全套交付流水线 (One-Click Tailored Delivery Workflow)

    【端到端业务全流程】：
    1. [JD 解析与穿透比对] 解析岗位画像，打出契合度得分、缺口清单与自荐信
    2. [开源实战赋能] 针对技能缺口检索 GitHub 开源项目并给出速成学习路线
    3. [经历 STAR 定向强化] 结合目标岗位核心考点对经历进行提分强化（内存深拷贝零污染）
    4. [简历生成] 调用 resume_generator，编译输出针对该企业的专属 Word + PDF 双格式简历
    5. [打包战报] 生成 Markdown 格式《一键定向投递综合战报》，汇总自荐信、缺口补强与简历路径
    6. [自动看板追踪] 如开启 auto_track，自动将本次投递登记入本地 SQLite 看板
    """
    start_time = time.time()
    if profile is None:
        profile = load_user_profile()

    jd_text = _resolve_jd_text(jd_input)
    if not jd_text:
        raise ValueError("传入的岗位招聘 JD 内容为空，请检查输入或文件路径。")

    print("[Step 1/5] 正在深度穿透解析岗位 JD 并进行全维度技术比对...")
    parsed_jd = parse_jd(jd_text, provider=provider)
    match_result = match_profile_with_jd(profile, parsed_jd, provider=provider)
    print(f"  └─ 目标岗位: {parsed_jd.company} · {parsed_jd.role} (契合度: {match_result.score}/100)")

    # 步骤 2：开源赋能（针对技能缺口搜索 GitHub 项目）
    project_report: ProjectRecommendationReport | None = None
    if enable_github_search and match_result.missing_skills:
        print("[Step 2/5] 正在针对检测到的技术缺口检索 GitHub 开源实战项目...")
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
            print(f"  └─ 已智能推荐 {len(project_report.recommendations)} 个开源实战补强项目")
        except Exception as e:
            print(f"  └─ [提示] 开源项目检索跳过或遇到警告: {e}")
    else:
        print("[Step 2/5] 无显著技能缺口或已跳过开源项目检索。")

    # 步骤 3：经历定向 STAR 提分与内存快照定制（零污染原则）
    print("[Step 3/5] 正在针对该岗位关键技术考点进行经历 STAR 提分与装配...")
    # 深拷贝主档案，确保原版 profile.yaml 绝对干净不受污染
    tailored_profile = profile.model_copy(deep=True)
    if tailored_profile.objective:
        tailored_profile.objective.target_role = parsed_jd.role

    polish_report = polish_experiences(profile=tailored_profile, provider=provider)
    _apply_polish_to_profile(tailored_profile, polish_report)
    print(f"  └─ 已完成 {len(polish_report.items)} 条核心经历的定制化 STAR 强化")

    # 步骤 4：编译专属双格式简历
    print("[Step 4/5] 正在调用排版引擎编译生成定制版 PDF 与 Word 简历...")
    if not output_name:
        clean_company = "".join(c for c in parsed_jd.company if c.isalnum() or c in ("_", "-")) or "target"
        clean_role = "".join(c for c in parsed_jd.role if c.isalnum() or c in ("_", "-")) or "role"
        output_name = f"resume_{clean_company}_{clean_role}_tailored"

    resume_paths = generate_resume(
        profile=tailored_profile,
        output_name=output_name,
        template=template,
    )
    print(f"  └─ 定制版简历已输出: {resume_paths['pdf'].name} & {resume_paths['docx'].name}")

    # 步骤 5：封装一键定向投递综合战报
    print("[Step 5/5] 正在封装一键定向投递综合战报...")
    exports_dir = Path("storage/exports")
    exports_dir.mkdir(parents=True, exist_ok=True)

    timestamp_file = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_company = "".join(c for c in parsed_jd.company if c.isalnum() or c in ("_", "-")) or "公司"
    clean_role = "".join(c for c in parsed_jd.role if c.isalnum() or c in ("_", "-")) or "岗位"
    report_filename = f"package_{clean_company}_{clean_role}_{timestamp_file}.md"
    report_path = exports_dir / report_filename

    package = TailoredApplicationPackage(
        target_company=parsed_jd.company,
        target_role=parsed_jd.role,
        job_description=parsed_jd,
        match_result=match_result,
        project_recommendations=project_report,
        tailored_experiences_summary=f"针对 {parsed_jd.role} 核心考点完成了 {len(polish_report.items)} 条经历的 STAR 精修",
        resume_files={
            "pdf": str(resume_paths["pdf"].resolve()),
            "docx": str(resume_paths["docx"].resolve()),
        },
        package_report_path=str(report_path.resolve()),
    )

    report_markdown = _build_package_markdown(package, project_report, polish_report)
    report_path.write_text(report_markdown, encoding="utf-8")
    print(f"  └─ 综合交付物料战报已落盘: {report_path.name}")

    # 联动投递追踪器: 自动登记入库
    if auto_track:
        try:
            record = add_application(
                company=package.target_company,
                role=package.target_role,
                status=ApplicationStatus.APPLIED,
                resume_path=str(resume_paths["pdf"].resolve()),
                note=f"一键定制流水线生成，岗位匹配度: {match_result.score}/100",
            )
            print(f"  └─ [✓ 看板联动] 已自动登记入本地投递看板 (Record ID: #{record.id})")
        except Exception as e:
            print(f"  └─ [提示] 自动登记投递看板跳过: {e}")

    elapsed = time.time() - start_time
    print(f"[✓] 一键岗位定向全套交付流水线顺利完成！总耗时: {elapsed:.2f}s\n")
    return package
