"""counted monthly risks replace the model's risk grid (PLAN_40, contract 2.0)

Revision ID: 0002_risk_counts
Revises: 0001_init
"""

from alembic import op

revision = "0002_risk_counts"
down_revision = "0001_init"
branch_labels = None
depends_on = None

UP = """
-- One row per cell x calendar month x stress type: in how many years the rule fired.
CREATE TABLE risk_counts (
    cell_id          text NOT NULL,
    calendar_month   smallint NOT NULL CHECK (calendar_month BETWEEN 1 AND 12),
    stress_type      text NOT NULL,
    years_hit        smallint NOT NULL,
    years_total      smallint NOT NULL,
    frequency        real,
    recent_frequency real,
    example_years    smallint[] NOT NULL DEFAULT '{}',
    PRIMARY KEY (cell_id, calendar_month, stress_type)
);
CREATE INDEX risk_counts_month_idx ON risk_counts (calendar_month, stress_type);
DROP TABLE risk_grid;
"""

DOWN = """
DROP TABLE IF EXISTS risk_counts;
CREATE TABLE risk_grid (
    cell_id          text NOT NULL,
    calendar_month   smallint NOT NULL CHECK (calendar_month BETWEEN 1 AND 12),
    p_mean_10y       real,
    p_lo             real,
    p_hi             real,
    trend_per_decade real,
    dominant_type    text,
    PRIMARY KEY (cell_id, calendar_month)
);
CREATE INDEX risk_grid_month_idx ON risk_grid (calendar_month);
"""


def upgrade() -> None:
    op.execute(UP)


def downgrade() -> None:
    op.execute(DOWN)
