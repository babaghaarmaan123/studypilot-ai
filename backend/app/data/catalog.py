"""Static reference data for the UK education system.

Everything the onboarding assistant and subject manager need to offer sensible
choices: curricula, subject lists, exam boards, admissions tests, universities
and degree options. Served to the frontend from /api/v1/catalog so the two
sides can never drift apart.
"""

import json
from pathlib import Path
from typing import Dict, List

# ---------------------------------------------------------------------------
# Curricula — deliberately limited to the three supported pathways.
# StudyPilot does not support undergraduate, postgraduate, Foundation or IB.
# ---------------------------------------------------------------------------
CURRICULA: List[Dict[str, str]] = [
    {
        "code": "gcse",
        "label": "GCSE",
        "description": "Years 9–11 · GCSE and IGCSE qualifications",
    },
    {
        "code": "a_level",
        "label": "A Levels",
        "description": "Years 12–13 · UK domestic A Levels",
    },
    {
        "code": "international_a_level",
        "label": "International A Levels",
        "description": "Years 12–13 · Edexcel IAL / Cambridge International",
    },
]

YEAR_GROUPS: List[str] = ["Year 10", "Year 11", "Year 12", "Year 13", "Other"]

PREFERRED_STUDY_TIMES: List[Dict[str, str]] = [
    {"code": "morning", "label": "Morning", "window": "06:00 – 12:00"},
    {"code": "afternoon", "label": "Afternoon", "window": "12:00 – 17:00"},
    {"code": "evening", "label": "Evening", "window": "17:00 – 21:00"},
    {"code": "night", "label": "Night", "window": "21:00 – 00:00"},
]

# Start hour used by the scheduler for each preference.
STUDY_WINDOW_START: Dict[str, int] = {
    "morning": 8,
    "afternoon": 13,
    "evening": 17,
    "night": 20,
}

STUDY_HABITS: List[Dict[str, str]] = [
    {
        "code": "procrastinate",
        "label": "I procrastinate.",
        "strategy": "Short 25-minute blocks with an easy first task to break inertia.",
    },
    {
        "code": "regular",
        "label": "I study regularly.",
        "strategy": "Longer deep-work blocks and an ambitious weekly target.",
    },
    {
        "code": "cram",
        "label": "I only study before exams.",
        "strategy": "Front-loaded revision and earlier spaced-repetition checkpoints.",
    },
    {
        "code": "time_management",
        "label": "I struggle with time management.",
        "strategy": "Fixed daily slots at the same time with explicit finish times.",
    },
    {
        "code": "focus",
        "label": "I lose focus easily.",
        "strategy": "Capped 40-minute sessions with scheduled breaks between them.",
    },
]

# ---------------------------------------------------------------------------
# Subjects per curriculum
#
# Stored in subjects.json (not hardcoded here) so the list can be extended
# without touching any Python code — see that file for the full GCSE /
# A Level / International A Level subject sets.
# ---------------------------------------------------------------------------
def _load_subjects() -> Dict[str, List[str]]:
    path = Path(__file__).parent / "subjects.json"
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


SUBJECTS_BY_CURRICULUM: Dict[str, List[str]] = _load_subjects()

EXAM_BOARDS: Dict[str, List[str]] = {
    "gcse": ["AQA", "Edexcel", "OCR", "WJEC / Eduqas", "Cambridge IGCSE", "Other"],
    "a_level": ["AQA", "Edexcel", "OCR", "WJEC / Eduqas", "Other"],
    "international_a_level": [
        "Edexcel IAL",
        "Cambridge International (CAIE)",
        "Oxford AQA International",
        "Other",
    ],
}

