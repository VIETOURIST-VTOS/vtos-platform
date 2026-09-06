"""Hồ sơ nhân sự, hợp đồng lao động, người phụ thuộc, đơn từ, chấm công (phân hệ Nhân sự theo MISA)

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
"""
from alembic import op
import sqlalchemy as sa

revision = "a7b8c9d0e1f2"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "employee_profiles",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("employee_id", sa.Integer, sa.ForeignKey("employees.id"), nullable=False, unique=True, index=True),
        sa.Column("dob", sa.Date, nullable=True),
        sa.Column("gender", sa.String(10), nullable=False, server_default=""),
        sa.Column("id_number", sa.String(20), nullable=False, server_default=""),
        sa.Column("id_issued_on", sa.Date, nullable=True),
        sa.Column("id_issued_by", sa.String(120), nullable=False, server_default=""),
        sa.Column("permanent_address", sa.String(300), nullable=False, server_default=""),
        sa.Column("current_address", sa.String(300), nullable=False, server_default=""),
        sa.Column("phone", sa.String(30), nullable=False, server_default=""),
        sa.Column("email", sa.String(120), nullable=False, server_default=""),
        sa.Column("tax_code", sa.String(20), nullable=False, server_default=""),
        sa.Column("social_insurance_no", sa.String(20), nullable=False, server_default=""),
        sa.Column("bank_account", sa.String(40), nullable=False, server_default=""),
        sa.Column("bank_name", sa.String(120), nullable=False, server_default=""),
        sa.Column("marital_status", sa.String(20), nullable=False, server_default=""),
        sa.Column("education", sa.String(120), nullable=False, server_default=""),
        sa.Column("emergency_contact", sa.String(160), nullable=False, server_default=""),
        sa.Column("note", sa.String(300), nullable=False, server_default=""),
        sa.Column("updated_by", sa.String(50), nullable=False, server_default=""),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )
    op.create_table(
        "labor_contracts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("employee_id", sa.Integer, sa.ForeignKey("employees.id"), nullable=False, index=True),
        sa.Column("code", sa.String(40), nullable=False, unique=True, index=True),
        sa.Column("kind", sa.String(20), nullable=False, server_default="xac_dinh_12"),
        sa.Column("signed_on", sa.Date, nullable=True),
        sa.Column("effective_from", sa.Date, nullable=False),
        sa.Column("effective_to", sa.Date, nullable=True),
        sa.Column("salary", sa.Float, nullable=False, server_default="0"),
        sa.Column("si_salary", sa.Float, nullable=False, server_default="0"),
        sa.Column("allowance", sa.Float, nullable=False, server_default="0"),
        sa.Column("annual_leave_days", sa.Float, nullable=False, server_default="12"),
        sa.Column("status", sa.String(20), nullable=False, server_default="hieu_luc"),
        sa.Column("terminated_on", sa.Date, nullable=True),
        sa.Column("terminate_reason", sa.String(300), nullable=False, server_default=""),
        sa.Column("note", sa.String(300), nullable=False, server_default=""),
        sa.Column("created_by", sa.String(50), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime, nullable=True),
    )
    op.create_table(
        "dependents",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("employee_id", sa.Integer, sa.ForeignKey("employees.id"), nullable=False, index=True),
        sa.Column("full_name", sa.String(120), nullable=False),
        sa.Column("relation", sa.String(20), nullable=False, server_default="con"),
        sa.Column("dob", sa.Date, nullable=True),
        sa.Column("tax_code", sa.String(20), nullable=False, server_default=""),
        sa.Column("id_number", sa.String(20), nullable=False, server_default=""),
        sa.Column("from_period", sa.String(7), nullable=False, server_default=""),
        sa.Column("to_period", sa.String(7), nullable=False, server_default=""),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("note", sa.String(200), nullable=False, server_default=""),
        sa.Column("created_by", sa.String(50), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime, nullable=True),
    )
    op.create_table(
        "leave_requests",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("employee_id", sa.Integer, sa.ForeignKey("employees.id"), nullable=False, index=True),
        sa.Column("kind", sa.String(20), nullable=False, server_default="phep_nam"),
        sa.Column("date_from", sa.Date, nullable=False, index=True),
        sa.Column("date_to", sa.Date, nullable=False),
        sa.Column("days", sa.Float, nullable=False, server_default="1"),
        sa.Column("ot_hours", sa.Float, nullable=False, server_default="0"),
        sa.Column("reason", sa.String(300), nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default="cho_duyet"),
        sa.Column("approved_by", sa.String(50), nullable=False, server_default=""),
        sa.Column("approved_at", sa.DateTime, nullable=True),
        sa.Column("decision_note", sa.String(300), nullable=False, server_default=""),
        sa.Column("created_by", sa.String(50), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime, nullable=True),
    )
    op.create_table(
        "attendance_days",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("employee_id", sa.Integer, sa.ForeignKey("employees.id"), nullable=False, index=True),
        sa.Column("day", sa.Date, nullable=False, index=True),
        sa.Column("kind", sa.String(20), nullable=False, server_default="lam_viec"),
        sa.Column("work", sa.Float, nullable=False, server_default="1"),
        sa.Column("ot_hours", sa.Float, nullable=False, server_default="0"),
        sa.Column("leave_id", sa.Integer, sa.ForeignKey("leave_requests.id"), nullable=True),
        sa.Column("note", sa.String(200), nullable=False, server_default=""),
        sa.Column("updated_by", sa.String(50), nullable=False, server_default=""),
        sa.Column("updated_at", sa.DateTime, nullable=True),
        sa.UniqueConstraint("employee_id", "day", name="uq_attendance_emp_day"),
    )


def downgrade():
    op.drop_table("attendance_days")
    op.drop_table("leave_requests")
    op.drop_table("dependents")
    op.drop_table("labor_contracts")
    op.drop_table("employee_profiles")
