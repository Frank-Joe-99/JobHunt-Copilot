"""
🎯 JobHunt-Copilot 统一终端命令总控网关 (Unified CLI Gateway)
提供一站式求职赋能：一键定向全套交付、全真 AI 模拟面试、投递看板与日程、机会雷达扫描与 MCP 协议服务。
"""

import sys
from pathlib import Path
from typing import Optional

# 确保 Windows 终端 UTF-8 编码
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        sys.stdin.reconfigure(encoding="utf-8")
    except Exception:
        pass

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns

app = typer.Typer(
    name="jobhunt",
    help="🎯 JobHunt-Copilot：大模型时代的智能求职外挂与交付引擎",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
console = Console()

# 投递看板独立子命令集
tracker_app = typer.Typer(
    name="tracker",
    help="📋 求职投递看板、面试日程与转化漏斗管理",
    no_args_is_help=False,
    rich_markup_mode="rich",
)
app.add_typer(tracker_app, name="tracker")


# ==============================================================================
# 1. 一键岗位定向全套交付 (tailor)
# ==============================================================================

@app.command(name="tailor")
def cmd_tailor(
    jd: str = typer.Argument(..., help="岗位招聘 JD 文本或本地文件路径 (如: storage/raw_jds/01_bytedance_backend.txt)"),
    output_name: Optional[str] = typer.Option(None, "--output-name", "-o", help="输出简历基本文件名（无需后缀）"),
    template: str = typer.Option("modern", "--template", "-t", help="简历排版模板 (默认: modern)"),
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="大模型供应商 (如: deepseek/aliyun/custom)"),
    no_github: bool = typer.Option(False, "--no-github", help="跳过 GitHub 开源实战项目检索"),
    no_track: bool = typer.Option(False, "--no-track", help="不自动将本次投递登记到投递看板"),
):
    """
    🚀 【一键岗位定向全套交付流】
    输入目标岗位 JD，端到端执行：JD深度比对 ➔ 开源项目补强 ➔ 经历 STAR 强化 ➔ 编译专属双格式简历 ➔ 综合交付物料战报 ➔ 自动登记入库。
    """
    from core.workflow import tailor_application_flow

    console.print(Panel(
        "[bold cyan]🎯 JobHunt-Copilot 一键岗位定向交付流水线启动[/bold cyan]\n"
        "正在进行 JD 深度穿透比对、技能补短板、经历定向 STAR 提分与专属简历编译...",
        border_style="cyan"
    ))

    package = tailor_application_flow(
        jd_input=jd,
        output_name=output_name,
        template=template,
        provider=provider,
        enable_github_search=not no_github,
        auto_track=not no_track,
    )

    pdf_p = Path(package.resume_files.get("pdf", ""))
    docx_p = Path(package.resume_files.get("docx", ""))
    report_p = Path(package.package_report_path)

    table = Table(title="📦 交付物料明细清单", border_style="green", show_lines=True)
    table.add_column("物料类型", style="bold cyan", width=18)
    table.add_column("路径 / 状态", style="yellow")

    table.add_row("目标企业与岗位", f"{package.target_company} · {package.target_role}")
    table.add_row("岗位契合度得分", f"[bold green]{package.match_result.score} / 100[/bold green]")
    table.add_row("📄 PDF 定制简历", str(pdf_p.resolve()) if pdf_p.exists() else "生成中")
    table.add_row("📝 Word 定制简历", str(docx_p.resolve()) if docx_p.exists() else "生成中")
    table.add_row("📊 综合交付物料战报", str(report_p.resolve()) if report_p.exists() else "未落盘")

    console.print(table)
    console.print(Panel(
        f"[bold green]✔ 一键定向交付全部完成！[/bold green]\n"
        f"自荐信草稿与缺口补强方案已写入：[underline]{report_p}[/underline]\n"
        f"简历已就绪，祝您直投顺畅、早日拿 Offer！",
        border_style="green"
    ))


# ==============================================================================
# 2. 基础简历极速编译 (resume)
# ==============================================================================

