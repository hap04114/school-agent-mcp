"""
Piazza MCP server.

Exposes recent posts from a Piazza class as read-only tools. Piazza has no
official API, so this uses the unofficial `piazza-api` package and logs in
with your Piazza email + password.

Setup:
1. Find your class's network ID: open the class on piazza.com, the URL is
   https://piazza.com/class/<network_id>
2. If you sign in to Piazza via school SSO, set a Piazza password first
   ("Forgot password" on the Piazza login page).
3. Fill in .env in this folder (see .env.example):
     PIAZZA_NETWORK_ID   the ID from step 1
     PIAZZA_EMAIL        your Piazza login email
     PIAZZA_PASSWORD     your Piazza password
4. pip install -r ../requirements.txt

Read-only: only feed/search endpoints are used. The library also has
create/delete/update methods — do not expose them here.
"""

import os
import re
import html

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from piazza_api import Piazza

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

NETWORK_ID = os.environ.get("PIAZZA_NETWORK_ID", "")
EMAIL = os.environ.get("PIAZZA_EMAIL", "")
PASSWORD = os.environ.get("PIAZZA_PASSWORD", "")

mcp = FastMCP("piazza")

_network = None


def _get_network():
    global _network
    if _network is None:
        if not (NETWORK_ID and EMAIL and PASSWORD):
            raise RuntimeError(
                "PIAZZA_NETWORK_ID, PIAZZA_EMAIL and PIAZZA_PASSWORD must be set in piazza_mcp/.env."
            )
        p = Piazza()
        p.user_login(email=EMAIL, password=PASSWORD)
        _network = p.network(NETWORK_ID)
    return _network


def _clean(text: str, limit: int = 200) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit] + "..."


def _format_feed_item(item: dict) -> str:
    nr = item.get("nr", "?")
    subject = _clean(item.get("subject", "(no subject)"), 120)
    when = item.get("modified") or item.get("updated") or "?"
    folders = ", ".join(item.get("folders") or [])
    flags = []
    if item.get("type") == "question" and item.get("no_answer"):
        flags.append("unanswered")
    if item.get("is_new"):
        flags.append("new")
    flag_str = f" [{', '.join(flags)}]" if flags else ""
    snippet = _clean(item.get("content_snipet") or item.get("snippet") or "")
    line = f"- @{nr}: {subject}{flag_str} (updated {when}"
    line += f"; folders: {folders})" if folders else ")"
    return line + (f"\n    {snippet}" if snippet else "")


@mcp.tool()
def get_recent_posts(limit: int = 15) -> str:
    """Get the most recently active posts in the Piazza class, newest first.

    Args:
        limit: How many posts to return (default 15, max 50).
    """
    limit = max(1, min(limit, 50))
    feed = _get_network().get_feed(limit=limit, offset=0).get("feed", [])
    if not feed:
        return "No posts found in this Piazza class."
    return "\n".join(_format_feed_item(item) for item in feed[:limit])


@mcp.tool()
def search_posts(query: str) -> str:
    """Search the Piazza class for posts matching a keyword or phrase.

    Args:
        query: Text to search for (e.g. "midterm", "assignment 2").
    """
    results = _get_network().search_feed(query)
    if not results:
        return f"No Piazza posts match '{query}'."
    return "\n".join(_format_feed_item(item) for item in results[:25])


if __name__ == "__main__":
    mcp.run()
