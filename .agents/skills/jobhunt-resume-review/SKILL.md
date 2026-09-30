---
name: jobhunt-resume-review
description: Review and improve resume/project experience wording using the local JobHunt-Copilot profile, STAR structure, and ATS diagnosis. Use when the user asks to polish resume bullets, tailor evidence to a JD, or diagnose resume keyword coverage.
---

# JobHunt Resume Review

Use `skills.resume_polisher.handler` for the repository's saved profile. If the user provides a different resume draft, review that text directly and clearly distinguish it from the saved profile; do not silently replace or merge either source.

## Workflow

1. Confirm the repository's local environment and profile configuration exist. Never display `config/profile.yaml` or expose contact/identity fields in chat.
2. If a target JD was supplied, pass it to `diagnose_ats(target_jd_text=...)`; also call `polish_experiences()` when the user wants project/experience rewrites. These APIs read the local profile.
3. Present evidence-based suggestions in Chinese: stronger verbs, clearer situation/action/result, relevant JD keywords, and any unsupported or ambiguous claims to confirm.
4. Preserve the candidate's actual responsibility and skill level. Never invent employers, projects, tools, performance numbers, scale, authorship, or impact. When a metric is missing, use `[待确认：测试口径/数据]` or suggest how to measure it; do not estimate it.
5. Return draft bullets for review. Do not edit the main profile or overwrite resume files unless the user explicitly asks for those file changes.

## Privacy

Polishing and ATS diagnosis send profile/JD-derived content to the configured LLM provider. Do not run for an offline-only request. Avoid reproducing personal contact details or unrelated profile fields in the response.
