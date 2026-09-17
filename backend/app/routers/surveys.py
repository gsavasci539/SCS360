"""
Anket & Geri Bildirim Sistemi Module API
Handles surveys, questions, and responses
"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.responses import success_response
from app.core.security import PermissionChecker, TenantContext
from app.domain.entities import User

router = APIRouter(prefix="/api/surveys", tags=["Surveys"])


# ==================== Schemas ====================

class SurveyCreate(BaseModel):
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    target_audience: Optional[str] = None
    start_date: date = Field(..., description="Survey start date")
    end_date: date = Field(..., description="Survey end date")
    is_anonymous: bool = Field(default=False)

class SurveyQuestionCreate(BaseModel):
    survey_id: UUID
    question_text: str = Field(..., description="Question text")
    question_type: str = Field(..., description="MULTIPLE_CHOICE, RATING, TEXT")
    options: Optional[List[str]] = None
    is_required: bool = Field(default=True)
    order_index: int = Field(default=0)

class SurveyResponseCreate(BaseModel):
    survey_id: UUID
    response_data: Dict[str, Any] = Field(..., description="Response data as JSON")
    ip_address: Optional[str] = None


# ==================== Surveys Endpoints ====================

@router.get("/surveys")
async def get_surveys(
    status: Optional[str] = Query(None),
    target_audience: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("surveys.read"))
):
    """Get surveys with filtering"""
    from app.domain.entities.surveys import Survey
    
    query = select(Survey)
    
    conditions = []
    if status:
        conditions.append(Survey.status == status.upper())
    if target_audience:
        conditions.append(Survey.target_audience == target_audience)
    if start_date:
        conditions.append(Survey.start_date >= start_date)
    if end_date:
        conditions.append(Survey.end_date <= end_date)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(Survey.start_date.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    surveys = result.scalars().all()
    
    enriched_surveys = []
    for survey in surveys:
        # Get created by name
        created_by_name = None
        if survey.created_by:
            user_result = await db.execute(
                select(User).where(User.id == survey.created_by)
            )
            user = user_result.scalar_one_or_none()
            if user:
                created_by_name = f"{user.first_name} {user.last_name}"
        
        # Get response count
        from app.domain.entities.surveys import SurveyResponse
        response_result = await db.execute(
            select(func.count(SurveyResponse.id)).where(SurveyResponse.survey_id == survey.id)
        )
        response_count = response_result.scalar() or 0
        
        enriched_surveys.append({
            "id": str(survey.id),
            "title": survey.title,
            "description": survey.description,
            "target_audience": survey.target_audience,
            "start_date": survey.start_date.isoformat(),
            "end_date": survey.end_date.isoformat(),
            "is_anonymous": survey.is_anonymous,
            "status": survey.status,
            "response_count": response_count,
            "created_by": str(survey.created_by),
            "created_by_name": created_by_name,
            "created_at": survey.created_at.isoformat()
        })
    
    return success_response(enriched_surveys)


@router.post("/surveys")
async def create_survey(
    survey: SurveyCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("surveys.write"))
):
    """Create a new survey"""
    from app.domain.entities.surveys import Survey
    
    new_survey = Survey(
        title=survey.title,
        description=survey.description,
        target_audience=survey.target_audience,
        start_date=survey.start_date,
        end_date=survey.end_date,
        is_anonymous=survey.is_anonymous,
        status="DRAFT",
        created_by=None  # Will be set from current user context
    )
    db.add(new_survey)
    await db.commit()
    await db.refresh(new_survey)
    
    return success_response({
        "id": str(new_survey.id),
        "title": new_survey.title,
        "status": new_survey.status,
        "created_at": new_survey.created_at.isoformat()
    })


@router.put("/surveys/{survey_id}")
async def update_survey(
    survey_id: UUID,
    survey: SurveyCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("surveys.write"))
):
    """Update a survey"""
    from app.domain.entities.surveys import Survey
    
    result = await db.execute(
        select(Survey).where(Survey.id == survey_id)
    )
    existing_survey = result.scalar_one_or_none()
    
    if not existing_survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    
    existing_survey.title = survey.title
    existing_survey.description = survey.description
    existing_survey.target_audience = survey.target_audience
    existing_survey.start_date = survey.start_date
    existing_survey.end_date = survey.end_date
    existing_survey.is_anonymous = survey.is_anonymous
    
    await db.commit()
    
    return success_response({
        "id": str(existing_survey.id),
        "updated_at": existing_survey.updated_at.isoformat()
    })


@router.post("/surveys/{survey_id}/publish")
async def publish_survey(
    survey_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("surveys.write"))
):
    """Publish a survey"""
    from app.domain.entities.surveys import Survey
    
    result = await db.execute(
        select(Survey).where(Survey.id == survey_id)
    )
    survey = result.scalar_one_or_none()
    
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    
    survey.status = "ACTIVE"
    
    await db.commit()
    
    return success_response({
        "id": str(survey.id),
        "status": "ACTIVE"
    })


# ==================== Survey Questions Endpoints ====================

@router.get("/questions")
async def get_survey_questions(
    survey_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("surveys.read"))
):
    """Get survey questions"""
    from app.domain.entities.surveys import SurveyQuestion
    
    query = select(SurveyQuestion)
    
    if survey_id:
        query = query.where(SurveyQuestion.survey_id == survey_id)
    
    query = query.order_by(SurveyQuestion.order_index)
    
    result = await db.execute(query)
    questions = result.scalars().all()
    
    enriched_questions = []
    for question in questions:
        enriched_questions.append({
            "id": str(question.id),
            "survey_id": str(question.survey_id),
            "question_text": question.question_text,
            "question_type": question.question_type,
            "options": question.options,
            "is_required": question.is_required,
            "order_index": question.order_index,
            "created_at": question.created_at.isoformat()
        })
    
    return success_response(enriched_questions)


@router.post("/questions")
async def create_survey_question(
    question: SurveyQuestionCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("surveys.write"))
):
    """Create a new survey question"""
    from app.domain.entities.surveys import SurveyQuestion
    
    new_question = SurveyQuestion(
        survey_id=question.survey_id,
        question_text=question.question_text,
        question_type=question.question_type.upper(),
        options=question.options,
        is_required=question.is_required,
        order_index=question.order_index
    )
    db.add(new_question)
    await db.commit()
    await db.refresh(new_question)
    
    return success_response({
        "id": str(new_question.id),
        "question_type": new_question.question_type,
        "order_index": new_question.order_index,
        "created_at": new_question.created_at.isoformat()
    })


# ==================== Survey Responses Endpoints ====================

@router.get("/responses")
async def get_survey_responses(
    survey_id: Optional[UUID] = Query(None),
    respondent_id: Optional[UUID] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("surveys.read"))
):
    """Get survey responses with filtering"""
    from app.domain.entities.surveys import SurveyResponse
    
    query = select(SurveyResponse)
    
    conditions = []
    if survey_id:
        conditions.append(SurveyResponse.survey_id == survey_id)
    if respondent_id:
        conditions.append(SurveyResponse.respondent_id == respondent_id)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(SurveyResponse.submitted_at.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    responses = result.scalars().all()
    
    enriched_responses = []
    for response in responses:
        # Get respondent name
        respondent_name = None
        if response.respondent_id and not response.survey.is_anonymous:
            user_result = await db.execute(
                select(User).where(User.id == response.respondent_id)
            )
            user = user_result.scalar_one_or_none()
            if user:
                respondent_name = f"{user.first_name} {user.last_name}"
        
        enriched_responses.append({
            "id": str(response.id),
            "survey_id": str(response.survey_id),
            "respondent_id": str(response.respondent_id) if response.respondent_id else None,
            "respondent_name": respondent_name,
            "response_data": response.response_data,
            "submitted_at": response.submitted_at.isoformat(),
            "ip_address": str(response.ip_address) if response.ip_address else None,
            "created_at": response.created_at.isoformat()
        })
    
    return success_response(enriched_responses)


@router.post("/responses")
async def create_survey_response(
    response: SurveyResponseCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("surveys.write"))
):
    """Create a new survey response"""
    from app.domain.entities.surveys import SurveyResponse, Survey
    
    # Check if survey is active
    survey_result = await db.execute(
        select(Survey).where(Survey.id == response.survey_id)
    )
    survey = survey_result.scalar_one_or_none()
    
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    
    if survey.status != "ACTIVE":
        raise HTTPException(status_code=400, detail="Survey is not active")
    
    new_response = SurveyResponse(
        survey_id=response.survey_id,
        respondent_id=None,  # Will be set from current user context
        response_data=response.response_data,
        ip_address=response.ip_address
    )
    db.add(new_response)
    await db.commit()
    await db.refresh(new_response)
    
    return success_response({
        "id": str(new_response.id),
        "submitted_at": new_response.submitted_at.isoformat()
    })


@router.get("/surveys/{survey_id}/results")
async def get_survey_results(
    survey_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("surveys.read"))
):
    """Get survey results with statistical aggregation"""
    from app.domain.entities.surveys import SurveyQuestion, SurveyResponse
    
    # Get questions
    questions_result = await db.execute(
        select(SurveyQuestion).where(SurveyQuestion.survey_id == survey_id).order_by(SurveyQuestion.order_index)
    )
    questions = questions_result.scalars().all()
    
    # Get all responses
    responses_result = await db.execute(
        select(SurveyResponse).where(SurveyResponse.survey_id == survey_id)
    )
    responses = responses_result.scalars().all()
    
    # Calculate statistics
    results = []
    for question in questions:
        question_key = str(question.id)
        
        if question.question_type == "RATING":
            ratings = []
            for response in responses:
                if question_key in response.response_data:
                    try:
                        ratings.append(float(response.response_data[question_key]))
                    except (ValueError, TypeError):
                        pass
            
            if ratings:
                avg_rating = sum(ratings) / len(ratings)
                results.append({
                    "question_id": str(question.id),
                    "question_text": question.question_text,
                    "question_type": question.question_type,
                    "response_count": len(ratings),
                    "average_rating": round(avg_rating, 2),
                    "min_rating": min(ratings),
                    "max_rating": max(ratings)
                })
            else:
                results.append({
                    "question_id": str(question.id),
                    "question_text": question.question_text,
                    "question_type": question.question_type,
                    "response_count": 0
                })
        
        elif question.question_type == "MULTIPLE_CHOICE":
            option_counts = {}
            for response in responses:
                if question_key in response.response_data:
                    selected_option = response.response_data[question_key]
                    option_counts[selected_option] = option_counts.get(selected_option, 0) + 1
            
            results.append({
                "question_id": str(question.id),
                "question_text": question.question_text,
                "question_type": question.question_type,
                "response_count": sum(option_counts.values()),
                "option_counts": option_counts
            })
        
        else:  # TEXT
            results.append({
                "question_id": str(question.id),
                "question_text": question.question_text,
                "question_type": question.question_type,
                "response_count": len(responses)
            })
    
    return success_response({
        "survey_id": str(survey_id),
        "total_responses": len(responses),
        "question_results": results
    })
