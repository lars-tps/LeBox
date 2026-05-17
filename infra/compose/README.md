# Local dev with Docker Compose

From this directory:

```bash
docker compose up --build
```

Then open:

- App: http://localhost:8080
- Backend API docs: http://localhost:8000/docs
- MinIO console: http://localhost:9001 (login: `minioadmin` / `minioadmin`)

The `minio-init` service creates the `lebox` bucket on first run. The backend
runs Alembic migrations on startup.

To wipe everything (including the database):

```bash
docker compose down -v
```
