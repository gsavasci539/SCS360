"""Survey drafts, published questions and validated responses."""
from datetime import date
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import delete, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services import survey_service as service
from app.application.services.consent_service import form_organization
from app.core.database import get_db
from app.core.dates import school_today
from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.core.permissions import PermissionChecker
from app.core.responses import success_response
from app.core.tenant import TenantContext
from app.domain.entities.surveys import Survey, SurveyQuestion, SurveyResponse
from app.infrastructure.models.models import Organization, User

router = APIRouter(prefix="/api/surveys", tags=["Surveys"])


class SurveyCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    organization_id: UUID | None = None
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    target_audience: Literal["PARENTS", "STAFF", "ALL"] = "PARENTS"
    start_date: date
    end_date: date
    is_anonymous: bool = False

    @model_validator(mode="after")
    def dates(self):
        if self.end_date < self.start_date:
            raise ValueError("Bitiş tarihi başlangıçtan önce olamaz")
        return self


class SurveyQuestionCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    survey_id: UUID
    question_text: str = Field(min_length=1, max_length=2000)
    question_type: Literal["MULTIPLE_CHOICE", "RATING", "TEXT"]
    options: list[str] | None = Field(default=None, max_length=25)
    is_required: bool = True
    order_index: int = Field(default=0, ge=0, le=100)

    @model_validator(mode="after")
    def choices(self):
        if self.question_type == "MULTIPLE_CHOICE":
            if not self.options or not 2 <= len(self.options) <= 25 or any(not option or len(option) > 200 for option in self.options) or len(set(self.options)) != len(self.options):
                raise ValueError("Seçmeli soruda en az iki farklı, boş olmayan seçenek gerekir")
        elif self.options:
            raise ValueError("Yalnız seçmeli sorulara seçenek eklenebilir")
        return self


class SurveyResponseCreate(BaseModel):
    survey_id: UUID
    response_data: dict[str, Any] = Field(max_length=100)
    # Retained for old mobile clients; client-supplied IP is never stored.
    ip_address: str | None = Field(default=None, max_length=45)


async def require_editable(db, row):
    service.require_draft(row)
    if (await db.execute(select(exists().where(SurveyResponse.__table__.c.survey_id == row.id)))).scalar():
        raise ConflictException("Yanıtı bulunan anket değiştirilemez")


@router.get("/options")
async def options(db: AsyncSession = Depends(get_db, scope="function"), tenant: TenantContext = Depends(PermissionChecker("surveys.write"))):
    rows = (await db.execute(select(Organization).where(Organization.deleted_at.is_(None), Organization.is_active.is_(True))
        .order_by(Organization.name).limit(100))).scalars().all()
    return success_response({"organizations": [{"id": str(row.id), "name": row.name} for row in rows]})


@router.get("/summary")
async def summary(db: AsyncSession = Depends(get_db, scope="function"), tenant: TenantContext = Depends(PermissionChecker("surveys.read"))):
    return success_response(await service.summary(db))


@router.get("/my-surveys")
async def own_surveys(limit: int = Query(21, ge=1, le=100), offset: int = Query(0, ge=0), db: AsyncSession = Depends(get_db, scope="function"),
                      tenant: TenantContext = Depends(PermissionChecker("surveys.respond"))):
    if tenant.organization_id is None:
        return success_response([])
    return success_response(await service.available(db, tenant.organization_id, tenant.user_id, "STAFF", limit, offset))


@router.get("/surveys")
async def list_surveys(status: str | None = None, target_audience: str | None = None, start_date: date | None = None, end_date: date | None = None,
                       limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0), db: AsyncSession = Depends(get_db, scope="function"),
                       tenant: TenantContext = Depends(PermissionChecker("surveys.read"))):
    query = select(Survey)
    if status:
        query = query.where(Survey.status == status.upper())
    if target_audience:
        query = query.where(Survey.target_audience == target_audience)
    if start_date:
        query = query.where(Survey.start_date >= start_date)
    if end_date:
        query = query.where(Survey.end_date <= end_date)
    rows = (await db.execute(query.order_by(Survey.start_date.desc(), Survey.id).limit(limit).offset(offset))).scalars().all()
    counts = dict((await db.execute(select(SurveyResponse.survey_id, func.count(SurveyResponse.id)).where(SurveyResponse.survey_id.in_([row.id for row in rows]))
        .group_by(SurveyResponse.survey_id))).all()) if rows else {}
    names = {user.id: f"{user.first_name} {user.last_name}" for user in (await db.execute(select(User).where(User.id.in_([row.created_by for row in rows])))).scalars()} if rows else {}
    return success_response([{**service.survey_data(row, counts.get(row.id, 0)), "created_by_name": names.get(row.created_by)} for row in rows])


@router.post("/surveys")
async def create_survey(survey: SurveyCreate, db: AsyncSession = Depends(get_db, scope="function"), tenant: TenantContext = Depends(PermissionChecker("surveys.write"))):
    row = Survey(**survey.model_dump(exclude={"organization_id"}), organization_id=await form_organization(db, tenant, survey.organization_id), created_by=tenant.user_id, status="DRAFT")
    db.add(row); await db.commit(); await db.refresh(row)
    return success_response(service.survey_data(row))


