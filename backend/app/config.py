from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # API
    cors_origins: str = "http://localhost:5173,http://localhost:8080"

    # Database
    database_url: str = "postgresql+asyncpg://lebox:lebox@postgres:5432/lebox"

    # Auth
    auth_mode: Literal["dev", "cognito"] = "dev"
    # Dev shim
    dev_jwt_secret: str = "dev-secret-change-me"
    dev_jwt_issuer: str = "lebox-dev"
    dev_jwt_audience: str = "lebox-api"
    # Cognito
    cognito_region: str = ""
    cognito_user_pool_id: str = ""
    cognito_app_client_id: str = ""

    # Storage (S3 or MinIO)
    s3_bucket: str = "lebox"
    s3_region: str = "us-east-1"
    s3_endpoint_url: str | None = None  # set for MinIO; leave unset for real AWS
    # Endpoint the BROWSER will use when following presigned URLs. Different
    # from s3_endpoint_url when the backend reaches the bucket via an internal
    # hostname (e.g. "minio:9000" inside docker-compose) but the browser
    # has to use a host-routable name (e.g. "localhost:9000"). Defaults to
    # s3_endpoint_url when unset (correct for real AWS S3).
    s3_public_endpoint_url: str | None = None
    s3_access_key_id: str | None = None  # use IAM role in prod; static for local
    s3_secret_access_key: str | None = None
    s3_use_path_style: bool = True  # MinIO needs this

    # Upload thresholds
    multipart_threshold_bytes: int = 100 * 1024 * 1024  # 100 MB
    multipart_part_size_bytes: int = 10 * 1024 * 1024   # 10 MB
    presigned_url_ttl_seconds: int = 3600


settings = Settings()