@app.command(name="resume")
def cmd_resume(
    template: str = typer.Option("modern", "--template", "-t", help="简历排版视觉模板 (默认: modern)"),
    output_name: str = typer.Option("resume_default", "--output-name", "-o", help="输出简历基本文件名"),
):
    """
    📄 【基础简历极速排版编译】
    基于 config/profile.yaml 主档案，秒级排版编译输出最新 PDF 与 Word 双格式简历。
    """
    from skills.resume_generator import generate_resume

    with console.status("[bold green]正在根据 profile.yaml 排版并编译简历...[/bold green]"):
        paths = generate_resume(template=template, output_name=output_name)

    pdf_p = paths["pdf"]
    docx_p = paths["docx"]

    table = Table(title="✨ 简历编译成功", border_style="cyan")
    table.add_column("格式", style="bold cyan")
    table.add_column("文件大小", style="green")
    table.add_column("保存物理路径", style="yellow")

    table.add_row("PDF 格式 (推荐直投)", f"{pdf_p.stat().st_size:,} bytes", str(pdf_p.resolve()))
    table.add_row("Word 格式 (便于微调)", f"{docx_p.stat().st_size:,} bytes", str(docx_p.resolve()))

    console.print(table)


# ==============================================================================
# 3. 全真 AI 模拟面试官 (interview)
# ==============================================================================

@app.command(name="interview")
def cmd_interview(
    role: Optional[str] = typer.Option(None, "--role", "-r", help="面试官人设 (strict_architect / practical_lead / hrbp)"),
    company: Optional[str] = typer.Option(None, "--company", "-c", help="目标企业名称 (如: 字节跳动)"),
    target_role: Optional[str] = typer.Option(None, "--target-role", help="目标求职岗位 (如: 后端开发工程师)"),
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="大模型供应商"),
):
    """
    🎯 【全真 AI 模拟面试官】
    启动终端沉浸式场景化模拟面试：5 大面试阶段流转、三大真实面试官人设追问、全景复盘体检报告。
    """
    import run_interview
    run_interview.main(
        role=role,
        company=company,
        target_role=target_role,
        provider=provider,
    )


# ==============================================================================
# 4. 机会雷达扫描 (radar)
# ==============================================================================

@app.command(name="radar")
def cmd_radar(
    dir_path: str = typer.Option("storage/raw_jds", "--dir", "-d", help="存放待扫描 JD 文件的本地目录"),
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="大模型供应商"),
):
    """
    📡 【全网/批量岗位机会雷达】
    批量扫描指定目录中的岗位 JD，按人岗契合度智能降序排名，提取高频短板并出具战略报告。
    """
    from skills.job_radar import scan_from_directory, export_radar_report

    with console.status(f"[bold cyan]正在扫描 {dir_path} 中的所有岗位 JD...[/bold cyan]"):
        opportunities = scan_from_directory(dir_path=dir_path, provider=provider)

    if not opportunities:
        console.print(f"[yellow]提示：目录 {dir_path} 中未找到有效的 .txt 岗位 JD 文件。[/yellow]")
        return

    report = export_radar_report(opportunities)

    table = Table(title=f"📡 机会雷达智能排名榜 (共扫描 {len(opportunities)} 个岗位)", border_style="magenta", show_lines=True)
    table.add_column("排名", style="bold cyan", width=6)
    table.add_column("企业 / 部门", style="bold white", width=14)
    table.add_column("目标岗位", style="bold yellow", width=18)
    table.add_column("得分", style="bold green", width=8)
    table.add_column("投递梯队", style="magenta", width=10)
    table.add_column("核心短板缺口", style="red", width=22)

    for opp in opportunities:
        table.add_row(
            f"#{opp.rank}",
            f"{opp.company}\n({opp.department})" if opp.department else opp.company,
            opp.role,
            f"{opp.score} 分",
            opp.tier,
            ", ".join(opp.key_gaps) if opp.key_gaps else "无显著缺口",
        )

    console.print(table)
    console.print(f"[bold green]✔ 战略复盘报告已生成：[/bold green] [underline]{report.report_file_path}[/underline]")


# ==============================================================================
# 5. MCP 跨生态协议服务启动 (mcp)
# ==============================================================================

@app.command(name="mcp")
def cmd_mcp():
    """
    🔌 【启动 Model Context Protocol 服务端】
    以标准 stdio 协议运行 MCP 服务端，供 Claude Desktop、Cursor IDE、VS Code 等宿主即插即用。
    """
    from adapters.mcp_server import main as run_mcp
    run_mcp()


