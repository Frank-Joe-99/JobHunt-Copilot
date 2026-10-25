"""跨业务的 JD 解析/匹配协调，集中在 core，雷达模块只排名和导出。"""

import logging
from pathlib import Path

from core.config import load_user_profile
from core.state import JobMatchEvaluation, JobRadarReport, RankedOpportunity, UserProfile
from skills.jd_matcher.handler import match_profile_with_jd, parse_jd
from skills.job_radar.handler import export_radar_report, rank_evaluations, read_jd_texts

logger = logging.getLogger(__name__)


def scan_opportunities(
    jd_texts: list[str], profile: UserProfile | None = None, provider: str | None = None,
) -> list[RankedOpportunity]:
    if not jd_texts:
        return []
    if profile is None:
        profile = load_user_profile()
    evaluations = []
    for index, text in enumerate(jd_texts, 1):
        if not text.strip():
            continue
        try:
            job = parse_jd(text.strip(), provider=provider)
            match = match_profile_with_jd(profile, job, provider=provider)
            evaluations.append(JobMatchEvaluation(job=job, match=match))
        except Exception as exc:
            logger.warning("第 %s 份 JD 分析失败，已跳过 (%s)", index, type(exc).__name__)
    return rank_evaluations(evaluations)


def scan_from_directory(
    dir_path: str | Path = "storage/raw_jds", profile: UserProfile | None = None,
    provider: str | None = None,
) -> list[RankedOpportunity]:
    return scan_opportunities(read_jd_texts(dir_path), profile=profile, provider=provider)


def run_radar_pipeline(
    dir_path: str | Path = "storage/raw_jds", profile: UserProfile | None = None,
    provider: str | None = None,
) -> JobRadarReport:
    return export_radar_report(scan_from_directory(dir_path, profile, provider))
