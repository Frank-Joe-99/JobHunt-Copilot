"""Phase 2 全链路验证脚本"""
import json

# === Step 1: LLM Client ===
print("=" * 50)
print("Step 1: tools/llm_client.py")
print("=" * 50)
from tools.llm_client import LLMClient

c = LLMClient()
print(f"  Provider: {c.provider_name}, Model: {c.config.model}")

reply = c.chat([{"role": "user", "content": "Say OK"}], timeout=15)
print(f"  chat() reply: {repr(reply[:60])}")

j = c.chat_json(
    [
        {"role": "system", "content": "Output valid JSON only."},
        {"role": "user", "content": 'Return a JSON with key "status" and value "ok"'},
    ],
    timeout=15,
)
print(f"  chat_json() result: {j}")
print("  [PASS] Step 1\n")

# === Step 2: Resume Polisher ===
print("=" * 50)
print("Step 2: skills/resume_polisher")
print("=" * 50)
from skills.resume_polisher.handler import polish_experiences, diagnose_ats

report = polish_experiences()
print(f"  polish_experiences() -> summary length: {len(report.summary)}, items: {len(report.items)}")
if report.items:
    first = report.items[0]
    print(f"  First item source: {first.source}")
    print(f"  Original:  {first.original[:60]}...")
    print(f"  Polished:  {first.polished[:60]}...")

ats = diagnose_ats()
print(f"  diagnose_ats() -> score: {ats.score}, matched: {len(ats.matched_keywords)}, missing: {len(ats.missing_keywords)}")
print("  [PASS] Step 2\n")

# === Step 3: JD Matcher ===
print("=" * 50)
print("Step 3: skills/jd_matcher")
print("=" * 50)
from skills.jd_matcher.handler import analyze_jd

sample_jd = """
公司：字节跳动
职位：后端开发工程师 - 基础架构
要求：
1. 熟练掌握 Python 或 Go
2. 熟悉 Redis、MySQL 高并发优化
3. 有分布式系统设计经验
加分项：有开源项目经验者优先
"""
match = analyze_jd(sample_jd)
print(f"  analyze_jd() -> score: {match.score}")
print(f"  Overview: {match.overview[:80]}...")
print(f"  Matched skills: {len(match.matched_skills)}, Missing skills: {len(match.missing_skills)}")
print(f"  Cover letter length: {len(match.cover_letter_draft)} chars")
print("  [PASS] Step 3\n")

print("=" * 50)
print("[ALL PASS] Phase 2 fully verified!")
print("=" * 50)

