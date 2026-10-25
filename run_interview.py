"""
🎯 JobHunt-Copilot AI 场景化模拟面试终端总控台 (Interactive Interview Runner)
使用方式:
    uv run run_interview.py                  # 交互式菜单引导
    uv run run_interview.py --role strict_architect --company 字节跳动 --target-role 分布式存储工程师
"""

import sys
from pathlib import Path
from typing import Optional

# 确保控制台 UTF-8 输入输出正常 (兼容 Windows Terminal)
if sys.platform == "win32":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    try:
        sys.stdin.reconfigure(encoding="utf-8")
    except Exception:
        pass

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from core.config import load_job_preference, load_user_profile
from core.state import InterviewPolicy, InterviewRole, InterviewStage
from core.interview_service import (
    finish_interview,
    resume_interview,
    start_interview,
    step_interview_stream,
)

app = typer.Typer(help="AI 场景化模拟面试官 CLI 运行器")
console = Console()

# 阶段中英文对照与主题色
STAGE_INFO = {
    InterviewStage.INTRO: ("阶段 1/5", "开场破冰与自我介绍", "cyan"),
    InterviewStage.RESUME_DEEP_DIVE: ("阶段 2/5", "简历项目穿透式深挖", "magenta"),
    InterviewStage.FUNDAMENTALS: ("阶段 3/5", "计算机基础与核心考点", "yellow"),
    InterviewStage.BEHAVIORAL: ("阶段 4/5", "行为情境与综合素养", "blue"),
    InterviewStage.REVERSE_QA: ("阶段 5/5", "候选人反问环节", "purple"),
    InterviewStage.COMPLETED: ("已完成", "面试流程已结束", "green"),
}

# 面试官角色中文映射与人设标签
ROLE_INFO = {
    InterviewRole.STRICT_ARCHITECT: {
        "name": "严苛型技术委员会架构师",
        "badge": "🔴 严苛大牛",
        "color": "red",
        "desc": "死磕底层机制、高并发瓶颈与因果链条，不接受含糊套话",
    },
    InterviewRole.PRACTICAL_LEAD: {
        "name": "务实型业务研发团队主管 (Lead)",
        "badge": "🔵 务实主管",
        "color": "cyan",
        "desc": "关注代码可维护性、方案对比选型、线上排障与工程交付",
    },
    InterviewRole.HRBP: {
        "name": "资深大厂校招与雇主品牌 HRBP",
        "badge": "🟢 亲和 HR",
        "color": "green",
        "desc": "考察求职动机、团队协作、沟通表达与抗压稳定性",
    },
}


def render_banner() -> None:
    """打印欢迎横幅"""
    banner_text = Text()
    banner_text.append("🎯 JobHunt-Copilot AI 全真场景化模拟面试官\n", style="bold cyan")
    banner_text.append(
        "多轮状态机 · 穿透式追问 · 真实大厂人设 · 全景复盘体检报告", style="dim"
    )
    console.print(
        Panel(banner_text, border_style="cyan", padding=(1, 2), expand=False)
    )


def select_role(preset_role: Optional[str] = None) -> InterviewRole:
    """选择面试官角色"""
    if preset_role:
        for r in InterviewRole:
            if r.value.lower() == preset_role.lower():
                return r

    table = Table(title="👥 请选择你希望演练的面试官风格", border_style="blue")
    table.add_column("序号", style="bold yellow", width=6)
    table.add_column("面试官类型", style="bold", width=22)
    table.add_column("考核偏好与风格特点", style="dim")

    table.add_row("1", "🔴 严苛型大牛架构师", "深度死磕底层原理、高并发极限、指标量化与因果推导")
    table.add_row("2", "🔵 务实型研发主管 (Lead)", "关注工程落地、技术选型权衡、线上排障链路与代码规范")
    table.add_row("3", "🟢 亲和型资深 HRBP", "关注自驱力、团队沟通冲突解决、职业规划与抗压韧性")

    console.print(table)
    choice = Prompt.ask(
        "请输入面试官序号 [1/2/3]", choices=["1", "2", "3"], default="1"
    )

    mapping = {
        "1": InterviewRole.STRICT_ARCHITECT,
        "2": InterviewRole.PRACTICAL_LEAD,
        "3": InterviewRole.HRBP,
    }
    return mapping[choice]


