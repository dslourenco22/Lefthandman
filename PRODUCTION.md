# Production Deployment & Hardening Guide

This guide covers taking the Resume Ranking system from the runnable foundation in this
repo to a production deployment. It is organized by concern, with the highest-impact
hardening steps first.

---

## 1. Deployment topology

The included `docker-compose.yml` runs three services: `db` (Postgres), `backend`
(FastAPI/uvicorn), and `frontend` (nginx serving the built SPA and proxying `/api`).

For production:

1. **Put a TLS-terminating reverse proxy in front** (nginx, Traefik, Caddy, or a cloud
   load balancer). Never expose the backend on plain HTTP over the network.
2. **Pin image versions** and build in CI rather than on the host.
3. **Run multiple backend workers** behind the proxy:
   ```
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
   ```
   or run uvicorn under Gunicorn with the uvicorn worker class.
4. **Externalize the database.** For real workloads use a managed Postgres (RDS, Cloud
   SQL, etc.) instead of the in-compose container, and take regular backups.

---

## 2. Secrets and configuration

- Generate a strong `SECRET_KEY`:
  ```
  python -c "import secrets; print(secrets.token_urlsafe(64))"
  ```
- Never commit `.env`. Use your platform's secret manager (AWS Secrets Manager, GCP
  Secret Manager, Kubernetes Secrets, Docker secrets).
- Change the bootstrap admin password on first login, then disable or rotate the
  bootstrap credentials.
- Set `ACCESS_TOKEN_EXPIRE_MINUTES` to a sane value for your security posture.

---

## 3. Scaling resume processing to 500+ at once

The spec calls for 500+ resumes processed in under five minutes. The current
implementation queues parsing/scoring via FastAPI `BackgroundTasks`, which runs in the
web process — fine for moderate batches but not ideal for large bursts or horizontal
scale.

To scale out, move `process_batch()` (in `app/services/pipeline.py`) onto a real task
queue:

1. Add **Celery** (or **RQ**) with **Redis** or **RabbitMQ** as the broker.
2. Turn `process_candidate(candidate_id)` into a task; enqueue one task per resume in the
   upload router instead of calling `BackgroundTasks`.
3. Run a pool of workers (`celery -A app.worker worker --concurrency=8`). Throughput
   scales with worker count and CPU.
4. The status endpoint already derives progress from per-candidate DB status, so the UI
   progress bar keeps working unchanged.

**Embedding throughput tips:** load the `all-MiniLM-L6-v2` model once per worker (the
embeddings service already uses a thread-safe singleton), batch-encode where possible,
and consider a GPU node or an ONNX-optimized model if CPU latency dominates.

---

## 4. File upload security

This is the most important hardening gap to close before accepting untrusted files.

- **Virus scanning:** wire `scan_for_malware()` in `app/services/parsing.py` to a real
  scanner. The common pattern is a ClamAV daemon (`clamd`) reachable from the backend:
  add a `clamav/clamav` service to compose and call it from the hook. Reject on any hit.
- **Validation already present:** extension allow-list, size limit, and magic-byte
  sniffing. Keep these strict.
- **Isolation:** process uploads in a container with no outbound network and a read-only
  root filesystem where possible. Store uploads on a dedicated volume, not alongside code.
- **Limits:** enforce per-request and per-batch size caps at the proxy
  (`client_max_body_size` is set in `nginx.conf`) as well as in the app.

---

## 5. Protecting candidate data

Resumes are personal data and often fall under GDPR/CCPA and employment law.

- **Encryption in transit:** TLS everywhere (see topology).
- **Encryption at rest:** enable storage/volume encryption for the database and the
  uploads volume. For defense in depth, apply column-level encryption (e.g. pgcrypto or
  application-side envelope encryption) to PII columns on `Candidates`.
- **Retention:** define and enforce a retention policy; provide a deletion path for
  candidate data on request. The `AuditLogs` table supports accountability here.
- **Access:** the audit log records user actions; review it. Keep the admin role small.
- **Least privilege DB user:** the app's Postgres role should not be a superuser.

---

## 6. Authentication & access control

- JWT auth and admin/hr roles ship working; admin-only routes are enforced server-side.
- For production, consider: refresh tokens + short-lived access tokens, account lockout
  / rate limiting on login, and SSO (OIDC/SAML) integration if HR uses an IdP.
- Tighten CORS: `app/main.py` currently allows all origins for convenience. Restrict
  `allow_origins` to your actual frontend domain(s).

---

## 7. Observability

- **Logging:** ship structured logs to your aggregator. Audit entries already capture
  key actions.
- **Health checks:** `/api/health` is wired; point your orchestrator's liveness/readiness
  probes at it. The Postgres service has a healthcheck in compose.
- **Metrics & tracing:** add Prometheus metrics and OpenTelemetry tracing around the
  parsing/scoring pipeline to find bottlenecks under load.

---

## 8. Database migrations

Tables are auto-created on startup, which is convenient for dev but unsafe for evolving
a production schema. Before your first real deployment, introduce **Alembic**:

```
pip install alembic
alembic init migrations
# configure sqlalchemy.url from settings, autogenerate, review, apply
```

Then disable auto-create and manage all schema changes through reviewed migrations.

---

## 9. Pre-launch checklist

- [ ] Strong `SECRET_KEY` and DB password from a secret manager
- [ ] Bootstrap admin password changed; bootstrap creds rotated
- [ ] TLS terminating proxy in front of everything
- [ ] CORS restricted to known origins
- [ ] Virus scanning wired and tested
- [ ] Encryption at rest enabled (DB + uploads volume)
- [ ] Task queue + workers for large batches (if 500+ is a real requirement)
- [ ] Alembic migrations replacing auto-create
- [ ] Backups + restore tested
- [ ] Health probes and logging/metrics in place
- [ ] Bias/fairness review and legal sign-off for automated screening (see README)
