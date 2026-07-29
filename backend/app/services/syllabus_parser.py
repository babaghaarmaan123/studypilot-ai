"""Structure-aware parsing of an uploaded syllabus specification PDF.

No external LLM call is made here — consistent with the rest of StudyPilot's
"AI" study engine, which is deterministic rather than generative.

Real exam board specifications (AQA, Edexcel, OCR, CAIE, WJEC, ...) all share
the same underlying shape even though the wording differs:

    Unit 1: Principles of Computer Science          <- unit / module / component
      Topic 1: Problem solving                      <- optional mid level
        1.1 Decomposition and abstraction           <- the smallest named area
          a  understand the term decomposition      <- content statements
          b  be able to decompose a problem

    3.1 Measurements and their errors               <- AQA: no "unit" keyword
      3.1.1 Use of SI units and their prefixes
        Fundamental (base) units.

This module rebuilds that hierarchy:

* **units**   — the outermost heading level present in the document
* **topics**  — the deepest headings that actually carry content
* **key points** — the content statements underneath each topic, stored on
  `Topic.notes` so the student sees what the board actually asks them to know

The two rules that keep the output clean, and which the previous
line-length-based version lacked:

1. A line only becomes a *heading* if it is numbered or keyword-prefixed **and**
   its title reads like a title (starts with a capital). "1 identify the
   products" is therefore a content statement, not a section.
2. A line only becomes a *key point* while a heading is open, and only if it is
   bulleted, enumerated, verb-led, or a genuine content sentence. Running
   headers, footers, page numbers, contents entries, copyright lines and
   front-matter prose are stripped before that decision is made.

If a PDF can't be parsed into anything useful (a scanned image with no text
layer, for example), the caller falls back to the generic syllabus template so
the subject is never left completely empty after a successful upload.
"""

import re
from collections import Counter
from io import BytesIO
from typing import List, Optional, Tuple

from pypdf import PdfReader

#: (name, estimated_hours, difficulty, key_points_or_None)
TopicTuple = Tuple[str, float, int, Optional[str]]
UnitEntry = Tuple[str, List[TopicTuple]]

MAX_UNITS = 24
MAX_TOPICS_PER_UNIT = 30
MAX_TOTAL_TOPICS = 200
MAX_POINTS_PER_TOPIC = 14
MAX_POINT_CHARS = 300
MAX_NOTES_CHARS = 4000

_MIN_POINT_LEN = 12
_MAX_HEADING_LEN = 130


# ---------------------------------------------------------------------------
# Exam board detection
# ---------------------------------------------------------------------------
_EXAM_BOARD_KEYWORDS: List[Tuple[str, str]] = [
    ("edexcel", "Edexcel"),
    ("pearson", "Edexcel"),
    ("aqa", "AQA"),
    ("ocr", "OCR"),
    ("oxford cambridge and rsa", "OCR"),
    ("wjec", "WJEC / Eduqas"),
    ("eduqas", "WJEC / Eduqas"),
    ("cambridge international", "Cambridge International (CAIE)"),
    ("caie", "Cambridge International (CAIE)"),
    ("cambridge assessment", "Cambridge International (CAIE)"),
]


# ---------------------------------------------------------------------------
# Line classification patterns
# ---------------------------------------------------------------------------
#: "Unit 3", "Module 2:", "Component 1 –", "Paper 2", "Theme B"
_UNIT_HEADING_RE = re.compile(
    r"^(unit|module|component|paper|theme)\s+"
    r"([0-9]{1,2}|[ivxlc]{1,5}|[A-H])\b\s*[:.\-–—]?\s*(.*)$",
    re.IGNORECASE,
)

#: "Topic 4", "Chapter 2", "Section B", "Area of study 1"
_TOPIC_HEADING_RE = re.compile(
    r"^(topic|chapter|section|area of study|subject content)\s+"
    r"([0-9]{1,2}|[ivxlc]{1,5}|[A-H])\b\s*[:.\-–—]?\s*(.*)$",
    re.IGNORECASE,
)

#: "3.1.2 Limitation of physical measurements" — the title must look like a
#: title (leading capital) so numbered *statements* are not mistaken for
#: sections.
_NUMERIC_HEADING_RE = re.compile(r"^(\d{1,2}(?:\.\d{1,2}){0,3})\.?\s+([A-Z][^\n]{2,%d})$" % _MAX_HEADING_LEN)