def select_target(
    preset_company: Optional[str] = None, preset_role: Optional[str] = None
) -> tuple[str, str]:
    """选择目标公司与求职岗位"""
    if preset_company and preset_role:
        return preset_company, preset_role

    table = Table(title="🏢 请选择本次模拟面试的目标企业与岗位", border_style="cyan")
    table.add_column("序号", style="bold yellow", width=6)
    table.add_column("企业 / 部门", style="bold", width=18)
    table.add_column("求职目标岗位", style="green")

    table.add_row("1", "字节跳动", "基础架构 · 高性能计算与分布式存储工程师")
    table.add_row("2", "阿里巴巴", "阿里云基础软件 · 云原生分布式系统研发")
    table.add_row("3", "腾讯", "微信技术架构部 · 高并发后端研发工程师")
    table.add_row("4", "配置文件偏好", "从 config/preferences.yaml 自动读取目标岗位")
    table.add_row("5", "自定义输入", "手动指定目标企业与岗位名称")

    console.print(table)
    choice = Prompt.ask(
        "请选择岗位序号 [1/2/3/4/5]", choices=["1", "2", "3", "4", "5"], default="1"
    )

    if choice == "1":
        return "字节跳动", "高性能计算与分布式存储工程师"
    elif choice == "2":
        return "阿里巴巴", "云原生分布式系统工程师"
    elif choice == "3":
        return "腾讯", "高并发后端研发工程师"
    elif choice == "4":
        try:
            pref = load_job_preference()
            target_roles = pref.search_criteria.target_roles
            target = target_roles[0] if target_roles else "后端开发工程师"
            company = pref.search_criteria.company_types[0] if pref.search_criteria.company_types else "一线互联网大厂"
            return company, target
        except Exception:
            return "目标大厂", "后端研发工程师"
    else:
        company = Prompt.ask("请输入目标企业名称 (如: 百度 / 华为 / 美团)", default="目标大厂")
        role = Prompt.ask("请输入目标岗位名称 (如: AI Infra 研究员)", default="核心研发工程师")
        return company, role


def get_candidate_input() -> str:
    """
    获取候选人终端回答，支持换行排版与代码粘贴。
    提交方式：
    1. 输入内容后，按 Enter 换行，再按一次 Enter（即空行回车）自动提交
    2. 或在末尾单独一行输入 /send 立即提交
    3. /next 跳过，/finish 交卷，/pause 暂停，/retry 重试失败请求
    """
    console.print(
        "\n[bold green]👤 候选人回答[/bold green] "
        "[dim](空行或 /send 提交；/next 跳过；/finish 交卷；/pause 暂停；/retry 重试)[/dim]:"
    )

    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            # 兼容 Ctrl+Z / Ctrl+D
            if lines:
                break
            return "/pause"
        except KeyboardInterrupt:
            console.print("\n[yellow]检测到中断，正在暂停会话...[/yellow]")
            return "/pause"

        clean_line = line.strip()

        # 检查是否是控制指令
        stripped_lower = clean_line.lower()
        if stripped_lower in ("/next", "next", "跳过"):
            return "/next"
        if stripped_lower in ("/finish", "finish", "交卷", "quit", "/quit"):
            return "/finish"
        if stripped_lower in ("/pause", "pause", "暂停"):
            return "/pause"
        if stripped_lower in ("/retry", "retry", "重试"):
            return "/retry"
        if stripped_lower in ("/send", "send", "/done", "done", "//"):
            # 显式提交指令
            break

        # 空行判定：消除所有空格、制表符与不可见字符后的空行
        if not clean_line:
            if lines:
                # 已经录入过内容，输入空行代表连续两次回车结束作答
                break
            else:
                # 用户还没开始输入就误敲回车，忽略并继续等待输入
                continue

        lines.append(line)

    raw_text = "\n".join(lines).strip()
    result = raw_text.encode("utf-8", errors="replace").decode("utf-8")
    if result and result not in ("/next", "/finish"):
        console.print("[dim]⚡ 回答已提交，面试官正在思考与追问...[/dim]")
    return result


def render_stage_header(stage: InterviewStage, role: InterviewRole, company: str, target_role: str) -> None:
    """渲染当前阶段状态指示条"""
    stage_num, stage_name, color = STAGE_INFO.get(stage, ("进行中", "问答交互", "white"))
    role_meta = ROLE_INFO[role]

    status_line = (
        f"[{role_meta['color']}]{role_meta['badge']}[/{role_meta['color']}] · "
        f"[bold white]{company}[/bold white]（{target_role}） │ "
        f"[bold {color}]{stage_num}：{stage_name}[/bold {color}]"
    )
    console.print(f"\n{status_line}")
    console.print("[dim]─" * 68 + "[/dim]")


