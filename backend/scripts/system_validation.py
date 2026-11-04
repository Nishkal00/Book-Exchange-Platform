"""End-to-end system validation of the running application (writes a Markdown report).

Usage (from the backend folder):
    python scripts/system_validation.py --base-url http://localhost:8000 --email-domain example.com
    python scripts/system_validation.py --base-url https://bep-backend.onrender.com \\
        --email-domain <an allowed college domain>

It creates fresh throw-away users and one test listing through the public API, walks the core
borrowing flow and checks each requirement from the Test Plan, then writes
docs/system-validation-report.md. Use test environments only; the data it creates stays in the
database.
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path

DOCS = Path(__file__).resolve().parents[2] / "docs"


class Client:
    def __init__(self, base: str) -> None:
        self.base = base.rstrip("/")

    def call(self, method: str, path: str, body=None, token: str | None = None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(
            self.base + path, data=data, method=method, headers=headers
        )
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                raw = response.read()
                return response.status, (json.loads(raw) if raw else None)
        except urllib.error.HTTPError as error:
            raw = error.read()
            try:
                return error.code, (json.loads(raw) if raw else None)
            except ValueError:
                return error.code, None


class Report:
    def __init__(self) -> None:
        self.rows: list[tuple[str, str, str, str, str, bool]] = []

    def check(self, step, requirement, test_case, expected, actual, ok) -> bool:
        self.rows.append((step, requirement, test_case, expected, str(actual), bool(ok)))
        print(("PASS " if ok else "FAIL ") + step + f" -> {actual}")
        return bool(ok)


def run(base: str, domain: str) -> Report:
    api = Client(base)
    rep = Report()
    stamp = str(int(time.time()))

    status, body = api.call("GET", "/health")
    rep.check(
        "Health endpoint responds",
        "NF-002",
        "TC-OPS-01",
        "200 ok",
        status,
        status == 200 and body == {"status": "ok"},
    )

    def new_user(label: str):
        email = f"{label}{stamp}@{domain}"
        status, _ = api.call(
            "POST",
            "/api/v1/auth/register",
            {"email": email, "password": "Passw0rd!x", "name": label.title()},
        )
        return email, status

    lender_email, s1 = new_user("lender")
    borrower_email, s2 = new_user("borrower")
    outsider_email, s3 = new_user("outsider")
    rep.check(
        "Register three users",
        "F-001",
        "TC-AUTH-01",
        "201 each",
        f"{s1},{s2},{s3}",
        (s1, s2, s3) == (201, 201, 201),
    )

    tokens = {}
    for label, email in (
        ("lender", lender_email),
        ("borrower", borrower_email),
        ("outsider", outsider_email),
    ):
        status, body = api.call(
            "POST", "/api/v1/auth/login", {"email": email, "password": "Passw0rd!x"}
        )
        tokens[label] = body.get("access_token") if body else None
        if label == "lender":
            rep.check(
                "Login returns a token",
                "F-002",
                "TC-AUTH-03",
                "200 + token",
                status,
                status == 200 and bool(tokens[label]),
            )
    L, B, X = tokens["lender"], tokens["borrower"], tokens["outsider"]

    status, _ = api.call(
        "POST", "/api/v1/auth/login", {"email": lender_email, "password": "wrong-password"}
    )
    rep.check(
        "Wrong password is rejected", "F-002 / SR-006", "TC-AUTH-04", "401", status, status == 401
    )

    for token in (L, B, X):
        api.call("PATCH", "/api/v1/auth/me", {"location": "Campus"}, token)
    status, body = api.call("GET", "/api/v1/auth/me", token=B)
    rep.check(
        "View profile",
        "F-004",
        "TC-PRF-01",
        "200 + email",
        status,
        status == 200 and body.get("email") == borrower_email,
    )

    isbn = "97802" + stamp[-8:]
    title = f"Validation Book {stamp}"
    status, listing = api.call(
        "POST",
        "/api/v1/listings",
        {
            "title": title,
            "author": "Test Author",
            "isbn": isbn,
            "condition": "GOOD",
            "location": "Campus",
        },
        L,
    )
    rep.check("Create listing", "F-010", "TC-LST-01", "201", status, status == 201)

    status, found = api.call("GET", f"/api/v1/listings?q={title.replace(' ', '%20')}", token=B)
    items = found.get("items", []) if isinstance(found, dict) else (found or [])
    rep.check(
        "Search finds the listing",
        "F-011",
        "TC-LST-03",
        "listing in results",
        len(items),
        any(i.get("isbn") == isbn for i in items),
    )

    status, request = api.call("POST", "/api/v1/requests", {"isbn": isbn, "location": "Campus"}, B)
    rep.check(
        "Create borrow request",
        "F-020",
        "TC-REQ-01",
        "201 OPEN",
        status,
        status == 201 and request.get("status") == "OPEN",
    )

    status, matches = api.call("GET", f"/api/v1/requests/{request['id']}/matches", token=B)
    rep.check(
        "Matching engine proposes the listing",
        "F-022",
        "TC-MAT-01",
        "1 ranked match",
        len(matches or []),
        status == 200 and len(matches or []) == 1,
    )
    match_id = matches[0]["match_id"]

    status, lender_notes = api.call("GET", "/api/v1/notifications", token=L)
    kinds = {n["event_type"] for n in (lender_notes or {}).get("items", [])}
    rep.check(
        "Lender receives a match notification",
        "F-023",
        "TC-NOT-01",
        "MATCH_FOUND",
        sorted(kinds),
        "MATCH_FOUND" in kinds,
    )

    status, my_matches = api.call("GET", "/api/v1/matches", token=L)
    leaked = {"email", "phone"} & set((my_matches or [{}])[0])
    rep.check(
        "Match list shows no contact details",
        "SR-007",
        "TC-SEC-07",
        "no email/phone fields",
        sorted(leaked) or "none",
        status == 200 and not leaked,
    )

    status, _ = api.call("POST", f"/api/v1/matches/{match_id}/decision", {"decision": "accept"}, X)
    rep.check("Outsider cannot decide a match", "SR-005", "TC-SEC-05", "403", status, status == 403)

    api.call("POST", f"/api/v1/matches/{match_id}/decision", {"decision": "accept"}, B)
    status, decision = api.call(
        "POST", f"/api/v1/matches/{match_id}/decision", {"decision": "accept"}, L
    )
    exchange_id = (decision or {}).get("exchangeId")
    rep.check(
        "Mutual acceptance creates an exchange",
        "F-024",
        "TC-MAT-04",
        "exchangeId set",
        exchange_id,
        status == 200 and bool(exchange_id),
    )
    base_ex = f"/api/v1/exchanges/{exchange_id}"

    status, _ = api.call("GET", base_ex + "/contact", token=X)
    rep.check(
        "Outsider cannot read partner contact",
        "SR-007",
        "TC-SEC-07",
        "403 or 404",
        status,
        status in (403, 404),
    )
    status, contact = api.call("GET", base_ex + "/contact", token=B)
    rep.check(
        "Participant can read partner contact after acceptance",
        "SR-007",
        "TC-SEC-07",
        "200 + email",
        status,
        status == 200 and "email" in (contact or {}),
    )

    status, _ = api.call("POST", base_ex + "/handover", token=L)
    rep.check("Handover needs a due date", "F-025", "TC-EXC-01", "409", status, status == 409)
    past = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    status, _ = api.call("PUT", base_ex + "/due-date", {"due_at": past}, B)
    rep.check("Past due date is rejected", "F-025", "TC-EXC-01", "422", status, status == 422)
    future = (datetime.now(UTC) + timedelta(days=7)).isoformat()
    status, _ = api.call("PUT", base_ex + "/due-date", {"due_at": future}, B)
    rep.check(
        "Agreed future due date is recorded", "F-025", "TC-EXC-01", "200", status, status == 200
    )
    status, _ = api.call("POST", base_ex + "/handover", token=B)
    rep.check(
        "Only the lender can confirm handover", "F-025", "TC-EXC-01", "403", status, status == 403
    )
    status, body = api.call("POST", base_ex + "/handover", token=L)
    rep.check(
        "Lender confirms handover",
        "F-025",
        "TC-EXC-01",
        "ON_LOAN",
        (body or {}).get("state"),
        status == 200 and body.get("state") == "ON_LOAN",
    )
    status, _ = api.call("POST", base_ex + "/cancel", token=B)
    rep.check(
        "Cancel after handover is rejected", "F-025", "TC-EXC-01", "409", status, status == 409
    )

    status, body = api.call("POST", base_ex + "/return", token=B)
    rep.check(
        "First return confirmation keeps ON_LOAN",
        "F-026",
        "TC-EXC-02",
        "ON_LOAN",
        (body or {}).get("state"),
        status == 200 and body.get("state") == "ON_LOAN",
    )
    status, body = api.call("POST", base_ex + "/return", token=B)
    events = [e["event_type"] for e in (body or {}).get("events", [])]
    rep.check(
        "Repeated confirmation is idempotent",
        "F-026",
        "TC-EXC-02",
        "one RETURN_CONFIRMED",
        events.count("RETURN_CONFIRMED"),
        status == 200 and events.count("RETURN_CONFIRMED") == 1,
    )
    status, body = api.call("POST", base_ex + "/return", token=L)
    rep.check(
        "Second confirmation completes the return",
        "F-026",
        "TC-EXC-02",
        "RETURNED",
        (body or {}).get("state"),
        status == 200 and body.get("state") == "RETURNED",
    )
    status, mine = api.call("GET", "/api/v1/listings/mine", token=L)
    mine_items = mine.get("items", []) if isinstance(mine, dict) else (mine or [])
    rep.check(
        "Listing is available again",
        "F-026",
        "TC-EXC-02",
        "AVAILABLE",
        [i["status"] for i in mine_items if i.get("isbn") == isbn],
        any(i.get("isbn") == isbn and i.get("status") == "AVAILABLE" for i in mine_items),
    )

    status, hist_b = api.call("GET", "/api/v1/exchanges", token=B)
    status_o, hist_o = api.call("GET", "/api/v1/exchanges", token=X)
    ids_b = [e["id"] for e in (hist_b or {}).get("items", [])] if isinstance(hist_b, dict) else []
    ids_o = [e["id"] for e in (hist_o or {}).get("items", [])] if isinstance(hist_o, dict) else []
    rep.check(
        "History shows the exchange only to participants",
        "F-030",
        "TC-HIS-01",
        "borrower yes, outsider no",
        f"borrower={exchange_id in ids_b}, outsider={exchange_id in ids_o}",
        exchange_id in ids_b and exchange_id not in ids_o,
    )

    status, _ = api.call("GET", base_ex)
    rep.check(
        "Anonymous access is refused",
        "SR-002 / SR-005",
        "TC-SEC-02",
        "401 or 403",
        status,
        status in (401, 403),
    )

    status, _ = api.call("POST", "/api/v1/auth/logout", token=B)
    status_after, _ = api.call("GET", "/api/v1/auth/me", token=B)
    rep.check(
        "Logout revokes the token",
        "F-003 / SR-002",
        "TC-AUTH-05",
        "204 then 401",
        f"{status} then {status_after}",
        status == 204 and status_after == 401,
    )
    return rep


def write_report(rep: Report, base: str, path: Path) -> None:
    passed = sum(1 for r in rep.rows if r[5])
    lines = [
        "# System Validation Report",
        "",
        "| Item | Value |",
        "| :--- | :--- |",
        f"| Date | {datetime.now().strftime('%d %b %Y %H:%M')} |",
        f"| Target | `{base}` |",
        "| Method | `python backend/scripts/system_validation.py` (public API only, fresh users) |",
        f"| Result | **{passed} of {len(rep.rows)} checks passed** |",
        "",
        "## Checks",
        "",
        "| # | Step | Requirement | Test case | Expected | Actual | Result |",
        "| ---: | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]
    for i, (step, req, tc, expected, actual, ok) in enumerate(rep.rows, 1):
        lines.append(
            f"| {i} | {step} | {req} | {tc} | {expected} | {actual} | "
            f"{'PASS' if ok else '**FAIL**'} |"
        )
    lines += [
        "",
        "## Not covered by this run",
        "",
        "Features not part of the scripted flow (ratings F-031, admin moderation F-040, response",
        "time targets NF-001/NF-005, uptime NF-002, usability NF-003) are verified by their own",
        "reports and tests; see the RTM.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--email-domain", default="example.com")
    parser.add_argument("--out", default=str(DOCS / "system-validation-report.md"))
    args = parser.parse_args()
    report = run(args.base_url, args.email_domain)
    DOCS.mkdir(exist_ok=True)
    write_report(report, args.base_url, Path(args.out))
    failed = [r for r in report.rows if not r[5]]
    print(f"\n{len(report.rows) - len(failed)}/{len(report.rows)} passed -> {args.out}")
    raise SystemExit(1 if failed else 0)
