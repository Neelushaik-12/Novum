import json
import logging
import os
from functools import lru_cache
from typing import Any, Optional

from google.api_core import exceptions
from google.cloud import secretmanager

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _client() -> secretmanager.SecretManagerServiceClient:
    return secretmanager.SecretManagerServiceClient()


def _resolve_project_id(explicit_project: Optional[str] = None) -> Optional[str]:
    if explicit_project:
        return explicit_project
    return (
        os.getenv("GCP_PROJECT")
        or os.getenv("GOOGLE_CLOUD_PROJECT")
        or os.getenv("GCLOUD_PROJECT")
    )


@lru_cache(maxsize=256)
def get_secret(
    secret_id: str,
    *,
    project_id: Optional[str] = None,
    version: str = "latest",
    default: Optional[str] = None,
    required: bool = True,
) -> Optional[str]:
    """Return secret value, first honoring explicit env overrides.

    Args:
        secret_id: Secret identifier (matches Secret Manager ID and env var key).
        project_id: Optional GCP project override.
        version: Secret version (default 'latest').
        default: Fallback value returned when secret is not available.
        required: If True, raise on failure; otherwise return default.
    """
    env_override = os.getenv(secret_id)
    if env_override is not None:
        return env_override

    project = _resolve_project_id(project_id)
    if not project:
        msg = (
            f"Cannot resolve project for secret '{secret_id}'. "
            "Set GCP_PROJECT/GOOGLE_CLOUD_PROJECT or provide project_id."
        )
        if required and default is None:
            raise RuntimeError(msg)
        logger.warning(msg)
        return default

    name = f"projects/{project}/secrets/{secret_id}/versions/{version}"
    try:
        response = _client().access_secret_version(name=name)
        payload = response.payload.data.decode("utf-8")
        return payload
    except exceptions.NotFound:
        msg = f"Secret '{secret_id}' (version '{version}') not found in project '{project}'."
        if required and default is None:
            raise RuntimeError(msg)
        logger.warning(msg)
        return default
    except exceptions.GoogleAPICallError as exc:
        msg = f"Failed to access secret '{secret_id}': {exc}"
        if required and default is None:
            raise RuntimeError(msg)
        logger.warning(msg)
        return default


def get_secret_json(
    secret_id: str,
    *,
    project_id: Optional[str] = None,
    version: str = "latest",
    default: Optional[Any] = None,
    required: bool = True,
) -> Any:
    """Convenience wrapper that parses a secret as JSON."""
    value = get_secret(
        secret_id,
        project_id=project_id,
        version=version,
        default=default,
        required=required,
    )
    if value is None:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        msg = f"Secret '{secret_id}' does not contain valid JSON: {exc}"
        if required:
            raise ValueError(msg) from exc
        logger.warning(msg)
        return default

