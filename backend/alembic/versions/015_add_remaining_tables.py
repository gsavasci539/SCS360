"""Add remaining entity tables to database"""

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from alembic import op
    from app.core.database import Base
    # Revision 002 may already have created these tables on a clean install.
    # Use the canonical UUID types on both PostgreSQL and SQLite.
    names = ["health_records","medication_schedules","medication_logs","infirmary_visits","guidance_sessions","behavioral_incidents","guidance_notes","pickup_authorizations","pickup_logs","exams","exam_results","report_cards","course_materials","digital_id_tokens","gate_logs","sms_providers","broadcast_jobs","delivery_reports","branch_financial_summary","branch_academic_summary","tutoring_sessions","tutoring_requests","teacher_availability","school_clubs","club_memberships","club_events","student_certificates","staff_timesheets","additional_course_hours","payroll_records","inventory_items","inventory_locations","asset_assignments","maintenance_requests","surveys","survey_questions","survey_responses","consent_documents","student_consents"]
    Base.metadata.create_all(bind=op.get_bind(), tables=[Base.metadata.tables[name] for name in names], checkfirst=True)


def downgrade() -> None:
    from alembic import op

    # Drop in reverse order of creation (due to foreign key dependencies)
    op.drop_table('student_consents')
    op.drop_table('consent_documents')
    
    op.drop_table('survey_responses')
    op.drop_table('survey_questions')
    op.drop_table('surveys')
    
    op.drop_table('maintenance_requests')
    op.drop_table('asset_assignments')
    op.drop_table('inventory_locations')
    op.drop_table('inventory_items')
    
    op.drop_table('payroll_records')
    op.drop_table('additional_course_hours')
    op.drop_table('staff_timesheets')
    
    op.drop_table('student_certificates')
    op.drop_table('club_events')
    op.drop_table('club_memberships')
    op.drop_table('school_clubs')
    
    op.drop_table('teacher_availability')
    op.drop_table('tutoring_requests')
    op.drop_table('tutoring_sessions')
    
    op.drop_table('branch_academic_summary')
    op.drop_table('branch_financial_summary')
    
    op.drop_table('delivery_reports')
    op.drop_table('broadcast_jobs')
    op.drop_table('sms_providers')
    
    op.drop_table('gate_logs')
    op.drop_table('digital_id_tokens')
    
    op.drop_table('course_materials')
    
    op.drop_table('report_cards')
    op.drop_table('exam_results')
    op.drop_table('exams')
    
    op.drop_table('pickup_logs')
    op.drop_table('pickup_authorizations')
    
    op.drop_table('guidance_notes')
    op.drop_table('behavioral_incidents')
    op.drop_table('guidance_sessions')
    
    op.drop_table('infirmary_visits')
    op.drop_table('medication_logs')
    op.drop_table('medication_schedules')
    op.drop_table('health_records')
