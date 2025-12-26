"""Add persons table and link players

Revision ID: 0002_add_persons
Revises: 0001_initial
Create Date: 2024-12-26 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002_add_persons"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "persons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("display_name", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("display_name", name="uq_person_display_name"),
    )
    op.add_column("players", sa.Column("person_id", sa.Integer(), nullable=True))
    if op.get_bind().dialect.name != "sqlite":
        op.create_foreign_key(
            "fk_players_person_id",
            "players",
            "persons",
            ["person_id"],
            ["id"],
        )

    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            INSERT INTO persons (display_name, created_at)
            SELECT DISTINCT name, CURRENT_TIMESTAMP
            FROM players
            WHERE name IS NOT NULL
            """
        )
    )
    connection.execute(
        sa.text(
            """
            UPDATE players
            SET person_id = (
              SELECT id FROM persons WHERE persons.display_name = players.name LIMIT 1
            )
            """
        )
    )


def downgrade():
    op.drop_constraint("fk_players_person_id", "players", type_="foreignkey")
    op.drop_column("players", "person_id")
    op.drop_table("persons")
