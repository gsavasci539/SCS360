"""Validated forms, real results and private duplicate participation checks."""
from math import isfinite

from sqlalchemy import exists, func, select, update

from app.application.services.consent_service import utc_iso
from app.application.services.parent_data_service import child
from app.core.dates import school_today
from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.domain.entities.surveys import Survey, SurveyQuestion, SurveyResponse, SurveyParticipation
from app.infrastructure.models.models import User


def survey_data(row, response_count=0):
    return {"id": str(row.id), "organization_id": str(row.organization_id) if row.organization_id else None,
        "title": row.title, "description": row.description, "target_audience": row.target_audience,
        "start_date": row.start_date.isoformat(), "end_date": row.end_date.isoformat(),
        "is_anonymous": row.is_anonymous, "status": row.status, "response_count": response_count,
        "created_by": str(row.created_by), "created_at": utc_iso(row.created_at)}


def question_data(row):
    return {"id": str(row.id), "survey_id": str(row.survey_id), "question_text": row.question_text,
        "question_type": row.question_type, "options": row.options, "is_required": row.is_required, "order_index": row.order_index}


async def get(db, identifier):
    row = (await db.execute(select(Survey).where(Survey.id == identifier))).scalar_one_or_none()
    if row is None:
        raise NotFoundException("Anket bulunamadı")
    return row


async def lock(db, identifier):
    result = await db.execute(update(Survey).where(Survey.id == identifier).values(status=Survey.status)
        .execution_options(synchronize_session=False))
    if result.rowcount != 1:
        raise NotFoundException("Anket bulunamadı")
    return (await db.execute(select(Survey).where(Survey.id == identifier).execution_options(populate_existing=True))).scalar_one()


def require_draft(survey):
    if survey.status != "DRAFT":
        raise ConflictException("Yayımlanmış anketin soruları ve koşulları değiştirilemez; yeni bir anket oluşturun")


async def questions(db, survey_id):
    return (await db.execute(select(SurveyQuestion).where(SurveyQuestion.survey_id == survey_id)
        .order_by(SurveyQuestion.order_index, SurveyQuestion.id))).scalars().all()


def validate_answer(question, value):
    if question.question_type == "RATING":
        return type(value) in (int, float) and 1 <= value <= 5 and isfinite(value) and int(value) == value
    if question.question_type == "MULTIPLE_CHOICE":
        return isinstance(value, str) and isinstance(question.options, list) and value in question.options
    if question.question_type == "TEXT":
        return isinstance(value, str) and bool(value.strip()) and len(value) <= 2000
    return False


async def respond(db, survey_id, actor_id, answers, *, parent_user=None, student_id=None, staff_only=False):
    if parent_user is not None:
        _, student = await child(db, parent_user, student_id)
    survey = await lock(db, survey_id)
    if staff_only and survey.target_audience not in {"STAFF", "ALL"}:
        raise NotFoundException("Personel katılımına açık anket bulunamadı")
    if parent_user is not None and (survey.organization_id != student.organization_id or survey.target_audience not in {"PARENTS", "ALL"}):
        raise NotFoundException("Veli katılımına açık anket bulunamadı")
    if survey.status != "ACTIVE" or not survey.start_date <= school_today() <= survey.end_date:
        raise ConflictException("Anket şu anda yanıta açık değil")
    items = await questions(db, survey.id)
    if not items:
        raise ConflictException("Anketin yayımlanmış sorusu yok")
    keys = {str(row.id) for row in items}
    if not set(answers).issubset(keys):
        raise ValidationException("Ankete ait olmayan soru gönderildi")
    clean = {}
    for question in items:
        value = answers.get(str(question.id))
        if value is None or value == "":
            if question.is_required:
                raise ValidationException("Zorunlu sorular yanıtlanmalıdır")
            continue
        if not validate_answer(question, value):
            raise ValidationException("Yanıt soru türüne uygun değil; puanlar 1–5 arasında tam sayı olmalıdır")
        clean[str(question.id)] = value.strip() if isinstance(value, str) else value
    participation = exists().where(SurveyParticipation.survey_id == survey.id, SurveyParticipation.user_id == actor_id)
    legacy_response = exists().where(SurveyResponse.survey_id == survey.id, SurveyResponse.respondent_id == actor_id)
    if (await db.execute(select(participation | legacy_response))).scalar():
        raise ConflictException("Bu ankete daha önce katıldınız")
    db.add(SurveyParticipation(survey_id=survey.id, user_id=actor_id))
    response = SurveyResponse(survey_id=survey.id, respondent_id=None if survey.is_anonymous else actor_id,
        response_data=clean, ip_address=None)
    db.add(response)
    await db.flush()
    return {"id": str(response.id), "submitted_at": utc_iso(response.submitted_at)}


