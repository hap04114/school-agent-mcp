"""
Canvas MCP server.

Exposes your Canvas LMS data (courses, assignments, grades, to-do list) as
tools that Claude can call directly.

Setup:
1. In Canvas: Account -> Settings -> New Access Token. Copy it.
2. Set two environment variables (see .env.example in this folder):
     CANVAS_BASE_URL   e.g. https://yourschool.instructure.com
     CANVAS_TOKEN      the access token you generated
3. pip install -r ../requirements.txt
4. Point Claude Desktop's config at this file (see README.md).
"""

import os
import requests
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

CANVAS_BASE_URL = os.environ.get("CANVAS_BASE_URL", "").rstrip("/")
CANVAS_TOKEN = os.environ.get("CANVAS_TOKEN", "")

mcp = FastMCP("canvas")


def _headers():
    if not CANVAS_TOKEN or not CANVAS_BASE_URL:
        raise RuntimeError(
            "CANVAS_BASE_URL and CANVAS_TOKEN must be set as environment variables."
        )
    return {"Authorization": f"Bearer {CANVAS_TOKEN}"}


def _get(path: str, params: dict | None = None):
    resp = requests.get(f"{CANVAS_BASE_URL}{path}", headers=_headers(), params=params, timeout=20)
    resp.raise_for_status()
    return resp.json()


@mcp.tool()
def list_courses() -> str:
    """List the user's active Canvas courses with their course IDs and names."""
    courses = _get("/api/v1/courses", params={"enrollment_state": "active", "per_page": 100})
    if not courses:
        return "No active courses found."
    lines = [f"- {c.get('id')}: {c.get('name', 'Unnamed course')}" for c in courses]
    return "\n".join(lines)


@mcp.tool()
def get_todo_list() -> str:
    """Get the user's Canvas to-do list (upcoming assignments needing grading/submission)."""
    items = _get("/api/v1/users/self/todo", params={"per_page": 50})
    if not items:
        return "Nothing on the Canvas to-do list right now."
    lines = []
    for item in items:
        assignment = item.get("assignment", {})
        name = assignment.get("name", "Untitled item")
        due = assignment.get("due_at", "no due date")
        course_id = item.get("course_id", "?")
        lines.append(f"- [{course_id}] {name} (due: {due})")
    return "\n".join(lines)


@mcp.tool()
def get_assignments(course_id: int, only_upcoming: bool = True) -> str:
    """Get assignments for a specific course.

    Args:
        course_id: The Canvas course ID (get this from list_courses).
        only_upcoming: If true, only include assignments not yet due.
    """
    assignments = _get(
        f"/api/v1/courses/{course_id}/assignments",
        params={"per_page": 100, "order_by": "due_at"},
    )
    if not assignments:
        return f"No assignments found for course {course_id}."

    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    lines = []
    for a in assignments:
        due_at = a.get("due_at")
        if only_upcoming and due_at:
            due_dt = datetime.fromisoformat(due_at.replace("Z", "+00:00"))
            if due_dt < now:
                continue
        lines.append(f"- {a.get('name')} (due: {due_at or 'no due date'}, points: {a.get('points_possible')})")

    return "\n".join(lines) if lines else f"No upcoming assignments for course {course_id}."


@mcp.tool()
def get_grades(course_id: int) -> str:
    """Get the user's current grade/score summary for a specific course."""
    enrollments = _get(
        "/api/v1/users/self/enrollments",
        params={"state[]": "active", "type[]": "StudentEnrollment"},
    )
    for e in enrollments:
        if e.get("course_id") == course_id:
            grades = e.get("grades", {})
            current_score = grades.get("current_score")
            current_grade = grades.get("current_grade")
            return f"Course {course_id}: score={current_score}, grade={current_grade}"
    return f"No grade data found for course {course_id}."


if __name__ == "__main__":
    mcp.run()
