from __future__ import annotations

import ipaddress
from urllib.parse import urlparse

from app.core.config import Settings


class SecurityValidationError(ValueError):
    pass


def validate_public_http_url(url: str, settings: Settings) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise SecurityValidationError("Only http and https URLs can be ingested.")
    if not parsed.hostname:
        raise SecurityValidationError("URL must include a hostname.")
    if settings.allow_private_web_ingest:
        return

    host = parsed.hostname.strip().lower()
    if host in {"localhost", "127.0.0.1", "::1"} or host.endswith(".localhost"):
        raise SecurityValidationError("Private or localhost URLs are not allowed.")

    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return
    if (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    ):
        raise SecurityValidationError("Private or non-routable IP URLs are not allowed.")


def validate_upload(filename: str, raw: bytes, settings: Settings) -> None:
    if len(raw) > settings.max_upload_bytes:
        raise SecurityValidationError(
            f"Upload exceeds {settings.max_upload_bytes} bytes."
        )
    suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else "txt"
    if suffix not in settings.upload_extensions:
        raise SecurityValidationError(f"Unsupported upload extension: {suffix}.")
