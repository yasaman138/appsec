import pytest
from fastapi import HTTPException
from services.api.src.utils.network import validate_safe_url


def test_validate_safe_url_allows_public_https():
    # Valid external public URL format
    url = "https://example.com/webhook"
    assert validate_safe_url(url) == url


def test_validate_safe_url_rejects_non_http_schemes():
    with pytest.raises(HTTPException) as exc_info:
        validate_safe_url("file:///etc/passwd")
    assert exc_info.value.status_code == 400
    assert "scheme" in exc_info.value.detail.lower()

    with pytest.raises(HTTPException) as exc_info:
        validate_safe_url("gopher://127.0.0.1:70/1")
    assert exc_info.value.status_code == 400


def test_validate_safe_url_rejects_loopback():
    with pytest.raises(HTTPException) as exc_info:
        validate_safe_url("http://127.0.0.1:8000/health")
    assert exc_info.value.status_code == 400
    assert "restricted" in exc_info.value.detail.lower() or "blocked" in exc_info.value.detail.lower()

    with pytest.raises(HTTPException) as exc_info:
        validate_safe_url("http://localhost:8000/api")
    assert exc_info.value.status_code == 400


def test_validate_safe_url_rejects_private_subnets():
    # 10.0.0.0/8
    with pytest.raises(HTTPException) as exc_info:
        validate_safe_url("http://10.0.0.1/admin")
    assert exc_info.value.status_code == 400

    # 172.16.0.0/12
    with pytest.raises(HTTPException) as exc_info:
        validate_safe_url("http://172.16.0.5:8080/internal")
    assert exc_info.value.status_code == 400

    # 192.168.0.0/16
    with pytest.raises(HTTPException) as exc_info:
        validate_safe_url("http://192.168.1.1:80/router")
    assert exc_info.value.status_code == 400


def test_validate_safe_url_rejects_cloud_metadata():
    # AWS / GCP / Azure link-local metadata address
    with pytest.raises(HTTPException) as exc_info:
        validate_safe_url("http://169.254.169.254/latest/meta-data/")
    assert exc_info.value.status_code == 400
    assert "restricted" in exc_info.value.detail.lower() or "blocked" in exc_info.value.detail.lower()


def test_validate_safe_url_rejects_empty_or_malformed():
    with pytest.raises(HTTPException) as exc_info:
        validate_safe_url("")
    assert exc_info.value.status_code == 400

    with pytest.raises(HTTPException) as exc_info:
        validate_safe_url("not_a_valid_url")
    assert exc_info.value.status_code == 400


def test_resolve_and_validate_target_pins_ip_and_preserves_host_header():
    from services.api.src.utils.network import resolve_and_validate_target

    target = resolve_and_validate_target("http://93.184.216.34/webhook")
    assert target.hostname == "93.184.216.34"
    assert target.resolved_ip == "93.184.216.34"
    assert target.host_header == "93.184.216.34"
    assert target.pinned_url == "http://93.184.216.34/webhook"