def render_debrief_dashboard(report, file_path: Path) -> None:
    """渲染复盘体检成绩单仪表盘"""
    console.print("\n" + "═" * 70, style="bold cyan")
    console.print("       🏆 AI 模拟面试全景复盘体检报告", style="bold cyan")
    console.print("═" * 70 + "\n", style="bold cyan")

    # 1. 核心综合评定卡
    score = report.overall_score
    if score >= 80:
        score_color = "bold green"
        verdict_color = "bold green"
    elif score >= 65:
        score_color = "bold yellow"
        verdict_color = "bold yellow"
    else:
        score_color = "bold red"
        verdict_color = "bold red"

    score_panel = Panel(
        f"综合总分: [{score_color}]{score} / 100[/{score_color}]   "
        f"练习结果建议: [{verdict_color}]{report.result}[/{verdict_color}]\n\n"
        f"[dim]{report.summary}[/dim]",
        title="[bold]📊 综合评级[/bold]",
        border_style="cyan",
        padding=(1, 2),
    )
    console.print(score_panel)

    # 2. 多维度打分条形表
    table = Table(title="📈 岗位相关能力诊断", border_style="blue", expand=False)
    table.add_column("能力维度", style="bold white", width=16)
    table.add_column("分值", style="bold", width=8)
    table.add_column("表现诊断条", width=26)
    table.add_column("评级", width=10)

    for dim, d_score in report.dimension_scores.items():
        filled = int(d_score / 10)
        empty = 10 - filled
        if d_score >= 85:
            bar_color = "green"
            tag = "[green]🟢 优秀[/green]"
        elif d_score >= 70:
            bar_color = "yellow"
            tag = "[yellow]🟡 良好[/yellow]"
        else:
            bar_color = "red"
            tag = "[red]🔴 需加固[/red]"

        bar = f"[{bar_color}]{'█' * filled}{'░' * empty}[/{bar_color}]"
        table.add_row(dim, str(d_score), bar, tag)

    console.print(table)

    # 3. 亮点与失分项
    if report.highlights:
        hl_text = "\n".join(f"[green]✔[/green] {h}" for h in report.highlights)
        console.print(Panel(hl_text, title="[bold green]🌟 回答高光亮点[/bold green]", border_style="green"))

    if report.weaknesses:
        wk_text = "\n".join(f"[red]✘[/red] {w}" for w in report.weaknesses)
        console.print(Panel(wk_text, title="[bold red]⚠️ 核心失分硬伤[/bold red]", border_style="red"))

    # 4. 满分示范指引
    num_models = len(report.model_answers)
    console.print(
        f"\n[bold yellow]💡 本次复盘已生成 {num_models} 道核心考点的标准满分参考回答 (Model Answers)[/bold yellow]"
    )
    console.print(
        f"完整报告已落盘（包含全场问答实录与逐题满分示范）:\n"
        f"[bold underline cyan]{file_path.resolve().as_uri()}[/bold underline cyan]\n"
    )


def display_stream(stream, session, provider=None) -> None:
    """终端展示可以失败；持久化服务负责保存回答并隔离部分问题。"""
    role_color = ROLE_INFO[session.role]["color"]
    console.print(f"\n[bold {role_color}]🤖 面试官：[/bold {role_color}]", end="")
    try:
        for chunk in stream:
            console.print(chunk, end="", highlight=False, markup=False)
            sys.stdout.flush()
    except KeyboardInterrupt:
        stream.close()
        list(step_interview_stream(session, "/pause", provider=provider))
        console.print("\n[yellow]会话已暂停，已提交的回答已保存。[/yellow]")
    except (ValueError, RuntimeError, OSError) as exc:
        console.print(f"\n[bold red]本次请求未完成：[/bold red]{exc}")
        console.print("[yellow]回答已保存。输入 /retry 重试、/pause 暂停或 /finish 交卷。[/yellow]")
    console.print()