# ---------------------------------------------------------------------------
# University admissions tests
# ---------------------------------------------------------------------------
ADMISSION_EXAMS: List[Dict[str, str]] = [
    {
        "code": "TMUA",
        "name": "TMUA",
        "full_name": "Test of Mathematics for University Admission",
        "focus": "Mathematical thinking and reasoning",
        "sessions_per_week": 1,
        "session_minutes": 90,
        "practice_title": "TMUA practice — Paper 1 reasoning drills",
    },
    {
        "code": "ESAT",
        "name": "ESAT",
        "full_name": "Engineering and Science Admissions Test",
        "focus": "Physics and Mathematics",
        "sessions_per_week": 2,
        "session_minutes": 75,
        "practice_title": "ESAT practice — Physics & Mathematics",
    },
    {
        "code": "MAT",
        "name": "MAT",
        "full_name": "Mathematics Admissions Test",
        "focus": "Advanced problem-solving mathematics",
        "sessions_per_week": 1,
        "session_minutes": 90,
        "practice_title": "MAT practice — advanced mathematics session",
    },
    {
        "code": "PAT",
        "name": "PAT",
        "full_name": "Physics Aptitude Test",
        "focus": "Physics and Maths problem solving",
        "sessions_per_week": 1,
        "session_minutes": 90,
        "practice_title": "PAT practice — physics problem set",
    },
    {
        "code": "STEP",
        "name": "STEP",
        "full_name": "Sixth Term Examination Paper",
        "focus": "STEP-style long-form mathematics",
        "sessions_per_week": 2,
        "session_minutes": 90,
        "practice_title": "STEP-style practice — full question under timed conditions",
    },
    {
        "code": "LNAT",
        "name": "LNAT",
        "full_name": "Law National Aptitude Test",
        "focus": "Critical reading and argumentative essay",
        "sessions_per_week": 1,
        "session_minutes": 60,
        "practice_title": "LNAT practice — comprehension & essay",
    },
    {
        "code": "UCAT",
        "name": "UCAT",
        "full_name": "University Clinical Aptitude Test",
        "focus": "Reasoning, decision making and situational judgement",
        "sessions_per_week": 3,
        "session_minutes": 45,
        "practice_title": "UCAT practice — reasoning drills",
    },
    {
        "code": "OXFORD_TESTS",
        "name": "Oxford Admissions Tests",
        "full_name": "Oxford subject admissions assessments",
        "focus": "Subject-specific Oxford assessment preparation",
        "sessions_per_week": 1,
        "session_minutes": 75,
        "practice_title": "Oxford admissions test preparation",
    },
    {
        "code": "CAMBRIDGE_TESTS",
        "name": "Cambridge Admissions Tests",
        "full_name": "Cambridge subject admissions assessments",
        "focus": "Subject-specific Cambridge assessment preparation",
        "sessions_per_week": 1,
        "session_minutes": 75,
        "practice_title": "Cambridge admissions test preparation",
    },
    {
        "code": "IELTS",
        "name": "IELTS",
        "full_name": "International English Language Testing System",
        "focus": "Listening, reading, writing and speaking",
        "sessions_per_week": 2,
        "session_minutes": 60,
        "practice_title": "IELTS practice — skills rotation",
    },
    {
        "code": "PTE",
        "name": "Pearson PTE Academic",
        "full_name": "Pearson Test of English Academic",
        "focus": "Academic English across four skills",
        "sessions_per_week": 2,
        "session_minutes": 60,
        "practice_title": "PTE Academic practice — timed section",
    },
]

ADMISSION_EXAM_INDEX: Dict[str, Dict[str, str]] = {
    exam["code"]: exam for exam in ADMISSION_EXAMS
}

UNIVERSITIES: List[str] = [
    "University of Oxford",
    "University of Cambridge",
    "Imperial College London",
    "University College London",
    "King's College London",
    "University of Warwick",
    "University of Manchester",
    "University of Bristol",
    "University of Edinburgh",
    "Durham University",
    "University of Southampton",
    "University of Birmingham",
    "University of Leeds",
    "Other",
]

DEGREES: List[str] = [
    "Computer Science",
    "Artificial Intelligence",
    "Engineering",
    "Medicine",
    "Economics",
    "Law",
    "Mathematics",
    "Physics",
    "Business",
    "Psychology",
    "Architecture",
    "Finance",
    "Data Science",
    "Other",
]

# A palette that stays legible in both light and dark mode.
SUBJECT_COLOURS: List[str] = [
    "#6366f1",  # indigo
    "#ec4899",  # pink
    "#14b8a6",  # teal
    "#f59e0b",  # amber
    "#8b5cf6",  # violet
    "#06b6d4",  # cyan
    "#ef4444",  # red
    "#22c55e",  # green
    "#3b82f6",  # blue
    "#f97316",  # orange
    "#a855f7",  # purple
    "#0ea5e9",  # sky
]


def colour_for_index(index: int) -> str:
    return SUBJECT_COLOURS[index % len(SUBJECT_COLOURS)]


# Keyword -> colour, matched against the subject name (case-insensitive).
# Mirrors frontend/src/lib/utils.js#colourForSubject so a subject gets the
# same colour regardless of whether it was created via onboarding or the
# Subjects page.
_SUBJECT_COLOUR_KEYWORDS: List[tuple[str, str]] = [
    ("computer science", "#3b82f6"),
    ("information technology", "#3b82f6"),
    ("mathematics", "#8b5cf6"),
    ("mechanics", "#8b5cf6"),
    ("statistics", "#8b5cf6"),
    ("decision maths", "#8b5cf6"),
    ("biology", "#22c55e"),
    ("chemistry", "#ef4444"),
    ("physics", "#f59e0b"),
    ("economics", "#eab308"),
    ("accounting", "#eab308"),
    ("business", "#eab308"),
    ("psychology", "#ec4899"),
]


def colour_for_subject(name: str, index: int = 0) -> str:
    lowered = (name or "").lower()
    for keyword, colour in _SUBJECT_COLOUR_KEYWORDS:
        if keyword in lowered:
            return colour
    return colour_for_index(index)


def subjects_for(curriculum: str) -> List[str]:
    return SUBJECTS_BY_CURRICULUM.get(curriculum, [])


def catalog_payload() -> Dict:
    """Single response consumed by the onboarding wizard and subject manager."""
    return {
        "curricula": CURRICULA,
        "year_groups": YEAR_GROUPS,
        "subjects": SUBJECTS_BY_CURRICULUM,
        "exam_boards": EXAM_BOARDS,
        "admission_exams": ADMISSION_EXAMS,
        "universities": UNIVERSITIES,
        "degrees": DEGREES,
        "study_habits": STUDY_HABITS,
        "preferred_study_times": PREFERRED_STUDY_TIMES,
        "subject_colours": SUBJECT_COLOURS,
    }
