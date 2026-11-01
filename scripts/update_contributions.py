#!/usr/bin/env python3
"""Refresh the profile's SVG from GitHub's authenticated contribution calendar.

Uses only the Python standard library and the workflow's built-in GITHUB_TOKEN.
Any failed request or invalid response leaves the existing image untouched.
The displayed total covers exactly the days drawn, not the API's full-year total.
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from html import escape
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


API_URL = "https://api.github.com/graphql"
OUTPUT = Path(__file__).resolve().parents[1] / "assets" / "contributions.svg"
COLORS = {
    "NONE": "#1b2a27",
    "FIRST_QUARTILE": "#335448",
    "SECOND_QUARTILE": "#4c7864",
    "THIRD_QUARTILE": "#77a28c",
    "FOURTH_QUARTILE": "#bed6c7",
}
QUERY = """
query ProfileContributions($login: String!) {
  user(login: $login) {
    login
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays { date weekday contributionCount contributionLevel }
        }
      }
    }
  }
}
"""


class ContributionError(ValueError):
    """An upstream response cannot be safely used as a contribution snapshot."""


@dataclass(frozen=True)
class Day:
    date: date
    weekday: int
    count: int
    level: str


def fetch_calendar(login: str, token: str) -> dict:
    if not token:
        raise ContributionError("GH_TOKEN is missing; the existing image was preserved.")
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})", login):
        raise ContributionError("PROFILE_LOGIN is not a valid GitHub username.")
    request = Request(
        API_URL,
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Royee-profile-contributions",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            body = response.read(2_000_001)
        if len(body) > 2_000_000:
            raise ContributionError("GitHub's response was unexpectedly large.")
        return json.loads(body)
    except HTTPError as error:
        # Do not log response bodies, request headers, or token values.
        raise ContributionError(f"GitHub API returned HTTP {error.code}.") from error
    except (URLError, TimeoutError) as error:
        raise ContributionError("Could not reach the GitHub API.") from error
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ContributionError("GitHub did not return valid JSON.") from error


def parse_calendar(payload: dict, login: str) -> list[list[Day]]:
    """Reject partial/error responses instead of silently treating them as zeros."""
    if not isinstance(payload, dict) or payload.get("errors"):
        raise ContributionError("GitHub returned a GraphQL error; no data was published.")
    try:
        user = payload["data"]["user"]
        if user["login"].casefold() != login.casefold():
            raise ContributionError("The calendar belongs to a different GitHub user.")
        calendar = user["contributionsCollection"]["contributionCalendar"]
        total = calendar["totalContributions"]
        raw_weeks = calendar["weeks"]
    except (KeyError, TypeError, AttributeError) as error:
        raise ContributionError("GitHub's calendar is missing required fields.") from error
    if type(total) is not int or total < 0:
        raise ContributionError("The calendar has an invalid contribution total.")
    if not isinstance(raw_weeks, list) or not 1 <= len(raw_weeks) <= 54:
        raise ContributionError("The calendar must contain between 1 and 54 weeks.")

    weeks = []
    previous = None
    for raw_week in raw_weeks:
        days = raw_week.get("contributionDays") if isinstance(raw_week, dict) else None
        if not isinstance(days, list) or not 1 <= len(days) <= 7:
            raise ContributionError("A contribution week is empty or malformed.")
        parsed = []
        for item in days:
            try:
                day = date.fromisoformat(item["date"])
                weekday = item["weekday"]
                count = item["contributionCount"]
                level = item["contributionLevel"]
            except (KeyError, TypeError, ValueError) as error:
                raise ContributionError("A contribution day is missing valid data.") from error
            if type(weekday) is not int or weekday != (day.weekday() + 1) % 7:
                raise ContributionError("A contribution weekday does not match its date.")
            if type(count) is not int or count < 0 or not isinstance(level, str) or level not in COLORS:
                raise ContributionError("A contribution day has an invalid count or level.")
            if (count == 0) != (level == "NONE"):
                raise ContributionError("A contribution count and its intensity disagree.")
            if previous and day != previous + timedelta(days=1):
                raise ContributionError("Contribution dates are duplicated, missing, or out of order.")
            if parsed and weekday <= parsed[-1].weekday:
                raise ContributionError("Contribution days cross a week boundary.")
            parsed.append(Day(day, weekday, count, level))
            previous = day
        if weeks and parsed[0].weekday != 0:
            raise ContributionError("A contribution week does not start on Sunday.")
        weeks.append(parsed)

    if sum(day.count for week in weeks for day in week) != total:
        raise ContributionError("The calendar total disagrees with its daily counts.")
    return weeks


def render_svg(login: str, weeks: list[list[Day]], updated_at: datetime) -> str:
    """Render the latest 26 calendar columns, including a partial current week."""
    shown = weeks[-26:]
    days = [day for week in shown for day in week]
    total = sum(day.count for day in days)
    start, end = days[0].date, days[-1].date
    period = f"{start:%d %b %Y} — {end:%d %b %Y}"
    updated = updated_at.astimezone(timezone.utc).strftime("%d %b %Y · %H:%M UTC")
    description = (
        f"{login}: {total} GitHub-reported contributions from {start} to {end}. "
        "Only the displayed days are counted. Visibility follows GitHub API permissions. "
        f"Updated {updated}."
    )
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="720" height="350" viewBox="0 0 720 350" role="img" aria-labelledby="title desc">',
        f'<title id="title">{escape(login)} — GitHub Contributions</title>',
        f'<desc id="desc">{escape(description)}</desc>',
        '<rect width="720" height="350" rx="16" fill="#101c19"/>',
        '<rect x="0.5" y="0.5" width="719" height="349" rx="15.5" fill="none" stroke="#2b3d36"/>',
        '<g font-family="Arial, Helvetica, sans-serif">',
        '<text x="32" y="35" fill="#9cb3a7" font-size="13" letter-spacing="2">GITHUB CONTRIBUTIONS</text>',
        f'<text x="32" y="78" fill="#e7efeb" font-size="32" font-weight="600">{total:,} contributions</text>',
        f'<text x="32" y="105" fill="#a4b8ae" font-size="17">{escape(period)}</text>',
        f'<text x="688" y="35" text-anchor="end" fill="#a4b8ae" font-size="13">{len(shown)} WEEKS</text>',
    ]
    x_start, y_start, step, size = 112, 143, 20, 16
    for weekday, label in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        parts.append(f'<text x="76" y="{y_start + weekday * step + 12}" text-anchor="end" fill="#9cb3a7" font-size="13">{label}</text>')
    last_month = None
    last_label_column = -3
    for column, week in enumerate(shown):
        month = (week[0].date.year, week[0].date.month)
        # Three columns between labels avoids collisions across short months.
        if month != last_month and column - last_label_column >= 3 and column <= len(shown) - 3:
            parts.append(f'<text x="{x_start + column * step}" y="133" fill="#9cb3a7" font-size="12">{week[0].date:%b}</text>')
            last_label_column = column
        last_month = month
        for day in week:
            x, y = x_start + column * step, y_start + day.weekday * step
            parts.append(
                f'<rect x="{x}" y="{y}" width="{size}" height="{size}" rx="3" fill="{COLORS[day.level]}">'
                f'<title>{day.date}: {day.count} contributions</title></rect>'
            )
    parts.extend([
        f'<text x="32" y="310" fill="#a4b8ae" font-size="13">Updated {escape(updated)}</text>',
        '<text x="32" y="332" fill="#7f9a8c" font-size="12">Source: GitHub API · visibility follows account permissions</text>',
        '<text x="518" y="312" fill="#9cb3a7" font-size="12">Less</text>',
    ])
    for index, color in enumerate(COLORS.values()):
        parts.append(f'<rect x="{550 + index * 19}" y="300" width="15" height="15" rx="3" fill="{color}"/>')
    parts.extend(['<text x="652" y="312" fill="#9cb3a7" font-size="12">More</text>', '</g>', '</svg>', ''])
    return "\n".join(parts)


def update(output: Path, login: str, token: str, now: datetime | None = None) -> None:
    weeks = parse_calendar(fetch_calendar(login, token), login)
    svg = render_svg(login, weeks, now or datetime.now(timezone.utc))
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=output.parent, suffix=".svg.tmp", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(svg)
        temporary.replace(output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main() -> int:
    login = os.environ.get("PROFILE_LOGIN", "Royee-eng")
    try:
        update(OUTPUT, login, os.environ.get("GH_TOKEN", ""))
    except (ContributionError, OSError) as error:
        print(f"Contribution refresh failed: {error}", file=sys.stderr)
        return 1
    print(f"Updated {OUTPUT.name} from GitHub's calendar for {login}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
