---
name: jobhunt-application-package
description: Prepare a complete, role-tailored JobHunt-Copilot application package from one job description, including match analysis, evidence-grounded resume materials, and local Word/PDF outputs. Use when the user asks to tailor a resume or prepare application materials for a specific role.
---

# JobHunt Application Package

1. Obtain the exact JD text or a specific local JD file. Confirm local profile/config exists; never expose private contact details in chat.
2. Before running the full flow, explain that candidate/JD-derived content is sent to the configured LLM provider. The default CLI workflow also queries GitHub and records preparation as a wishlist item, never as a submitted application. Unless the user asks for those actions, disable them with `--no-github --no-track`. The MCP composite tool still defaults to `auto_track=false`.
3. From the repository root run `uv run jobhunt tailor <JD-text-or-file> --no-github --no-track`. Use `--output-name` only when requested.
4. Review the generated report, full resume diff, and Word/PDF draft for factual fidelity. Stable references are valid only within the exported snapshot. Suggestions flagged for confirmation are not applied; the draft keeps their original text. Check ownership, proficiency, dates, metrics, and project status; automated checks do not prove semantic truth. Keep the private snapshot backup local.
5. Return local paths to the deliverables and a concise summary of fit, gaps, and any facts the user should verify. Do not submit the application, update the tracker, or commit generated files unless separately requested.

Treat outputs in `storage/` as private local artifacts. Never include API keys or unrelated personal data in reports or chat.
