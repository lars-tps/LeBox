# LeBox

A small per-user cloud storage app — upload, download, organize files in
folders. Backend in Python (FastAPI), frontend in React, blobs in S3 (or
MinIO locally), metadata in Postgres.

This is a personal project which heavily uses Claude Code (Opus 4.7) to explore AI-assisted development.

## Demo

Login:

![hippo](https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExb2t3bmhraXZnZW94aWtyNTkxYXB4YnFtNXdlNTBheHEwbnV4ZHJreCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/pBjm4TUyuuRKs6UOTX/giphy.gif)

File upload/download:

![hippo](https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExeTh6emN1YnFxcTRwdjRhemg0anlmMDFnNHlpbWVzdWk0aG4zbDRraCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/Kqq6vhD4YjG9QutMtF/giphy.gif)

Folder creation:

![hippo](https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExM3NsYTduOW5teGhzMGNiZnVqb3Bud3Z1YjAzdmdweWFvdWV3MHMxaiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/hndB5RikfF6JpDLZYx/giphy.gif)

## Repo layout

```
backend/           FastAPI app + Alembic migrations + Dockerfile
frontend/          React + Vite + TypeScript + Dockerfile (multi-stage → nginx)
infra/
  compose/         docker-compose for local dev (no k8s needed)
DEPLOYMENT.md      ← step-by-step instructions for local deployment
```

## Architecture in one paragraph

The frontend is static files served by nginx, which also reverse-proxies
`/api` to the backend so the browser only ever sees one origin. The backend
authenticates the user (dev JWT shim locally, AWS Cognito in prod), stores
file/folder metadata in Postgres, and hands out short-lived **presigned S3
URLs** so the browser uploads/downloads bytes directly to/from S3 without
the backend in the data path. Files >100MB use S3 multipart upload (one
presigned URL per 10MB part) for resumability.

## Auth modes

The backend has two auth backends behind one `AUTH_MODE` env var:

- `dev` — backend issues + verifies its own HS256 JWTs. The frontend has a
  simple "enter your email" form. **Local development only.**
- `cognito` — backend verifies JWTs issued by an AWS Cognito user pool.
  The frontend uses Cognito Hosted UI / Amplify SDK to log in.

## Extending later

- **Sharing**: add a `permissions` table and update `app/permissions.py` —
  the rest of the code already routes every authz check through that
  single function.
- **More auth providers**: add a new module under `app/auth/` and a branch
  in `app/auth/dependencies.py::_verify_token`.