#: Enumerated content statements: "a understand…", "(b) describe…",
#: "iii. explain…", "2 deduce…", "•  recognise…".
#: Deliberately case-sensitive: a capital letter enumerator would swallow
#: title lines such as "A level Mathematics".
#: U+FFFD is in the list because pypdf cannot map the bullet glyph in several
#: board templates and hands back a replacement character instead.
_BULLET_CHARS = "-•*▪◦‣·–—�●∙"
_ENUMERATED_RE = re.compile(
    r"^(?:[" + re.escape(_BULLET_CHARS) + r"]\s*"
    r"|\(?([a-hA-H]|[ivxIVX]{1,4}|\d{1,2})\)[\s.]+"
    r"|([a-hA-H]|[ivxIVX]{1,4})[.)]\s+"
    r"|(\d{1,3})[.)]?\s+(?=[a-z])"
    r"|([a-h]|[ivx]{1,4})\s+(?=[a-z]))\s*(?P<body>.+)$"
)

#: Specification command verbs — the vocabulary boards use to open a content
#: statement. A verb-led line is content even without a bullet or number.
_COMMAND_VERBS = (
    "understand", "know", "recognise", "recognize", "describe", "explain",
    "define", "state", "identify", "list", "outline", "discuss", "compare",
    "contrast", "evaluate", "assess", "analyse", "analyze", "interpret",
    "calculate", "determine", "derive", "prove", "show", "demonstrate",
    "apply", "use", "select", "construct", "draw", "sketch", "plot",
    "measure", "estimate", "predict", "suggest", "justify", "deduce",
    "solve", "simplify", "convert", "classify", "distinguish", "recall",
    "appreciate", "be able to", "be aware of", "candidates should",
    "students should", "learners should", "students must", "including",
    "awareness of", "understanding of", "knowledge of",
)

#: Lead-ins that introduce a block of statements. Must end in a colon so that
#: "Students should be able to convert between units" — real content — is kept.
_LEAD_IN_RE = re.compile(
    r"^(?:candidates?|students?|learners?)\s+(?:should|must|will)\b[^.]{0,80}:\s*$"
    r"|^(?:content|what students need to learn|additional information)\s*:?\s*$",
    re.IGNORECASE,
)

#: Front/back matter we never want as syllabus content. Hitting one of these
#: suspends collection until the next real heading.
_SKIP_SECTION_RE = re.compile(
    r"^(?:contents|table of contents|introduction|foreword|qualification at a glance"
    r"|why choose|support(?:ing you)?|assessment objectives?|scheme of assessment"
    r"|command words?|glossary|appendi(?:x|ces)|mathematical requirements"
    r"|grade descriptors?|entry (?:and|&) assessment|administration"
    r"|malpractice|access arrangements|resources|further information"
    r"|contact us|index|acknowledgements|copyright|summary of (?:changes|updates)"
    r"|specification at a glance|overview of assessment|how to (?:use|order)"
    r"|working with (?:us|schools)|about (?:pearson|aqa|ocr|cambridge)"
    # Per-unit administrative blocks: exam length, mark totals, first sitting.
    r"|unit description|assessment (?:information|overview|criteria)"
    r"|content overview|prior (?:knowledge|learning)|synoptic assessment"
    r"|qualification aims|use of calculators?|availability)\b",
    re.IGNORECASE,
)

_PAGE_NUMBER_RE = re.compile(r"^(?:page\s*)?\d{1,4}(?:\s*(?:of|/)\s*\d{1,4})?$", re.IGNORECASE)
_DOT_LEADER_RE = re.compile(r"(?:\.\s*){4,}\s*\d{1,4}\s*$")
_CONTENTS_ENTRY_RE = re.compile(r"\s\s+\d{1,4}\s*$")
_URL_RE = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
_BOILERPLATE_RE = re.compile(
    r"(?:©|\(c\)\s*\d{4}|all rights reserved|issue\s*\d+\b|version\s*\d+(?:\.\d+)?\s*$"
    r"|first teaching|for first (?:teaching|assessment)|registered (?:charity|company)"
    r"|specimen (?:paper|material)|^\s*pearson\b|^\s*aqa\b|^\s*ocr\b"
    r"|qualification (?:number|accreditation))",
    re.IGNORECASE,
)

