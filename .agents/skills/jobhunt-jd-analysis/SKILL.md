---
name: jobhunt-jd-analysis
description: Analyze a job description against the candidate profile stored in this JobHunt-Copilot repository. Use when the user asks to assess a JD, evaluate role fit, map requirements to evidence, identify gaps, or decide whether a role is worth applying to.
---

# JobHunt JD Analysis

Use the repository's existing JD matcher; do not recreate its profile or matching logic.

## Workflow

1. Locate the `JobHunt-Copilot` repository and confirm its local environment and `config/profile.yaml` are present. Never display the profile file or copy its personal contact fields into chat.
2. Get the JD from the user's message or an explicitly identified local file. If the user supplied only an image, extract its text first. Do not guess missing requirements.
3. From the repository root, pass the JD text to `skills.jd_matcher.handler.analyze_jd` and report the returned structured result. Prefer a short-lived Python invocation with the JD on standard input; do not interpolate arbitrary JD text into executable code.
4. Explain the role's core requirements, evidence-backed matches, gaps, project ordering, and apply/skip recommendation in Chinese unless asked otherwise. Separate direct evidence from transferable experience and unknowns.
5. Flag conflicts or eligibility-critical unknowns, especially graduation date, rather than silently choosing a value. Do not invent tools, proficiency, project results, or experience.

## Privacy and side effects

The matcher loads the local candidate profile and sends profile/JD-derived content to the configured LLM provider. Tell the user this when relevant, and do not run it if the user has asked for offline-only analysis. This skill does not edit the profile, resume, or tracker. Do not print API keys or unrelated personal data.
