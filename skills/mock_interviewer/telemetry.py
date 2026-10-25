"""收集调用计数等技术状态，不记录模型正文或认证信息。"""

from core.state import InterviewRequestMetrics


def collect_model_metrics(client, metrics: InterviewRequestMetrics | None):
    if metrics is None:
        return
    meta = getattr(client, "last_response", None)
    metrics.known_model_requests += meta.attempts if meta is not None else 1
    if meta is not None:
        metrics.format_used = meta.format_used
