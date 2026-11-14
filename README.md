# GrowÉire

**Know your land. Grow your future.** GrowÉire is a crop-rotation decision-support tool for small farms, built on NASA Earth observations. In four plain steps, a farmer finds their field and sees how often each month of the growing season has been too dry, too wet, too hot or frosty there. They then compare their current rotation with alternatives that lower that risk and build soil.

Built for **NASA Space Apps Challenge 2026: _Field Shift: Adapting Farms with NASA Data_** at HackAthlone 2026, Athlone, Ireland. The core runs on global NASA data, and **Ireland is the pilot region**.

> [!NOTE]
> **Status: hackathon proof of concept.** The guided flow, the counted-risk engine, the rotation comparison and the landing page all work end to end against the API or recorded fixtures. The project runs locally; see [Running locally](#running-locally).

> [!IMPORTANT]
> GrowÉire **supports, but does not replace**, the farmer's own judgement and local agronomic advice. Every answer lists its information gaps and points the farmer to their advisor.

---

## Contents

- [What it does](#what-it-does)
- [Who it is for](#who-it-is-for)
- [The farmer's journey](#the-farmers-journey)
- [Architecture](#architecture)
- [How the risk is worked out](#how-the-risk-is-worked-out)
- [How rotations are compared](#how-rotations-are-compared)
- [Data sources](#data-sources)
- [Repository layout](#repository-layout)
- [Getting started](#getting-started)
- [Configuration](#configuration)
- [API reference](#api-reference)
- [Database](#database)
- [The ML package and its contract](#the-ml-package-and-its-contract)
- [Building the real pilot data](#building-the-real-pilot-data)
- [Frontend](#frontend)
- [Testing and quality checks](#testing-and-quality-checks)
- [Operations](#operations)
- [Running locally](#running-locally)
- [Limitations](#limitations)
- [Roadmap](#roadmap)
- [Working on the code](#working-on-the-code)
- [Acknowledgements and data attribution](#acknowledgements-and-data-attribution)
- [Licence](#licence)

---

## What it does

Each year a farmer decides what to grow, in what order, and what covers the soil between crops. That choice sets how exposed the field is to the next bad season. Irish farmers have just had a record-wet spring followed by the driest July on record, and they usually make this decision from habit, with no simple view of how their own field has fared over time.

GrowÉire joins two things that already exist but have never been combined in a form a farmer can use in five minutes on a phone:

1. **Twenty-five years of NASA weather history**, turned into plain, checkable statements such as *"In 8 of the last 25 years, March had frost here."*
2. **Irish rotation evidence** (Teagasc, FAO-56 and DAFM rules), turned into a side-by-side comparison of the current rotation and two or three alternatives. Each option explains why it was suggested, the evidence, the benefits, the information gaps and the risks that need local review.

| Capability | Where it lives |
|---|---|
| Find a field by place name or by tapping the map; approximate size or a drawn outline | `GET /places`, `POST /fields`, step 1 of the app |
| How often each month (March–October) was too dry, too wet, too hot or frosty, in natural frequencies | `POST /predict/stress-risk`, month strip |
| Climate summary, 30-year trends, soil description and summer greenness history | `GET /fields/{id}/conditions`, *More detail* |
| Current rotation vs. 2–3 alternatives, weighted by the farmer's top-3 priorities | `POST /rotations/compare`, option cards |
| Questions to take to the advisor, and a printable one-page summary or share link | Option cards, `/app/field/:id/print` |
| NASA GIBS imagery (true colour, NDVI, SMAP soil moisture) and a pilot-wide risk map by month | `GET /layers`, `GET /layers/stress-risk`, *More maps* |
| Plain-language glossary (NDVI, evapotranspiration, water balance, …) | `GET /glossary`, *What the words mean* |

**Coverage model.** Weather and soil work for **any point on Earth** through live NASA POWER and ISRIC SoilGrids calls. The pre-computed pilot grid, the drainage-aware soil water model and the crop catalogue are **calibrated for the island of Ireland**. Outside Ireland, the answer says so and is labelled `outside_pilot`.

> **On the names.** *GrowÉire* is the product name used in the interface. *AgroLens* is the internal code name used by the API, the Python packages (`agrolens-backend`, `agrolens-ml`), the Docker image and the planning documents. They are the same project.

## Who it is for

The primary user is a **small Irish mixed or tillage farmer aged 45–65**. That group covers 46.6% of Irish holders (CSO Farm Structure Survey 2023), and eight in ten Irish farms are under 50 ha. Only about half of these farmers feel confident with technology, and they trust their advisor more than any app. That profile drives the design:

- **One question per screen, answer first.** Numbers, ranges and sources sit one tap below.
- **Tap, don't type.** Crops and priorities are large picture buttons and cards. There are no sliders.
- **Natural frequencies, not percentages,** on the main path: "about 3 years in 10".
- **Large, high-contrast text.** The body is at least 18 px and touch targets are at least 48 × 48 px. An **A+** button cycles text size through 100%, 125% and 150%.
- **No account, no install and no personal data.** The URL holds every answer, so a link *is* the saved plan.
- **The advisor is always in the loop.** Each option ends with "Ask your advisor about…".

The secondary users are **farm advisors** (Teagasc and private), who use the printable summary and *More maps*, and the **hackathon judges**.

## The farmer's journey

| Step | Screen | What happens |
|---|---|---|
| 1 | **Where is your field?** | Search a town or townland (server-side OpenStreetMap search with a GeoNames fallback), tap the map, and pick an approximate size (default 10 ha). Drawing the exact edges is optional. |
| 2 | **What did you grow here?** | Tap the main crop for each of the last four years. "Not sure" is allowed. |
| 3 | **What matters most to you?** | Pick up to three of eight priorities in order of importance: *steady income, less work, keep soil covered, use less water, feed for my animals, fix nitrogen, fewer weeds and pests, easy to sell*. Then answer up to three yes/no questions: livestock, a crop contract, a crop you won't grow. |
| 4 | **Your answer** | A one-sentence headline names the riskiest month. Below it come the March–October month strip, local proof (summer greenness, soil card) and the option cards: your rotation plus alternatives, each with *Why this option?* and *Ask your advisor*. **Print** and **Send** buttons sit at the end. |

Example headline from the recorded fixtures (real pilot data, spring barley):

> *March is the riskiest month for spring barley here. In about 8 years in 10 it is too frosty.*

---

## Architecture

The repository is a **monorepo** with three deployable parts:

- `frontend/` is a Vue 3 single-page app.
- `backend/` is a FastAPI service backed by PostGIS and Redis.
- `ml/` is the `agrolens_ml` Python package. It holds the risk rules, feature code and offline pipelines.

`backend` and `ml` are members of one **uv workspace** and share one `uv.lock`. As a result, the counting code the API runs on a live point is byte-for-byte the code that built the pilot tables.

```mermaid
flowchart LR
    subgraph Browser
        SPA["Vue 3 SPA<br/>landing page + field app"]
    end

    subgraph API["agrolens-api (FastAPI, Uvicorn)"]
        R["routes /api/v1"] --> S["services<br/>fields · risk · conditions · rotation · plain"]
        S --> ML["agrolens_ml<br/>count_risks · ET0 · SMD model"]
        S --> C["clients<br/>POWER · SoilGrids · Nominatim"]
    end

    subgraph Stores
        PG[("PostGIS<br/>grid_cells · cell_month · risk_counts<br/>fields · gazetteer · api_cache")]
        RD[("Redis<br/>cache + 1 req/s place-search token")]
    end

    subgraph External["External services"]
        POWER["NASA POWER<br/>daily point API"]
        SG["ISRIC SoilGrids v2"]
        OSM["OSM Nominatim"]
        GIBS["NASA GIBS WMTS"]
        OFM["OpenFreeMap basemap"]
    end

    SPA -- "JSON over /api/v1" --> R
    SPA -- "map tiles (direct)" --> GIBS
    SPA -- "vector style (direct)" --> OFM
    S --> PG
    C --> RD
    C -. "fallback cache" .-> PG
    C --> POWER
    C --> SG
    C --> OSM

    subgraph Offline["Offline, on a laptop (not deployed)"]
        DL["ml/pipelines/download<br/>POWER · AppEEARS · IMERG · SoilGrids · Met Éireann · GeoNames"]
        CLI["python -m agrolens_ml.cli<br/>grid · labels · features · risk-counts"]
        PQ[/"data/processed/*.parquet<br/>+ _MANIFEST.json"/]
        DL --> CLI --> PQ
    end
    PQ -- "jobs.load_pilot (one transaction)" --> PG
```

| Component | Technology | Responsibility |
|---|---|---|
| **Frontend** | Vue 3.5, TypeScript, Vite 8, Tailwind CSS 4, shadcn-vue (reka-ui), Pinia, vue-router, MapLibre GL, openapi-fetch, MSW | Landing page, guided 4-step field app, map, print view; typed API client generated from `backend/openapi.json` |
| **API** | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, GeoAlchemy2, Alembic, httpx, tenacity, Shapely, loguru, Prometheus instrumentator | Validation, geometry, counted risk, plain-language wording, rotation engine, caching, error envelope |
| **`agrolens_ml`** | pandas, NumPy, pyarrow, scikit-learn, LightGBM, joblib (+ `[train]` extra: earthaccess, xarray, rasterio, geopandas, …) | Risk rules and counting, FAO-56 ET0, soil moisture deficit model, data-product schemas, synthetic tables, the earlier stress model |
| **Database** | PostgreSQL 16 + PostGIS 3.4 (`pg_trgm` for fuzzy place names) | Pilot grid, counted risks, satellite series, fields, gazetteer, cache fallback |
| **Cache** | Redis 7 | Upstream responses (POWER, SoilGrids, Nominatim), app-wide Nominatim rate-limit token |

### What happens on the answer screen

```mermaid
sequenceDiagram
    autonumber
    actor F as Farmer
    participant UI as Field app
    participant API as API /api/v1
    participant DB as PostGIS
    participant EXT as POWER / SoilGrids

    F->>UI: types "Bagenalstown", taps field, picks 10 ha
    UI->>API: GET /places?q=Bagenalstown
    API-->>UI: up to 5 places (OSM, else GeoNames)
    UI->>API: POST /fields {point, area_ha}
    API->>DB: geodesic circle, intersect pilot grid
    API-->>UI: field_id, centroid, pilot_coverage, cell_ids
    par prefetch while the farmer answers steps 2–3
        UI->>API: GET /fields/{id}/conditions
        API->>EXT: POWER daily (cached 30 days) + SoilGrids (outside pilot)
        UI->>API: GET /crops
    end
    F->>UI: crops, priorities, yes/no answers (all kept in the URL)
    UI->>API: POST /predict/stress-risk {field_id, crop_id}
    API->>DB: risk_counts of the field's main cell
    UI->>API: POST /rotations/compare {current_rotation, priorities, constraints}
    API-->>UI: headline, month strip, ranked strategies with explanations
    UI-->>F: answer, options, Print / Send
```

---

## How the risk is worked out

The risk a farmer sees is **counted, not predicted**. For each calendar month from March to October and each of four stress types, GrowÉire counts the years in which an **absolute, documented rule** fired in NASA weather history. The result is a sentence anyone can check against their memory: *"In 6 of the last 25 years, July was too dry here."*

### The daily soil water balance

Drought and waterlogging are judged from a daily **soil moisture deficit (SMD)**, using the Met Éireann / Teagasc hybrid model (Schulte et al., 2005, *Irish Journal of Agricultural and Food Research* 44: 95–110):

```text
SMD_t = SMD_{t-1} − Rain + ETa + Drain        (mm; 0 = field capacity, −10 = saturated)
ETa   = ET0                                    when SMD_{t-1} ≤ SMDc
ETa   = ET0 × (110 − SMD_{t-1}) / (110 − SMDc) when SMD_{t-1} > SMDc
```

- **ET0** is FAO-56 Penman–Monteith reference evapotranspiration, computed daily from POWER `T2M_MAX`, `T2M_MIN`, `RH2M`, `WS2M` and `ALLSKY_SFC_SW_DWN` plus elevation (`ml/src/agrolens_ml/features/et0.py`, unit-tested against the FAO-56 worked example).
- **The drainage class** comes from the EPA/Teagasc national soil map. It selects the model's *well*, *moderate* or *poor* parameters.
- **Rain** comes from the POWER node (about 50 km). In the pilot it is **rescaled per cell and month to the GPM IMERG monthly total** (about 10 km), because POWER flattens Ireland's wet west and drier east.

### The rules

All thresholds live in [`ml/src/agrolens_ml/config.py`](ml/src/agrolens_ml/config.py). The rule set is versioned as `RISK_RULES_VERSION = "counted-1"`, and every response carries that version.

| Stress type | A day counts when… | A month is hit when… |
|---|---|---|
| **Drought** (*Dry*) | SMD > 50 mm, the upper limit of optimum grass growth (Teagasc 2021, via Basu et al. 2024; consistent with FAO-56 ch. 8) | ≥ 15 such days |
| **Waterlogging** (*Wet*) | SMD < 0 mm, i.e. water above field capacity (Met Éireann) | ≥ 15 such days |
| **Heat** (*Heat*) | `T2M_MAX` ≥ 25 °C | ≥ 3 hot days |
| **Frost** (*Frost*) | `T2M_MIN` ≤ 0 °C | ≥ 1 frost day, March–May only |

A month with more than 3 missing days is not counted. For each cell, month and stress type, the pilot table `risk_counts` stores `years_hit`, `years_total`, `frequency`, `recent_frequency` (the last 10 years) and up to five `example_years`, worst first.

### From counts to words

1. **Dominant type.** For each month, the most frequent stress type wins. Ties are broken by `drought → waterlogging → heat → frost`.
2. **Uncertainty.** A 90% **Wilson score interval** around *N years out of M* is shown under *More detail*.
3. **Crop weighting.** When a crop is chosen, the counted frequency is multiplied by that crop's monthly sensitivity to the stress type (`crops_ie.json`). The weighted value sets the level, the label and the riskiest month. The sentence *"about N years in 10"* always describes the **counted weather**, so the farmer can check it.
4. **Plain language.** `backend/app/services/plain.py` and [`backend/app/config/plain.yaml`](backend/app/config/plain.yaml) produce every user-facing string. The frontend never invents wording.

| Displayed risk *p* | Level | Frequency text |
|---|---|---|
| *p* < 0.05 | low | "less than 1 year in 20" |
| 0.05 ≤ *p* < 0.10 | low | "about 1 year in 20" |
| 0.10 ≤ *p* < 0.25 | medium | "about N years in 10" |
| 0.25 ≤ *p* < 0.95 | high | "about N years in 10" |
| *p* ≥ 0.95 | high | "almost every year" |

**Pilot vs. elsewhere.** A pilot field reads `risk_counts` for the grid cell covering most of it, so the counts are for whole years. Any other point runs **the same `count_risks` function** on live POWER data (30 years, cached), with drainage unknown. That fact is surfaced as an information gap.

### Why not a machine-learning model?

The first design trained a **seasonal stress model**: MODIS NDVI anomalies (z ≤ −1 against 2001–2020) as labels, 36 lagged climate, soil and vegetation features, and a LightGBM classifier with year-grouped cross-validation and a 2022–2025 holdout. It was trained on real data (`ml/artifacts/stress_lgbm_v1/`). The honest result on the holdout was weak:

| Model | PR-AUC | ROC-AUC | Brier |
|---|---|---|---|
| B0 climatology | 0.173 | 0.539 | 0.1339 |
| B1 logistic regression | 0.200 | 0.595 | 0.1334 |
| LightGBM, calibrated | 0.219 | 0.654 | 0.1357 |

LightGBM beat both baselines on PR-AUC but **not on Brier score**, so under our own acceptance rule the logistic baseline would have shipped. Next-month vegetation stress in cloudy Ireland, at 250 m, with grass cutting in the signal, is too noisy to present to a farmer as a probability. **Contract 2.0** therefore replaced the model on the main path with counted rules. They are transparent, verifiable by the farmer, and they run on any point on Earth. The model, its card and its reports stay in `ml/artifacts/` as evidence and as an optional add-on. The full metrics are in [`ml/artifacts/stress_lgbm_v1/reports/metrics.md`](ml/artifacts/stress_lgbm_v1/reports/metrics.md). The NDVI labels pass a sanity check: the 2018 drought ranks first of 25 years ([`labels_summary.md`](ml/artifacts/reports/labels_summary.md)).

---

## How rotations are compared

The rotation engine in [`backend/app/services/rotation/`](backend/app/services/rotation/) is **deterministic and rule-based**. Every number traces to a metric or to a catalogue source. The pipeline is `generate → score → explain → present → select`.

1. **Generate.** Candidates come from three places:
   - the farmer's own crops with winter cover crops added;
   - the farmer's own rotation with one year changed to a break crop (beans, oats or oilseed rape) or to a required crop;
   - sourced templates in [`rotations_ie.json`](backend/app/data/rotations_ie.json), for example the Teagasc five-year rotation WW-WB-WOSR-WW-Beans, SB-SB-WW-Beans, and a grass-clover ley with cereals.

   Constraints filter the list: excluded crops, livestock for leys and forage, and required crops. Winter gaps of three months or more before a spring crop get the best allowed **cover crop** (oats-vetch, phacelia or mustard).
2. **Score.** Ten metrics are computed per strategy over the rotation cycle:
   - bare months per year;
   - crop-weighted stress (from the counted risk);
   - water demand (FAO-56 Kc × ET0);
   - workability risk;
   - erosion index;
   - nitrogen-fixing years;
   - pest-break score;
   - organic-matter score;
   - forage score;
   - market fit.

   Compliance with the Irish **two-crops-in-four-years** conditionality rule is also checked. The metrics are min-max normalised across the candidate set and combined as Σ wᵢ·sᵢ / Σ wᵢ, where climate risk always has weight 1 and the farmer's ordered priorities add **3, 2 and 1**.
3. **Explain.** Each strategy gets the five blocks the challenge requires: *why suggested, evidence, benefits, information gaps, risks needing local review*. They are built only from computed metrics and catalogue sources, with no LLM.
4. **Present.** A headline ("Add beans in year 3"), a one-line why, *vs. current* icons (risk, bare soil, work) and 2–4 **advisor questions**, mapped from risk codes in [`advisor_questions.json`](backend/app/data/advisor_questions.json). The API refuses to start if any code lacks a question.
5. **Select.** The current rotation comes first, followed by the best-scoring alternatives that differ meaningfully from it (Jaccard distance ≥ 0.25 on crop sets). At most one "small step" and one "cover crops only" option are kept, so the choices show different kinds of change.

The crop catalogue ([`crops_ie.json`](backend/app/data/crops_ie.json)) covers 11 main crops and 3 cover crops: spring and winter barley, winter wheat, spring and winter oats, spring beans, winter oilseed rape, potatoes, maize silage, grass-clover ley, multispecies sward, and the oats-vetch, phacelia and mustard covers. **Every numeric parameter carries a `source`**, and the catalogue loader raises at start-up on an unsourced number. Values not yet verified are tagged `draft_unverified` and shown to the farmer as information gaps.

---

## Data sources

| Dataset | Provider | Resolution / period | Access | Used for | Mode |
|---|---|---|---|---|---|
| **NASA POWER** daily, AG community (10 parameters) | NASA LaRC (MERRA-2 / CERES) | ~0.5° × 0.625°, 1981 → | REST point API | ET0, SMD model, risk counts, climate summary and trends | Live (any point, cached 30 days) and offline (pilot) |
| **GPM IMERG Final, monthly** (`GPM_3IMERGM` V07) | NASA GES DISC | 0.1°, 2001 → | earthaccess | Rescaling pilot rain per cell and month | Offline |
| **MODIS MOD13Q1 / MYD13Q1 v6.1** NDVI | NASA LP DAAC | 250 m, 16-day, 2000 → | AppEEARS | Summer greenness history; NDVI labels for the earlier model | Offline |
| **MODIS MCD12Q1 v6.1** land cover | NASA LP DAAC | 500 m, yearly | AppEEARS or earthaccess | Agricultural mask for the pilot grid (≥ 30% grassland, cropland or mosaic) | Offline |
| **SRTMGL1 v003** | NASA LP DAAC | 30 m | AppEEARS or earthaccess | Elevation and slope (erosion index) | Offline |
| **SMAP L4** root-zone soil moisture (`SPL4SMGP` v8) | NASA NSIDC DAAC | 9 km, 2015 → | AppEEARS (point) | Satellite series under *More detail* | Offline |
| **NASA GIBS** WMTS | NASA ESDIS | tiles | Browser, direct | *More maps*: true colour, NDVI, soil moisture | Live |
| **ISRIC SoilGrids v2.0** | ISRIC (CC BY 4.0) | 250 m | REST | Soil texture, carbon, pH and bulk density (0–30 cm) | Live (cached indefinitely) and offline |
| **Irish Soil Information System** drainage | EPA / Teagasc | 1:250 000 polygons | Manual download | Drainage class → SMD parameters | Offline (Republic of Ireland only) |
| **Met Éireann** station data | Met Éireann (CC BY 4.0) | ~25 synoptic stations | CSV | Ground truth for POWER and ET0 checks | Offline |
| **OpenStreetMap Nominatim** | OSMF (ODbL) | — | REST, server-side proxy | Place search (≤ 1 req/s app-wide) | Live |
| **GeoNames** IE + GB | GeoNames (CC BY 4.0) | — | Dump download | Place-search fallback (`gazetteer` table) | Offline |
| **OpenFreeMap** "liberty" style | OpenFreeMap / OSM | vector | Browser, direct | Basemap (falls back to MapLibre demo tiles) | Live |

The full list, with DOIs, licences and the exact attribution wording, is in [`ml/pipelines/download/REFERENCES.md`](ml/pipelines/download/REFERENCES.md). Every API response that contains derived data carries a `provenance` list naming the datasets it used.

**Known data caveats**, which the app also shows the farmer:

- POWER is reanalysis at about 50 km, not a field weather station.
- NDVI pixels are larger than many Irish fields.
- Ireland is very cloudy.
- Grass cutting can look like stress.

That is why field-level outputs are *risk indicators*, not measurements.

---

## Repository layout

```text
.
├── backend/                     FastAPI service (uv member `agrolens-backend`, run with PYTHONPATH=backend/app)
│   ├── alembic/versions/        0001_init (schema), 0002_risk_counts (contract 2.0)
│   ├── app/
│   │   ├── main.py              app factory + lifespan (DB engine, Redis, httpx client, catalogue checks)
│   │   ├── api/routes/          health · places · fields · conditions · predict · crops · rotations · layers
│   │   ├── services/            fields · places · context · risk · conditions · plain · rotation/{generate,score,explain,present,catalog}
│   │   ├── clients/             power · soilgrids · nominatim · cache (Redis → Postgres fallback)
│   │   ├── core/                config · deps · errors · middleware · logging · metrics
│   │   ├── models/              Pydantic request/response schemas
│   │   ├── db/                  engine/session + SQL (PostGIS) queries
│   │   ├── jobs/                load_pilot · export_openapi · export_fixtures
│   │   ├── data/                crops_ie · rotations_ie · advisor_questions · glossary · layers · sources (JSON)
│   │   └── config/plain.yaml    every threshold and word the farmer reads
│   ├── openapi.json             committed Backend → Frontend contract
│   └── tests/                   unit, contract, integration + fixtures/api/*.json (recorded responses)
├── ml/                          uv member `agrolens-ml`
│   ├── src/agrolens_ml/         contract · config · risk_counts · features/ · labels/ · model/ · grid · pipeline · synthetic · cli
│   ├── pipelines/
│   │   ├── config/              Ireland outline + 0.05° / 0.1° / 0.25° grids
│   │   └── download/            data download scripts (POWER, SoilGrids, Met Éireann, GeoNames, AppEEARS, IMERG)
│   ├── artifacts/               stress_lgbm_v1 (earlier model, metrics, model card) · stub_v0 · reports/
│   └── tests/                   unit tests + contract/ (ML → Backend)
├── frontend/                    Vue 3 SPA (npm project)
│   ├── src/
│   │   ├── views/               HomeView (landing) · WorkspaceView (field app) · PrintView
│   │   ├── components/          site/ (landing) · shell/ · steps/ · answer/ · options/ · map/ · more/ · share/ · common/ · ui/ (shadcn-vue)
│   │   ├── stores/              flow · field · catalog · risk · rotations (Pinia)
│   │   ├── lib/                 api client + generated api-types · query (URL state) · geo · share · format
│   │   ├── composables/         useMap · useMapScene · useTextScale · useCountUp · useLayout
│   │   ├── copy/en.ts           all static interface wording in one file
│   │   └── mocks/               MSW handlers that replay backend/tests/fixtures/api
│   └── public/                  images, Space Apps 2026 logo (brand/ + SOURCES.md), MSW worker
├── deploy/docker/api.Dockerfile multi-stage, non-root API image
├── compose.yaml                 local stack: db, redis, migrate, api (+ load-pilot under profile `ops`)
├── .envs/.example/.api          environment template (copy to .envs/.dev/.api, never commit real values)
├── Makefile                     every common task (see below)
├── pyproject.toml · uv.lock     uv workspace root (Python 3.12)
└── .mcp.json · .claude/skills/  shadcn-vue MCP server and agent skill for Claude Code
```

`data/` (raw downloads, processed Parquet and generated synthetic tables) is **gitignored**. It is created locally by the steps below.

---

## Getting started

### Prerequisites

| Tool | Version | Needed for |
|---|---|---|
| [uv](https://docs.astral.sh/uv/) | ≥ 0.8 | Python workspace (installs Python 3.12 if missing) |
| Node.js + npm | Node 20.19+ or 22.12+ (required by Vite 8) | Frontend |
| Docker Engine + Compose v2 | Docker ≥ 24 | PostGIS and Redis (and optionally the API image) |
| GNU Make + a POSIX shell | any | The `Makefile` targets. On Windows use Git Bash with `make`, or run the commands shown under each target directly. |

There are three ways to run the project, from lightest to fullest.

### Option A: frontend only, no backend (2 minutes)

The field app replays the backend's recorded responses through Mock Service Worker. No Python, Docker or network APIs are needed.

```bash
cd frontend
npm ci
npm run dev:mock
```

Open <http://localhost:5173> for the landing page and <http://localhost:5173/app> for the field app. Mock mode answers from the recorded fixtures (real pilot data), so the results are the same whichever field you choose.

### Option B: full stack on your machine (synthetic pilot data)

```bash
# 1. Python workspace (backend + ml) into .venv
make sync                       # = uv sync --all-packages

# 2. PostGIS on :55432 and Redis on :56379
make db-up                      # = docker compose -f compose.yaml up -d --wait db redis

# 3. Schema
make migrate                    # = cd backend && PYTHONPATH=app uv run --package agrolens-backend alembic upgrade head

# 4. Pilot tables: seeded, schema-exact synthetic data on the real 0.05° Irish grid
make synthetic                  # writes data/synthetic/
make load-pilot DATA=data/synthetic

# 5. (optional) offline place-search fallback
make geonames load-gazetteer

# 6. API with auto-reload on :8080
make api
```

Then, in a second terminal:

```bash
cd frontend
npm ci
npm run dev                     # Vite proxies /api to http://localhost:8080
```

Check that everything is ready:

```bash
curl -s http://localhost:8080/api/v1/health/ready
# {"status":"ok","model_version":"counted-1","model_kind":"counted_history","data_source":"synthetic","contract_version":"2.0","cache":"redis"}
```

Interactive API docs are at <http://localhost:8080/api/v1/docs>.

> [!WARNING]
> Synthetic tables contain **invented numbers**. Every response built on them carries `data_quality: ["synthetic_data"]`, and `/health/ready` refuses them when `ALLOW_STUB_MODEL=false` (production).

### Option C: API in Docker

```bash
make up                                     # db + redis + one-shot migrate + api on :8080 (API_PORT=8081 to move it)
make synthetic                              # on the host: data/ is mounted read-only into the job
make load-pilot-docker PILOT_DATA=synthetic # runs jobs.load_pilot inside the API image (compose profile `ops`)
```

`make db-down` stops the stack and keeps the database volume (`agrolens-backend_pgdata`).

### Loading real pilot data

Real tables come from the offline pipeline described in [Building the real pilot data](#building-the-real-pilot-data). Once `data/processed/` holds `grid_cells.parquet`, `cell_month_features.parquet`, `risk_counts.parquet` and `_MANIFEST.json`, load it as follows:

```bash
make load-pilot DATA=data/processed
```

The loader checks the manifest's contract version and feature-name hash against the installed `agrolens_ml`. If either differs, it refuses with a plain message and loads nothing. On success, the data and its `dataset_meta` label are written **in one transaction**.

---

## Configuration

The API reads **environment variables only**; it does not read a `.env` file. The defaults below match `compose.yaml`, so a local run needs no configuration. The template is [`.envs/.example/.api`](.envs/.example/.api). Copy it to `.envs/.dev/.api` or `.envs/.prod/.api`; both paths are gitignored.

| Variable | Default | Purpose |
|---|---|---|
| `APP_ENV` | `dev` | `dev` · `test` · `prod`. `prod` enables `TrustedHostMiddleware` and turns CORS off (same-origin behind the proxy). `test` switches JSON logs off. |
| `DATABASE_URL` | `postgresql+psycopg2://agrolens:agrolens@localhost:55432/agrolens` | PostGIS connection |
| `REDIS_URL` | `redis://localhost:56379/0` | Cache and rate-limit token |
| `ALLOW_STUB_MODEL` | `true` | `false` in production: `/health/ready` then returns 503 if synthetic tables are loaded. The name dates from the model era and is kept so deploy files keep working. |
| `LOG_LEVEL` | `INFO` | loguru level |
| `FRONTEND_ORIGIN` | `http://localhost:5173` | Only origin allowed by CORS (non-prod) |
| `DOMAIN` | `localhost` | Allowed `Host` header in production |
| `ENABLE_DOCS` | `true` | Serves Swagger UI at `/api/v1/docs` |
| `REPO_URL`, `CONTACT_EMAIL` | placeholders | Sent in the Nominatim `User-Agent`, as its usage policy requires. **Set real values before any public deployment.** |
| `WEB_CONCURRENCY` | `2` (image) / `1` (compose) | Uvicorn workers per container |
| `API_PORT` | `8080` | Host port published by `compose.yaml` |

**Frontend.** `npm run dev:mock` loads `frontend/.env.mock` (`VITE_MOCK=1`). In development, Vite proxies `/api` to `http://localhost:8080`. In production, the SPA expects the API on the **same origin**.

**Data pipeline.** Earthdata credentials (`EARTHDATA_USERNAME`, `EARTHDATA_PASSWORD`) go in `ml/pipelines/.env`, created from `ml/pipelines/download/.env.example`. Optional overrides are `AGROLENS_YEAR_START`, `AGROLENS_YEAR_END`, `AGROLENS_RAW` and `AGROLENS_PROCESSED`. Never commit `.env` or `.netrc`.

---

## API reference

All routes live under **`/api/v1`**. The machine-readable contract is [`backend/openapi.json`](backend/openapi.json), also served live at `/api/v1/openapi.json`. Real request/response pairs for every endpoint are in [`backend/tests/fixtures/api/`](backend/tests/fixtures/api/).

| Method & path | Purpose | Notes |
|---|---|---|
| `GET /health/live` | The process is up | Used by the Docker health check |
| `GET /health/ready` | DB reachable, pilot data loaded, counted risks present | Reports `model_version` (rules version), `data_source`, `contract_version`, `cache: redis \| degraded` |
| `GET /places?q=` | Find a town, village or townland (Ireland and Northern Ireland) | 2–100 characters, ≤ 5 results. Order: cache → Nominatim (shared 1 req/s token) → GeoNames gazetteer → `503 place_search_busy` |
| `POST /fields` | Create a field | **Exactly one of** `{point: [lon, lat], area_ha}` (geodesic circle) or `{geometry: Polygon}`. 0.1–2,000 ha, ≤ 500 vertices, valid polygon |
| `GET /fields/{id}` | Field metadata | `area_source`, `pilot_coverage`, `cell_ids`, stored geometry |
| `GET /fields/{id}/conditions?years=30` | Climate by month, trends (Sen's slope per decade), soil (+ plain words), satellite series, summer greenness | `years` 5–40 |
| `POST /predict/stress-risk` | Counted monthly risk, March–October | `{field_id \| geometry, crop_id?}`. Only `mode: "seasonal_profile"` exists since contract 2.0 |
| `GET /crops?region=IE` | Crop catalogue | Only `IE` is available |
| `POST /rotations/compare` | Current rotation vs. alternatives | `current_rotation` (1–8 crop ids), `priorities` (≤ 3, unique, ordered), `constraints`, `n_alternatives` 1–5 |
| `GET /layers` | Map layer catalogue | GIBS WMTS identifiers and URL templates plus our GeoJSON layer |
| `GET /layers/stress-risk?month=7&type=drought` | Pilot grid as GeoJSON: counted frequency per cell | `month` 3–10; `type` optional (omit for each cell's most frequent type) |
| `GET /glossary` | Plain-language terms | Farmer title + technical term + explanation |
| `GET /metrics` | Prometheus metrics | Not in the OpenAPI schema; keep it internal |

**Example.**

```bash
FIELD=$(curl -s -X POST http://localhost:8080/api/v1/fields \
  -H 'Content-Type: application/json' \
  -d '{"name":"Home field","point":[-6.955,52.705],"area_ha":10}' | python -c 'import sys,json;print(json.load(sys.stdin)["field_id"])')

curl -s -X POST http://localhost:8080/api/v1/predict/stress-risk \
  -H 'Content-Type: application/json' \
  -d "{\"field_id\":\"$FIELD\",\"crop_id\":\"spring_barley\"}"

curl -s -X POST http://localhost:8080/api/v1/rotations/compare \
  -H 'Content-Type: application/json' \
  -d "{\"field_id\":\"$FIELD\",\"current_rotation\":[\"spring_barley\",\"spring_barley\",\"spring_barley\",\"spring_barley\"],
       \"priorities\":[\"income_stability\",\"simplicity\",\"soil_cover\"],
       \"constraints\":{\"has_livestock\":true,\"excluded_crops\":[\"potatoes\"],\"market_contracts\":[\"malting_barley\"]}}"
```

**Conventions shared by every endpoint:**

- **Errors** always have the shape `{"detail": "<plain sentence>", "code": "<stable_code>"}`. Validation errors add `errors: [{loc, msg, type}]`. Examples of codes: `field_not_found`, `field_input_ambiguous`, `area_out_of_range`, `unknown_crop`, `place_search_busy`, `climate_unavailable`, `dataset_not_loaded`, `payload_too_large`.
- **Upstream failures degrade instead of failing.** A SoilGrids outage becomes an `information_gaps` entry, not a 500. Only the weather history is essential, and its absence returns `503 climate_unavailable`.
- **Every data response** carries `data_quality` flags (`synthetic_data`, `outside_pilot`, `drainage_unknown`, …), `information_gaps` (code + plain text), `provenance` and the `disclaimer`.
- **`X-Request-ID`** is accepted or generated, echoed on the response and written to every log line. Bodies over 1 MB get `413 payload_too_large`. Responses over 1 kB are gzipped.

---

## Database

PostgreSQL 16 with PostGIS. All geometry is EPSG:4326, and areas are computed on `geography` (m²). Migrations live in [`backend/alembic/versions/`](backend/alembic/versions/) and **never run at API start-up**: run `make migrate` locally, or let the one-shot `migrate` service in `compose.yaml` run them.

| Table | Contents | Written by |
|---|---|---|
| `grid_cells` | 0.05° pilot cells (≈ 5.6 × 3.3 km): polygon, centroid, elevation, slope, SoilGrids texture/carbon/pH/bulk density, drainage class, agricultural and crop fractions | `load_pilot` |
| `cell_month` | Per cell and month: NDVI, NDVI anomaly, SMAP root-zone moisture, rain, ET0, water balance, temperature; model features as `jsonb` | `load_pilot` |
| `risk_counts` | Per cell × calendar month × stress type: `years_hit`, `years_total`, `frequency`, `recent_frequency`, `example_years[]` | `load_pilot` |
| `dataset_meta` | Single row: `source` (`synthetic` / `real`), contract version, feature hash, row counts, load time | `load_pilot` (same transaction) |
| `fields` | Fields created by users: polygon, area, `area_source` (`approximate` / `drawn`), input point, centroid, `pilot_coverage` | `POST /fields` |
| `gazetteer` | GeoNames places for IE + GB, with a trigram index on the ASCII name | `load_pilot --gazetteer-only` |
| `api_cache` | JSON cache with TTL, used when Redis is unreachable | `clients/cache.py` |
| `request_log` | Reserved for request logging (requests are currently logged to stdout only) | — |

A field is linked to the grid by `ST_Intersects`. Static values are **area-weighted** over the cells it overlaps, while the drainage class (an ordinal) and the risk counts come from the cell that covers most of the field.

---

## The ML package and its contract

`agrolens_ml` is the only place where weather is turned into indicators. The backend imports it and **never re-implements feature or rule code**, so the pilot tables (built offline) and a live point (computed in the API) cannot drift apart.

The **ML → Backend contract** is the `__all__` of [`ml/src/agrolens_ml/__init__.py`](ml/src/agrolens_ml/__init__.py) plus [`schemas.py`](ml/src/agrolens_ml/schemas.py):

- `CONTRACT_VERSION = "2.0"` and `RISK_RULES_VERSION = "counted-1"`.
- `count_risks(daily, elev_m, lat, drainage_class, monthly_rain_mm=None)` is the live path used by the API.
- `POWER_DAILY_PARAMETERS` is the exact POWER parameter list, shared by the download script and the API client.
- `power_daily_to_monthly`, `CELL_STATIC_KEYS`, `MONTHLY_INPUT_COLUMNS`, `RISK_TYPES`.
- `GRID_CELLS_SCHEMA`, `CELL_MONTH_SCHEMA`, `RISK_COUNTS_SCHEMA` and the `_MANIFEST.json` keys.
- The model interface (`StressModel`, `load_bundle`, `make_stub_bundle`) and `make_synthetic_tables`, kept for the optional ML add-on and for parallel development.

**Changing the surface** (a signature, a column, a schema) means bumping `CONTRACT_VERSION` and updating the synthetic tables and `ml/tests/contract/` **in one commit**, then re-running both sides' contract tests. Anything behind the surface (thresholds in `config.py`, feature engineering) can change freely. A threshold change must bump `RISK_RULES_VERSION`, so every response stays traceable to the rules that produced it.

```bash
make test-ml                                                  # ML unit tests, offline
make contract BUNDLE=ml/artifacts/stub_v0 DATA=data/synthetic # ML → Backend contract tests
```

`ml/artifacts/CURRENT` points at `stress_lgbm_v1`. That bundle is **not** loaded by the API since contract 2.0, and the API image contains no model.

---

## Building the real pilot data

The pilot data is built offline on a laptop. It needs a free [Earthdata Login](https://urs.earthdata.nasa.gov/users/new) for AppEEARS and earthaccess, and the training extras: `uv sync --all-packages --all-extras`. All outputs go to `data/raw/` and `data/processed/`.

```mermaid
flowchart TB
    A["01_power.py<br/>POWER daily per node, 2001–2025"] --> P1["power_daily.parquet<br/>power_nodes.csv · cell_to_power_node.csv"]
    B["02_soilgrids.py<br/>SoilGrids at 4,533 centroids"] --> P2["soil_cell.parquet"]
    C["10/11_appeears_*.py · 12_direct_landcover_srtm.py<br/>MODIS NDVI · MCD12Q1 · SRTM · SMAP"] --> R1["data/raw/appeears · data/raw/direct"]
    D["20_imerg.py<br/>GPM IMERG monthly"] --> P3["imerg_cell_month.parquet"]
    E["Irish SIS drainage (manual)"] --> R2["data/raw/irish_sis"]
    P1 & P2 & R1 & R2 --> G["cli grid → grid_cells.parquet<br/>(cells ≥ 30% agricultural)"]
    R1 --> L["cli labels → ndvi_cell_month.parquet"]
    P1 --> PM["cli power-monthly"]
    G & L & PM --> F["cli features → cell_month_features.parquet + _MANIFEST.json"]
    G & P1 & P3 --> RC["cli risk-counts → risk_counts.parquet"]
    F & RC --> LP["make load-pilot DATA=data/processed"]
```

```bash
# Downloads (submit AppEEARS first: its queue can take hours)
cp ml/pipelines/download/.env.example ml/pipelines/.env     # add Earthdata credentials
uv run python ml/pipelines/download/10_appeears_submit.py   # MODIS NDVI, land cover, SRTM, SMAP
uv run python ml/pipelines/download/01_power.py             # ~5–15 min, no login
uv run python ml/pipelines/download/02_soilgrids.py         # ~10–30 min, no login
uv run python ml/pipelines/download/03_met_eireann.py       # station ground truth
uv run python ml/pipelines/download/04_geonames.py
uv run python ml/pipelines/download/20_imerg.py             # optional but recommended (rain rescaling)
uv run python ml/pipelines/download/12_direct_landcover_srtm.py   # faster than the AppEEARS land-cover/SRTM jobs
uv run python ml/pipelines/download/11_appeears_download.py --wait
uv run python ml/pipelines/download/99_check.py             # what is on disk

# Processing
uv run --package agrolens-ml python -m agrolens_ml.cli power-monthly
uv run --package agrolens-ml python -m agrolens_ml.cli grid
uv run --package agrolens-ml python -m agrolens_ml.cli labels
uv run --package agrolens-ml python -m agrolens_ml.cli features
make risk-counts

# Load
make load-pilot DATA=data/processed
```

The Irish Soil Information System drainage map (EPA GIS downloads, *Soils*) is a manual download. Northern Ireland cells keep `drainage_class = null` and use the *moderate* parameters, which the app reports as an information gap. The download folder's own [README](ml/pipelines/download/README.md) (in Russian) has troubleshooting notes for AppEEARS and SoilGrids.

---

## Frontend

The SPA in [`frontend/`](frontend/) has two faces that share one build.

| Route | View | Contents |
|---|---|---|
| `/` | `HomeView` | Landing page: hero, audience cards, NASA coverage marquee and stats, *How it works*, data-provider strips, footer |
| `/app` | `WorkspaceView` | Field app before a field exists (step 1) |
| `/app/field/:id` | `WorkspaceView` | Guided steps and the answer. One persistent MapLibre map is never rebuilt between steps |
| `/app/…/maps` · `/words` · `/sources` | `WorkspaceView` | *More maps* (GIBS layers + risk grid by month), *What the words mean*, *Data and sources* |
| `/app/field/:id/print` | `PrintView` | One-page summary to print and bring to the advisor |

**The URL is the state.** Every answer is encoded in the query string, so browser *Back*, the in-app *Back* and a shared link all agree ([`src/lib/query.ts`](frontend/src/lib/query.ts)):

| Key | Meaning | Example |
|---|---|---|
| `s` | Step, 1–4 | `s=4` |
| `c` | Crop per year, oldest → newest, `-` = not sure | `c=-,winter_wheat,spring_barley,spring_barley` |
| `p` | Priorities in the order tapped | `p=income_stability,simplicity,soil_cover` |
| `k` | Yes/no answers: `ls1`/`ls0` livestock, `ct.<market>` contract, `x.<crop>` excluded | `k=ls1,ct.malting_barley,x.potatoes` |
| `m` | Month selected on the answer screen, 3–10 | `m=7` |

Other implementation notes:

- **Typed API.** `src/lib/api-types.ts` is generated from `backend/openapi.json` with `npm run gen:api`. `src/lib/api.ts` turns every failure into a plain sentence plus a next step, and warns in the console if the API's `contract_version` differs from the one the build expects (`2.0`).
- **Mocks.** `npm run dev:mock` serves `backend/tests/fixtures/api/*.json` through MSW. The mock code is a separate chunk that a normal build never loads.
- **Wording.** User-facing risk text comes from the API. All static interface copy lives in [`src/copy/en.ts`](frontend/src/copy/en.ts), so it can be reviewed for reading age in one place.
- **Theming.** The landing page has its own palette (forest, emerald, lime, Manrope + Atkinson Hyperlegible). The field app uses a shadcn-vue preset scoped under `html.theme-app`.
- **Accessibility.**
  - The A+ text scale (`useTextScale`, stored in `localStorage` under a try/catch) rescales the whole page, and the layout has safeguards so it never overflows at 125% or 150%.
  - `prefers-reduced-motion` is honoured, and `?static=1` freezes all motion for screenshots.
  - Colour is always paired with an icon and a word.
  - The landing page has been checked for horizontal overflow from 320 px to 2,560 px wide at every text size.

```bash
npm run dev          # http://localhost:5173, API proxied to :8080
npm run dev:mock     # no backend needed
npm run build        # vue-tsc type-check + production build into dist/
npm run test         # Vitest
npm run type-check
npm run gen:api      # regenerate API types after the backend contract changes
```

**No official logos.** Data sources (NASA missions, Met Éireann, Teagasc) are named in text only, so nothing implies an endorsement. The one logo on the site is the official NASA Space Apps Challenge 2026 logo in the footer ([`frontend/public/brand/SOURCES.md`](frontend/public/brand/SOURCES.md)).

---

## Testing and quality checks

| Suite | Command | Notes |
|---|---|---|
| ML unit tests | `make test-ml` | Offline. Covers ET0 against FAO-56, the SMD model and counting rules, the no-leakage guard, grid, labels, bundle and train/serve parity |
| ML → Backend contract | `make contract BUNDLE=… DATA=…` | Marker `contract`; checks the public surface, table schemas and the live path |
| Backend | `make test-backend` | `respx` mocks every external call (tests never hit the network). DB tests (marker `db`) are skipped when PostGIS is not running; marker `integration` runs counted-risk checks against the **real** tables when they are loaded |
| Frontend | `cd frontend && npm test` | Vitest: URL answers, field geometry, request payloads, month strip, option cards |
| Type check and build | `cd frontend && npm run build` | `vue-tsc -b && vite build` |
| Everything | `make check` | `test-ml` + `synthetic` + `contract` + `test-backend` + `compose-config` |
| Formatting | `uv run black --check backend ml` | Line length 100, Python 3.12 |
| Lint | `uv run pylint backend/app --disable=C` | |

**Contract artefacts are regenerated, never hand-edited:**

```bash
make openapi      # backend/openapi.json             (Backend → Frontend schema)
make fixtures     # backend/tests/fixtures/api/*.json (recorded responses used by tests and dev:mock)
cd frontend && npm run gen:api
```

---

## Operations

- **Health.** `GET /health/live` is used by the image's `HEALTHCHECK`. `GET /health/ready` returns 503 with a stable code (`db_unavailable`, `dataset_not_loaded`, `stub_model_in_prod`) when the service should not receive traffic.
- **Logs.** loguru writes one JSON line per request to stdout, with `request_id`, method, path, status and duration. Liveness and metrics calls are not logged.
- **Metrics.** `/metrics` exposes the Prometheus HTTP metrics plus `stress_model_predictions_total` (months scored), `external_api_errors_total{source}` and `cache_hits_total{layer}`.
- **Degraded mode.** If Redis is down, the cache falls back to the Postgres `api_cache` table, the Nominatim limit falls back to a per-process limiter, and `/health/ready` reports `cache: degraded`. The API keeps serving.
- **Upstream etiquette.**
  - POWER: requests are snapped to its 0.5° × 0.625° grid, so neighbouring fields share one cached response. Up to 3 attempts with exponential back-off, 20 s timeout.
  - Nominatim: one request per second for the whole app, never retried, search on submit only, identifying `User-Agent`, results cached for 30 days.
- **Shutdown.** Uvicorn has a 20 s graceful timeout and Compose has `stop_grace_period: 30s`.
- **Container.** The image runs as a non-root user (`app`, uid 10001) and uses BuildKit cache mounts. It contains no model bundle and no data.

## Running locally

GrowÉire runs on a local machine. Everything it needs is in the repository:

- a Compose stack ([`compose.yaml`](compose.yaml)) with `db`, `redis`, `migrate` and `api`, plus a `load-pilot` job under the `ops` profile. Every port is bound to `127.0.0.1` only;
- the API image ([`deploy/docker/api.Dockerfile`](deploy/docker/api.Dockerfile));
- the frontend, served by Vite (`npm run dev`), or built into `frontend/dist` and previewed with `npm run preview`.

See [Getting started](#getting-started) for the three ways to start it.

---

## Limitations

- **Weather is an area average.** POWER is about 50 km, and IMERG rescaling brings rain to about 10 km. The soil drainage is per cell. The answer is a risk indicator for the area, not a measurement of the field.
- **Crop sensitivities are first estimates** (`draft_unverified`) and have not been checked against field trials.
- **Ireland only, for the calibrated parts.** The pilot grid, the drainage model and the crop catalogue are Irish. Elsewhere, the same rules run on live weather without drainage, flagged `outside_pilot`.
- **Northern Ireland has no drainage class** in the soil map used. The moderate class is assumed and reported as a gap.
- **Place search** depends on the public Nominatim service (1 req/s). The GeoNames fallback must be loaded for it to help.
- **Photo credits to confirm before public release:** the landing-page photos came from the design prototype, and their source is not yet recorded.
- **No user accounts**, by design: the share link is the saved plan. A shared link reveals the field's location, and the app says so on the *Send* button.

## Roadmap

- **Validation.** Review the results and crop sensitivities with a Teagasc advisor. Check the counted months against Met Éireann station SMD and CSO yield years (2018, 2022, 2026).
- **More regions.** Add a regional pack per country (crop catalogue, rotation templates, soil drainage source, conditionality rules) on the same global core.
- **Richer evidence.** ECOSTRESS evaporative stress and GRACE-FO long-term water storage as context layers. VIIRS as the NDVI continuity product after MODIS.
- **Optional ML add-on.** Revisit a learned stress signal at field scale (HLS 30 m, Prithvi-EO embeddings) only if it beats the counted baseline on calibration as well as ranking.
- **Field testing.** Usability sessions with farmers aged 45–65: from link to three explained options in under five minutes, without help.

---

## Working on the code

- **Branches and commits.** Use feature branches (`feat/…`, `fix/…`, `docs/…`) and [Conventional Commits](https://www.conventionalcommits.org/) (`feat(backend): …`, `fix(frontend): …`, `feat!:` for breaking contract changes). `main` is protected and needs one approving review.
- **Backend imports** are rooted at `backend/app` (`from core.config import …`, not `from app.core…`). Always run with `PYTHONPATH=backend/app`; the Makefile does this for you.
- **Never invent agronomic facts.** A number shown to a farmer must come from `crops_ie.json` (with its `source`) or from a listed dataset. Unknown values are `null` and become information gaps.
- **Tests never hit the network.** Mock external HTTP with `respx`, using fixtures in `backend/tests/fixtures/`.
- **Changing wording** in `plain.yaml` changes what farmers read. The snapshot tests in `backend/tests/test_plain.py` must be updated deliberately.
- **Changing the API** means regenerating `openapi.json`, the fixtures and the frontend types in the same change (see [Testing](#testing-and-quality-checks)).
- **Secrets.** Never commit `.env`, `.netrc`, `.envs/.dev/` or `.envs/.prod/`, or Earthdata credentials.
- **Claude Code.** `.mcp.json` registers the shadcn-vue MCP server, and `.claude/skills/shadcn-vue/` holds its skill for adding UI components consistently.

## Acknowledgements and data attribution

- **NASA POWER:** *These data were obtained from the NASA Langley Research Center (LaRC) POWER Project funded through the NASA Earth Science/Applied Science Program.*
- **NASA GIBS:** *We acknowledge the use of imagery provided by services from NASA's Global Imagery Browse Services (GIBS), part of NASA's Earth Science Data and Information System (ESDIS).*
- **MODIS (MOD13Q1, MYD13Q1, MCD12Q1) and SRTMGL1:** NASA LP DAAC. **SMAP L4 (SPL4SMGP v8):** Reichle et al. (2025), NASA NSIDC DAAC, <https://doi.org/10.5067/T5RUATAQREF8>. **GPM IMERG V07:** NASA GES DISC.
- **SoilGrids 2.0:** ISRIC – World Soil Information (Poggio et al., 2021), CC BY 4.0.
- **Met Éireann:** *Copyright Met Éireann. Source www.met.ie. Published under CC BY 4.0. Data modified (aggregated) from the original.* Soil moisture deficit model after Schulte et al. (2005).
- **Irish Soil Information System:** Teagasc / EPA (Creamer et al., 2014).
- **Teagasc** rotation and cover-crop guidance; **FAO-56** (Allen et al., 1998) for ET0 and crop coefficients; **DAFM** conditionality rules.
- **OpenStreetMap** contributors (place search, basemap via OpenFreeMap); **GeoNames** (CC BY 4.0); **Natural Earth** (public domain).

The planning documents (product requirements, technical brief and per-track plans for ML, backend and frontend) were written for this project and record the original decisions. Where they describe the stress model as the main path, the code and this README reflect the later switch to counted risk (contract 2.0).

## Licence

No licence file has been added yet, so all rights are reserved by the authors by default. Add a `LICENSE` file (for example MIT or Apache-2.0) before the Space Apps submission if the project is to be reused. Third-party data keeps its own licence, listed above.