# ==============================================================================
# 6. 求职投递看板与日程管理 (tracker)
# ==============================================================================

@tracker_app.callback(invoke_without_command=True)
def tracker_dashboard(ctx: typer.Context):
    """展示求职投递总看板、近期面试日程与转化漏斗 (默认行为)"""
    if ctx.invoked_subcommand is not None:
        return

    from skills.application_tracker import (
        get_funnel_analytics,
        get_upcoming_schedules,
        list_applications,
    )

    funnel = get_funnel_analytics()
    schedules = get_upcoming_schedules(days_ahead=7)
    recent_apps = list_applications(limit=15)

    # 1. 漏斗指标面板
    funnel_panel = Panel(
        f"[bold]投递总量[/bold]: [cyan]{funnel.total_count}[/cyan]  │  "
        f"[bold]正式投递[/bold]: [blue]{funnel.applied_count}[/blue]  │  "
        f"[bold]笔试测评[/bold]: [yellow]{funnel.assessment_count}[/yellow]  │  "
        f"[bold]技术面试[/bold]: [magenta]{funnel.interview_count}[/magenta]  │  "
        f"[bold]录用Offer[/bold]: [bold green]{funnel.offer_count}[/bold green]  │  "
        f"[bold]已淘汰[/bold]: [red]{funnel.rejected_count}[/red]\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 [bold]进面率[/bold]: [bold cyan]{funnel.interview_rate}%[/bold cyan]   "
        f"🎉 [bold]Offer 转化率[/bold]: [bold green]{funnel.offer_rate}%[/bold green]   "
        f"🔥 [bold]在途进行中流程[/bold]: [bold yellow]{funnel.active_in_progress}[/bold yellow] 家",
        title="📊 个人求职全景转化漏斗 (Funnel Analytics)",
        border_style="cyan",
    )
    console.print(funnel_panel)

    # 2. 近期待办日程
    if schedules:
        sched_table = Table(title="⏰ 未来 7 天待办面试/笔试日程", border_style="yellow")
        sched_table.add_column("时间", style="bold yellow", width=18)
        sched_table.add_column("企业 / 岗位", style="bold white", width=22)
        sched_table.add_column("阶段", style="cyan", width=12)
        sched_table.add_column("倒计时", style="bold green", width=10)
        sched_table.add_column("备忘 / 会议链接", style="white")

        for s in schedules:
            cd_str = "[bold red]今天！[/bold red]" if s.days_left == 0 else f"{s.days_left} 天后"
            sched_table.add_row(
                s.schedule_time,
                f"{s.company} · {s.role}",
                s.status.label,
                cd_str,
                s.notes or "无",
            )
        console.print(sched_table)
    else:
        console.print("[dim]⏰ 未来 7 天暂无待办面试日程，保持状态随时迎战！[/dim]\n")

    # 3. 投递记录明细表
    if recent_apps:
        app_table = Table(title="📋 最近投递与流程跟踪清单 (Top 15)", border_style="blue", show_lines=True)
        app_table.add_column("ID", style="bold cyan", width=5)
        app_table.add_column("目标企业", style="bold white", width=12)
        app_table.add_column("求职岗位", style="yellow", width=18)
        app_table.add_column("当前阶段", style="bold magenta", width=14)
        app_table.add_column("投递日期", style="dim", width=12)
        app_table.add_column("最新日程 / 备注", style="white")

        for a in recent_apps:
            latest_note = a.notes[-1] if a.notes else "无"
            schedule_info = f"[yellow]📅 {a.next_schedule_time}[/yellow]\n" if a.next_schedule_time else ""
            app_table.add_row(
                str(a.id),
                a.company,
                a.role,
                a.status.label,
                a.apply_date,
                f"{schedule_info}{latest_note}",
            )
        console.print(app_table)
    else:
        console.print("[dim]看板暂无投递记录，可通过 `jobhunt tailor` 或 `jobhunt tracker add` 登记第一家企业！[/dim]\n")