@app.command()
def main(
    role: Optional[str] = typer.Option(None, "--role", "-r", help="面试官风格: strict_architect / practical_lead / hrbp"),
    company: Optional[str] = typer.Option(None, "--company", "-c", help="目标企业名称"),
    target_role: Optional[str] = typer.Option(None, "--target-role", "-t", help="目标岗位名称"),
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="指定大模型供应商"),
    jd: Optional[str] = typer.Option(None, "--jd", help="可选 JD 文本或本地文本路径"),
    mode: str = typer.Option("simulation", "--mode", help="simulation 模拟 / practice 训练"),
    resume_session: Optional[str] = typer.Option(None, "--resume-session", help="恢复已有会话 ID"),
    flow: str = typer.Option("fixed", "--flow", help="fixed / adaptive"),
    max_turns: Optional[int] = typer.Option(None, "--max-turns", min=1, max=60),
    max_duration: Optional[int] = typer.Option(None, "--max-duration", min=1, max=7200),
    max_followups: Optional[int] = typer.Option(None, "--max-followups", min=0, max=4),
    request_budget: Optional[int] = typer.Option(None, "--request-budget", min=1, max=3),
    max_requests: Optional[int] = typer.Option(None, "--max-requests", min=1, max=180),
    request_timeout: Optional[int] = typer.Option(None, "--request-timeout", min=1, max=120),
) -> None:
    """启动或恢复 AI 模拟面试，保存的事实快照不会随主档案变化。"""
    render_banner()
    try:
        if mode not in ("simulation", "practice"):
            raise ValueError("mode 必须为 simulation 或 practice。")
        if flow not in ("fixed", "adaptive"):
            raise ValueError("flow 必须为 fixed 或 adaptive。")
        policy_values = {key: value for key, value in {
            "max_turns": max_turns, "max_duration_seconds": max_duration,
            "max_followups": max_followups, "max_requests_per_turn": request_budget,
            "max_requests_total": max_requests, "request_timeout_seconds": request_timeout,
        }.items() if value is not None}
        if resume_session:
            if any(value is not None for value in (role, company, target_role, jd)) or policy_values or flow != "fixed":
                raise ValueError("恢复使用原岗位、风格和 JD；背景变化请新建会话。")
            session = resume_interview(resume_session)
            stream = None
        else:
            selected_role = select_role(role)
            selected_company, selected_target_role = select_target(company, target_role)
            profile = load_user_profile()
            job_description = None
            if jd:
                from core.workflow import _resolve_jd_text
                from core.state import JobDescription
                job_description = JobDescription(
                    company=selected_company, role=selected_target_role, raw_text=_resolve_jd_text(jd),
                )
            session, stream = start_interview(
                profile=profile, target_role=selected_target_role,
                target_company=selected_company, role=selected_role, provider=provider,
                job_description=job_description, mode=mode,
                flow=flow, policy=InterviewPolicy(**policy_values) if policy_values or flow == "adaptive" else None,
            )
    except (FileNotFoundError, ValueError, RuntimeError, OSError) as exc:
        console.print(Panel(str(exc), title="会话初始化失败", border_style="red"))
        raise typer.Exit(code=2) from None

    console.print(f"\n[bold green]会话已保存：[/bold green]{session.session_id}")
    console.print(f"目标：{session.target_company} · {session.target_role}（{session.mode} / {session.flow}）", markup=False)
    if session.flow == "adaptive":
        console.print("自适应试验：每轮校验动作和完整问题后显示；可新建 --flow fixed 会话回到原流式流程。", markup=False)
    console.print(f"恢复命令：uv run jobhunt interview --resume-session {session.session_id}", markup=False)
    console.print("[dim]/next 跳过；/finish 交卷；/pause 暂停；/retry 重试。[/dim]")
    render_stage_header(session.current_stage, session.role, session.target_company, session.target_role)

    if stream is not None:
        display_stream(stream, session, provider)
    elif not session.is_finished and session.history:
        console.print(session.history[-1].question, markup=False)
    if session.pending_request_id:
        console.print("[yellow]有未完成请求；请 /retry 重试，或 /finish 交卷。[/yellow]")

    while not session.is_finished and not session.is_paused:
        user_answer = get_candidate_input()
        if not user_answer:
            continue
        prev_stage = session.current_stage
        stream = step_interview_stream(session, user_answer, provider=provider)
        display_stream(stream, session, provider)
        if session.current_stage != prev_stage and not session.is_finished:
            render_stage_header(session.current_stage, session.role, session.target_company, session.target_role)

    if session.is_paused:
        console.print(f"已暂停。恢复：uv run jobhunt interview --resume-session {session.session_id}", markup=False)
        return

    try:
        with console.status("[bold green]正在基于完整问答生成复盘报告...[/bold green]"):
            report, file_path = finish_interview(session=session, provider=provider)
    except (ValueError, RuntimeError, OSError) as exc:
        console.print(f"[bold red]复盘生成失败，会话仍已保存：[/bold red]{exc}")
        console.print(f"重试：uv run jobhunt interview --resume-session {session.session_id}", markup=False)
        raise typer.Exit(code=2) from None
    render_debrief_dashboard(report, file_path)


if __name__ == "__main__":
    app()
