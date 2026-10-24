from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.api.dependencies import AnalystUser, DatabaseSession
from app.models import (
    DetectionCandidate,
    DetectionValidation,
    Evidence,
    Finding,
    Investigation,
)
from app.models.enums import DetectionValidationStatus, UserRole
from app.operations import emit_audit
from app.schemas.operations import DetectionCreate, DetectionResponse, DetectionValidationCreate

router = APIRouter(prefix="/detections", tags=["detection engineering"])


@router.get("", response_model=list[DetectionResponse])
async def list_detections(
    session: DatabaseSession,
    validation_status: DetectionValidationStatus | None = None,
    limit: int = Query(default=100, ge=1, le=200),
) -> list[DetectionCandidate]:
    filters = []
    if validation_status is not None:
        filters.append(DetectionCandidate.validation_status == validation_status)
    return list(
        (
            await session.scalars(
                select(DetectionCandidate)
                .where(*filters)
                .order_by(DetectionCandidate.updated_at.desc())
                .limit(limit)
            )
        ).all()
    )


@router.post("", response_model=DetectionResponse, status_code=status.HTTP_201_CREATED)
async def create_detection(
    payload: DetectionCreate,
    session: DatabaseSession,
    user: AnalystUser,
) -> DetectionCandidate:
    if payload.investigation_id and await session.get(
        Investigation, payload.investigation_id
    ) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investigation not found")
    if payload.finding_id and await session.get(Finding, payload.finding_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")
    evidence_ids = set(payload.supporting_evidence_ids)
    found = set(
        (
            await session.scalars(select(Evidence.id).where(Evidence.id.in_(evidence_ids)))
        ).all()
    )
    if found != evidence_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Every detection candidate requires existing supporting evidence",
        )
    detection = DetectionCandidate(
        investigation_id=payload.investigation_id,
        finding_id=payload.finding_id,
        title=payload.title.strip(),
        kind=payload.kind,
        behavior_hypothesis=payload.behavior_hypothesis.strip(),
        technique_ids=payload.technique_ids,
        required_telemetry=payload.required_telemetry,
        field_assumptions=payload.field_assumptions,
        candidate_logic=payload.candidate_logic,
        supporting_evidence_ids=[str(item) for item in payload.supporting_evidence_ids],
        false_positives=payload.false_positives,
        limitations=payload.limitations,
        validation_status=DetectionValidationStatus.NEEDS_VALIDATION,
        created_by=user.id,
    )
    session.add(detection)
    await session.flush()
    emit_audit(
        session,
        actor_id=user.id,
        action="DETECTION_CANDIDATE_CREATED",
        object_type="DetectionCandidate",
        object_id=detection.id,
        details={"kind": detection.kind.value},
    )
    await session.commit()
    await session.refresh(detection)
    return detection


@router.post("/{detection_id}/validations", response_model=DetectionResponse)
async def validate_detection(
    detection_id: UUID,
    payload: DetectionValidationCreate,
    session: DatabaseSession,
    user: AnalystUser,
) -> DetectionCandidate:
    detection = await session.get(DetectionCandidate, detection_id)
    if detection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Detection not found")
    if (
        payload.status == DetectionValidationStatus.VALIDATED_IN_PRODUCTION
        and user.role != UserRole.ADMIN
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Production validation requires an administrator",
        )
    validation = DetectionValidation(
        detection_id=detection.id,
        status=payload.status,
        environment=payload.environment,
        validation_evidence=payload.validation_evidence,
        notes=payload.notes,
        validated_by=user.id,
        validated_at=datetime.now(UTC),
    )
    session.add(validation)
    detection.validation_status = payload.status
    emit_audit(
        session,
        actor_id=user.id,
        action="DETECTION_VALIDATED",
        object_type="DetectionCandidate",
        object_id=detection.id,
        details={"status": payload.status.value, "environment": payload.environment},
    )
    await session.commit()
    await session.refresh(detection)
    return detection


@router.get("/coverage", response_model=dict[str, int])
async def detection_coverage(session: DatabaseSession) -> dict[str, int]:
    candidates = await session.scalar(select(func.count(DetectionCandidate.id)))
    test_validated = await session.scalar(
        select(func.count(DetectionCandidate.id)).where(
            DetectionCandidate.validation_status
            == DetectionValidationStatus.VALIDATED_IN_TEST
        )
    )
    production_validated = await session.scalar(
        select(func.count(DetectionCandidate.id)).where(
            DetectionCandidate.validation_status
            == DetectionValidationStatus.VALIDATED_IN_PRODUCTION
        )
    )
    return {
        "candidates": candidates or 0,
        "validated_in_test": test_validated or 0,
        "validated_in_production": production_validated or 0,
    }
