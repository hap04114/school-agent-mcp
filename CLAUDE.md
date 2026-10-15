# School agent MCP servers

Three MCP servers exposing Canvas, Outlook, and Google Calendar data as
read-only tools, connectable to Claude Desktop and/or OpenClaw.

## Structure

- `canvas_mcp/server.py` — Canvas LMS REST API. Auth via `CANVAS_TOKEN` +
  `CANVAS_BASE_URL` env vars (personal access token, no OAuth).
- `microsoft_mcp/server.py` — Outlook mail + calendar via Microsoft Graph.
  Auth via MSAL device code flow, `MS_CLIENT_ID` env var. Token cached to
  `microsoft_mcp/token_cache.json`.
- `google_calendar_mcp/server.py` — Google Calendar API. OAuth installed-app
  flow, needs `google_calendar_mcp/credentials.json` (downloaded from Google
  Cloud Console). Token cached to `google_calendar_mcp/token.json`.
- `requirements.txt` — shared dependencies for all three servers.
- `openclaw_config_example.json` — example config for wiring these into
  OpenClaw instead of / alongside Claude Desktop.
- `README.md` — full setup instructions for every account/credential needed.

## Conventions

- **Read-only by design.** No send-email, delete-event, or submit-assignment
  tools. Keep new tools read-only unless explicitly asked to add a write
  action, and flag it clearly if you do.
- Each server is standalone — runs via `python server.py`, no shared code
  between them.
- Auth tokens are cached to local JSON files (`token_cache.json`,
  `token.json`) — safe to delete to force re-authentication.
- Uses `mcp.server.fastmcp.FastMCP` — tools are plain Python functions
  decorated with `@mcp.tool()`, docstring becomes the tool description.
- Never commit `.env`, `token_cache.json`, `token.json`, or
  `credentials.json` — these hold real secrets. Only `.env.example` files
  should be tracked.

## Current status / next steps

- [x] Canvas server tested end-to-end with a real token (2026-09-24;
      Northeastern caps tokens at 90 days — current one expires ~2026-12-22,
      regenerate and update `canvas_mcp/.env` then)
- [ ] Outlook server tested — **BLOCKED (2026-10-15):** Northeastern tenant
      denies students app registration (portal.azure.com → 401). Options:
      ask NU IT to register/consent a read-only app, or use a personal
      Outlook account. Workaround for calendar: publish Outlook calendar as
      ICS and subscribe in Google Calendar.
- [x] Google Calendar server tested (2026-10-15; GCP project `school-agent`,
      Desktop OAuth client, app in Testing mode with personal Gmail as the
      only test user). Testing-mode refresh tokens
      expire after 7 days — on auth errors, delete
      `google_calendar_mcp/token.json` and sign in again.
- [ ] All three connected in Claude Desktop config and verified working
- [ ] (Optional) Wired into OpenClaw for 24/7 + Telegram access

## When adding features

Ask before adding any tool that sends, deletes, or modifies something
(emails, calendar events, assignment submissions) — everything so far is
intentionally read-only for safety.
