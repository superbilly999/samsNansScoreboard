"""Initial tables

Revision ID: 0001_initial
Revises: 
Create Date: 2024-12-26 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "games",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("current_round_index", sa.Integer(), nullable=False),
        sa.Column("finished", sa.Boolean(), nullable=False),
        sa.Column("archived", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "players",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("game_id", sa.Integer(), sa.ForeignKey("games.id"), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "rounds",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("game_id", sa.Integer(), sa.ForeignKey("games.id"), nullable=False),
        sa.Column("round_index", sa.Integer(), nullable=False),
        sa.Column("round_name", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("game_id", "round_index", name="uq_round_game_index"),
    )
    op.create_table(
        "round_scores",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("round_id", sa.Integer(), sa.ForeignKey("rounds.id"), nullable=False),
        sa.Column("player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("went_out", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("round_id", "player_id", name="uq_score_round_player"),
    )


def downgrade():
    op.drop_table("round_scores")
    op.drop_table("rounds")
    op.drop_table("players")
    op.drop_table("games")
