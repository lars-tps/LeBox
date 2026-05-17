
## Docker Compose

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows/macOS) or Docker Engine + Compose plugin (Linux)

### Steps

```bash
cd infra/compose
docker compose up --build
```

When you see `Uvicorn running on http://0.0.0.0:8000`, open:

- **App**: http://localhost:8080
- **API docs (Swagger UI)**: http://localhost:8000/docs
- **MinIO console**: http://localhost:9001 (login `minioadmin` / `minioadmin`)

Sign in with any email — the dev shim accepts anything and gives you a JWT.
Each distinct email becomes a separate user with its own files.

To stop: `Ctrl+C`, then `docker compose down`.
To reset state (wipe DB + bucket): `docker compose down -v`.

## Updating dependencies

Both backend and frontend use lockfiles for reproducible builds. **Always
regenerate the lockfile before changing the Dockerfile install step**, or
the build will fail.

### Backend (Python)

Edit top-level deps in `backend/requirements.in`, then:

```bash
cd backend
python -m pip install --user pip-tools     # one-time
python -m piptools compile --generate-hashes --output-file=requirements.txt requirements.in
```

The Dockerfile uses `pip install --require-hashes --no-deps`, which refuses
to install anything not in `requirements.txt` with a matching SHA256.

### Frontend (Node)

```bash
cd frontend
npm install <new-package>     # updates package-lock.json automatically
```

The Dockerfile uses `npm ci`, which fails if `package-lock.json` is missing
or out of sync with `package.json`. Commit the lockfile.

### Pinned Docker image digests

The MinIO and mc images are pinned by digest, not just tag, in
`infra/compose/docker-compose.yml`. To upgrade: pull the new image, get its digest
(`docker inspect <image> --format '{{index .RepoDigests 0}}'`), update
both files.

---

## Troubleshooting

**Upload fails with "missing ETag header"** — this is the multipart upload
path; the browser needs to read each part's ETag, which requires
`ExposeHeaders: ETag` in the bucket's CORS config. MinIO's defaults usually
work; if not, configure CORS via `mc admin` or use the MinIO console.

**Upload fails with "NetworkError" or `ERR_NAME_NOT_RESOLVED`** — the
presigned URL the backend gave the browser uses a hostname the browser
can't reach. The backend reaches MinIO via an internal name (`minio:9000`
in compose, `minio.lebox.svc` in k8s); the browser needs a host-routable
name. Check the failed request URL in the browser's Network tab — it
should be `http://localhost:9000/...` (compose) or
`http://s3.lebox.localhost/...` (k8s). If it shows the internal hostname,
verify `S3_PUBLIC_ENDPOINT_URL` is set on the backend pod/container.