"""Public reference data — no authentication required."""

from typing import List

from fastapi import APIRouter, HTTPException, Query, status

from app.data.catalog import (
    ADMISSION_EXAMS,
    CURRICULA,
    DEGREES,
    EXAM_BOARDS,
    SUBJECTS_BY_CURRICULUM,
    UNIVERSITIES,
    catalog_payload,
)
from app.data.syllabus import template_for

router = APIRouter(prefix="/catalog", tags=["Reference data"])


@router.get(
    "",
    summary="All reference data",
    description=(
        "Curricula, year groups, subject lists, exam boards, admissions tests, "
        "universities, degrees, study habits and the subject colour palette."
    ),
)
def catalog() -> dict:
    return catalog_payload()


@router.get("/curricula", summary="Supported curricula")
def curricula() -> List[dict]:
    return CURRICULA


@router.get(
    "/subjects",
    summary="Subjects for a curriculum",
    description="StudyPilot supports GCSE, A Level and International A Level only.",
)
def subjects(
    curriculum: str = Query(..., pattern="^(gcse|a_level|international_a_level)$")
) -> dict:
    return {
        "curriculum": curriculum,
        "subjects": SUBJECTS_BY_CURRICULUM[curriculum],
        "exam_boards": EXAM_BOARDS.get(curriculum, []),
    }


@router.get("/admission-exams", summary="University admissions tests")
def admission_exams() -> List[dict]:
    return ADMISSION_EXAMS


@router.get("/universities", summary="Target universities")
def universities() -> List[str]:
    return UNIVERSITIES


@router.get("/degrees", summary="Degree options")
def degrees() -> List[str]:
    return DEGREES


@router.get(
    "/syllabus-template",
    summary="Preview the starter syllabus for a subject",
    description="Shows the units and topics StudyPilot would seed for a subject.",
)
def syllabus_template(subject: str, curriculum: str | None = None) -> dict:
    template = template_for(subject, curriculum)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No template available for that subject.",
        )
    return {
        "subject": subject,
        "curriculum": curriculum,
        "units": [
            {
                "name": unit,
                "topics": [
                    {"name": name, "estimated_hours": hours, "difficulty": difficulty}
                    for name, hours, difficulty in topics
                ],
            }
            for unit, topics in template.items()
        ],
    }
