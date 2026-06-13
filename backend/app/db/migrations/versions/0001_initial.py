"""Initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-13
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("avatar_url", sa.String(512), nullable=True),
        sa.Column("oauth_provider", sa.String(50), nullable=False),
        sa.Column("oauth_id", sa.String(255), nullable=False),
        sa.Column("level", sa.String(50), nullable=False, server_default="beginner"),
        sa.Column("learning_style", sa.String(50), nullable=False, server_default="practical"),
        sa.Column("goal", sa.String(50), nullable=False, server_default="general"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # topics
    op.create_table(
        "topics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("difficulty", sa.String(50), nullable=False, server_default="intermediate"),
        sa.Column("estimated_hours", sa.Float, nullable=False, server_default="2.0"),
        sa.Column("is_seed", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["parent_id"], ["topics.id"], name="fk_topics_parent_id_topics", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_topics"),
        sa.UniqueConstraint("slug", name="uq_topics_slug"),
    )
    op.create_index("ix_topics_slug", "topics", ["slug"])
    op.create_index("ix_topics_parent_id", "topics", ["parent_id"])

    # topic_dependencies
    op.create_table(
        "topic_dependencies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("prerequisite_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dependent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.Text, nullable=True),
        sa.ForeignKeyConstraint(["prerequisite_id"], ["topics.id"], name="fk_topic_dependencies_prerequisite_id_topics", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["dependent_id"], ["topics.id"], name="fk_topic_dependencies_dependent_id_topics", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_topic_dependencies"),
    )
    op.create_index("ix_topic_dependencies_prerequisite_id", "topic_dependencies", ["prerequisite_id"])
    op.create_index("ix_topic_dependencies_dependent_id", "topic_dependencies", ["dependent_id"])

    # trusted_domains
    op.create_table(
        "trusted_domains",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("domain", sa.String(255), nullable=False),
        sa.Column("base_trust_score", sa.Float, nullable=False, server_default="70.0"),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_trusted_domains"),
        sa.UniqueConstraint("domain", name="uq_trusted_domains_domain"),
    )
    op.create_index("ix_trusted_domains_domain", "trusted_domains", ["domain"])

    # resources
    op.create_table(
        "resources",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("topic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("author", sa.String(255), nullable=True),
        sa.Column("published_at", sa.Date, nullable=True),
        sa.Column("trust_score", sa.Float, nullable=False, server_default="50.0"),
        sa.Column("quality_score", sa.Float, nullable=False, server_default="50.0"),
        sa.Column("composite_score", sa.Float, nullable=False, server_default="50.0"),
        sa.Column("is_alive", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("last_checked", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resource_metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], name="fk_resources_topic_id_topics", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_resources"),
        sa.UniqueConstraint("url", name="uq_resources_url"),
    )
    op.create_index("ix_resources_topic_id", "resources", ["topic_id"])

    # resource_refresh_logs
    op.create_table(
        "resource_refresh_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("topic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("new_resources_found", sa.Integer, nullable=False, server_default="0"),
        sa.Column("stale_resources_flagged", sa.Integer, nullable=False, server_default="0"),
        sa.Column("dead_links_removed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("refreshed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], name="fk_resource_refresh_logs_topic_id_topics", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_resource_refresh_logs"),
    )
    op.create_index("ix_resource_refresh_logs_topic_id", "resource_refresh_logs", ["topic_id"])

    # generated_content
    op.create_table(
        "generated_content",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cache_key", sa.String(512), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("provider_used", sa.String(100), nullable=False),
        sa.Column("model_used", sa.String(100), nullable=False),
        sa.Column("tokens_input", sa.Integer, nullable=False, server_default="0"),
        sa.Column("tokens_output", sa.Integer, nullable=False, server_default="0"),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_generated_content"),
        sa.UniqueConstraint("cache_key", name="uq_generated_content_cache_key"),
    )
    op.create_index("ix_generated_content_cache_key", "generated_content", ["cache_key"])

    # curricula
    op.create_table(
        "curricula",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("root_topic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("level", sa.String(50), nullable=False),
        sa.Column("learning_style", sa.String(50), nullable=False),
        sa.Column("goal", sa.String(50), nullable=False),
        sa.Column("module_order", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("cache_key", sa.String(512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_curricula_user_id_users", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["root_topic_id"], ["topics.id"], name="fk_curricula_root_topic_id_topics", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_curricula"),
    )
    op.create_index("ix_curricula_user_id", "curricula", ["user_id"])
    op.create_index("ix_curricula_root_topic_id", "curricula", ["root_topic_id"])
    op.create_index("ix_curricula_cache_key", "curricula", ["cache_key"])

    # modules
    op.create_table(
        "modules",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("curriculum_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("topic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_index", sa.Integer, nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("why_next", sa.Text, nullable=True),
        sa.Column("estimated_hours", sa.Float, nullable=False, server_default="2.0"),
        sa.Column("difficulty", sa.String(50), nullable=False, server_default="intermediate"),
        sa.ForeignKeyConstraint(["curriculum_id"], ["curricula.id"], name="fk_modules_curriculum_id_curricula", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], name="fk_modules_topic_id_topics", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_modules"),
    )
    op.create_index("ix_modules_curriculum_id", "modules", ["curriculum_id"])
    op.create_index("ix_modules_topic_id", "modules", ["topic_id"])

    # artifact_shells
    op.create_table(
        "artifact_shells",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("topic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("overview", sa.Text, nullable=True),
        sa.Column("section_titles", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("cache_key", sa.String(512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], name="fk_artifact_shells_topic_id_topics", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_artifact_shells"),
        sa.UniqueConstraint("topic_id", name="uq_artifact_shells_topic_id"),
        sa.UniqueConstraint("cache_key", name="uq_artifact_shells_cache_key"),
    )
    op.create_index("ix_artifact_shells_topic_id", "artifact_shells", ["topic_id"])

    # artifact_sections
    op.create_table(
        "artifact_sections",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shell_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("section_slug", sa.String(255), nullable=False),
        sa.Column("section_title", sa.String(512), nullable=False),
        sa.Column("base_content", sa.Text, nullable=True),
        sa.Column("style_overlays", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("cache_key", sa.String(512), nullable=False),
        sa.Column("order_index", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["shell_id"], ["artifact_shells.id"], name="fk_artifact_sections_shell_id_artifact_shells", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_artifact_sections"),
        sa.UniqueConstraint("cache_key", name="uq_artifact_sections_cache_key"),
    )
    op.create_index("ix_artifact_sections_shell_id", "artifact_sections", ["shell_id"])

    # quizzes
    op.create_table(
        "quizzes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("section_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("questions", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("cache_key", sa.String(512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["section_id"], ["artifact_sections.id"], name="fk_quizzes_section_id_artifact_sections", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_quizzes"),
        sa.UniqueConstraint("section_id", name="uq_quizzes_section_id"),
        sa.UniqueConstraint("cache_key", name="uq_quizzes_cache_key"),
    )
    op.create_index("ix_quizzes_section_id", "quizzes", ["section_id"])

    # learning_progress
    op.create_table(
        "learning_progress",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("module_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mastery_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("quizzes_taken", sa.Integer, nullable=False, server_default="0"),
        sa.Column("avg_quiz_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("time_spent_minutes", sa.Integer, nullable=False, server_default="0"),
        sa.Column("sections_completed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_reviewed", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_review", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_learning_progress_user_id_users", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["module_id"], ["modules.id"], name="fk_learning_progress_module_id_modules", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_learning_progress"),
    )
    op.create_index("ix_learning_progress_user_id", "learning_progress", ["user_id"])
    op.create_index("ix_learning_progress_module_id", "learning_progress", ["module_id"])

    # chat_sessions
    op.create_table(
        "chat_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("topic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_chat_sessions_user_id_users", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], name="fk_chat_sessions_topic_id_topics", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_chat_sessions"),
    )
    op.create_index("ix_chat_sessions_user_id", "chat_sessions", ["user_id"])
    op.create_index("ix_chat_sessions_topic_id", "chat_sessions", ["topic_id"])

    # chat_messages
    op.create_table(
        "chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("sources", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("tokens_used", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["session_id"], ["chat_sessions.id"], name="fk_chat_messages_session_id_chat_sessions", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_chat_messages"),
    )
    op.create_index("ix_chat_messages_session_id", "chat_messages", ["session_id"])

    # provider_usage
    op.create_table(
        "provider_usage",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("usage_date", sa.Date, nullable=False),
        sa.Column("tokens_input", sa.Integer, nullable=False, server_default="0"),
        sa.Column("tokens_output", sa.Integer, nullable=False, server_default="0"),
        sa.Column("request_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_provider_usage"),
    )
    op.create_index("ix_provider_usage_provider", "provider_usage", ["provider"])
    op.create_index("ix_provider_usage_usage_date", "provider_usage", ["usage_date"])


def downgrade() -> None:
    op.drop_table("provider_usage")
    op.drop_table("chat_messages")
    op.drop_table("chat_sessions")
    op.drop_table("learning_progress")
    op.drop_table("quizzes")
    op.drop_table("artifact_sections")
    op.drop_table("artifact_shells")
    op.drop_table("modules")
    op.drop_table("curricula")
    op.drop_table("generated_content")
    op.drop_table("resource_refresh_logs")
    op.drop_table("resources")
    op.drop_table("trusted_domains")
    op.drop_table("topic_dependencies")
    op.drop_table("topics")
    op.drop_table("users")
