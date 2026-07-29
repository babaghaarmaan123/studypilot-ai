"""Reads what it can off an uploaded past paper PDF.

Uploading the paper should be the whole interaction, so everything that can be
inferred from the file is inferred: which subject it belongs to, the board, the
year and session, the paper number and the total marks available. Anything that
cannot be read is simply left blank for the student to fill in — nothing is
invented.
"""

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from app.services.syllabus_parser import detect_exam_board, extract_pages

#: Only the front matter matters — the cover page carries the metadata.
_PAGES_TO_READ = 3

_YEAR_RE = re.compile(r"\b(19[89]\d|20[0-4]\d)\b")
_PAPER_RE = re.compile(
    r"\b(?:paper|unit|component)\s*([0-9]{1,2}[A-Z]?)\b", re.IGNORECASE
)
#: "9701/22", "WCS11/01" — board paper codes.
_PAPER_CODE_RE = re.compile(r"\b([0-9]{4}|[A-Z]{2,4}[0-9]{2,4})\s*/\s*([0-9]{2})\b")
_TOTAL_MARKS_PATTERNS = [
    # "The total mark for this paper is 75."
    re.compile(r"total\s+marks?\s+for\s+th(?:is|e)\s+paper\s+is\s+(\d{1,3})", re.IGNORECASE),
    # "Total for this paper: 75 marks" / "Total marks: 75"
    re.compile(r"total\s+(?:for\s+(?:this\s+)?paper|marks?)\s*[:\-]?\s*(\d{1,3})", re.IGNORECASE),
    # "Total: 75 marks"
    re.compile(r"total\s*[:\-]\s*(\d{1,3})\s*marks?", re.IGNORECASE),
    # "75 marks in total" / "75 marks available"
    re.compile(r"(\d{1,3})\s*marks?\s+(?:in\s+total|available)", re.IGNORECASE),
]
_TIME_ALLOWED_RE = re.compile(
    r"(?:time\s*(?:allowed)?\s*[:\-]?\s*)?"
    r"(?:(\d)\s*hours?\s*(?:(\d{1,2})\s*minutes?)?|(\d{1,3})\s*minutes?)",
    re.IGNORECASE,
)

_SESSIONS: List[Tuple[str, str]] = [
    ("may/june", "May/June"),
    ("october/november", "Oct/Nov"),
    ("february/march", "Feb/March"),
    ("january", "January"),
    ("february", "February"),
    ("march", "March"),
    ("may", "May"),
    ("june", "June"),
    ("october", "October"),
    ("november", "November"),
    ("summer", "Summer"),
    ("winter", "Winter"),
    ("autumn", "Autumn"),
    ("mock", "Mock"),
]

#: Words to strip when a filename has to stand in for the title.
_FILENAME_NOISE_RE = re.compile(
    r"\b(?:qp|ms|question\s*paper|mark\s*scheme|insert|final|copy|\(\d+\))\b",
    re.IGNORECASE,
)

#: Awarding-body and qualification banners. They match the title keywords but
#: name the qualification rather than the paper, so they are never the title.
_BANNER_RE = re.compile(
    r"^(?:pearson|edexcel|aqa|ocr|wjec|eduqas|cambridge|oxford)\b"
    r"|^(?:international\s+)?(?:general\s+certificate|advanced\s+(?:level|subsidiary)"
    r"|gce|as\s*(?:&|and)\s*a\s*level|a\s*level|as\s*level|gcse)\b"
    r"|^(?:candidate|centre|surname|other\s+names?|write\s+your)\b",
    re.IGNORECASE,
)


@dataclass
class PaperMetadata:
    """Everything read off the PDF. Every field is best-effort."""

    title: str
    exam_board: Optional[str] = None
    year: Optional[int] = None
    paper: Optional[str] = None
    session_label: Optional[str] = None
    marks_total: Optional[float] = None
    time_taken_minutes: Optional[int] = None
    subject_id: Optional[int] = None


def _title_from_filename(filename: str) -> str:
    stem = Path(filename or "past paper").stem
    stem = stem.replace("_", " ").replace("-", " ")
    stem = _FILENAME_NOISE_RE.sub(" ", stem)
    stem = re.sub(r"\s+", " ", stem).strip(" .")
    return (stem or "Past paper")[:200]


