"""Bounded remote-image ingestion for Office documents."""

from __future__ import annotations

from hashlib import sha256
from io import BytesIO
from ipaddress import ip_address
from pathlib import Path
import socket
from tempfile import NamedTemporaryFile
from typing import Annotated, Any
from urllib.parse import urlsplit

import httpx
from PIL import Image, UnidentifiedImageError
from pydantic import Field

from app.config import office_image_domains, office_input_dirs
from app.tools.office.paths import MAX_IMAGE_DIMENSION, MAX_IMAGE_PIXELS, resolve_image_path

MAX_DOWNLOAD_BYTES = 12 * 1024 * 1024
MAX_FETCH_IMAGES = 12
DEFAULT_MAX_WIDTH = 1600
DEFAULT_MAX_HEIGHT = 1200
_CACHE_DIR = ".office-images"


def fetch_images(
    urls: Annotated[list[str], Field(min_length=1, max_length=MAX_FETCH_IMAGES)],
    max_width: Annotated[int, Field(ge=320, le=2400)] = DEFAULT_MAX_WIDTH,
    max_height: Annotated[int, Field(ge=240, le=1800)] = DEFAULT_MAX_HEIGHT,
) -> list[dict[str, str | int]]:
    """Fetch HTTPS images, normalize them, and return guarded local paths.

    OFFICE_IMAGE_DOMAINS can optionally restrict hosts with a comma-separated
    allowlist. When unset, public HTTPS hosts are allowed. Every connected peer
    must still be a public IP; redirects and oversized responses are rejected.
    """
    timeout = httpx.Timeout(15.0, connect=5.0)
    limits = httpx.Limits(max_connections=4, max_keepalive_connections=2)
    with httpx.Client(
        follow_redirects=False,
        timeout=timeout,
        limits=limits,
        trust_env=False,
        headers={"User-Agent": "deep-agents-quick-office-images/1.0"},
    ) as client:
        return _fetch_batch(client, urls, max_width, max_height)


def _fetch_batch(
    client: Any, urls: list[str], max_width: int, max_height: int
) -> list[dict[str, str | int]]:
    results: list[dict[str, str | int]] = []
    for url in urls:
        try:
            results.append(_fetch_one(client, url, max_width, max_height))
        except ValueError as exc:
            results.append({"source_url": url, "error": str(exc)})
    return results


def _fetch_one(client: Any, url: str, max_width: int, max_height: int) -> dict[str, str | int]:
    host = _validate_url(url)
    _validate_resolved_host(host)
    try:
        with client.stream("GET", url) as response:
            if 300 <= response.status_code < 400:
                raise ValueError(f"Redirects are not allowed for remote images: {url!r}")
            _validate_connected_peer(response, url)
            response.raise_for_status()
            declared = response.headers.get("content-length")
            if declared is not None:
                try:
                    declared_size = int(declared)
                except ValueError as exc:
                    raise ValueError("Remote image returned an invalid Content-Length") from exc
                if declared_size < 0 or declared_size > MAX_DOWNLOAD_BYTES:
                    raise ValueError(f"Remote image exceeds the {MAX_DOWNLOAD_BYTES}-byte limit")
            payload = bytearray()
            for chunk in response.iter_bytes():
                payload.extend(chunk)
                if len(payload) > MAX_DOWNLOAD_BYTES:
                    raise ValueError(f"Remote image exceeds the {MAX_DOWNLOAD_BYTES}-byte limit")
    except httpx.HTTPError as exc:
        raise ValueError(f"Unable to fetch remote image {url!r}: {exc}") from exc

    normalized, width, height = _normalize_image(bytes(payload), max_width, max_height)
    digest = sha256(normalized).hexdigest()
    relative = Path(_CACHE_DIR) / f"{digest}.jpg"
    root = office_input_dirs()[0]
    destination = (root / relative).resolve()
    if not destination.is_relative_to(root):
        raise ValueError("Remote image cache escaped the Office input root")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        with NamedTemporaryFile(dir=destination.parent, suffix=".tmp", delete=False) as temp:
            temp.write(normalized)
            temporary = Path(temp.name)
        temporary.replace(destination)
    resolve_image_path(str(relative))
    return {
        "source_url": url,
        "image": str(relative),
        "sha256": digest,
        "width": width,
        "height": height,
        "bytes": len(normalized),
    }


def _validate_url(url: str) -> str:
    if len(url) > 2048:
        raise ValueError("Remote image URL is too long")
    parsed = urlsplit(url)
    if parsed.scheme.casefold() != "https" or not parsed.hostname:
        raise ValueError("Remote images require an absolute HTTPS URL")
    if parsed.username or parsed.password:
        raise ValueError("Remote image URLs cannot include credentials")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Remote image URL has an invalid port") from exc
    if port not in {None, 443}:
        raise ValueError("Remote image URLs must use HTTPS port 443")
    host = parsed.hostname.casefold().rstrip(".")
    domains = office_image_domains()
    if domains and not any(host == domain or host.endswith(f".{domain}") for domain in domains):
        raise ValueError(f"Remote image host {host!r} is not in OFFICE_IMAGE_DOMAINS")
    return host


def _validate_resolved_host(host: str) -> None:
    # This preflight and the connected-peer check bound response exposure, but
    # httpx performs its own resolution between them. A rebinding attacker can
    # still receive a blind GET at a private peer before that peer is rejected;
    # fully closing that window requires a custom IP-pinning transport with SNI.
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)}
    except socket.gaierror as exc:
        raise ValueError(f"Unable to resolve remote image host {host!r}") from exc
    if not addresses or any(not _is_public_address(address) for address in addresses):
        raise ValueError(f"Remote image host {host!r} resolves to a non-public address")


def _validate_connected_peer(response: Any, url: str) -> None:
    stream = response.extensions.get("network_stream")
    peer = stream.get_extra_info("server_addr") if stream is not None else None
    address = peer[0] if isinstance(peer, tuple) and peer else peer
    if not isinstance(address, str) or not _is_public_address(address):
        raise ValueError(f"Remote image connection for {url!r} did not use a public peer")


def _is_public_address(value: str) -> bool:
    try:
        address = ip_address(value.split("%", 1)[0])
    except ValueError:
        return False
    if getattr(address, "ipv4_mapped", None) is not None:
        address = address.ipv4_mapped
    return address.is_global


def _normalize_image(payload: bytes, max_width: int, max_height: int) -> tuple[bytes, int, int]:
    try:
        with Image.open(BytesIO(payload)) as image:
            width, height = image.size
            if (
                width <= 0
                or height <= 0
                or max(width, height) > MAX_IMAGE_DIMENSION
                or width * height > MAX_IMAGE_PIXELS
            ):
                raise ValueError(
                    f"Remote image is {width}x{height}; limits are "
                    f"{MAX_IMAGE_DIMENSION}px per side and {MAX_IMAGE_PIXELS} pixels"
                )
            image.load()
            converted = image.convert("RGB")
            converted.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            output = BytesIO()
            converted.save(output, format="JPEG", quality=85, optimize=True)
            return output.getvalue(), converted.width, converted.height
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("Remote response is not a supported image") from exc
