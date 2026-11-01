"""Source integrity and failure behavior for the live contribution snapshot."""

import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import update_contributions as contributions


def response_fixture(week_count=2):
    """Explicitly synthetic test data; never copied into the published image."""
    start = date(2026, 1, 4)  # Sunday
    weeks = []
    for week in range(week_count):
        days = []
        for weekday in range(7):
            count = 3 if weekday == 1 else 0
            days.append({
                "date": (start + timedelta(days=7 * week + weekday)).isoformat(),
                "weekday": weekday,
                "contributionCount": count,
                "contributionLevel": "SECOND_QUARTILE" if count else "NONE",
            })
        weeks.append({"contributionDays": days})
    return {"data": {"user": {
        "login": "Royee-eng",
        "contributionsCollection": {"contributionCalendar": {
            "totalContributions": week_count * 3, "weeks": weeks,
        }},
    }}}


def calendar_of(payload):
    return payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]


class ContributionsTests(unittest.TestCase):
    def test_graphql_errors_cannot_publish_partial_data(self):
        payload = response_fixture()
        payload["errors"] = [{"message": "Resource not accessible"}]
        with self.assertRaises(contributions.ContributionError):
            contributions.parse_calendar(payload, "Royee-eng")

    def test_missing_data_is_not_a_zero_calendar(self):
        for payload in ({}, {"data": {"user": None}}, {"data": {"user": {"login": "Royee-eng"}}}):
            with self.subTest(payload=payload), self.assertRaises(contributions.ContributionError):
                contributions.parse_calendar(payload, "Royee-eng")

    def test_wrong_identity_and_wrong_total_are_rejected(self):
        payload = response_fixture()
        with self.assertRaises(contributions.ContributionError):
            contributions.parse_calendar(payload, "someone-else")
        calendar_of(payload)["totalContributions"] = 999
        with self.assertRaises(contributions.ContributionError):
            contributions.parse_calendar(payload, "Royee-eng")

    def test_missing_duplicate_and_invalid_day_fields_are_rejected(self):
        for field, value in (("contributionCount", -1), ("contributionCount", True),
                             ("contributionLevel", "FIRST_QUARTILE"), ("weekday", 4),
                             ("date", "2026-01-05")):
            payload = response_fixture()
            calendar_of(payload)["weeks"][0]["contributionDays"][0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(contributions.ContributionError):
                contributions.parse_calendar(payload, "Royee-eng")
        payload = response_fixture()
        del calendar_of(payload)["weeks"][0]["contributionDays"][2]["contributionCount"]
        with self.assertRaises(contributions.ContributionError):
            contributions.parse_calendar(payload, "Royee-eng")

    def test_gap_and_empty_weeks_are_rejected(self):
        for kind in ("gap", "empty"):
            payload = response_fixture()
            days = calendar_of(payload)["weeks"][0]["contributionDays"]
            if kind == "gap":
                days.pop(2)
            else:
                days.clear()
            with self.subTest(kind=kind), self.assertRaises(contributions.ContributionError):
                contributions.parse_calendar(payload, "Royee-eng")

    def test_26_week_render_counts_only_the_displayed_real_days(self):
        weeks = contributions.parse_calendar(response_fixture(28), "Royee-eng")
        svg = contributions.render_svg("Royee-eng", weeks, datetime(2026, 7, 20, tzinfo=timezone.utc))
        root = ET.fromstring(svg)
        cells = [element for element in root.iter("{http://www.w3.org/2000/svg}rect")
                 if element.find("{http://www.w3.org/2000/svg}title") is not None]
        self.assertEqual(len(cells), 26 * 7)
        self.assertIn("78 contributions", svg)
        self.assertNotIn("84 contributions", svg)
        self.assertIn("2026-01-18: 0 contributions", svg)
        self.assertNotIn("2026-01-04:", svg)
        self.assertIn("20 Jul 2026 · 00:00 UTC", svg)

    def test_partial_final_week_does_not_invent_future_cells(self):
        payload = response_fixture()
        calendar_of(payload)["weeks"][-1]["contributionDays"] = calendar_of(payload)["weeks"][-1]["contributionDays"][:3]
        weeks = contributions.parse_calendar(payload, "Royee-eng")
        svg = contributions.render_svg("Royee-eng", weeks, datetime.now(timezone.utc))
        self.assertIn("2026-01-13: 0 contributions", svg)
        self.assertNotIn("2026-01-14:", svg)

    def test_valid_zero_calendar_remains_distinct_from_missing_data(self):
        payload = response_fixture()
        calendar_of(payload)["totalContributions"] = 0
        for week in calendar_of(payload)["weeks"]:
            for day in week["contributionDays"]:
                day["contributionCount"] = 0
                day["contributionLevel"] = "NONE"
        weeks = contributions.parse_calendar(payload, "Royee-eng")
        self.assertEqual(sum(day.count for week in weeks for day in week), 0)

    def test_api_failure_and_invalid_payload_preserve_previous_file(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "contributions.svg"
            output.write_text("previous-valid-image")
            with patch.object(contributions, "fetch_calendar", side_effect=contributions.ContributionError("API failed")):
                with self.assertRaises(contributions.ContributionError):
                    contributions.update(output, "Royee-eng", "test-token")
            self.assertEqual(output.read_text(), "previous-valid-image")
            with patch.object(contributions, "fetch_calendar", return_value={"errors": [{}]}):
                with self.assertRaises(contributions.ContributionError):
                    contributions.update(output, "Royee-eng", "test-token")
            self.assertEqual(output.read_text(), "previous-valid-image")
            self.assertEqual(list(output.parent.iterdir()), [output])

    def test_success_replaces_file_with_valid_svg(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "contributions.svg"
            output.write_text("previous-valid-image")
            with patch.object(contributions, "fetch_calendar", return_value=response_fixture()):
                contributions.update(output, "Royee-eng", "test-token")
            ET.fromstring(output.read_text())
            self.assertIn("6 contributions", output.read_text())
            self.assertEqual(list(output.parent.iterdir()), [output])

    def test_missing_token_fails_without_a_request(self):
        with patch.object(contributions, "urlopen") as request:
            with self.assertRaises(contributions.ContributionError):
                contributions.fetch_calendar("Royee-eng", "")
            request.assert_not_called()

    def test_http_errors_do_not_expose_token(self):
        error = HTTPError(contributions.API_URL, 403, "Forbidden", {}, None)
        with patch.object(contributions, "urlopen", side_effect=error):
            with self.assertRaises(contributions.ContributionError) as caught:
                contributions.fetch_calendar("Royee-eng", "never-log-this-token")
        self.assertIn("403", str(caught.exception))
        self.assertNotIn("never-log-this-token", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
