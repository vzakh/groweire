"""init: pilot grid, features, risk grid, fields, gazetteer, cache (plan 20 task 20)

Revision ID: 0001_init
Revises:
"""

from alembic import op

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None

UP = """
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE grid_cells (
    cell_id         text PRIMARY KEY,
    geom            geometry(Polygon, 4326) NOT NULL,
    centroid        geometry(Point, 4326) NOT NULL,
    lat             double precision NOT NULL,
    lon             double precision NOT NULL,
    elev_m          real,
    slope_deg       real,
    clay            real,
    sand            real,
    soc             real,
    phh2o           real,
    bdod            real,
    drainage_class  smallint,
    ag_fraction     real,
    crop_fraction   real,
    arable_fraction real
);
CREATE INDEX grid_cells_geom_idx ON grid_cells USING gist (geom);

-- D22: every model feature lives in `features` (keyed by name); fixed columns only for what
-- the API reads directly. The primary key is the btree(cell_id, month) index.
CREATE TABLE cell_month (
    cell_id      text NOT NULL,
    month        date NOT NULL,
    features     jsonb NOT NULL,
    ndvi         real,
    ndvi_z       real,
    stress_label boolean,
    valid_frac   real,
    precip       real,
    et0          real,
    p_minus_et0  real,
    t2m          real,
    sm_rootzone  real,
    PRIMARY KEY (cell_id, month)
);

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

-- Single row, written in the same transaction as the data it describes.
CREATE TABLE dataset_meta (
    id                   boolean PRIMARY KEY DEFAULT true CHECK (id),
    source               text NOT NULL CHECK (source IN ('synthetic', 'real')),
    contract_version     text NOT NULL,
    feature_names_sha256 text NOT NULL,
    ml_version           text,
    row_counts           jsonb,
    loaded_at            timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE fields (
    field_id       text PRIMARY KEY,
    name           text,
    geom           geometry(Polygon, 4326) NOT NULL,
    area_ha        double precision NOT NULL,
    area_source    text NOT NULL CHECK (area_source IN ('approximate', 'drawn')),
    input_point    geometry(Point, 4326),
    centroid       geometry(Point, 4326) NOT NULL,
    pilot_coverage boolean NOT NULL,
    created_at     timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX fields_geom_idx ON fields USING gist (geom);

CREATE TABLE gazetteer (
    place_id   bigint PRIMARY KEY,
    name       text NOT NULL,
    ascii_name text NOT NULL,
    kind       text NOT NULL,
    county     text,
    geom       geometry(Point, 4326) NOT NULL,
    population bigint NOT NULL DEFAULT 0
);
CREATE INDEX gazetteer_ascii_trgm_idx ON gazetteer USING gin (lower(ascii_name) gin_trgm_ops);
CREATE INDEX gazetteer_geom_idx ON gazetteer USING gist (geom);

CREATE TABLE api_cache (
    key        text PRIMARY KEY,
    payload    jsonb NOT NULL,
    fetched_at timestamptz NOT NULL DEFAULT now(),
    ttl_s      bigint
);

CREATE TABLE request_log (
    id         bigserial PRIMARY KEY,
    ts         timestamptz NOT NULL DEFAULT now(),
    method     text,
    path       text,
    status     integer,
    ms         real,
    request_id text
);
CREATE INDEX request_log_ts_idx ON request_log (ts);
"""

DOWN = """
DROP TABLE IF EXISTS request_log, api_cache, gazetteer, fields, dataset_meta, risk_grid,
    cell_month, grid_cells;
"""


def upgrade() -> None:
    op.execute(UP)


def downgrade() -> None:
    op.execute(DOWN)