@tracker_app.command(name="add")
def tracker_add(
    company: str = typer.Option(..., "--company", "-c", help="企业名称 (如: 字节跳动)"),
    role: str = typer.Option(..., "--role", "-r", help="岗位名称 (如: 后端开发工程师)"),
    status: str = typer.Option("applied", "--status", "-s", help="状态 (wishlist/applied/assessment/interview_1/interview_2/hr_stage/offer/rejected/closed)"),
    salary: Optional[str] = typer.Option(None, "--salary", help="薪资预期或范围"),
    location: Optional[str] = typer.Option(None, "--location", "-l", help="工作地点"),
    schedule: Optional[str] = typer.Option(None, "--schedule", help="面试或笔试时间 (YYYY-MM-DD HH:MM)"),
    notes: Optional[str] = typer.Option(None, "--notes", help="日程备忘或会议号"),
    note: Optional[str] = typer.Option(None, "--note", "-n", help="流转备注信息"),
):
    """登记一条新的求职投递记录"""
    from skills.application_tracker import add_application

    record = add_application(
        company=company,
        role=role,
        status=status,
        salary_range=salary,
        location=location,
        next_schedule_time=schedule,
        next_schedule_notes=notes,
        note=note,
    )
    console.print(f"[bold green]✔ 投递登记成功！[/bold green] 记录 ID: [cyan]#{record.id}[/cyan], 当前阶段: [magenta]{record.status.label}[/magenta]")


@tracker_app.command(name="update")
def tracker_update(
    record_id: int = typer.Argument(..., help="待更新的投递记录 ID"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="推进状态 (wishlist/applied/assessment/interview_1/interview_2/hr_stage/offer/rejected/closed)"),
    schedule: Optional[str] = typer.Option(None, "--schedule", help="更新面试/笔试日程 (YYYY-MM-DD HH:MM)"),
    notes: Optional[str] = typer.Option(None, "--notes", help="更新日程备注/会议号"),
    salary: Optional[str] = typer.Option(None, "--salary", help="更新薪资待遇预期"),
    location: Optional[str] = typer.Option(None, "--location", "-l", help="更新地点"),
    note: Optional[str] = typer.Option(None, "--note", "-n", help="追加跟进或面试复盘备忘流水"),
    clear_schedule: bool = typer.Option(False, "--clear-schedule", help="清空已完成的日程提醒"),
):
    """推进求职流程阶段、预约面试日程或追加复盘备忘"""
    from skills.application_tracker import update_status

    updated = update_status(
        record_id=record_id,
        status=status,
        next_schedule_time=schedule,
        next_schedule_notes=notes,
        salary_range=salary,
        location=location,
        note=note,
        clear_schedule=clear_schedule,
    )
    if not updated:
        console.print(f"[bold red]❌ 未找到 ID 为 #{record_id} 的投递记录！[/bold red]")
        return

    console.print(f"[bold green]✔ 记录 #{record_id} 更新成功！[/bold green] 当前阶段: [magenta]{updated.status.label}[/magenta]")


@tracker_app.command(name="schedules")
def tracker_schedules(
    days: int = typer.Option(7, "--days", "-d", help="检索未来多少天内的日程"),
):
    """查询近期待办面试与笔试日程"""
    from skills.application_tracker import get_upcoming_schedules

    events = get_upcoming_schedules(days_ahead=days)
    if not events:
        console.print(f"[dim]未来 {days} 天内无待办笔试/面试日程。[/dim]")
        return

    sched_table = Table(title=f"⏰ 未来 {days} 天待办日程提醒", border_style="yellow")
    sched_table.add_column("时间", style="bold yellow", width=18)
    sched_table.add_column("企业 / 岗位", style="bold white", width=22)
    sched_table.add_column("阶段", style="cyan", width=12)
    sched_table.add_column("倒计时", style="bold green", width=10)
    sched_table.add_column("备忘 / 会议链接", style="white")

    for s in events:
        cd_str = "[bold red]今天！[/bold red]" if s.days_left == 0 else f"{s.days_left} 天后"
        sched_table.add_row(
            s.schedule_time,
            f"{s.company} · {s.role}",
            s.status.label,
            cd_str,
            s.notes or "无",
        )
    console.print(sched_table)


def main():
    """主程序入口"""
    app()


if __name__ == "__main__":
    main()
