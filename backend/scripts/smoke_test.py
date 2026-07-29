"""End-to-end check of a running StudyPilot API, local or deployed.

    python -m scripts.smoke_test                                  # localhost
    python -m scripts.smoke_test --base-url https://api.example.com
    python -m scripts.smoke_test --base-url ... --keep            # keep the account

Registers a throwaway account, walks the whole product path - onboarding,
subjects, a syllabus PDF upload, plan generation, sessions, revision, a past
paper upload and scoring, analytics - then deletes the account again. Only the
standard library is used, so it runs anywhere Python does.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import secrets
import sys
import urllib.error
import urllib.request
import uuid
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_BASE = "http://127.0.0.1:8000"
TIMEOUT = 120


class Result:
    def __init__(self) -> None:
        self.rows: List[Tuple[bool, str, str]] = []

    def record(self, ok: bool, name: str, detail: str = "") -> bool:
        self.rows.append((ok, name, detail))
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {name}" + (f" - {detail}" if detail else ""))
        return ok

    @property
    def failures(self) -> List[Tuple[bool, str, str]]:
        return [row for row in self.rows if not row[0]]


def _decode(raw: bytes, headers) -> Any:
    """JSON when the response says so, otherwise a description of the bytes.

    Endpoints that serve uploaded files hand back a PDF, so the client cannot
    assume every body is JSON.
    """
    if not raw:
        return None
    content_type = (headers.get("Content-Type") or "").split(";")[0].strip().lower()
    if content_type in ("application/json", "application/problem+json"):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
    if content_type.startswith(("application/pdf", "image/", "application/octet")):
        return {"content_type": content_type, "bytes": len(raw)}
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {"content_type": content_type, "bytes": len(raw),
                "preview": raw[:200].decode(errors="replace")}


class Client:
    def __init__(self, base_url: str) -> None:
        self.base = base_url.rstrip("/")
        self.api = f"{self.base}/api/v1"
        self.token: Optional[str] = None

    def request(
        self,
        method: str,
        path: str,
        body: Any = None,
        *,
        multipart: Optional[Tuple[str, str, bytes]] = None,
        absolute: bool = False,
    ) -> Tuple[int, Any]:
        url = path if absolute else f"{self.api}{path}"
        headers = {"Accept": "application/json"}
        data: Optional[bytes] = None

        if multipart is not None:
            field, filename, payload = multipart
            boundary = f"----StudyPilot{secrets.token_hex(12)}"
            content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
            data = (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{field}"; filename="{filename}"\r\n'
                f"Content-Type: {content_type}\r\n\r\n"
            ).encode() + payload + f"\r\n--{boundary}--\r\n".encode()
            headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
        elif body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"

        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                return response.status, _decode(response.read(), response.headers)
        except urllib.error.HTTPError as error:
            return error.code, _decode(error.read(), error.headers)
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            return 0, {"error": str(error)}

    def get(self, path, **kw):
        return self.request("GET", path, **kw)

    def post(self, path, body=None, **kw):
        return self.request("POST", path, body, **kw)

    def patch(self, path, body=None):
        return self.request("PATCH", path, body)

    def delete(self, path):
        return self.request("DELETE", path)


def _tiny_pdf(lines: List[str], header: str = "Specification") -> bytes:
    """A minimal one-page PDF with a real text layer."""
    stream_parts = ["BT", "/F1 9 Tf", "12 TL", "1 0 0 1 40 780 Tm", f"({header}) Tj", "T*"]
    for line in lines:
        escaped = line.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
        stream_parts += [f"({escaped}) Tj", "T*"]
    stream_parts.append("ET")
    stream = "\n".join(stream_parts)
    encoded = stream.encode("latin-1", "replace")

    objects = [
        (1, "<< /Type /Catalog /Pages 2 0 R >>"),
        (2, "<< /Type /Pages /Count 1 /Kids [5 0 R] >>"),
        (3, "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"),
        (4, f"<< /Length {len(encoded)} >>\nstream\n{stream}\nendstream"),
        (
            5,
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            "/Resources << /Font << /F1 3 0 R >> >> /Contents 4 0 R >>",
        ),
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets: Dict[int, int] = {}
    for number, body in objects:
        offsets[number] = len(out)
        out += f"{number} 0 obj\n{body}\nendobj\n".encode("latin-1", "replace")
    xref_at = len(out)
    count = max(offsets) + 1
    out += f"xref\n0 {count}\n".encode() + b"0000000000 65535 f \n"
    for number in range(1, count):
        out += f"{offsets.get(number, 0):010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {count} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n".encode()
    return bytes(out)


SYLLABUS_PDF = _tiny_pdf(
    [
        "Unit 1: Pure Mathematics",
        "1.1 Algebraic expressions",
        "a be able to simplify surds and rationalise denominators",
        "b understand and use the laws of indices",
        "c be able to expand and factorise quadratic expressions",
        "1.2 Quadratic functions",
        "a be able to complete the square and sketch the resulting curve",
        "b understand the discriminant and what it says about the roots",
        "Unit 2: Statistics",
        "2.1 Data presentation",
        "a be able to interpret histograms and cumulative frequency graphs",
        "b understand measures of location and spread",
    ],
    header="Pearson Edexcel International Advanced Level Mathematics",
)

PAPER_PDF = _tiny_pdf(
    [
        "Mathematics",
        "Pure Mathematics P1",
        "Paper 1",
        "Tuesday 12 January 2021",
        "Morning (Time: 1 hour 30 minutes)",
        "Information",
        "The total mark for this paper is 75.",
        "1. Solve the equation 3x - 7 = 11.",
    ],
    header="Pearson Edexcel International Advanced Level",
)


def run(base_url: str, keep: bool) -> int:
    client = Client(base_url)
    result = Result()
    email = f"smoke-{uuid.uuid4().hex[:10]}@example.com"
    password = "SmokeTest!2026"

    print(f"\nStudyPilot smoke test -> {client.base}\n")

    # --- Service reachability ---------------------------------------------
    print("service")
    status, body = client.request("GET", f"{client.base}/health", absolute=True)
    result.record(status == 200, "GET /health", f"status={status}")
    if isinstance(body, dict):
        result.record(
            body.get("database") == "ok",
            "database reachable from the API",
            f"engine={body.get('engine')} database={body.get('database')}",
        )
    status, _ = client.request("GET", f"{client.base}/openapi.json", absolute=True)
    result.record(status == 200, "GET /openapi.json", f"status={status}")

    # --- Public catalogue -------------------------------------------------
    print("\ncatalogue (unauthenticated)")
    status, body = client.get("/catalog")
    result.record(status == 200 and bool(body), "GET /catalog", f"status={status}")
    status, body = client.get("/catalog/subjects?curriculum=a_level")
    result.record(
        status == 200 and bool(body),
        "GET /catalog/subjects",
        f"{len(body) if isinstance(body, list) else '?'} subjects",
    )

    # --- Auth --------------------------------------------------------------
    print("\nauthentication")
    status, body = client.post(
        "/auth/register",
        {"name": "Smoke Test", "email": email, "password": password,
         "confirm_password": password},
    )
    registered = result.record(status in (200, 201), "POST /auth/register", f"status={status}")
    if not registered:
        print(f"\n  cannot continue: {json.dumps(body)[:300]}")
        return 1

    status, body = client.post("/auth/login", {"email": email, "password": password})
    result.record(status == 200 and "access_token" in (body or {}), "POST /auth/login",
                  f"status={status}")
    client.token = (body or {}).get("access_token")

    status, body = client.get("/auth/me")
    result.record(status == 200 and body.get("email") == email, "GET /auth/me (bearer token)",
                  f"status={status}")

    saved, client.token = client.token, "not-a-real-token"
    status, _ = client.get("/auth/me")
    result.record(status == 401, "rejects an invalid token", f"status={status}")
    client.token = saved

    saved, client.token = client.token, None
    status, _ = client.get("/subjects")
    result.record(status == 401, "rejects an anonymous request", f"status={status}")
    client.token = saved

    # --- Onboarding --------------------------------------------------------
    print("\nonboarding")
    status, body = client.get("/onboarding/questions")
    result.record(status == 200, "GET /onboarding/questions", f"status={status}")
    status, body = client.post(
        "/onboarding/complete",
        {
            "name": "Smoke Test",
            "year_group": "Year 13",
            "curriculum": "international_a_level",
            "subjects": ["Mathematics", "Physics"],
            "preparing_admission_exams": False,
            "admission_exams": [],
            "universities": [],
            "target_degree": "Computer Science",
            "exams": [
                {
                    "subject": "Mathematics",
                    "exam_board": "Edexcel",
                    "exam_date": (date.today() + timedelta(days=90)).isoformat(),
                    "exam_time": "09:00",
                    "paper": "Paper 1",
                }
            ],
            "weekday_hours": 3,
            "weekend_hours": 5,
            "preferred_study_time": "evening",
            "study_habits": ["focus"],
        },
    )
    result.record(status in (200, 201), "POST /onboarding/complete",
                  f"subjects={(body or {}).get('subjects_created')}")

    # --- Subjects & syllabus upload ---------------------------------------
    print("\nsubjects and syllabus PDF parsing")
    status, subjects = client.get("/subjects")
    ok = status == 200 and isinstance(subjects, list) and subjects
    result.record(ok, "GET /subjects", f"{len(subjects) if ok else 0} subjects")
    if not ok:
        return 1
    subject_id = subjects[0]["id"]

    status, detail = client.post(
        f"/subjects/{subject_id}/syllabus-pdf",
        multipart=("file", "specification.pdf", SYLLABUS_PDF),
    )
    units = (detail or {}).get("units") or []
    topics = sum(len(u.get("topics", [])) for u in units)
    with_points = sum(
        1 for u in units for t in u.get("topics", []) if (t.get("notes") or "").strip()
    )
    result.record(status in (200, 201) and topics > 0, "POST /subjects/{id}/syllabus-pdf",
                  f"{len(units)} units, {topics} topics, {with_points} with key points")
    result.record(with_points > 0, "key points extracted from the specification",
                  f"{with_points}/{topics} topics")

    if (detail or {}).get("syllabus_pdf_url"):
        status, _ = client.request(
            "GET", f"{client.base}{detail['syllabus_pdf_url']}", absolute=True
        )
        result.record(status == 200, "uploaded syllabus PDF is served back",
                      f"status={status}")

    status, body = client.get(f"/subjects/{subject_id}/topics")
    result.record(status == 200 and bool(body), "GET /subjects/{id}/topics",
                  f"{len(body) if isinstance(body, list) else 0} topics")

    # --- Plan generation ---------------------------------------------------
    print("\nstudy planner")
    status, plan = client.post("/plans/generate", {})
    sessions = (plan or {}).get("sessions") or []
    result.record(status in (200, 201) and bool(sessions), "POST /plans/generate",
                  f"{len(sessions)} sessions, {(plan or {}).get('total_hours')}h")

    status, today = client.get("/plans/today")
    result.record(status == 200, "GET /plans/today",
                  f"{len(today) if isinstance(today, list) else 0} sessions")
    status, week = client.get("/plans/week")
    result.record(status == 200 and "days" in (week or {}), "GET /plans/week",
                  f"status={status}")
    status, _ = client.get("/plans/month")
    result.record(status == 200, "GET /plans/month", f"status={status}")
    status, _ = client.get("/plans/active")
    result.record(status == 200, "GET /plans/active", f"status={status}")

    status, created = client.post(
        "/plans/sessions",
        {"title": "Smoke test session", "session_date": date.today().isoformat(),
         "start_time": "18:00", "duration_minutes": 45, "kind": "study"},
    )
    made = result.record(status in (200, 201), "POST /plans/sessions", f"status={status}")
    if made:
        session_id = created["id"]
        status, _ = client.post(f"/plans/sessions/{session_id}/complete", {})
        result.record(status == 200, "POST /plans/sessions/{id}/complete", f"status={status}")
        status, _ = client.post(f"/plans/sessions/{session_id}/reset")
        result.record(status == 200, "POST /plans/sessions/{id}/reset", f"status={status}")
        status, _ = client.delete(f"/plans/sessions/{session_id}")
        result.record(status == 200, "DELETE /plans/sessions/{id}", f"status={status}")

    # --- Topic completion drives revision ---------------------------------
    print("\ntopics, revision and achievements")
    status, topic_list = client.get(f"/subjects/{subject_id}/topics")
    if status == 200 and topic_list:
        topic_id = topic_list[0]["id"]
        status, _ = client.post(
            f"/subjects/topics/{topic_id}/complete",
            {"confidence": 4, "minutes_spent": 30, "schedule_revision": True},
        )
        result.record(status == 200, "POST /subjects/topics/{id}/complete", f"status={status}")
        status, revisions = client.get("/revision")
        result.record(
            status == 200 and bool(revisions),
            "spaced repetition booked after completion",
            f"{len(revisions) if isinstance(revisions, list) else 0} entries",
        )
        status, _ = client.get("/revision/stats")
        result.record(status == 200, "GET /revision/stats", f"status={status}")

    status, achievements = client.get("/achievements")
    result.record(status == 200 and "achievements" in (achievements or {}),
                  "GET /achievements",
                  f"xp={(achievements or {}).get('xp')}")

    # --- Past papers -------------------------------------------------------
    print("\npast papers (upload, auto-metadata, scoring)")
    status, paper = client.post(
        "/past-papers/upload", multipart=("file", "WMA11_01_que_20210112.pdf", PAPER_PDF)
    )
    uploaded = result.record(
        status in (200, 201),
        "POST /past-papers/upload",
        f"detected: {(paper or {}).get('exam_board')} / "
        f"{(paper or {}).get('paper')} / {(paper or {}).get('year')} / "
        f"total={(paper or {}).get('marks_total')}",
    )
    if uploaded:
        result.record((paper or {}).get("scored") is False,
                      "uploaded paper starts unscored", f"scored={paper.get('scored')}")
        if paper.get("file_url"):
            status, _ = client.request(
                "GET", f"{client.base}{paper['file_url']}", absolute=True
            )
            result.record(status == 200, "uploaded paper PDF is served back",
                          f"status={status}")
        status, scored = client.post(
            f"/past-papers/{paper['id']}/score",
            {"marks_scored": 61, "marks_total": paper.get("marks_total") or 75,
             "time_taken_minutes": 90},
        )
        result.record(
            status == 200 and (scored or {}).get("scored") is True,
            "POST /past-papers/{id}/score",
            f"{(scored or {}).get('percentage')}% grade {(scored or {}).get('grade')}",
        )
        status, stats = client.get("/past-papers/stats")
        result.record(status == 200 and (stats or {}).get("total_papers", 0) >= 1,
                      "GET /past-papers/stats",
                      f"avg={(stats or {}).get('average_percentage')}%")

    # --- Remaining read surfaces ------------------------------------------
    print("\ndashboard, analytics and the rest")
    for label, path in (
        ("GET /dashboard", "/dashboard"),
        ("GET /analytics", "/analytics"),
        ("GET /exams", "/exams"),
        ("GET /exams/countdown", "/exams/countdown"),
        ("GET /notifications", "/notifications"),
        ("GET /activity", "/activity"),
        ("GET /users/me/settings", "/users/me/settings"),
        ("GET /onboarding/summary", "/onboarding/summary"),
    ):
        status, _ = client.get(path)
        result.record(status == 200, label, f"status={status}")

    status, _ = client.patch("/users/me", {"year_group": "Year 12"})
    result.record(status == 200, "PATCH /users/me", f"status={status}")
    status, _ = client.patch("/users/me/settings", {"study_reminders": False})
    result.record(status == 200, "PATCH /users/me/settings", f"status={status}")

    # --- Clean up ----------------------------------------------------------
    if not keep:
        print("\ncleanup")
        status, _ = client.delete("/users/me")
        result.record(status == 200, "DELETE /users/me (account removed)",
                      f"status={status}")
    else:
        print(f"\nkeeping account {email} / {password}")

    total = len(result.rows)
    failed = len(result.failures)
    print(f"\n{'=' * 62}")
    print(f"{total - failed}/{total} checks passed")
    if failed:
        print("\nfailures:")
        for _, name, detail in result.failures:
            print(f"  - {name} ({detail})")
    print("=" * 62)
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE,
                        help=f"API root, default {DEFAULT_BASE}")
    parser.add_argument("--keep", action="store_true",
                        help="do not delete the test account afterwards")
    args = parser.parse_args()
    return run(args.base_url, args.keep)


if __name__ == "__main__":
    sys.exit(main())