@router.put("/surveys/{survey_id}")
async def edit_survey(survey_id: UUID, survey: SurveyCreate, db: AsyncSession = Depends(get_db, scope="function"), tenant: TenantContext = Depends(PermissionChecker("surveys.write"))):
    row = await service.lock(db, survey_id); await require_editable(db, row)
    if survey.organization_id and survey.organization_id != row.organization_id:
        raise ValidationException("Anketin kurumu değiştirilemez")
    for field, value in survey.model_dump(exclude={"organization_id"}).items():
        setattr(row, field, value)
    await db.commit(); await db.refresh(row)
    return success_response(service.survey_data(row))


@router.get("/surveys/{survey_id}")
async def get_survey(survey_id: UUID, db: AsyncSession = Depends(get_db, scope="function"), tenant: TenantContext = Depends(PermissionChecker("surveys.read"))):
    return success_response(service.survey_data(await service.get(db, survey_id)))


@router.post("/surveys/{survey_id}/publish")
async def publish(survey_id: UUID, db: AsyncSession = Depends(get_db, scope="function"), tenant: TenantContext = Depends(PermissionChecker("surveys.write"))):
    row = await service.lock(db, survey_id)
    if row.status == "ACTIVE":
        return success_response(service.survey_data(row))
    await require_editable(db, row)
    items = await service.questions(db, row.id)
    if not items or row.end_date < school_today() or row.start_date > row.end_date or row.target_audience not in {"PARENTS", "STAFF", "ALL"}:
        raise ValidationException("Yayımlamak için geçerli tarihler, hedef kitle ve en az bir soru gerekir")
    for item in items:
        try:
            SurveyQuestionCreate(survey_id=row.id, question_text=item.question_text, question_type=item.question_type,
                options=item.options, is_required=item.is_required, order_index=item.order_index)
        except ValueError as error:
            raise ValidationException("Ankette geçersiz eski soru var; soruyu düzeltip yeniden yayımlayın") from error
    row.status = "ACTIVE"; await db.commit()
    return success_response(service.survey_data(row))


@router.post("/surveys/{survey_id}/close")
async def close(survey_id: UUID, db: AsyncSession = Depends(get_db, scope="function"), tenant: TenantContext = Depends(PermissionChecker("surveys.write"))):
    row = await service.lock(db, survey_id)
    if row.status == "DRAFT":
        raise ConflictException("Taslak anket henüz yayımlanmadı")
    row.status = "CLOSED"; await db.commit()
    return success_response(service.survey_data(row))


@router.get("/questions")
async def questions(survey_id: UUID | None = None, limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0),
                    db: AsyncSession = Depends(get_db, scope="function"), tenant: TenantContext = Depends(PermissionChecker("surveys.read"))):
    query = select(SurveyQuestion)
    if survey_id:
        await service.get(db, survey_id)
        query = query.where(SurveyQuestion.survey_id == survey_id)
    rows = (await db.execute(query.order_by(SurveyQuestion.order_index, SurveyQuestion.id).limit(limit).offset(offset))).scalars().all()
    return success_response([service.question_data(row) for row in rows])


@router.post("/questions")
async def create_question(question: SurveyQuestionCreate, db: AsyncSession = Depends(get_db, scope="function"), tenant: TenantContext = Depends(PermissionChecker("surveys.write"))):
    survey = await service.lock(db, question.survey_id); await require_editable(db, survey)
    if len(await service.questions(db, survey.id)) >= 100:
        raise ValidationException("Bir ankette en fazla 100 soru bulunabilir")
    row = SurveyQuestion(**question.model_dump()); db.add(row); await db.commit(); await db.refresh(row)
    return success_response(service.question_data(row))


@router.delete("/questions/{question_id}")
async def delete_question(question_id: UUID, db: AsyncSession = Depends(get_db, scope="function"), tenant: TenantContext = Depends(PermissionChecker("surveys.write"))):
    question = (await db.execute(select(SurveyQuestion).where(SurveyQuestion.id == question_id))).scalar_one_or_none()
    if question is None:
        raise NotFoundException("Soru bulunamadı")
    survey = await service.lock(db, question.survey_id); await require_editable(db, survey)
    await db.execute(delete(SurveyQuestion).where(SurveyQuestion.id == question_id)); await db.commit()
    return success_response({"id": str(question_id)})


@router.get("/responses")
async def responses(survey_id: UUID | None = None, respondent_id: UUID | None = None, limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0),
                    db: AsyncSession = Depends(get_db, scope="function"), tenant: TenantContext = Depends(PermissionChecker("surveys.read"))):
    return success_response(await service.responses(db, survey_id, respondent_id, limit, offset))


@router.post("/responses")
async def respond(response: SurveyResponseCreate, db: AsyncSession = Depends(get_db, scope="function"), tenant: TenantContext = Depends(PermissionChecker("surveys.write", "surveys.respond"))):
    result = await service.respond(db, response.survey_id, tenant.user_id, response.response_data, staff_only=not tenant.has_permission("surveys.write"))
    await db.commit()
    return success_response(result)


@router.get("/surveys/{survey_id}/results")
async def results(survey_id: UUID, db: AsyncSession = Depends(get_db, scope="function"), tenant: TenantContext = Depends(PermissionChecker("surveys.read"))):
    return success_response(await service.results(db, survey_id))