def _title_from_text(lines: List[str]) -> Optional[str]:
    """The first cover-page line that reads like a paper title."""
    for line in lines[:40]:
        if not (12 <= len(line) <= 120):
            continue
        if _YEAR_RE.fullmatch(line) or line.isdigit():
            continue
        if _BANNER_RE.match(line):
            continue
        letters = sum(1 for character in line if character.isalpha())
        if letters < len(line) * 0.6:
            continue
        if re.search(
            r"\b(paper|unit|component|advanced|level|certificate|mathematics"
            r"|physics|chemistry|biology|computer|economics|psychology|business"
            r"|english|history|geography)\b",
            line,
            re.IGNORECASE,
        ):
            return line[:200]
    return None


def _detect_session(blob: str) -> Optional[str]:
    lowered = blob.lower()
    for needle, label in _SESSIONS:
        if needle in lowered:
            return label
    return None


def _detect_paper(blob: str) -> Optional[str]:
    match = _PAPER_RE.search(blob)
    if match:
        keyword = blob[match.start() : match.end()].split()[0].capitalize()
        return f"{keyword} {match.group(1).upper()}"[:64]
    match = _PAPER_CODE_RE.search(blob)
    if match:
        return f"Paper {match.group(2).lstrip('0') or match.group(2)}"[:64]
    return None


def _detect_total_marks(blob: str) -> Optional[float]:
    for pattern in _TOTAL_MARKS_PATTERNS:
        for match in pattern.finditer(blob):
            value = float(match.group(1))
            # Sanity: exam papers run from about 10 to 300 marks.
            if 10 <= value <= 300:
                return value
    return None


def _detect_minutes(blob: str) -> Optional[int]:
    window = blob.lower()
    index = window.find("time")
    if index == -1:
        return None
    match = _TIME_ALLOWED_RE.search(blob[index : index + 120])
    if not match:
        return None
    hours, minutes, only_minutes = match.group(1), match.group(2), match.group(3)
    total = 0
    if hours:
        total += int(hours) * 60
    if minutes:
        total += int(minutes)
    if only_minutes and not hours:
        total = int(only_minutes)
    return total if 15 <= total <= 600 else None


def _detect_year(blob: str) -> Optional[int]:
    years = [int(match) for match in _YEAR_RE.findall(blob)]
    if not years:
        return None
    # The most recent plausible year on the cover is the exam year; older ones
    # tend to be copyright or specification dates.
    current = date.today().year
    candidates = [year for year in years if year <= current + 1]
    return max(candidates) if candidates else None


def _detect_subject(blob: str, filename: str, subjects: Iterable) -> Optional[int]:
    """Match the paper against one of the student's own subjects."""
    haystacks = [filename.lower(), blob[:2500].lower()]
    best: Optional[Tuple[int, int]] = None  # (score, subject_id)

    for subject in subjects:
        name = (subject.name or "").strip().lower()
        if not name:
            continue
        # Try the full name, then its individual significant words, so
        # "Mathematics" still matches a subject called "Further Mathematics".
        terms = [name] + [
            word for word in re.split(r"[^a-z]+", name) if len(word) >= 5
        ]
        for weight, haystack in enumerate(haystacks):
            for term in terms:
                if term and term in haystack:
                    # Filename matches (weight 0) beat body-text matches, and a
                    # full-name match beats a single-word match.
                    score = (2 - weight) * 10 + (5 if term == name else 1)
                    if best is None or score > best[0]:
                        best = (score, subject.id)
    return best[1] if best else None


def read_metadata(file_bytes: bytes, filename: str, subjects: Iterable) -> PaperMetadata:
    """Best-effort metadata for an uploaded past paper PDF."""
    try:
        pages = extract_pages(file_bytes)[:_PAGES_TO_READ]
    except Exception:  # noqa: BLE001 — an unreadable PDF still uploads fine
        pages = []

    text = "\n".join(pages)
    lines = [
        re.sub(r"\s+", " ", line).strip()
        for line in text.splitlines()
        if line.strip()
    ]
    blob = "\n".join(lines)
    searchable = f"{filename}\n{blob}"

    return PaperMetadata(
        title=_title_from_text(lines) or _title_from_filename(filename),
        exam_board=detect_exam_board(blob) if blob else None,
        year=_detect_year(searchable),
        paper=_detect_paper(searchable),
        session_label=_detect_session(searchable),
        marks_total=_detect_total_marks(blob),
        time_taken_minutes=_detect_minutes(blob),
        subject_id=_detect_subject(blob, filename.lower(), subjects),
    )
