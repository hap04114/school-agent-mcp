"""
Microsoft (Outlook mail + Outlook calendar) MCP server, via Microsoft Graph.

Setup:
1. Go to https://portal.azure.com -> Azure Active Directory -> App registrations
   -> New registration.
     - Name: anything (e.g. "school-agent")
     - Supported account types: "Accounts in any organizational directory and
       personal Microsoft accounts" (so school + personal Outlook both work)
     - Redirect URI: leave blank (we use device code flow, no redirect needed)
2. After creating it, note the "Application (client) ID" from the Overview page.
3. Under "API permissions" add (Microsoft Graph, Delegated):
     Mail.Read, Calendars.Read, User.Read
   Click "Grant admin consent" if you're able to (not required for personal use).
4. Set environment variable:
     MS_CLIENT_ID   the Application (client) ID from step 2
5. pip install -r ../requirements.txt
6. First run will print a device code + URL. Visit the URL, enter the code,
   sign in with the Outlook account. Token is cached to token_cache.json
   afterward so you won't need to repeat this every time.
"""

import os
import json
import atexit
from datetime import datetime, timedelta, timezone

import msal
import requests
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

CLIENT_ID = os.environ.get("MS_CLIENT_ID", "")
# "common" accepts both school/work and personal accounts; set MS_TENANT to
# "consumers" (personal only) or your school's tenant ID to restrict it.
AUTHORITY = f"https://login.microsoftonline.com/{os.environ.get('MS_TENANT', 'common')}"
SCOPES = ["Mail.Read", "Calendars.Read", "User.Read"]
CACHE_FILE = os.path.join(os.path.dirname(__file__), "token_cache.json")
GRAPH_BASE = "https://graph.microsoft.com/v1.0"

mcp = FastMCP("microsoft-outlook")

_cache = msal.SerializableTokenCache()
if os.path.exists(CACHE_FILE):
    _cache.deserialize(open(CACHE_FILE, "r").read())


def _save_cache():
    if _cache.has_state_changed:
        with open(CACHE_FILE, "w") as f:
            f.write(_cache.serialize())


atexit.register(_save_cache)

_app = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY, token_cache=_cache)


def _get_token() -> str:
    if not CLIENT_ID:
        raise RuntimeError("MS_CLIENT_ID environment variable must be set.")

    accounts = _app.get_accounts()
    result = None
    if accounts:
        result = _app.acquire_token_silent(SCOPES, account=accounts[0])

    if not result:
        flow = _app.initiate_device_flow(scopes=SCOPES)
        if "user_code" not in flow:
            raise RuntimeError(f"Failed to start device flow: {flow}")
        print(flow["message"])  # visible in Claude Desktop's MCP server logs
        result = _app.acquire_token_by_device_flow(flow)

    if "access_token" not in result:
        raise RuntimeError(f"Auth failed: {result.get('error_description')}")

    _save_cache()
    return result["access_token"]


def _graph_get(path: str, params: dict | None = None):
    token = _get_token()
    resp = requests.get(
        f"{GRAPH_BASE}{path}",
        headers={"Authorization": f"Bearer {token}"},
        params=params,
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()


@mcp.tool()
def list_unread_emails(limit: int = 10) -> str:
    """List the user's most recent unread Outlook emails (subject, sender, received time)."""
    data = _graph_get(
        "/me/mailFolders/inbox/messages",
        params={
            "$filter": "isRead eq false",
            "$top": limit,
            "$select": "subject,from,receivedDateTime",
            "$orderby": "receivedDateTime desc",
        },
    )
    messages = data.get("value", [])
    if not messages:
        return "No unread emails."
    lines = []
    for m in messages:
        sender = m.get("from", {}).get("emailAddress", {}).get("address", "unknown")
        lines.append(f"- {m.get('subject')} (from {sender}, {m.get('receivedDateTime')})")
    return "\n".join(lines)


@mcp.tool()
def list_upcoming_events(days_ahead: int = 7) -> str:
    """List upcoming Outlook calendar events in the next N days."""
    now = datetime.now(timezone.utc)
    end = now + timedelta(days=days_ahead)
    data = _graph_get(
        "/me/calendarview",
        params={
            "startDateTime": now.isoformat(),
            "endDateTime": end.isoformat(),
            "$select": "subject,start,end,location",
            "$orderby": "start/dateTime",
            "$top": 50,
        },
    )
    events = data.get("value", [])
    if not events:
        return f"No events in the next {days_ahead} days."
    lines = []
    for e in events:
        start = e.get("start", {}).get("dateTime", "?")
        loc = e.get("location", {}).get("displayName", "")
        lines.append(f"- {e.get('subject')} at {start} {f'({loc})' if loc else ''}")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
