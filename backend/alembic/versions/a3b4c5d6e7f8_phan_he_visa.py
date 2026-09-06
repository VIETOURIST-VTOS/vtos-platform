"""Phân hệ Visa: hồ sơ, nhóm gia đình, form, checklist, tài liệu, ngoại lệ, công việc, lịch hẹn, kết quả, bàn giao

Revision ID: a3b4c5d6e7f8
Revises: f2b3c4d5e6f7
"""
from alembic import op
import sqlalchemy as sa

revision = "a3b4c5d6e7f8"
down_revision = "f2b3c4d5e6f7"
branch_labels = None
depends_on = None

TABLES = ["visa_ai_suggestions", "visa_access_links", "visa_handovers", "visa_results", "visa_appointments",
          "visa_applications", "visa_tasks", "visa_waiver_requests", "visa_document_reviews",
          "visa_document_versions", "visa_checklist_items", "visa_checklist_templates",
          "visa_customer_confirmations", "visa_form_versions", "visa_cases", "visa_family_groups",
          "visa_markets"]


def upgrade():
    op.create_table(
        "visa_markets",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("code", sa.String(20), nullable=False, unique=True, index=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("visa_types", sa.JSON, nullable=True),
        sa.Column("requires_biometrics", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("requires_appointment", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("skip_stages", sa.JSON, nullable=True),
        sa.Column("sla_hours", sa.JSON, nullable=True),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "visa_family_groups",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("code", sa.String(30), nullable=False, unique=True, index=True),
        sa.Column("company_id", sa.Integer, nullable=True, index=True),
        sa.Column("name", sa.String(160), nullable=False, server_default=""),
        sa.Column("contact_name", sa.String(120), nullable=False, server_default=""),
        sa.Column("contact_phone", sa.String(30), nullable=False, server_default=""),
        sa.Column("contact_email", sa.String(120), nullable=False, server_default=""),
        sa.Column("main_case_id", sa.Integer, nullable=True),
        sa.Column("booking_id", sa.Integer, nullable=True),
        sa.Column("contact_sees_members", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_by", sa.String(50), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime, nullable=True),
    )
    op.create_table(
        "visa_cases",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("case_code", sa.String(30), nullable=False, unique=True, index=True),
        sa.Column("company_id", sa.Integer, nullable=True, index=True),
        sa.Column("applicant_name", sa.String(120), nullable=False),
        sa.Column("applicant_dob", sa.Date, nullable=True),
        sa.Column("applicant_phone", sa.String(30), nullable=False, server_default=""),
        sa.Column("applicant_email", sa.String(120), nullable=False, server_default=""),
        sa.Column("passport_last4", sa.String(8), nullable=False, server_default=""),
        sa.Column("passport_expiry", sa.Date, nullable=True),
        sa.Column("booking_id", sa.Integer, nullable=True, index=True),
        sa.Column("tour_id", sa.Integer, nullable=True, index=True),
        sa.Column("family_group_id", sa.Integer, nullable=True, index=True),
        sa.Column("family_role", sa.String(40), nullable=False, server_default=""),
        sa.Column("market_code", sa.String(20), nullable=False, index=True),
        sa.Column("visa_type", sa.String(60), nullable=False, server_default=""),
        sa.Column("service_mode", sa.String(20), nullable=False, server_default="TOUR_LINKED"),
        sa.Column("departure_date", sa.Date, nullable=True, index=True),
        sa.Column("return_date", sa.Date, nullable=True),
        sa.Column("sales_user_id", sa.Integer, nullable=True, index=True),
        sa.Column("visa_owner_user_id", sa.Integer, nullable=True, index=True),
        sa.Column("supervisor_user_id", sa.Integer, nullable=True),
        sa.Column("current_stage", sa.String(30), nullable=False, server_default="tiep_nhan", index=True),
        sa.Column("lifecycle_status", sa.String(20), nullable=False, server_default="ACTIVE", index=True),
        sa.Column("result_status", sa.String(20), nullable=False, server_default="NOT_AVAILABLE", index=True),
        sa.Column("hold_reason", sa.String(200), nullable=False, server_default=""),
        sa.Column("cancellation_reason", sa.String(200), nullable=False, server_default=""),
        sa.Column("previous_case_id", sa.Integer, nullable=True),
        sa.Column("relationship_type", sa.String(20), nullable=False, server_default=""),
        sa.Column("source_system", sa.String(30), nullable=False, server_default=""),
        sa.Column("source_record_id", sa.String(60), nullable=False, server_default=""),
        sa.Column("hr_visa_file_id", sa.Integer, nullable=True),
        sa.Column("is_test", sa.Boolean, nullable=False, server_default=sa.false(), index=True),
        sa.Column("row_version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_by", sa.String(50), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )
    op.create_table(
        "visa_form_versions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("case_id", sa.Integer, nullable=False, index=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("state", sa.String(20), nullable=False, server_default="DRAFT"),
        sa.Column("data", sa.JSON, nullable=True),
        sa.Column("changed_fields", sa.JSON, nullable=True),
        sa.Column("critical_changed", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_by", sa.String(50), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime, nullable=True),
    )
    op.create_table(
        "visa_customer_confirmations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("case_id", sa.Integer, nullable=False, index=True),
        sa.Column("form_version_id", sa.Integer, nullable=False),
        sa.Column("confirmed_by_name", sa.String(120), nullable=False, server_default=""),
        sa.Column("channel", sa.String(30), nullable=False, server_default="link"),
        sa.Column("evidence", sa.String(300), nullable=False, server_default=""),
        sa.Column("access_link_id", sa.Integer, nullable=True),
        sa.Column("confirmed_at", sa.DateTime, nullable=True),
    )
    op.create_table(
        "visa_checklist_templates",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("market_code", sa.String(20), nullable=False, index=True),
        sa.Column("visa_type", sa.String(60), nullable=False, server_default=""),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("items", sa.JSON, nullable=True),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime, nullable=True),
    )
    op.create_table(
        "visa_checklist_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("case_id", sa.Integer, nullable=False, index=True),
        sa.Column("template_id", sa.Integer, nullable=True),
        sa.Column("template_version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("key", sa.String(60), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("required", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("status", sa.String(25), nullable=False, server_default="MISSING", index=True),
        sa.Column("current_document_id", sa.Integer, nullable=True),
        sa.Column("reviewed_by", sa.String(50), nullable=False, server_default=""),
        sa.Column("reviewed_at", sa.DateTime, nullable=True),
        sa.Column("note", sa.Text, nullable=False, server_default=""),
        sa.Column("needs_recheck", sa.Boolean, nullable=False, server_default=sa.false()),
    )
    op.create_table(
        "visa_document_versions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("case_id", sa.Integer, nullable=False, index=True),
        sa.Column("checklist_item_id", sa.Integer, nullable=True, index=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("file_name", sa.String(255), nullable=False, server_default=""),
        sa.Column("content_type", sa.String(100), nullable=False, server_default=""),
        sa.Column("size_bytes", sa.Integer, nullable=False, server_default="0"),
        sa.Column("checksum", sa.String(64), nullable=False, server_default="", index=True),
        sa.Column("storage_path", sa.String(400), nullable=False, server_default=""),
        sa.Column("uploaded_by", sa.String(50), nullable=False, server_default=""),
        sa.Column("uploaded_at", sa.DateTime, nullable=True),
        sa.Column("superseded_by", sa.Integer, nullable=True),
    )
    op.create_table(
        "visa_document_reviews",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("document_id", sa.Integer, nullable=False, index=True),
        sa.Column("case_id", sa.Integer, nullable=False, index=True),
        sa.Column("decision", sa.String(25), nullable=False),
        sa.Column("reason", sa.Text, nullable=False, server_default=""),
        sa.Column("reviewer", sa.String(50), nullable=False),
        sa.Column("reviewed_at", sa.DateTime, nullable=True),
    )
    op.create_table(
        "visa_waiver_requests",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("case_id", sa.Integer, nullable=False, index=True),
        sa.Column("checklist_item_id", sa.Integer, nullable=False, index=True),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("requested_by", sa.String(50), nullable=False),
        sa.Column("requested_at", sa.DateTime, nullable=True),
        sa.Column("decision", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("decided_by", sa.String(50), nullable=False, server_default=""),
        sa.Column("decided_at", sa.DateTime, nullable=True),
        sa.Column("decision_note", sa.Text, nullable=False, server_default=""),
    )
    op.create_table(
        "visa_tasks",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("case_id", sa.Integer, nullable=False, index=True),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("assignee_user_id", sa.Integer, nullable=True, index=True),
        sa.Column("collaborators", sa.JSON, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="open", index=True),
        sa.Column("priority", sa.String(10), nullable=False, server_default="thuong"),
        sa.Column("waiting_reason", sa.String(200), nullable=False, server_default=""),
        sa.Column("assigned_at", sa.DateTime, nullable=True),
        sa.Column("due_at", sa.DateTime, nullable=True, index=True),
        sa.Column("done_at", sa.DateTime, nullable=True),
        sa.Column("evidence", sa.String(300), nullable=False, server_default=""),
        sa.Column("created_by", sa.String(50), nullable=False, server_default=""),
    )
    op.create_table(
        "visa_applications",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("case_id", sa.Integer, nullable=False, index=True),
        sa.Column("reference_code", sa.String(80), nullable=False, index=True),
        sa.Column("portal", sa.String(60), nullable=False, server_default=""),
        sa.Column("form_version_id", sa.Integer, nullable=True),
        sa.Column("submitted_by", sa.String(50), nullable=False),
        sa.Column("submitted_at", sa.DateTime, nullable=True),
        sa.Column("evidence", sa.String(300), nullable=False, server_default=""),
        sa.Column("note", sa.Text, nullable=False, server_default=""),
    )
    op.create_table(
        "visa_appointments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("case_id", sa.Integer, nullable=False, index=True),
        sa.Column("starts_at", sa.DateTime, nullable=False, index=True),
        sa.Column("timezone", sa.String(40), nullable=False, server_default="Asia/Ho_Chi_Minh"),
        sa.Column("location", sa.String(200), nullable=False, server_default=""),
        sa.Column("escort", sa.String(120), nullable=False, server_default=""),
        sa.Column("confirmation_ref", sa.String(120), nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default="SCHEDULED", index=True),
        sa.Column("biometrics_done", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("biometrics_note", sa.Text, nullable=False, server_default=""),
        sa.Column("replaces_id", sa.Integer, nullable=True),
        sa.Column("reschedule_reason", sa.String(300), nullable=False, server_default=""),
        sa.Column("created_by", sa.String(50), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime, nullable=True),
    )
    op.create_table(
        "visa_results",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("case_id", sa.Integer, nullable=False, index=True),
        sa.Column("outcome", sa.String(20), nullable=False),
        sa.Column("received_on", sa.Date, nullable=False),
        sa.Column("visa_valid_from", sa.Date, nullable=True),
        sa.Column("visa_valid_to", sa.Date, nullable=True),
        sa.Column("entries", sa.String(30), nullable=False, server_default=""),
        sa.Column("refusal_reason", sa.Text, nullable=False, server_default=""),
        sa.Column("evidence", sa.String(300), nullable=False, server_default=""),
        sa.Column("recorded_by", sa.String(50), nullable=False),
        sa.Column("verified_by", sa.String(50), nullable=False, server_default=""),
        sa.Column("recorded_at", sa.DateTime, nullable=True),
    )
    op.create_table(
        "visa_handovers",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("case_id", sa.Integer, nullable=False, index=True),
        sa.Column("direction", sa.String(20), nullable=False),
        sa.Column("item_type", sa.String(60), nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False, server_default="1"),
        sa.Column("from_party", sa.String(120), nullable=False, server_default=""),
        sa.Column("to_party", sa.String(120), nullable=False, server_default=""),
        sa.Column("method", sa.String(60), nullable=False, server_default=""),
        sa.Column("happened_at", sa.DateTime, nullable=True),
        sa.Column("confirmed", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("evidence", sa.String(300), nullable=False, server_default=""),
        sa.Column("recorded_by", sa.String(50), nullable=False),
        sa.Column("note", sa.Text, nullable=False, server_default=""),
    )
    op.create_table(
        "visa_access_links",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("case_id", sa.Integer, nullable=False, index=True),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column("scopes", sa.JSON, nullable=True),
        sa.Column("expires_at", sa.DateTime, nullable=False),
        sa.Column("revoked", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("used_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_used_at", sa.DateTime, nullable=True),
        sa.Column("created_by", sa.String(50), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime, nullable=True),
    )
    op.create_table(
        "visa_ai_suggestions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("case_id", sa.Integer, nullable=False, index=True),
        sa.Column("agent", sa.String(40), nullable=False),
        sa.Column("target", sa.String(60), nullable=False, server_default=""),
        sa.Column("payload", sa.JSON, nullable=True),
        sa.Column("source_ref", sa.String(200), nullable=False, server_default=""),
        sa.Column("state", sa.String(20), nullable=False, server_default="NEW", index=True),
        sa.Column("decided_by", sa.String(50), nullable=False, server_default=""),
        sa.Column("decided_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
    )


def downgrade():
    for t in TABLES:
        op.drop_table(t)