#: Difficulty signals.
_HARD_KEYWORDS = (
    "calculus", "differentiation", "integration", "organic", "thermodynamic",
    "quantum", "proof", "mechanism", "synthesis", "derivation", "equilibri",
    "kinetics", "vectors", "matrices", "recursion", "complexity", "entropy",
    "electromagnetic", "nuclear", "statistical inference", "hypothesis",
    "differential equation", "normal distribution", "stoichiometry",
)
_HARD_VERBS = ("derive", "prove", "evaluate", "analyse", "analyze", "justify", "assess", "model")
_EASY_VERBS = ("state", "define", "list", "name", "recall", "identify", "label")


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------
def extract_pages(file_bytes: bytes) -> List[str]:
    """Per-page text, so repeated headers/footers can be detected.

    Returns `[]` for a PDF that cannot be opened at all (truncated download,
    wrong file type) — the caller treats that the same as a scan with no text.
    """
    try:
        reader = PdfReader(BytesIO(file_bytes))
    except Exception:  # noqa: BLE001 — a corrupt PDF degrades, it doesn't raise
        return []

    pages: List[str] = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:  # noqa: BLE001 — a single bad page shouldn't fail the upload
            pages.append("")
    return pages


def extract_text(file_bytes: bytes) -> str:
    return "\n".join(extract_pages(file_bytes))


def detect_exam_board(text: str) -> Optional[str]:
    """Whichever board is named most often in the first few thousand characters."""
    head = text[:8000].lower()
    hits = Counter()
    for needle, label in _EXAM_BOARD_KEYWORDS:
        count = head.count(needle)
        if count:
            hits[label] += count
    if not hits:
        return None
    return hits.most_common(1)[0][0]


# ---------------------------------------------------------------------------
# Cleaning
# ---------------------------------------------------------------------------
#: Typographic characters that break plain-text matching.
_PUNCTUATION = str.maketrans(
    {
        "\xa0": " ",
        "‘": "'",
        "’": "'",
        "‚": "'",
        "‛": "'",
        "“": '"',
        "”": '"',
        "′": "'",
        "ﬁ": "fi",
        "ﬂ": "fl",
    }
)


def _normalise(line: str) -> str:
    line = line.translate(_PUNCTUATION)
    line = _URL_RE.sub("", line)
    return re.sub(r"\s+", " ", line).strip()


def _running_lines(pages: List[str]) -> set:
    """Lines that repeat across pages — i.e. running headers and footers."""
    if len(pages) < 3:
        return set()
    seen_on_pages = Counter()
    for page in pages:
        unique = {
            _normalise(ln).lower()
            for ln in page.splitlines()
            if len(_normalise(ln)) > 2
        }
        seen_on_pages.update(unique)

    threshold = max(3, int(len(pages) * 0.25))
    return {
        line
        for line, count in seen_on_pages.items()
        if count >= threshold and len(line) < 90
    }


def clean_lines(pages: List[str]) -> List[str]:
    """Flatten the pages into usable content lines, dropping the furniture."""
    running = _running_lines(pages)
    cleaned: List[str] = []

    for page in pages:
        for raw in page.splitlines():
            line = _normalise(raw)
            if len(line) < 3:
                continue
            if line.lower() in running:
                continue
            if _PAGE_NUMBER_RE.match(line):
                continue
            if _DOT_LEADER_RE.search(line):
                continue
            if _BOILERPLATE_RE.search(line):
                continue
            if not re.search(r"[A-Za-z]{2}", line):
                continue
            # "Topic 1: Problem solving        14" — a contents entry.
            if _CONTENTS_ENTRY_RE.search(line):
                line = _CONTENTS_ENTRY_RE.sub("", line).strip()
                if len(line) < 3:
                    continue
            cleaned.append(line)

    return cleaned


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------
#: A heading line that also carries its own first content statement, e.g.
#: "The demand curve a) The concept of 'demand'." — the PDF put the section
#: title and the first statement in the same table cell.
_INLINE_STATEMENT_RE = re.compile(r"^(?P<title>.{3,}?)\s+(?P<rest>\(?[a-h]\)\s+\S.*)$")

#: How much of a wrapped heading title may be pulled back from following lines.
_TITLE_TAIL_MAX_LEN = 60
_TITLE_TAIL_LIMIT = 2

#: Specs repeat a section heading on the next page marked "(continued)". Both
#: halves describe the same section, so the marker is dropped and the content
#: merged back together.
_CONTINUED_RE = re.compile(r"\s*[\(\[]?\s*cont(?:inued|\.)?\s*[\)\]]?\s*$", re.IGNORECASE)


