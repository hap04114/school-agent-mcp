"""
Google Calendar MCP server.

Setup:
1. Go to https://console.cloud.google.com -> create a project (free).
2. Enable the "Google Calendar API" (APIs & Services -> Library).
3. Go to APIs & Services -> Credentials -> Create Credentials -> OAuth client ID.
     - Application type: Desktop app
   Download the JSON, save it in this folder as credentials.json.
4. Go to APIs & Services -> OAuth consent screen -> Audience, add your own
   Google account as a "test user" (required while the app is unpublished,
   which is fine for personal use, totally free).
5. pip install -r ../requirements.txt
6. First run opens a browser window to sign in and approve access. A
   token.json is saved afterward so you won't need to repeat this.
"""

import os
import datetime as dt

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from mcp.server.fastmcp import FastMCP

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
FOLDER = os.path.dirname(__file__)
CREDENTIALS_FILE = os.path.join(FOLDER, "credentials.json")
TOKEN_FILE = os.path.join(FOLDER, "token.json")

mcp = FastMCP("google-calendar")


def _get_credentials() -> Credentials:
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                raise RuntimeError(
                    f"Missing {CREDENTIALS_FILE}. Follow the setup steps in the "
                    "docstring at the top of server.py."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return creds


@mcp.tool()
def list_upcoming_events(days_ahead: int = 7, calendar_id: str = "primary") -> str:
    """List upcoming Google Calendar events in the next N days.

    Args:
        days_ahead: How many days ahead to look.
        calendar_id: Which calendar to check ("primary" for the main one).
    """
    creds = _get_credentials()
    service = build("calendar", "v3", credentials=creds)

    now = dt.datetime.utcnow().isoformat() + "Z"
    end = (dt.datetime.utcnow() + dt.timedelta(days=days_ahead)).isoformat() + "Z"

    events_result = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=now,
            timeMax=end,
            singleEvents=True,
            orderBy="startTime",
            maxResults=50,
        )
        .execute()
    )
    events = events_result.get("items", [])
    if not events:
        return f"No events in the next {days_ahead} days."

    lines = []
    for e in events:
        start = e.get("start", {}).get("dateTime", e.get("start", {}).get("date", "?"))
        lines.append(f"- {e.get('summary', 'Untitled event')} at {start}")
    return "\n".join(lines)


@mcp.tool()
def list_calendars() -> str:
    """List all calendars available on the user's Google account, with their IDs."""
    creds = _get_credentials()
    service = build("calendar", "v3", credentials=creds)
    calendar_list = service.calendarList().list().execute()
    items = calendar_list.get("items", [])
    if not items:
        return "No calendars found."
    return "\n".join(f"- {c.get('id')}: {c.get('summary')}" for c in items)


if __name__ == "__main__":
    mcp.run()
