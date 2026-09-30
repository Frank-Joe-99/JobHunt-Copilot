---
name: jobhunt-application-tracker
description: View or update the local JobHunt-Copilot job-application tracker, interview schedule, and funnel. Use when the user asks to check application status, record a submission, change a stage, add an interview schedule, or review upcoming deadlines.
---

# JobHunt Application Tracker

The tracker is a local SQLite database. Treat it as the user's private record.

1. For read requests, use `uv run jobhunt tracker` for the dashboard or `uv run jobhunt tracker schedules --days <N>` for upcoming events.
2. Add or update an application only when the user explicitly asks. Use `uv run jobhunt tracker add` or `uv run jobhunt tracker update` and preserve company, role, dates, status, and notes exactly as provided. Do not infer that the user applied, passed an interview, or received an offer.
3. Before changing a record, identify it unambiguously; ask if multiple records match. Confirm the proposed status and schedule when the user's instruction is unclear.
4. Keep conference links, recruiter details, compensation, and private notes out of chat unless needed to answer the request.
5. Do not contact employers, submit applications, or change any external portal. Do not delete tracker records unless the user explicitly identifies the record and requests deletion.

Tracker state is local and ignored by Git; do not stage or commit its database.