def _heading_number(line: str) -> Optional[str]:
    """The numeric prefix of a numbered heading, if `line` is one."""
    match = _NUMERIC_HEADING_RE.match(line)
    return match.group(1) if match else None


def _heading_match(line: str) -> Optional[Tuple[int, str, int]]:
    """Classify `line` as a heading.

    Returns `(kind, title, numeric_depth)` where `kind` is 0 for an explicit
    unit/module keyword, 1 for an explicit topic/section keyword and 2 for a
    numbered heading (whose depth is then meaningful), or `None`.
    """
    if len(line) > _MAX_HEADING_LEN:
        return None

    match = _UNIT_HEADING_RE.match(line)
    if match:
        keyword, label, rest = match.group(1), match.group(2), match.group(3)
        rest = rest.strip(" :.-–—")
        if len(label) == 1 and label.isalpha():
            label = label.upper()
        # Keep the board's own word — "Module 2", not a rewritten "Unit 2".
        title = f"{keyword.capitalize()} {label}"
        return 0, f"{title}: {rest}" if rest else title, 0

    match = _TOPIC_HEADING_RE.match(line)
    if match:
        rest = match.group(3).strip(" :.-–—")
        return 1, rest or line, 0

    match = _NUMERIC_HEADING_RE.match(line)
    if match:
        number, rest = match.group(1), match.group(2).strip(" :.-–—")
        rest = _CONTINUED_RE.sub("", rest).strip(" :.-–—")
        if not rest:
            return None
        depth = number.count(".") + 1
        return 2, rest, depth

    return None


def _starts_with_command_verb(text: str) -> bool:
    lowered = text.lower().lstrip("( ")
    return any(lowered.startswith(verb) for verb in _COMMAND_VERBS)


def _statement_match(line: str) -> Optional[str]:
    """Return the statement text if `line` reads like a content statement."""
    match = _ENUMERATED_RE.match(line)
    if match:
        body = (match.group("body") or "").strip(" :;.-–—")
        # A bullet with a Title Case body and no verb is usually a sub-heading
        # in disguise; still useful as a key point, so keep it.
        return body or None

    if _starts_with_command_verb(line):
        return line.strip(" :;-–—")

    return None


