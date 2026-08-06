"""Security and normalization tests for remote Office images."""

from __future__ import annotations

from io import BytesIO
import socket

from PIL import Image
import pytest

from app.tools.office import images


class _Stream:
    def __init__(self, address: str):
        self.address = address

    def get_extra_info(self, name: str):
        return (self.address, 443) if name == "server_addr" else None


class _Response:
    def __init__(self, chunks, *, status=200, address="93.184.216.34", headers=None):
        self._chunks = chunks
        self.status_code = status
        self.headers = headers or {}
        self.extensions = {"network_stream": _Stream(address)}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def raise_for_status(self):
        return None

    def iter_bytes(self):
        yield from self._chunks


class _Client:
    def __init__(self, response):
        self.response = response

    def stream(self, method, url):
        assert method == "GET"
        assert url.startswith("https://")
        return self.response


@pytest.fixture
def public_dns(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *_args, **_kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))],
    )


def _png(width=2400, height=1200) -> bytes:
    output = BytesIO()
    Image.new("RGB", (width, height), "#336699").save(output, format="PNG")
    return output.getvalue()


def test_fetch_normalizes_caches_and_reuses_existing_guard(public_dns, tmp_path):
    result = images._fetch_one(
        _Client(_Response([_png()])), "https://images.example.com/photo.webp", 800, 600
    )

    assert result["source_url"] == "https://images.example.com/photo.webp"
    assert result["image"].startswith(".office-images/")
    assert result["image"].endswith(".jpg")
    assert (result["width"], result["height"]) == (800, 400)
    cached = tmp_path / "in" / result["image"]
    assert cached.is_file()
    with Image.open(cached) as normalized:
        assert normalized.format == "JPEG"


@pytest.mark.parametrize(
    "url",
    [
        "http://images.example.com/a.jpg",
        "https://user:pass@images.example.com/a.jpg",
        "https://images.example.com:8443/a.jpg",
    ],
)
def test_url_boundary_rejects_unsafe_forms(url):
    with pytest.raises(ValueError):
        images._validate_url(url)


def test_domain_configuration_is_optional_but_narrows_hosts(monkeypatch):
    assert images._validate_url("https://anything.example/photo.jpg") == "anything.example"
    monkeypatch.setenv("OFFICE_IMAGE_DOMAINS", "media.example.com")
    assert images._validate_url("https://cdn.media.example.com/photo.jpg") == "cdn.media.example.com"
    with pytest.raises(ValueError, match="OFFICE_IMAGE_DOMAINS"):
        images._validate_url("https://anything.example/photo.jpg")


def test_preflight_rejects_any_non_public_dns_answer(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *_args, **_kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443)),
        ],
    )
    with pytest.raises(ValueError, match="non-public"):
        images._validate_resolved_host("images.example.com")


def test_connected_peer_check_blocks_dns_rebinding(public_dns):
    with pytest.raises(ValueError, match="public peer"):
        images._fetch_one(
            _Client(_Response([_png(10, 10)], address="169.254.169.254")),
            "https://images.example.com/a.jpg",
            800,
            600,
        )


def test_redirects_are_not_followed(public_dns):
    with pytest.raises(ValueError, match="Redirects are not allowed"):
        images._fetch_one(
            _Client(_Response([], status=302)), "https://images.example.com/a.jpg", 800, 600
        )


def test_streaming_limit_applies_without_content_length(public_dns, monkeypatch):
    monkeypatch.setattr(images, "MAX_DOWNLOAD_BYTES", 8)
    with pytest.raises(ValueError, match="8-byte limit"):
        images._fetch_one(
            _Client(_Response([b"1234", b"56789"])),
            "https://images.example.com/a.jpg",
            800,
            600,
        )


def test_missing_peer_metadata_fails_closed(public_dns):
    response = _Response([_png(10, 10)])
    response.extensions = {}
    with pytest.raises(ValueError, match="public peer"):
        images._fetch_one(
            _Client(response), "https://images.example.com/a.jpg", 800, 600
        )


def test_batch_preserves_successes_and_reports_each_failure(public_dns, monkeypatch):
    calls = []

    def fetch_one(_client, url, _max_width, _max_height):
        calls.append(url)
        if url.endswith("bad"):
            raise ValueError("not an image")
        return {"source_url": url, "image": ".office-images/good.jpg"}

    monkeypatch.setattr(images, "_fetch_one", fetch_one)
    results = images._fetch_batch(
        object(), ["https://example.com/good", "https://example.com/bad"], 800, 600
    )

    assert calls == ["https://example.com/good", "https://example.com/bad"]
    assert results == [
        {
            "source_url": "https://example.com/good",
            "image": ".office-images/good.jpg",
        },
        {"source_url": "https://example.com/bad", "error": "not an image"},
    ]


@pytest.mark.parametrize(
    "url", ["https://example.com:99999/a.jpg", "https://example.com:abc/a.jpg"]
)
def test_invalid_ports_use_normalized_error(url):
    with pytest.raises(ValueError, match="invalid port"):
        images._validate_url(url)