async def available(db, organization_id, user_id, audience, limit, offset):
    surveys = (await db.execute(select(Survey).where(Survey.organization_id == organization_id,
        Survey.target_audience.in_([audience, "ALL"]), Survey.status == "ACTIVE",
        Survey.start_date <= school_today(), Survey.end_date >= school_today())
        .order_by(Survey.start_date.desc(), Survey.id).limit(limit).offset(offset))).scalars().all()
    ids = [row.id for row in surveys]
    submitted = set((await db.execute(select(SurveyParticipation.survey_id).where(SurveyParticipation.survey_id.in_(ids), SurveyParticipation.user_id == user_id))).scalars()) if ids else set()
    submitted |= set((await db.execute(select(SurveyResponse.survey_id).where(SurveyResponse.survey_id.in_(ids), SurveyResponse.respondent_id == user_id))).scalars()) if ids else set()
    items = (await db.execute(select(SurveyQuestion).where(SurveyQuestion.survey_id.in_(ids))
        .order_by(SurveyQuestion.order_index, SurveyQuestion.id))).scalars().all() if ids else []
    grouped = {}
    for question in items:
        grouped.setdefault(question.survey_id, []).append(question_data(question))
    return [{**survey_data(row), "submitted": row.id in submitted, "questions": grouped.get(row.id, [])} for row in surveys]


async def parent_surveys(db, user, student_id, limit, offset):
    _, student = await child(db, user, student_id)
    return await available(db, student.organization_id, user.id, "PARENTS", limit, offset)


async def responses(db, survey_id, respondent_id, limit, offset):
    query = select(SurveyResponse).join(Survey, Survey.id == SurveyResponse.survey_id)
    if survey_id:
        query = query.where(SurveyResponse.survey_id == survey_id)
    if respondent_id:
        query = query.where(SurveyResponse.respondent_id == respondent_id, Survey.is_anonymous.is_(False))
    rows = (await db.execute(query.order_by(SurveyResponse.submitted_at.desc(), SurveyResponse.id).limit(limit).offset(offset))).scalars().all()
    surveys = {row.id: row for row in (await db.execute(select(Survey).where(Survey.id.in_([row.survey_id for row in rows])))).scalars()} if rows else {}
    identities = [row.respondent_id for row in rows if row.respondent_id and not surveys[row.survey_id].is_anonymous]
    names = {row.id: f"{row.first_name} {row.last_name}" for row in (await db.execute(select(User).where(User.id.in_(identities)))).scalars()} if identities else {}
    items = (await db.execute(select(SurveyQuestion).where(SurveyQuestion.survey_id.in_(list(surveys))))).scalars().all() if surveys else []
    labels = {str(question.id): question.question_text for question in items}
    def safe_answers(row):
        values = row.response_data if isinstance(row.response_data, dict) else {}
        # Historical SQLite JSON may contain NaN/Infinity, which JSONResponse
        # cannot serialize. Preserve the DB and flag unsupported old answers.
        return {key: value if isinstance(value, (str, int, float, bool)) and not (isinstance(value, float) and not isfinite(value)) else None for key, value in values.items()}
    return [{"id": str(row.id), "survey_id": str(row.survey_id), "survey_title": surveys[row.survey_id].title,
        "is_anonymous": surveys[row.survey_id].is_anonymous,
        "respondent_id": str(row.respondent_id) if row.respondent_id and not surveys[row.survey_id].is_anonymous else None,
        "respondent_name": names.get(row.respondent_id) if not surveys[row.survey_id].is_anonymous else None,
        "response_data": safe_answers(row), "answers": [{"question_text": labels.get(key, "Eski soru"), "value": value} for key, value in safe_answers(row).items()],
        "submitted_at": utc_iso(row.submitted_at), "created_at": utc_iso(row.created_at)} for row in rows]


async def results(db, survey_id):
    survey = await get(db, survey_id)
    items = await questions(db, survey.id)
    rows = (await db.execute(select(SurveyResponse).where(SurveyResponse.survey_id == survey.id))).scalars().all()
    result = []
    for question in items:
        values = [row.response_data.get(str(question.id)) for row in rows if isinstance(row.response_data, dict)]
        valid = [value for value in values if validate_answer(question, value)]
        entry = {**question_data(question), "question_id": str(question.id), "response_count": len(valid),
            "invalid_count": sum(value is not None and value != "" and not validate_answer(question, value) for value in values)}
        if question.question_type == "RATING" and valid:
            entry.update(average_rating=round(sum(valid) / len(valid), 2), min_rating=min(valid), max_rating=max(valid))
        elif question.question_type == "MULTIPLE_CHOICE":
            entry["option_counts"] = {option: valid.count(option) for option in question.options or [] if isinstance(option, str)} if isinstance(question.options, list) else {}
        result.append(entry)
    return {"survey_id": str(survey.id), "total_responses": len(rows), "question_results": result}


async def summary(db):
    counts = dict((await db.execute(select(Survey.status, func.count(Survey.id)).group_by(Survey.status))).all())
    return {"total_surveys": sum(counts.values()), "active_surveys": counts.get("ACTIVE", 0), "draft_surveys": counts.get("DRAFT", 0),
        "total_responses": (await db.execute(select(func.count(SurveyResponse.id)))).scalar() or 0}