def _looks_like_sentence_content(line: str) -> bool:
    """AQA-style content written as plain sentence fragments in a table cell."""
    if not (_MIN_POINT_LEN <= len(line) <= 220):
        return False
    if line.endswith(("?", "!")):
        return False
    words = line.split()
    if len(words) < 3:
        return False
    # Needs some lower-case prose — an ALL CAPS or Title Case Line Like This
    # is a heading or a table header, not content.
    lower_words = sum(1 for w in words[1:] if w[:1].islower())
    return lower_words >= max(1, len(words) // 3)


def _split_inline_statement(title: str) -> Tuple[str, Optional[str]]:
    """Separate a heading title from a first statement stuck onto the end."""
    match = _INLINE_STATEMENT_RE.match(title)
    if not match:
        return title, None
    head = match.group("title").strip(" :.-–—")
    statement = _statement_match(match.group("rest"))
    if not head or not statement or len(statement) < _MIN_POINT_LEN:
        return title, None
    return head, statement


def _is_title_tail(line: str, title: str) -> bool:
    """A short lower-case line continuing a heading that wrapped mid-phrase."""
    if len(line) > _TITLE_TAIL_MAX_LEN or not line[:1].islower():
        return False
    if title.endswith((".", ":", ";", "?")):
        return False
    if _ENUMERATED_RE.match(line) or _heading_match(line):
        return False
    return not _starts_with_command_verb(line)


def _is_continuation(line: str, previous: str) -> bool:
    """A wrapped tail of the previous statement."""
    if not previous or previous.endswith((".", ":", ";")):
        return False
    if len(previous) < 25:
        return False
    if _heading_match(line) or _ENUMERATED_RE.match(line):
        return False
    return bool(line[:1].islower())


# ---------------------------------------------------------------------------
# Estimation
# ---------------------------------------------------------------------------
def _estimate(name: str, points: List[str]) -> Tuple[float, int]:
    blob = " ".join([name] + points).lower()

    difficulty = 3
    if any(keyword in blob for keyword in _HARD_KEYWORDS):
        difficulty += 1
    if sum(blob.count(verb) for verb in _HARD_VERBS) >= 2:
        difficulty += 1
    elif points and all(
        not any(v in p.lower() for v in _HARD_VERBS) for p in points
    ) and sum(blob.count(verb) for verb in _EASY_VERBS) >= 2:
        difficulty -= 1
    difficulty = max(1, min(5, difficulty))

    # Roughly 20 minutes of work per content statement, floored at an hour so
    # a thin topic still earns a proper block on the timetable.
    hours = 0.75 + 0.35 * len(points)
    hours = max(1.0, min(6.0, round(hours * 4) / 4))
    return hours, difficulty


def _format_points(points: List[str]) -> Optional[str]:
    if not points:
        return None
    joined = "\n".join(points)
    return joined[:MAX_NOTES_CHARS]


# ---------------------------------------------------------------------------
# Structure building
# ---------------------------------------------------------------------------
class _Heading:
    """One heading and the content statements gathered directly beneath it."""

    __slots__ = ("rank", "title", "points", "parent")

    def __init__(self, rank: int, title: str, parent: Optional["_Heading"]):
        self.rank = rank
        self.title = title
        self.points: List[str] = []
        self.parent = parent

    def unit_name(self) -> str:
        """The unit this topic belongs to: the heading directly above it.

        Using the immediate parent rather than the outermost ancestor keeps the
        grouping the same size whichever numbering scheme a board uses — one
        unit per named section, instead of one enormous unit per exam paper.
        """
        return self.parent.title if self.parent else self.title


def _rank_for(kind: int, depth: int, min_depth: int, bare_are_items: bool) -> int:
    if kind == 0:
        return 0
    if kind == 1:
        return 1
    # A bare "1", "2", "3" is only a top-level section if the document uses it
    # that way. Table-based specifications (Edexcel Economics, for one) restart
    # bare numbering inside every section, where it marks individual content
    # areas — the most specific level, not the least.
    if bare_are_items and depth == 1:
        return 3
    # Otherwise the shallowest numbering sits at the topic level and deeper
    # numbering nests below it.
    return min(3, 1 + max(0, depth - min_depth))


def _content_lines(lines: List[str]) -> List[str]:
    """Drop front and back matter — contents, admin blocks, appendices.

    Both passes below work from this list so they can never disagree about
    which part of the document is real syllabus content.
    """
    kept: List[str] = []
    skipping = False
    for line in lines:
        match = _heading_match(line)
        if _SKIP_SECTION_RE.match(match[1] if match else line):
            skipping = True
            continue
        if match:
            skipping = False
        if not skipping:
            kept.append(line)
    return kept


def _numbering_scheme(lines: List[str]) -> Tuple[int, bool]:
    """Return `(min_depth, bare_numbers_are_items)` for this document.

    A bare "1", "2", "3" heading is usually a top-level section (CAIE, AQA).
    In table-based specifications it instead numbers the content areas *inside*
    a section, restarting each time — the most specific level, not the least.
    Those documents are recognised by two things together: no bare-numbered
    heading appears before the first dotted one, and bare numbers repeat.
    """
    numbers = [number for number in (_heading_number(line) for line in lines) if number]
    depths = [number.count(".") + 1 for number in numbers]
    if not depths:
        return 1, False

    first_dotted = next((i for i, depth in enumerate(depths) if depth > 1), None)
    bare_before_dotted = any(
        depth == 1 for depth in depths[: first_dotted if first_dotted is not None else 0]
    )
    bare_repeats = any(
        count > 1
        for count in Counter(n for n in numbers if "." not in n).values()
    )

    bare_are_items = (
        first_dotted is not None and not bare_before_dotted and bare_repeats
    )
    if bare_are_items:
        dotted = [depth for depth in depths if depth > 1]
        return (min(dotted) if dotted else 1), True
    return min(depths), False


def parse_units(text_or_lines) -> List[UnitEntry]:
    """Build the `[(unit_name, [(topic, hours, difficulty, points)...])...]` tree."""
    if isinstance(text_or_lines, str):
        lines = clean_lines([text_or_lines])
    else:
        lines = list(text_or_lines)

    # Pass 1 — work out the numbering scheme the document uses.
    lines = _content_lines(lines)
    min_depth, bare_are_items = _numbering_scheme(lines)

    # Pass 2 — walk the document, building the heading tree.
    headings: List[_Heading] = []
    stack: List[_Heading] = []
    current: Optional[_Heading] = None
    tails_taken = 0

    for line in lines:
        match = _heading_match(line)

        if match:
            kind, title, depth = match
            rank = _rank_for(kind, depth, min_depth, bare_are_items)
            title, inline_statement = _split_inline_statement(title)

            while stack and stack[-1].rank >= rank:
                stack.pop()
            node = _Heading(rank, title, stack[-1] if stack else None)
            stack.append(node)
            headings.append(node)
            current = node
            tails_taken = 0
            if inline_statement:
                node.points.append(inline_statement[:MAX_POINT_CHARS])
            continue

        if current is None:
            continue

        if _LEAD_IN_RE.match(line):
            continue

        # A heading whose title wrapped onto the next line: "1 Rational" /
        # "decision making". Recover it before anything else claims the line.
        if (
            not current.points
            and tails_taken < _TITLE_TAIL_LIMIT
            and _is_title_tail(line, current.title)
        ):
            current.title = f"{current.title} {line}"[:200]
            tails_taken += 1
            continue

        if current.points and _is_continuation(line, current.points[-1]):
            merged = f"{current.points[-1]} {line}"
            current.points[-1] = merged[:MAX_POINT_CHARS]
            continue

        if len(current.points) >= MAX_POINTS_PER_TOPIC:
            continue

        statement = _statement_match(line)
        if statement is None and current.rank >= 1 and _looks_like_sentence_content(line):
            # Sentence-style content (AQA writes its content as fragments in a
            # table). Only accepted below the outermost heading level, where
            # "Externally assessed. Availability: January and June." lives.
            statement = line
        if statement and len(statement) >= _MIN_POINT_LEN:
            current.points.append(statement[:MAX_POINT_CHARS])

    return _assemble(headings)


def _assemble(headings: List[_Heading]) -> List[UnitEntry]:
    """Turn the heading tree into units of topics, keeping document order.

    A section that the specification splits across pages arrives here twice
    under the same name; the two halves are merged rather than one being
    dropped, so no content statements are lost.
    """
    units: List[str] = []
    #: unit name -> list of (topic name, points)
    grouped: "dict[str, List[Tuple[str, List[str]]]]" = {}
    total = 0

    for heading in headings:
        if not heading.points:
            # No content beneath it — a contents entry or a pure grouping
            # heading. It still serves as a parent for its children.
            continue

        # Strip "(continued)" here as well as at match time — it can also
        # arrive on the wrapped second line of a heading.
        unit_name = _CONTINUED_RE.sub("", heading.unit_name()).strip()[:150]
        topic_name = _CONTINUED_RE.sub("", heading.title).strip()[:200]
        if unit_name == topic_name and heading.parent is not None:
            unit_name = _CONTINUED_RE.sub("", heading.parent.title).strip()[:150]

        if unit_name not in grouped:
            if len(units) >= MAX_UNITS:
                continue
            grouped[unit_name] = []
            units.append(unit_name)
        topics = grouped[unit_name]

        existing = next((entry for entry in topics if entry[0] == topic_name), None)
        if existing is not None:
            room = MAX_POINTS_PER_TOPIC - len(existing[1])
            for point in heading.points:
                if room <= 0:
                    break
                if point not in existing[1]:
                    existing[1].append(point)
                    room -= 1
            continue

        if total >= MAX_TOTAL_TOPICS or len(topics) >= MAX_TOPICS_PER_UNIT:
            continue
        topics.append((topic_name, list(heading.points)))
        total += 1

    result: List[UnitEntry] = []
    for name in units:
        entries = grouped.get(name) or []
        if not entries:
            continue
        built: List[TopicTuple] = []
        for topic_name, points in entries:
            hours, difficulty = _estimate(topic_name, points)
            built.append((topic_name, hours, difficulty, _format_points(points)))
        result.append((name, built))
    return result


def parse_pdf(file_bytes: bytes) -> Tuple[List[UnitEntry], Optional[str]]:
    """Extracts the syllabus from the PDF and returns (units, detected_board).

    `units` is `[]` if nothing usable could be parsed (e.g. a scanned PDF with
    no text layer) — the caller should fall back to the generic template.
    """
    pages = extract_pages(file_bytes)
    text = "\n".join(pages)
    if not text.strip():
        return [], None

    lines = clean_lines(pages)
    units = parse_units(lines)

    # A single topic carrying everything means the structure was not really
    # understood; treat that as a parse failure so the caller can fall back.
    if sum(len(topics) for _, topics in units) < 2:
        return [], detect_exam_board(text)

    return units, detect_exam_board(text)
