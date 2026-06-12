"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-06-09
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


job_status = postgresql.ENUM(
    "PENDING", "PROCESSING", "LLM_PROCESSING", "REPORTING", "COMPLETED", "FAILED", name="jobstatus"
)
job_event_type = postgresql.ENUM(
    "JOB_CREATED",
    "FILE_UPLOADED",
    "VALIDATION_STARTED",
    "VALIDATION_COMPLETED",
    "CLEANING_STARTED",
    "CLEANING_COMPLETED",
    "ANOMALY_DETECTION_STARTED",
    "ANOMALY_DETECTION_COMPLETED",
    "CLASSIFICATION_STARTED",
    "CLASSIFICATION_COMPLETED",
    "SUMMARY_GENERATION_STARTED",
    "SUMMARY_GENERATION_COMPLETED",
    "JOB_COMPLETED",
    "JOB_FAILED",
    name="jobeventtype",
)


def upgrade() -> None:
    job_status.create(op.get_bind(), checkfirst=True)
    job_event_type.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("filename", sa.String(length=512), nullable=False),
        sa.Column("storage_path", sa.String(length=1024), nullable=True),
        sa.Column("file_checksum", sa.String(length=64), nullable=True),
        sa.Column("status", job_status, nullable=False),
        sa.Column("row_count_raw", sa.Integer(), nullable=False),
        sa.Column("row_count_clean", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("llm_failed", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_jobs_created_at", "jobs", ["created_at"])
    op.create_index("ix_jobs_file_checksum", "jobs", ["file_checksum"])
    op.create_index("ix_jobs_status", "jobs", ["status"])
    op.create_table(
        "transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("txn_id", sa.String(length=255), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("merchant", sa.String(length=512), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("category", sa.String(length=255), nullable=False),
        sa.Column("account_id", sa.String(length=255), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_anomaly", sa.Boolean(), nullable=False),
        sa.Column("anomaly_reason", sa.Text(), nullable=True),
        sa.Column("risk_score", sa.Integer(), nullable=False),
        sa.Column("risk_level", sa.String(length=16), nullable=False),
        sa.Column("llm_category", sa.String(length=255), nullable=True),
        sa.Column("llm_raw_response", sa.Text(), nullable=True),
        sa.Column("llm_failed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", "fingerprint", name="uq_transactions_job_fingerprint"),
    )
    op.create_index("ix_transactions_account_id", "transactions", ["account_id"])
    op.create_index("ix_transactions_job_id", "transactions", ["job_id"])
    op.create_index("ix_transactions_merchant", "transactions", ["merchant"])

    op.create_table(
        "risk_signals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("signal_type", sa.String(length=128), nullable=False),
        sa.Column("signal_score", sa.Numeric(8, 2), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "transaction_id", "signal_type", name="uq_risk_signal_transaction_type"
        ),
    )
    op.create_index("ix_risk_signals_transaction_id", "risk_signals", ["transaction_id"])

    op.create_table(
        "job_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", job_event_type, nullable=False),
        sa.Column("domain_event_name", sa.String(length=128), nullable=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column(
            "timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", "idempotency_key", name="uq_job_events_idempotency"),
    )
    op.create_index("ix_job_events_job_id", "job_events", ["job_id"])
    op.create_index("ix_job_events_timestamp", "job_events", ["timestamp"])

    op.create_table(
        "job_summaries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("total_spend_inr", sa.Numeric(18, 2), nullable=False),
        sa.Column("total_spend_usd", sa.Numeric(18, 2), nullable=False),
        sa.Column("top_merchants", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("currency_breakdown", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("anomaly_count", sa.Integer(), nullable=False),
        sa.Column("narrative", sa.Text(), nullable=True),
        sa.Column("risk_level", sa.String(length=16), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id"),
    )
    op.create_index("ix_job_summaries_job_id", "job_summaries", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_job_summaries_job_id", table_name="job_summaries")
    op.drop_table("job_summaries")
    op.drop_index("ix_job_events_timestamp", table_name="job_events")
    op.drop_index("ix_job_events_job_id", table_name="job_events")
    op.drop_table("job_events")
    op.drop_index("ix_risk_signals_transaction_id", table_name="risk_signals")
    op.drop_table("risk_signals")
    op.drop_index("ix_transactions_merchant", table_name="transactions")
    op.drop_index("ix_transactions_job_id", table_name="transactions")
    op.drop_index("ix_transactions_account_id", table_name="transactions")
    op.drop_table("transactions")
    op.drop_index("ix_jobs_status", table_name="jobs")
    op.drop_index("ix_jobs_file_checksum", table_name="jobs")
    op.drop_index("ix_jobs_created_at", table_name="jobs")
    op.drop_table("jobs")
    job_event_type.drop(op.get_bind(), checkfirst=True)
    job_status.drop(op.get_bind(), checkfirst=True)
