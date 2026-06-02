# Resume Ranking & Candidate Screening — Omni Control Technology

An applicant-screening tool that ranks resumes against a job description. HR uploads
a job description and a batch of resumes; the system parses each resume, scores it on a
configurable weighted rubric (with semantic skill matching), and returns a ranked list
of candidates with strengths, gaps, and an interview recommendation.

This repository is a **complete, runnable foundation**. The core screening pipeline —
parsing, skill normalization, semantic matching, weighted scoring, ranking, export, and
the dashboard — is fully implemented. A few enterprise-hardening items are scaffolded
with clear extension points rather than fully built out; they are listed honestly under
[What's implemented vs. scaffolded](#whats-implemented-vs-scaffolded) so you know exactly
what you're getting.

> **Please read [Responsible use](#responsible-use) before screening real candidates.**
> Automated resume ranking can encode bias. This tool is designed to *assist* a human
> reviewer, not replace one.

---

## Table of contents
- [Architecture](#architecture)
- [Quick start (Docker)](#quick-start-docker)
- [Local development (no Docker)](#local-development-no-docker)
- [How scoring works](#how-scoring-works)
- [API overview](#api-overview)
- [Sample data](#sample-data)
- [What's implemented vs. scaffolded](#whats-implemented-vs-scaffolded)
- [Responsible use](#responsible-use)
- [Project layout](#project-layout)

---

## Architecture

```
┌─────────────────┐      HTTP/JSON       ┌──────────────────────────┐
│  React + TS UI  │ ───────────────────> │      FastAPI backend      │
│  (MUI, Vite)    │ <─────────────────── │                           │
└─────────────────┘                      │  routers → services       │
                                         │   • parsing (pdf/docx/txt) │
                                         │   • nlp (spaCy + regex)    │
                                         │   • embeddings (MiniLM)    │
                                         │   • scoring (weighted)     │
                                         │   • export (csv/xlsx/pdf)  │
                                         └────────────┬──────────────┘
                                                      │ SQLAlchemy
                                                      ▼
                                              ┌───────────────┐
                                              │  PostgreSQL   │
                                              │  (SQLite for  │
                                              │   local dev)  │
                                              └───────────────┘
```

**Backend:** Python, FastAPI, Pydantic v2, SQLAlchemy. JWT auth with role-based access
(admin / hr). Resume text is extracted with pdfplumber + PyMuPDF (PDF), python-docx
(DOCX), and plain reads (TXT), then parsed with spaCy and targeted regex. Semantic
matching uses `sentence-transformers` (`all-MiniLM-L6-v2`).

**Frontend:** React + TypeScript, Material UI, built with Vite. Login, job setup with
configurable weight sliders, drag-and-drop bulk upload with live progress, a sortable /
searchable / filterable ranking table, a candidate detail drawer, side-by-side
comparison, and CSV / Excel / PDF export.

**Database:** PostgreSQL in production (via Docker Compose); SQLite by default for
zero-setup local runs. Tables: Users, JobDescriptions, Candidates, Resumes, Skills,
CandidateScores, CandidateComparisons, AuditLogs.

---

## Quick start (Docker)

The fastest path to a running system. Requires Docker and Docker Compose.

```bash
cp .env.example .env
# Edit .env: set a strong SECRET_KEY and POSTGRES_PASSWORD.

docker compose up --build
```

Then open:
- **Frontend:** http://localhost:8080
- **API docs (Swagger):** http://localhost:8000/api/docs
- **Health check:** http://localhost:8000/api/health

Sign in with the bootstrap admin from your `.env`
(default `admin@omnicontrol.com` / `ChangeMe123!`). **Change this immediately.**

> The backend image downloads the spaCy model and the MiniLM embedding model at build
> time, so the first `docker compose up --build` takes a few minutes. Subsequent starts
> are fast.

---

## Local development (no Docker)

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# Optional: copy ../.env.example to .env and adjust. Without it, the app uses
# a local SQLite file and the default bootstrap admin.
uvicorn app.main:app --reload --port 8000
```

The database tables are created automatically on startup, and a bootstrap admin is
created if the users table is empty.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The dev server proxies `/api` to `http://localhost:8000`,
so run the backend alongside it.

> **Graceful degradation:** if the spaCy or sentence-transformers models aren't present,
> the backend still runs — it falls back to regex-based name/entity extraction and a
> Jaccard token-overlap similarity instead of embeddings. Scores will be less nuanced
> (semantic matches like "Cybersecurity" ≈ "Information Security" weaken), but nothing
> crashes. Install the models for full-quality results.

---

## How scoring works

Each candidate gets an overall match percentage from a weighted sum of seven dimensions.
Default weights (configurable per job in the UI or via the API):

| Dimension       | Weight | What it measures                                         |
|-----------------|--------|----------------------------------------------------------|
| Skills          | 40%    | Required + preferred skill coverage, semantic-matched    |
| Experience      | 20%    | Years of experience vs. the job's minimum                |
| Education       | 10%    | Highest degree vs. the requirement                       |
| Certifications  | 10%    | Required/preferred certs present                         |
| Projects        | 10%    | Semantic relevance of projects to the role               |
| Soft skills     | 5%     | Communication, leadership, etc.                          |
| Keywords        | 5%     | Density of role/industry keywords                        |

Skill matching is **semantic, not just literal**. "C Plus Plus" normalizes to "c++",
"Azure" to "microsoft azure" (via `app/data/skill_aliases.json`), and beyond aliases,
embedding similarity lets related terms match even when worded differently.

Recommendation bands: **90–100 Highly Recommended · 80–89 Recommended ·
70–79 Potential Candidate · below 70 Low Match.** Each candidate also gets a short
generated rationale, strengths, and weaknesses.

Weights are validated and renormalized, so they don't have to sum to exactly 100.

---

## API overview

Interactive docs live at `/api/docs`. Key endpoints:

| Method | Path                                  | Purpose                              |
|--------|---------------------------------------|--------------------------------------|
| POST   | `/api/auth/login`                     | Get a JWT (OAuth2 form)              |
| GET    | `/api/auth/me`                        | Current user                         |
| POST   | `/api/auth/users`                     | Create user (admin only)             |
| POST   | `/api/jobs`                           | Create a job from pasted text        |
| POST   | `/api/jobs/upload`                    | Create a job from an uploaded file   |
| PUT    | `/api/jobs/{id}/weights`              | Update scoring weights               |
| POST   | `/api/jobs/{job_id}/resumes`          | Bulk-upload resumes (queues scoring) |
| GET    | `/api/jobs/{job_id}/resumes/status`   | Processing progress (poll this)      |
| GET    | `/api/jobs/{job_id}/ranking`          | Ranked candidates (+filters)         |
| GET    | `/api/jobs/{job_id}/candidates/{id}`  | Full candidate detail                |
| GET    | `/api/jobs/{job_id}/compare`          | Compare selected candidates          |
| GET    | `/api/jobs/{job_id}/export/{fmt}`     | Export csv / xlsx / pdf              |

---

## Sample data

`backend/seed_data/` contains a sample cybersecurity job description and five resumes
spanning strong, medium, and weak fit (e.g. a senior security engineer vs. a frontend
developer). Use them to exercise the pipeline end to end: create a job from
`job_description.txt`, then bulk-upload everything in `seed_data/resumes/`.

---

## What's implemented vs. scaffolded

**Fully implemented and working:**
- PDF / DOCX / TXT text extraction with fallbacks
- Resume parsing: contact info, skills, certs, education, experience, projects, languages
- Skill normalization (alias map) + semantic skill coverage
- Configurable weighted scoring across all seven dimensions
- Ranking with sort / search / filter
- Candidate detail, comparison, and recommendation rationale
- CSV / Excel / PDF export
- JWT auth + admin/hr roles + audit logging
- Dockerized deployment with Postgres

**Scaffolded with clear extension points (not production-complete):**
- **Virus scanning** — `scan_for_malware()` in `parsing.py` is a hook ready to wire to
  ClamAV; it currently passes files through. Wire it up before accepting untrusted uploads.
- **Background processing at 500+ scale** — uploads are processed with FastAPI
  `BackgroundTasks`, which works well for moderate batches. `process_batch()` is written
  to drop straight onto Celery or RQ for true horizontal scale; see the production guide.
- **Encryption at rest** — candidate PII is stored in plaintext columns. The production
  guide describes enabling Postgres/volume encryption and column-level encryption.
- **RBAC depth** — two roles exist and admin-only routes are enforced; fine-grained
  per-resource permissions would need extending.

These are called out so the system is honest about its boundaries rather than appearing
"done" where it isn't.

---

## Responsible use

Automated resume screening carries real fairness and legal risk. A few essentials:

- **Keep a human in the loop.** Use rankings to prioritize review, not to auto-reject.
- **Watch for bias.** Models can correlate with protected characteristics through proxies
  (names, schools, employment gaps). Audit outcomes across demographic groups.
- **Be transparent and compliant.** Several jurisdictions regulate automated employment
  decision tools (e.g. NYC Local Law 144, the EU AI Act). Confirm your obligations.
- **The score is a signal, not a verdict.** Strong candidates are routinely worded in
  ways a parser underweights. Treat low scores as "look closer," not "discard."

See `PRODUCTION.md` for the deployment and hardening guide.

---

## Project layout

```
resume-ranker/
├── backend/
│   ├── app/
│   │   ├── routers/       # auth, jobs, resumes, ranking, export
│   │   ├── services/      # parsing, nlp, embeddings, scoring, export, pipeline, audit
│   │   ├── data/          # skill_aliases.json
│   │   ├── models.py      # SQLAlchemy ORM (8 tables)
│   │   ├── schemas.py     # Pydantic schemas + default weights
│   │   ├── auth.py        # JWT + RBAC
│   │   ├── config.py      # settings
│   │   ├── database.py    # engine / session
│   │   └── main.py        # app factory, CORS, bootstrap
│   ├── seed_data/         # sample job + resumes
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/           # axios client + types
│   │   ├── components/    # JobPanel, ResumeUpload, RankingTable, CandidateDetail, CompareDialog
│   │   ├── pages/         # Login, Dashboard
│   │   └── theme/         # MUI theme
│   ├── Dockerfile
│   └── nginx.conf
├── docker-compose.yml
├── .env.example
├── README.md
└── PRODUCTION.md
```

> **A note on Tailwind:** the spec lists both MUI and Tailwind. The UI is built on MUI
> (theme, components, layout) for consistency; Tailwind isn't required and isn't wired in.
> If you want Tailwind utility classes alongside MUI, add `tailwindcss` to the frontend
> and import it in `main.tsx` — it layers cleanly on top.
